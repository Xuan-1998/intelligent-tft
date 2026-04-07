#!/usr/bin/env python3 -u
"""TFT Autonomous Evolution Loop — queue, play, review, repeat.
Finds LCU credentials from process args. Handles full game lifecycle.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, time, subprocess, re
os.environ["PYTHONWARNINGS"] = "ignore"

import requests, urllib3; urllib3.disable_warnings()
from requests.auth import HTTPBasicAuth

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.expanduser("~/intelligent-tft/game_history.jsonl")


def get_lcu():
    """Extract LCU auth token and port from running LeagueClient process."""
    try:
        out = subprocess.check_output(["ps", "aux"], text=True)
        for line in out.split("\n"):
            if "LeagueClientUx" in line and "--app-port=" in line:
                port = re.search(r"--app-port=(\d+)", line)
                token = re.search(r"--remoting-auth-token=(\S+)", line)
                if port and token:
                    return token.group(1), int(port.group(1))
    except:
        pass
    return None, None


def lcu_get(endpoint, token, port):
    try:
        r = requests.get(f"https://127.0.0.1:{port}{endpoint}",
                         auth=HTTPBasicAuth("riot", token), timeout=10, verify=False)
        return r
    except:
        return None


def lcu_post(endpoint, token, port, data=None):
    try:
        r = requests.post(f"https://127.0.0.1:{port}{endpoint}",
                          json=data, auth=HTTPBasicAuth("riot", token), timeout=10, verify=False)
        return r
    except:
        return None


def get_phase(token, port):
    r = lcu_get("/lol-gameflow/v1/session", token, port)
    if r and r.status_code == 200:
        return r.json().get("phase", "Unknown")
    return "None"


def game_api_alive():
    try:
        r = requests.get("https://127.0.0.1:2999/liveclientdata/allgamedata",
                          timeout=3, verify=False)
        return r.status_code == 200
    except:
        return False


def queue_and_accept(token, port):
    """Queue into TFT and accept match. Returns True when InProgress."""
    phase = get_phase(token, port)
    print(f"  Client phase: {phase}")

    # If still in game (spectating after death), exit
    if phase == "InProgress" and not game_api_alive():
        # Game API down but client says InProgress = stuck spectating
        # Just wait for it to end
        print("  Waiting for game to fully end...")
        for _ in range(120):
            if get_phase(token, port) != "InProgress":
                break
            time.sleep(2)
        phase = get_phase(token, port)

    if phase == "InProgress" and game_api_alive():
        print("  Already in game!")
        return True

    # Create TFT lobby if needed
    if phase in ("None", "Lobby", "EndOfGame", "PreEndOfGame", "WaitingForStats", "Unknown"):
        lcu_post("/lol-lobby/v2/lobby/", token, port, {"queueId": 1090})
        time.sleep(2)

    # Start queue
    phase = get_phase(token, port)
    if phase == "Lobby":
        lcu_post("/lol-lobby/v2/lobby/matchmaking/search", token, port)
        print("  Queue started")
        time.sleep(1)

    # Fast accept loop (5 min timeout)
    print("  Waiting for match...")
    for i in range(600):
        lcu_post("/lol-matchmaking/v1/ready-check/accept", token, port)
        phase = get_phase(token, port)

        if phase == "InProgress":
            print("  ✅ Game started!")
            return True

        # Re-queue if dropped
        if phase in ("None", "Lobby"):
            lcu_post("/lol-lobby/v2/lobby/", token, port, {"queueId": 1090})
            time.sleep(1)
            lcu_post("/lol-lobby/v2/lobby/matchmaking/search", token, port)

        if i % 20 == 0 and i > 0:
            print(f"  Still waiting... ({phase}, {i//2}s)")

        time.sleep(0.5)

    print("  ❌ Queue timeout")
    return False


def wait_for_game_api():
    """Wait for in-game API to come up (loading screen)."""
    print("  Waiting for game to load...")
    for i in range(90):
        if game_api_alive():
            print("  Game loaded!")
            return True
        time.sleep(2)
    print("  ❌ Game API never came up")
    return False


def run_agent():
    """Run agent.py, stream output, return when done."""
    print("🤖 Starting agent...")
    proc = subprocess.Popen(
        [sys.executable, "-u", "agent.py"],
        cwd=SCRIPT_DIR,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    while proc.poll() is None:
        line = proc.stdout.readline()
        if line:
            print(f"  [agent] {line.rstrip()}")
    for line in proc.stdout:
        print(f"  [agent] {line.rstrip()}")
    return proc.returncode


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE) as f:
        return [json.loads(l) for l in f if l.strip()]


def print_summary():
    hist = load_history()
    if not hist:
        print("📊 No games yet")
        return
    recent = hist[-10:]
    avg = sum(g["placement"] for g in recent) / len(recent)
    best = min(g["placement"] for g in recent)
    top4 = sum(1 for g in recent if g["placement"] <= 4)
    print(f"📊 Last {len(recent)} games: avg={avg:.1f} best={best} top4={top4}/{len(recent)}")
    for g in recent[-5:]:
        print(f"  {g['time']} → #{g['placement']}")


# ═══════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════
if __name__ == "__main__":
    print("═══ TFT Autonomous Evolution Loop ═══")
    print("Press Ctrl+C to stop\n")

    game_num = 0
    while True:
        game_num += 1
        print(f"\n{'='*50}")
        print(f"  GAME {game_num}")
        print(f"{'='*50}")
        print_summary()

        # Find LCU credentials
        token, port = get_lcu()
        if not token:
            print("❌ LeagueClient not running. Waiting 30s...")
            time.sleep(30)
            continue
        print(f"  LCU: port={port}")

        # Queue
        if not queue_and_accept(token, port):
            print("⚠️ Queue failed, retrying in 15s...")
            time.sleep(15)
            continue

        # Wait for game to load
        time.sleep(5)
        if not wait_for_game_api():
            print("⚠️ Game didn't load, retrying...")
            time.sleep(10)
            continue

        # Play
        time.sleep(3)
        run_agent()

        # If game still running (agent crashed), wait for it to end
        if game_api_alive():
            print("⏳ Agent exited but game still running, waiting...")
            for _ in range(300):
                if not game_api_alive():
                    break
                time.sleep(3)

        # Wait for client to return to lobby
        print("  Waiting for lobby...")
        for _ in range(60):
            phase = get_phase(token, port)
            if phase in ("None", "Lobby", "EndOfGame", "PreEndOfGame"):
                break
            time.sleep(2)

        print_summary()
        print("⏰ Next game in 5s...")
        time.sleep(5)
