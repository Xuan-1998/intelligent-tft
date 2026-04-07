#!/usr/bin/env python3 -u
"""
TFT Overnight Evolution Loop
Fully autonomous: queue → accept → play → exit → analyze → repeat
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, time, subprocess, signal, re
os.environ["PYTHONWARNINGS"] = "ignore"

import pyautogui
import requests, urllib3; urllib3.disable_warnings()
from requests.auth import HTTPBasicAuth

pyautogui.FAILSAFE = False
LEAGUE_PATH = '/Applications/League of Legends (PBE).app/Contents/LoL'
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY = os.path.expanduser('~/intelligent-tft/game_history.jsonl')
VENV_PYTHON = os.path.join(SCRIPT_DIR, 'venv/bin/python3')


def get_client():
    try:
        with open(os.path.join(LEAGUE_PATH, 'lockfile'), 'r') as f:
            parts = f.read().split(':')
            return parts[3], f"https://127.0.0.1:{parts[2]}"
    except: return None, None


def lcu(method, endpoint, token, url, data=None):
    try:
        auth = HTTPBasicAuth('riot', token)
        if method == 'post':
            return requests.post(url+endpoint, json=data, auth=auth, timeout=5, verify=False)
        return requests.get(url+endpoint, auth=auth, timeout=5, verify=False)
    except: return None


def get_phase(token, url):
    r = lcu('get', '/lol-gameflow/v1/session', token, url)
    if r and r.status_code == 200:
        return r.json().get("phase", "None")
    return "None"


def game_api_alive():
    try:
        r = requests.get('https://127.0.0.1:2999/liveclientdata/allgamedata', timeout=3, verify=False)
        return r.status_code == 200
    except: return False


def exit_game():
    """Exit game: click EXIT NOW button, or Esc → Exit Game"""
    print("  Exiting game...")
    # First try EXIT NOW button (shown when dead)
    pyautogui.click(862, 578)
    time.sleep(2)
    # Then try Esc → Exit Game (options menu)
    pyautogui.press('escape')
    time.sleep(1)
    pyautogui.click(468, 661)
    time.sleep(2)


def queue_and_accept():
    """Full queue flow: handle any client state → queue → accept → in game"""
    print("\n🎮 Queuing...")
    token, url = None, None
    for _ in range(30):
        token, url = get_client()
        if token: break
        print("  Waiting for client...")
        time.sleep(5)
    if not token:
        print("❌ No client"); return False

    phase = get_phase(token, url)
    print(f"  Phase: {phase}")

    # Handle end-of-game states
    if phase in ('PreEndOfGame', 'EndOfGame', 'WaitingForStats'):
        pyautogui.click(590, 683)  # PLAY AGAIN
        time.sleep(3)
        phase = get_phase(token, url)

    # Handle still in game (spectating after death)
    if phase == 'InProgress':
        if not game_api_alive():
            # Game client open but API dead = transitioning
            time.sleep(5)
        else:
            exit_game()
            time.sleep(5)
        phase = get_phase(token, url)

    # Create lobby + queue
    if phase not in ('Matchmaking', 'ReadyCheck', 'ChampSelect'):
        lcu('post', '/lol-lobby/v2/lobby/', token, url, {"queueId": 1090})
        time.sleep(1)
        lcu('post', '/lol-lobby/v2/lobby/matchmaking/search', token, url)
        print("  Queue started")

    # Fast accept loop (0.3s interval, 3 min timeout)
    print("  Accepting...")
    for i in range(600):
        lcu('post', '/lol-matchmaking/v1/ready-check/accept', token, url)
        phase = get_phase(token, url)
        if phase == 'InProgress':
            print("  ✅ IN GAME!")
            return True
        if i % 20 == 0 and i > 0:
            print(f"  [{i//3}s] {phase}")
        # Re-queue if dropped
        if phase in ('None', 'Lobby'):
            lcu('post', '/lol-lobby/v2/lobby/', token, url, {"queueId": 1090})
            time.sleep(0.5)
            lcu('post', '/lol-lobby/v2/lobby/matchmaking/search', token, url)
        time.sleep(0.3)

    print("❌ Queue timeout")
    return False


def wait_for_game_window():
    sys.path.insert(0, SCRIPT_DIR)
    from game import find_league_window
    for _ in range(60):
        w = find_league_window()
        if w: return True
        time.sleep(2)
    return False


def run_agent():
    """Run agent.py, stream output, return when done"""
    print("🤖 Agent starting...")
    proc = subprocess.Popen(
        [VENV_PYTHON, '-u', 'agent.py'],
        cwd=SCRIPT_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    while proc.poll() is None:
        line = proc.stdout.readline()
        if line: print(f"  [bot] {line.rstrip()}")
    for line in proc.stdout:
        if line: print(f"  [bot] {line.rstrip()}")
    return proc.returncode


def load_history():
    if not os.path.exists(HISTORY): return []
    with open(HISTORY) as f:
        return [json.loads(l) for l in f if l.strip()]


def print_stats():
    hist = load_history()
    if not hist: print("📊 No history yet"); return
    recent = hist[-10:]
    avg = sum(g["placement"] for g in recent) / len(recent)
    best = min(g["placement"] for g in recent)
    top4 = sum(1 for g in recent if g["placement"] <= 4)
    print(f"📊 Last {len(recent)}: avg={avg:.1f} best={best} top4={top4}/{len(recent)}")
    for g in recent[-5:]:
        print(f"  {g.get('time','')} → #{g['placement']}")


# ═══ MAIN ═══
if __name__ == "__main__":
    print("═══ TFT OVERNIGHT EVOLUTION ═══")
    print("Goal: Top 4 consistently. Running until stopped.\n")

    game_num = 0
    while True:
        game_num += 1
        print(f"\n{'='*50}")
        print(f"  GAME {game_num} | {time.strftime('%H:%M:%S')}")
        print(f"{'='*50}")
        print_stats()

        try:
            # Queue
            if not queue_and_accept():
                print("⚠️ Queue failed, retry in 30s")
                time.sleep(30); continue

            # Wait for game window
            time.sleep(8)
            if not wait_for_game_window():
                print("⚠️ No window, retry in 15s")
                time.sleep(15); continue

            # Play
            time.sleep(5)
            run_agent()

            # Agent exited — handle cleanup
            time.sleep(3)
            token, url = get_client()
            if token:
                phase = get_phase(token, url)
                print(f"  Post-game phase: {phase}")
                if phase == 'InProgress':
                    exit_game()
                    time.sleep(5)
                elif phase in ('PreEndOfGame', 'EndOfGame', 'WaitingForStats'):
                    pyautogui.click(590, 683)  # PLAY AGAIN
                    time.sleep(3)

        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(30)

        print_stats()
        print(f"⏰ Next game in 10s...")
        time.sleep(10)
