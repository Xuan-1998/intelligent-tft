"""
TFT Game Grader for CORAL
Runs agent.py, monitors the game, returns placement as score.
Score = 9 - placement (1st place = 8 points, 8th = 1 point)
"""
import subprocess
import time
import requests
import urllib3
urllib3.disable_warnings()


def get_game_data():
    try:
        r = requests.get('https://127.0.0.1:2999/liveclientdata/allgamedata', timeout=3, verify=False)
        return r.json()
    except:
        return None


def get_placement():
    """Check if game is over and return placement (1-8)"""
    data = get_game_data()
    if not data:
        return None

    # Check all players, count how many are dead
    players = data.get('allPlayers', [])
    me = data.get('activePlayer', {}).get('summonerName', '')

    # If we can't get data, game might be over
    dead_count = sum(1 for p in players if p.get('isDead', False))

    # If our player is dead, our placement = 8 - (number who died before us)
    for p in players:
        if p.get('riotId', '') == me or p.get('summonerName', '') == me:
            if p.get('isDead', False):
                # Count players who are still alive = our placement
                alive = sum(1 for pl in players if not pl.get('isDead', False))
                return alive + 1  # placement = alive players + 1

    return None  # game still going


def wait_for_game_end(timeout=1800):
    """Wait for the game to end, return placement"""
    start = time.time()
    while time.time() - start < timeout:
        placement = get_placement()
        if placement:
            return placement

        # Check if game is still running
        data = get_game_data()
        if data is None:
            # API not responding = game ended or not started
            time.sleep(5)
            # Double check
            data = get_game_data()
            if data is None:
                return 8  # assume worst if we can't tell

        time.sleep(10)

    return 8  # timeout = assume worst


def grade():
    """
    Run the TFT agent and return a score.
    Called by CORAL's grading system.
    """
    # Start the agent
    proc = subprocess.Popen(
        ['python3', '-u', 'agent.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for game to end
    placement = wait_for_game_end(timeout=1800)  # 30 min max

    # Kill agent
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except:
        proc.kill()

    # Score: higher is better
    score = 9 - placement  # 1st = 8, 8th = 1
    print(f"Game finished! Placement: {placement}, Score: {score}")
    return score


if __name__ == "__main__":
    score = grade()
    print(f"Final score: {score}")
