#!/usr/bin/env python3 -u
"""
TFT Autonomous Evolution Loop
Queue → Accept → Wait for game → Run agent → Exit → Repeat
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, time, json, subprocess, signal
os.environ["PYTHONWARNINGS"] = "ignore"

import requests, urllib3; urllib3.disable_warnings()
from requests.auth import HTTPBasicAuth

LEAGUE_PATH = '/Applications/League of Legends (PBE).app/Contents/LoL'
HISTORY = os.path.expanduser('~/intelligent-tft/game_history.jsonl')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_auth():
    try:
        with open(os.path.join(LEAGUE_PATH, 'lockfile')) as f:
            parts = f.read().split(':')
            return parts[3], f"https://127.0.0.1:{parts[2]}"
    except:
        return None, None

def lcu_get(ep, token, url):
    try:
        return requests.get(url + ep, auth=HTTPBasicAuth('riot', token),
                          timeout=10, verify=False)
    except: return None

def lcu_post(ep, token, url, data=None):
    try:
        return requests.post(url + ep, json=data, auth=HTTPBasicAuth('riot', token),
                           timeout=10, verify=False)
    except: return None

def get_phase():
    token, url = get_auth()
    if not token: return "NoClient", None, None
    r = lcu_get('/lol-gameflow/v1/session', token, url)
    if r and r.status_code == 200:
        return r.json().get("phase", "Unknown"), token, url
    return "Unknown", token, url

def game_api_alive():
    try:
        r = requests.get('https://127.0.0.1:2999/liveclientdata/allgamedata',
                        timeout=3, verify=False)
        return r.status_code == 200
    except: return False

def queue_and_accept():
    """Queue into TFT, accept match, return True when in game"""
    print("🎮 Queuing...")
    for attempt in range(3):
        token, url = get_auth()
        if not token:
            print("  No client, waiting...")
            time.sleep(10); continue

        phase, token, url = get_phase()
        print(f"  Phase: {phase}")

        if phase == "EndOfGame":
            # Use early-exit API (not process quit!)
            lcu_post('/lol-gameflow/v1/early-exit', token, url)
            time.sleep(5)
            phase, token, url = get_phase()
            print(f"  After exit: {phase}")

        if phase in ("None", "Lobby", "Unknown"):
            lcu_post('/lol-lobby/v2/lobby/', token, url, {"queueId": 1090})
            time.sleep(2)
            lcu_post('/lol-lobby/v2/lobby/matchmaking/search', token, url)
            print("  Queue started")
            time.sleep(2)

        # Accept loop (3 min timeout)
        for i in range(180):
            lcu_post('/lol-matchmaking/v1/ready-check/accept', token, url)
            phase, _, _ = get_phase()

            if phase == "InProgress":
                print(f"  ✅ In game! ({i}s)")
                return True

            if phase in ("None", "Lobby") and i > 10:
                # Re-queue
                lcu_post('/lol-lobby/v2/lobby/', token, url, {"queueId": 1090})
                time.sleep(2)
                lcu_post('/lol-lobby/v2/lobby/matchmaking/search', token, url)

            if i % 15 == 0 and i > 0:
                print(f"  [{i}s] {phase}")
            time.sleep(1)

    print("❌ Queue failed after 3 attempts")
    return False

def wait_for_game_ready():
    """Wait for game window + API to be ready"""
    print("  Waiting for game to load...")
    for i in range(90):
        if game_api_alive():
            print(f"  Game ready ({i}s)")
            return True
        time.sleep(2)
    print("  ⚠️ Game API never came up")
    return False

def run_agent():
    """Run agent.py, stream output, return when done"""
    print("🤖 Agent starting...")
    proc = subprocess.Popen(
        [sys.executable, '-u', 'agent.py'],
        cwd=SCRIPT_DIR,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    while proc.poll() is None:
        line = proc.stdout.readline()
        if line: print(f"  {line.rstrip()}")
    for line in proc.stdout:
        print(f"  {line.rstrip()}")
    print(f"  Agent exited ({proc.returncode})")

def exit_game():
    """Exit finished game via API"""
    print("🚪 Exiting game...")
    # Wait for game to actually end
    for i in range(30):
        if not game_api_alive():
            break
        time.sleep(2)

    # Use early-exit API
    token, url = get_auth()
    if token:
        lcu_post('/lol-gameflow/v1/early-exit', token, url)
        time.sleep(3)
        phase, _, _ = get_phase()
        print(f"  Phase after exit: {phase}")

        # If still EndOfGame, try again
        if phase == "EndOfGame":
            lcu_post('/lol-gameflow/v1/early-exit', token, url)
            time.sleep(5)

def print_stats():
    if not os.path.exists(HISTORY): return
    with open(HISTORY) as f:
        games = [json.loads(l) for l in f if l.strip()]
    if not games: return
    recent = games[-10:]
    avg = sum(g["placement"] for g in recent) / len(recent)
    best = min(g["placement"] for g in recent)
    top4 = sum(1 for g in recent if g["placement"] <= 4)
    print(f"📊 {len(games)} games | Last {len(recent)}: avg={avg:.1f} best={best} top4={top4}/{len(recent)}")

# ═══ MAIN LOOP ═══
if __name__ == "__main__":
    print("═══ TFT Evolution Loop ═══")
    print("Goal: Keep playing until consistent top 4\n")

    game_num = 0
    while True:
        game_num += 1
        print(f"\n{'='*50}")
        print(f"  GAME {game_num}")
        print(f"{'='*50}")
        print_stats()

        # Step 1: Queue
        if not queue_and_accept():
            time.sleep(30)
            continue

        # Step 2: Wait for game
        time.sleep(8)
        if not wait_for_game_ready():
            time.sleep(15)
            continue

        # Step 3: Play
        time.sleep(3)
        run_agent()

        # Step 4: Exit
        exit_game()

        # Step 5: Brief pause
        print_stats()
        print("⏰ Next game in 10s...")
        time.sleep(10)
