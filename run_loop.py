#!/usr/bin/env python3 -u
"""
TFT Autonomous Evolution Loop
1. Click PLAY AGAIN / queue via LCU API
2. Accept match
3. Wait for game window
4. Run agent.py
5. Detect game end
6. Review logs, repeat
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, time, subprocess, signal
os.environ["PYTHONWARNINGS"] = "ignore"

import pyautogui
import requests, urllib3; urllib3.disable_warnings()
from requests.auth import HTTPBasicAuth

pyautogui.FAILSAFE = False

LEAGUE_PATH = '/Applications/League of Legends (PBE).app/Contents/LoL'
HISTORY_FILE = os.path.expanduser('~/intelligent-tft/game_history.jsonl')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_client():
    """Read LCU lockfile for auth token + port"""
    try:
        with open(os.path.join(LEAGUE_PATH, 'lockfile'), 'r') as f:
            parts = f.read().split(':')
            return parts[3], f"https://127.0.0.1:{parts[2]}"
    except:
        return None, None


def lcu(method, endpoint, token, url, data=None):
    try:
        auth = HTTPBasicAuth('riot', token)
        if method == 'post':
            return requests.post(url + endpoint, json=data, auth=auth, timeout=10, verify=False)
        return requests.get(url + endpoint, auth=auth, timeout=10, verify=False)
    except:
        return None


def game_api_alive():
    """Check if in-game API is responding (= game is running)"""
    try:
        r = requests.get('https://127.0.0.1:2999/liveclientdata/allgamedata', timeout=3, verify=False)
        return r.status_code == 200
    except:
        return False


def get_gameflow_phase(token, url):
    """Get current client phase: Lobby, Matchmaking, ReadyCheck, ChampSelect, InProgress, EndOfGame, None"""
    r = lcu('get', '/lol-gameflow/v1/session', token, url)
    if r and r.status_code == 200:
        return r.json().get("phase", "Unknown")
    return "None"


def click_play_again():
    """Click the PLAY AGAIN button on the end-of-game screen"""
    print("  Clicking PLAY AGAIN...")
    pyautogui.click(590, 683)
    time.sleep(2)


def queue_and_accept():
    """Queue into a TFT game via LCU API"""
    print("🎮 Queuing into TFT...")
    token, url = None, None

    # Wait for client
    for _ in range(60):
        token, url = get_client()
        if token: break
        print("  Waiting for client...")
        time.sleep(5)
    if not token:
        print("❌ Client not found")
        return False

    phase = get_gameflow_phase(token, url)
    print(f"  Client phase: {phase}")

    if phase == "EndOfGame":
        click_play_again()
        time.sleep(3)
        phase = get_gameflow_phase(token, url)

    if phase in ("None", "Lobby", "Unknown"):
        # Create TFT lobby
        lcu('post', '/lol-lobby/v2/lobby/', token, url, {"queueId": 1090})
        time.sleep(2)
        # Start queue
        lcu('post', '/lol-lobby/v2/lobby/matchmaking/search', token, url)
        print("  Queue started")
        time.sleep(2)

    # Accept and wait for game (5 min timeout)
    print("  Waiting for match...")
    for i in range(300):
        # Keep accepting
        lcu('post', '/lol-matchmaking/v1/ready-check/accept', token, url)

        phase = get_gameflow_phase(token, url)
        if phase == "InProgress":
            print("  ✅ Game started!")
            return True

        # If we fell out of queue, re-queue
        if phase in ("None", "Lobby"):
            lcu('post', '/lol-lobby/v2/lobby/', token, url, {"queueId": 1090})
            time.sleep(2)
            lcu('post', '/lol-lobby/v2/lobby/matchmaking/search', token, url)

        time.sleep(1)

    print("❌ Queue timeout")
    return False


def wait_for_game_window():
    """Wait for the League game window to appear"""
    print("  Waiting for game window...")
    from game import find_league_window
    for _ in range(90):
        w = find_league_window()
        if w:
            print(f"  Window found: {w}")
            return True
        time.sleep(2)
    return False


def run_agent():
    """Run agent.py as subprocess, return when it exits"""
    print("🤖 Starting agent...")
    proc = subprocess.Popen(
        [sys.executable, '-u', 'agent.py'],
        cwd=SCRIPT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    # Stream output in real-time
    while proc.poll() is None:
        line = proc.stdout.readline()
        if line:
            print(f"  [agent] {line.rstrip()}")

    # Drain remaining output
    for line in proc.stdout:
        print(f"  [agent] {line.rstrip()}")

    print(f"  Agent exited with code {proc.returncode}")
    return proc.returncode


def wait_for_game_end():
    """Wait for game to end by monitoring the API"""
    print("⏳ Monitoring game...")
    consecutive_fails = 0
    while True:
        if game_api_alive():
            consecutive_fails = 0
        else:
            consecutive_fails += 1
            if consecutive_fails >= 5:
                print("  Game API gone — game ended")
                return
        time.sleep(3)


def load_history():
    if not os.path.exists(HISTORY_FILE): return []
    with open(HISTORY_FILE) as f:
        return [json.loads(l) for l in f if l.strip()]


def print_evolution_summary():
    hist = load_history()
    if not hist:
        print("📊 No game history yet")
        return
    recent = hist[-10:]
    avg = sum(g["placement"] for g in recent) / len(recent)
    best = min(g["placement"] for g in recent)
    worst = max(g["placement"] for g in recent)
    top4 = sum(1 for g in recent if g["placement"] <= 4)
    print(f"📊 Last {len(recent)} games: avg={avg:.1f} best={best} worst={worst} top4={top4}/{len(recent)}")


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
        print_evolution_summary()

        # Step 1: Queue
        if not queue_and_accept():
            print("⚠️ Queue failed, retrying in 30s...")
            time.sleep(30)
            continue

        # Step 2: Wait for game window
        time.sleep(10)  # loading screen buffer
        if not wait_for_game_window():
            print("⚠️ No game window, retrying...")
            time.sleep(10)
            continue

        # Step 3: Run agent
        time.sleep(5)  # let game fully load
        run_agent()

        # Step 4: If agent exited but game still running, wait for it to end
        if game_api_alive():
            wait_for_game_end()

        # Step 5: Summary
        print_evolution_summary()

        # Step 6: Brief pause before next game
        print("⏰ Next game in 10s...")
        time.sleep(10)
