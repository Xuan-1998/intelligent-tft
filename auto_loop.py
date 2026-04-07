#!/usr/bin/env python3 -u
"""TFT Autonomous Loop v2: queue → play → exit → repeat.
Properly kills agent between games. Single agent at a time.
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
        r = requests.get(f"{url}/lol-gameflow/v1/session",
                         auth=HTTPBasicAuth('riot', token), timeout=10, verify=False)
        return r.json().get('phase', 'Unknown')
    except: return "Error"

def lcu_post(endpoint, data=None):
    token, url = get_lcu()
    if not token: return None
    return requests.post(f"{url}{endpoint}", json=data,
                         auth=HTTPBasicAuth('riot', token), timeout=10, verify=False)

def game_api_up():
    try:
        return requests.get('https://127.0.0.1:2999/liveclientdata/allgamedata',
                            timeout=3, verify=False).status_code == 200
    except: return False

def game_api_level():
    try:
        d = requests.get('https://127.0.0.1:2999/liveclientdata/allgamedata',
                         timeout=3, verify=False).json()
        return int(d['activePlayer']['level'])
    except: return -1

def kill_all_agents():
    """Make sure no stale agent.py processes exist"""
    os.system("pkill -f 'python.*agent\\.py' 2>/dev/null")
    time.sleep(1)

def exit_dead_game():
    print("  Exiting dead game (Esc → Exit Game)...")
    pyautogui.press('escape')
    time.sleep(2)
    for cx, cy in [(443, 665), (443, 670), (468, 661)]:
        pyautogui.click(cx, cy)
        time.sleep(0.5)
    time.sleep(5)

def queue_and_accept():
    print("🎮 Queuing...")
    for _ in range(3):
        p = lcu_phase()
        print(f"  Phase: {p}")
        if p == "InProgress": return True
        if p == "EndOfGame":
            pyautogui.click(608, 673); time.sleep(5); continue
        if p in ("Lobby", "None", "Unknown"):
            lcu_post('/lol-lobby/v2/lobby/', {"queueId": 1090}); time.sleep(2)
            lcu_post('/lol-lobby/v2/lobby/matchmaking/search'); time.sleep(2)
            break
        time.sleep(3)

    print("  Waiting for match...")
    for i in range(180):
        lcu_post('/lol-matchmaking/v1/ready-check/accept')
        p = lcu_phase()
        if p == "InProgress":
            print(f"  ✅ In game! ({i}s)"); return True
        if p in ("None", "Lobby"):
            lcu_post('/lol-lobby/v2/lobby/', {"queueId": 1090}); time.sleep(2)
            lcu_post('/lol-lobby/v2/lobby/matchmaking/search')
        if i % 15 == 0: print(f"  [{i}s] {p}")
        time.sleep(1)
    print("  ❌ Queue timeout"); return False

def run_agent():
    """Run ONE agent.py, wait for it to fully exit."""
    kill_all_agents()  # ensure clean slate

    # Wait for game API to be fresh (level resets to 1 at game start)
    print("  Waiting for fresh game...")
    for _ in range(60):
        lvl = game_api_level()
        if 1 <= lvl <= 3:  # fresh game
            print(f"  Fresh game detected (lvl={lvl})")
            break
        if not game_api_up():
            time.sleep(2); continue
        time.sleep(2)

    print("🤖 Starting agent...")
    proc = subprocess.Popen(
        [sys.executable, '-u', 'agent.py'],
        cwd=SCRIPT_DIR,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    start = time.time()
    try:
        while time.time() - start < 1800:  # 30 min max
            line = proc.stdout.readline()
            if line:
                print(f"  [bot] {line.rstrip()}")
            if not line and proc.poll() is not None:
                break
    finally:
        # ALWAYS kill the agent when we exit this function
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        # Drain remaining output
        try:
            for line in proc.stdout:
                print(f"  [bot] {line.rstrip()}")
        except: pass

    print(f"  Agent exited (code={proc.returncode}, {int(time.time()-start)}s)")

def handle_post_game():
    """Exit spectating if needed, wait for lobby"""
    if game_api_up():
        print("  Still in game (spectating)...")
        exit_dead_game()
        for _ in range(30):
            if not game_api_up(): break
            time.sleep(3)

    print("  Waiting for lobby...")
    for _ in range(60):
        p = lcu_phase()
        if p in ("Lobby", "None"): return
        if p == "EndOfGame":
            pyautogui.click(608, 673); time.sleep(5)
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
    print(f"📊 Last {len(recent)}: avg={avg:.1f} best={best} top4={top4}/{len(recent)}")

# ═══ MAIN ═══
if __name__ == "__main__":
    print("═══ TFT Auto Loop v2 ═══\n")
    kill_all_agents()
    game_num = 0

    while True:
        game_num += 1
        print(f"\n{'='*40}")
        print(f"  GAME {game_num}")
        print(f"{'='*40}")
        print_stats()

        if not queue_and_accept():
            print("⚠️ Queue failed, retry in 30s...")
            time.sleep(30); continue

        time.sleep(5)
        run_agent()
        kill_all_agents()  # ensure dead
        handle_post_game()
        print_stats()
        print("⏰ Next game in 8s...")
        time.sleep(8)
