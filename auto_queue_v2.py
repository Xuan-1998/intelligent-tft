"""
Auto-queue: Click Play, accept match, wait for game to load.
Handles the full lobby → game transition on macOS.
"""
import time
import pyautogui
import requests
import urllib3
import os
urllib3.disable_warnings()

LEAGUE_PATH = '/Applications/League of Legends (PBE).app/Contents/LoL'


def get_client_info():
    """Read lockfile to get client port and auth token"""
    lockfile = os.path.join(LEAGUE_PATH, 'lockfile')
    try:
        with open(lockfile, 'r') as f:
            parts = f.read().split(':')
            return parts[3], f"https://127.0.0.1:{parts[2]}"
    except:
        return None, None


def lcu_post(endpoint, token, url, data=None):
    from requests.auth import HTTPBasicAuth
    try:
        if data:
            import json
            return requests.post(url + endpoint, json.dumps(data),
                                auth=HTTPBasicAuth('riot', token), timeout=10, verify=False)
        return requests.post(url + endpoint,
                             auth=HTTPBasicAuth('riot', token), timeout=10, verify=False)
    except:
        return None


def lcu_get(endpoint, token, url):
    from requests.auth import HTTPBasicAuth
    try:
        return requests.get(url + endpoint,
                            auth=HTTPBasicAuth('riot', token), timeout=10, verify=False)
    except:
        return None


def auto_queue():
    """Queue into a TFT game and wait until in-game"""
    print("🎮 Auto-queue starting...")

    token, url = get_client_info()
    if not token:
        print("  Client not found, waiting...")
        while not token:
            time.sleep(5)
            token, url = get_client_info()

    print("  Client found")

    # Create TFT Normal lobby (queueId 1090)
    lcu_post("/lol-lobby/v2/lobby/", token, url, {"queueId": 1090})
    time.sleep(2)

    # Start queue
    lcu_post("/lol-lobby/v2/lobby/matchmaking/search", token, url)
    print("  Queue started")

    # Wait for match and accept
    in_game = False
    while not in_game:
        # Accept queue pop
        lcu_post("/lol-matchmaking/v1/ready-check/accept", token, url)

        # Check if in game
        try:
            status = lcu_get("/lol-gameflow/v1/session", token, url)
            if status and status.json().get("phase") == "InProgress":
                in_game = True
        except:
            pass

        time.sleep(2)

    print("  In game!")
    return True


def wait_for_game_window():
    """Wait until the TFT game window appears"""
    from game import find_league_window
    print("  Waiting for game window...")
    while True:
        w = find_league_window()
        if w:
            print(f"  Window found: {w}")
            return w
        time.sleep(2)


if __name__ == "__main__":
    auto_queue()
    wait_for_game_window()
    print("Ready to play!")
