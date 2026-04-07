#!/usr/bin/env python3 -u
"""Full autonomous TFT loop: queue → play → exit → repeat.
Run this and go to sleep. It will keep playing and logging results.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, time, json, subprocess, signal
os.environ["PYTHONWARNINGS"] = "ignore"

import pyautogui
import requests, urllib3; urllib3.disable_warnings()
from requests.auth import HTTPBasicAuth

pyautogui.FAILSAFE = False

LEAGUE_PATH = '/Applications/League of Legends (PBE).app/Contents/LoL'
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.expanduser('~/intelligent-tft/game_history.jsonl')

# ── LCU helpers ──
def get_lcu():
    try:
        with open(os.path.join(LEAGUE_PATH, 'lockfile'), 'r') as f:
            parts = f.read().split(':')
            return parts[3], f"https://127.0.0.1:{parts[2]}"
    except: return None, None

def lcu_phase():
    token, url = get_lcu()
    if not token: return "NoClient"
    try:
        auth = HTTPBasicAuth('riot', token)
        r = requests.get(url + '/lol-gameflow/v1/session', auth=auth, timeout=10, verify=False)
        return r.json().get('phase', 'Unknown')
    except: return "Error"

def lcu_post(endpoint, data=None):
    token, url = get_lcu()
    if not token: return None
    auth = HTTPBasicAuth('riot', token)
    return requests.post(url + endpoint, json=data, auth=auth, timeout=10, verify=False)

def game_api_up():
    try:
        r = requests.get('https://127.0.0.1:2999/liveclientdata/allgamedata', timeout=3, verify=False)
        return r.status_code == 200
    except: return False

# ── Game flow ──
def click_find_match():
    """Click FIND MATCH button in lobby"""
    print("  Clicking FIND MATCH...")
    pyautogui.click(608, 673)
    time.sleep(2)

def exit_dead_game():
    """When dead and spectating, press Esc → click Exit Game"""
    print("  Exiting dead game...")
    # Press Escape to open options
    pyautogui.press('escape')
    time.sleep(2)
    # Click Exit Game button (bottom-left of options dialog)
    # Try multiple positions to be safe
    for cx, cy in [(443, 653), (440, 650), (445, 655), (443, 648)]:
        pyautogui.click(cx, cy)
        time.sleep(0.5)
    time.sleep(5)

def queue_and_accept():
    """Get into a game. Returns True when in game."""
    print("🎮 Queuing...")

    for attempt in range(3):
        p = lcu_phase()
        print(f"  Phase: {p}")

        if p == "InProgress":
            return True

        if p == "EndOfGame":
            # Click through end-of-game screen
            pyautogui.click(608, 673)
            time.sleep(5)
            continue

        if p in ("Lobby", "None", "Unknown"):
            # Start queue
            lcu_post('/lol-lobby/v2/lobby/', {"queueId": 1090})
            time.sleep(2)
            lcu_post('/lol-lobby/v2/lobby/matchmaking/search')
            time.sleep(2)
            break

        time.sleep(3)

    # Poll for accept (3 min timeout)
    print("  Waiting for match...")
    for i in range(180):
        lcu_post('/lol-matchmaking/v1/ready-check/accept')
        p = lcu_phase()
        if p == "InProgress":
            print(f"  ✅ In game! ({i}s)")
            return True
        if p in ("None", "Lobby"):
            # Re-queue if we fell out
            lcu_post('/lol-lobby/v2/lobby/', {"queueId": 1090})
            time.sleep(2)
            lcu_post('/lol-lobby/v2/lobby/matchmaking/search')
        if i % 15 == 0:
            print(f"  [{i}s] {p}")
        time.sleep(1)

    print("  ❌ Queue timeout")
    return False

def wait_for_game_api():
    """Wait for in-game API to come up"""
    print("  Waiting for game API...")
    for i in range(90):
        if game_api_up():
            print(f"  API ready ({i*2}s)")
            return True
        time.sleep(2)
    return False

def run_agent():
    """Run agent.py, stream output, return when done"""
    print("🤖 Starting agent...")
    proc = subprocess.Popen(
        [sys.executable, '-u', 'agent.py'],
        cwd=SCRIPT_DIR,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    game_over = False
    start = time.time()
    while time.time() - start < 1800:  # 30 min max per game
        line = proc.stdout.readline()
        if line:
            print(f"  [bot] {line.rstrip()}")
            if 'Game over' in line or 'Placement' in line:
                game_over = True
                time.sleep(2)
                break
        if not line and proc.poll() is not None:
            break

    # Clean up
    if proc.poll() is None:
        proc.send_signal(signal.SIGINT)
        try: proc.wait(timeout=5)
        except: proc.kill()
    for line in proc.stdout:
        print(f"  [bot] {line.rstrip()}")

    return game_over

def wait_for_game_end():
    """If agent exited but game still running (spectating), exit it"""
    print("  Checking if still in game...")
    for _ in range(10):
        if not game_api_up():
            return
        time.sleep(3)
    # Still in game = we're dead and spectating
    exit_dead_game()
    # Wait for game to fully close
    for _ in range(30):
        if not game_api_up():
            return
        time.sleep(3)

def print_stats():
    if not os.path.exists(HISTORY_FILE): return
    with open(HISTORY_FILE) as f:
        hist = [json.loads(l) for l in f if l.strip()]
    if not hist: return
    recent = hist[-10:]
    avg = sum(g["placement"] for g in recent) / len(recent)
    best = min(g["placement"] for g in recent)
    top4 = sum(1 for g in recent if g["placement"] <= 4)
    print(f"📊 Last {len(recent)} games: avg={avg:.1f} best={best} top4={top4}/{len(recent)}")
    for g in recent[-5:]:
        print(f"    {g.get('time','')} → #{g['placement']}")

# ═══ MAIN LOOP ═══
if __name__ == "__main__":
    print("═══ TFT Autonomous Evolution Loop ═══")
    print("Will keep playing games until stopped (Ctrl+C)\n")

    game_num = 0
    while True:
        game_num += 1
        print(f"\n{'='*50}")
        print(f"  GAME {game_num}")
        print(f"{'='*50}")
        print_stats()

        # Step 1: Queue
        if not queue_and_accept():
            print("⚠️ Failed to queue, retrying in 30s...")
            time.sleep(30)
            continue

        # Step 2: Wait for game to load
        time.sleep(8)
        if not wait_for_game_api():
            print("⚠️ Game API never came up, retrying...")
            time.sleep(10)
            continue

        # Step 3: Play
        time.sleep(3)
        run_agent()

        # Step 4: Handle post-game (exit spectating if needed)
        wait_for_game_end()

        # Step 5: Wait for client to return to lobby
        print("  Waiting for lobby...")
        for _ in range(60):
            p = lcu_phase()
            if p in ("Lobby", "None", "EndOfGame"):
                break
            time.sleep(3)

        # If EndOfGame screen, click through it
        if lcu_phase() == "EndOfGame":
            pyautogui.click(608, 673)
            time.sleep(5)

        print_stats()
        print(f"\n⏰ Next game in 10s...")
        time.sleep(10)
