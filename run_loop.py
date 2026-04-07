"""
Full autonomous TFT game loop.
1. Auto-queue into game via LCU API
2. Run agent to play the game
3. Detect game end + placement
4. Log results for evolution
"""
import time, json, os, sys, subprocess
import warnings; warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

import requests, urllib3; urllib3.disable_warnings()
from requests.auth import HTTPBasicAuth

LEAGUE_PATH = '/Applications/League of Legends (PBE).app/Contents/LoL'
LOG_FILE = os.path.expanduser('~/intelligent-tft/game_history.jsonl')


def get_client():
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
            return requests.post(url+endpoint, json=data, auth=auth, timeout=10, verify=False)
        return requests.get(url+endpoint, auth=auth, timeout=10, verify=False)
    except:
        return None


def queue_into_game():
    print("🎮 Queuing into TFT...")
    token, url = None, None
    while not token:
        token, url = get_client()
        if not token: print("  Waiting for client..."); time.sleep(5)

    # Create lobby + start queue
    lcu('post', '/lol-lobby/v2/lobby/', token, url, {"queueId": 1090})
    time.sleep(2)
    lcu('post', '/lol-lobby/v2/lobby/matchmaking/search', token, url)
    print("  Queue started")

    # Accept and wait for game
    for _ in range(300):  # 10 min timeout
        lcu('post', '/lol-matchmaking/v1/ready-check/accept', token, url)
        r = lcu('get', '/lol-gameflow/v1/session', token, url)
        if r and r.json().get("phase") == "InProgress":
            print("  ✅ In game!")
            return True
        time.sleep(2)
    return False


def wait_for_game_window():
    from game import find_league_window
    for _ in range(60):
        w = find_league_window()
        if w: return w
        time.sleep(2)
    return None


def game_api():
    try:
        r = requests.get('https://127.0.0.1:2999/liveclientdata/allgamedata', timeout=3, verify=False)
        return r.json()
    except:
        return None


def wait_for_game_end():
    """Wait for game to end, return placement 1-8"""
    print("⏳ Waiting for game to end...")
    last_hp = 100
    while True:
        data = game_api()
        if data is None:
            # API gone = game ended
            time.sleep(3)
            if game_api() is None:
                print("  Game ended (API disconnected)")
                return 8  # can't determine placement
        else:
            # Check if we're dead
            me = data.get('activePlayer', {}).get('riotId', '')
            for p in data.get('allPlayers', []):
                if p.get('riotId') == me and p.get('isDead'):
                    alive = sum(1 for pl in data['allPlayers'] if not pl.get('isDead'))
                    placement = alive + 1
                    print(f"  ☠️ Eliminated! Placement: {placement}")
                    return placement
        time.sleep(5)


def log_game(placement, duration):
    entry = {
        "time": time.strftime("%Y-%m-%d %H:%M"),
        "placement": placement,
        "score": 9 - placement,
        "duration_min": round(duration/60, 1),
    }
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    print(f"📊 Logged: placement={placement}, score={9-placement}")
    return entry


def run_game_loop():
    """Single game: queue → play → score"""
    # Queue
    if not queue_into_game():
        print("❌ Failed to queue")
        return None

    # Wait for window
    time.sleep(10)
    w = wait_for_game_window()
    if not w:
        print("❌ No game window")
        return None

    # Play
    start = time.time()
    print("🤖 Starting agent...")
    proc = subprocess.Popen([sys.executable, '-u', 'agent.py'],
                            cwd=os.path.dirname(os.path.abspath(__file__)))

    # Wait for end
    placement = wait_for_game_end()
    duration = time.time() - start

    # Stop agent
    proc.terminate()
    try: proc.wait(timeout=5)
    except: proc.kill()

    # Log
    return log_game(placement, duration)


if __name__ == "__main__":
    print("═══ Intelligent TFT — Autonomous Loop ═══")
    print(f"Log: {LOG_FILE}\n")

    game_num = 0
    while True:
        game_num += 1
        print(f"\n{'='*50}")
        print(f"  GAME {game_num}")
        print(f"{'='*50}\n")

        result = run_game_loop()
        if result:
            print(f"\n📈 Game {game_num} result: {result}")
        else:
            print(f"\n⚠️ Game {game_num} failed, retrying in 30s...")
            time.sleep(30)

        # Wait before next game
        print("⏰ Waiting 15s before next game...")
        time.sleep(15)
