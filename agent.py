#!/usr/bin/env python3 -u
"""TFT Agent v8 — proper econ, API gold, smart buying, round-aware.
Press Ctrl+C to stop.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, time, re
os.environ["PYTHONWARNINGS"] = "ignore"

import pyautogui
import requests, urllib3; urllib3.disable_warnings()
from difflib import SequenceMatcher

from vec4 import Vec4
from vec2 import Vec2
from game import find_league_window
import screen_coords, ocr, game_assets, comps

RUNNING = True

# ── Window ──
w = None
for _r in range(15):
    w = find_league_window()
    if w: break
    time.sleep(2)
if not w: print("NO GAME WINDOW"); sys.exit(1)
x, y, W, H = w
Y_OFF = y + round(H * 0.028); EFF_H = H - round(H * 0.028)
Vec4.setup_screen(x, Y_OFF, W, EFF_H); Vec2.setup_screen(x, Y_OFF, W, EFF_H)
pyautogui.FAILSAFE = False

# ── Coords ──
BUY = [b.get_coords() for b in screen_coords.BUY_LOC]
BENCH = [b.get_coords() for b in screen_coords.BENCH_LOC]
BOARD = [b.get_coords() for b in screen_coords.BOARD_LOC]
DEFAULT = screen_coords.DEFAULT_LOC.get_coords()
AUG_LOC = [a.get_coords() for a in screen_coords.AUGMENT_LOC]
ALL_C = set(game_assets.CHAMPIONS.keys())

# ── Logging ──
LOG_DIR = os.path.expanduser("~/intelligent-tft/game_logs")
os.makedirs(LOG_DIR, exist_ok=True)
GID = time.strftime("%Y%m%d_%H%M%S")
LOG = []
HISTORY = os.path.expanduser("~/intelligent-tft/game_history.jsonl")

def log(ev, **kw):
    LOG.append({"t": time.strftime("%H:%M:%S"), "ev": ev, **kw})
    if ev in ("round", "game_over", "phase"):
        try: ocr._grab((0, 33, 1728, 1035)).save(f"{LOG_DIR}/{GID}_{ev}_{len(LOG)}.png")
        except: pass

def save_log():
    with open(f"{LOG_DIR}/{GID}_log.json", "w") as f: json.dump(LOG, f, indent=1)

def save_history(p):
    with open(HISTORY, "a") as f:
        f.write(json.dumps({"time": time.strftime("%Y-%m-%d %H:%M"), "gid": GID, "placement": p}) + "\n")

# ── API (single call, cached per tick) ──
_api_cache = {"data": None, "t": 0}

def api():
    now = time.time()
    if now - _api_cache["t"] < 0.3 and _api_cache["data"]:
        return _api_cache["data"]
    try:
        d = requests.get("https://127.0.0.1:2999/liveclientdata/allgamedata", timeout=3, verify=False).json()
        _api_cache["data"] = d; _api_cache["t"] = now
        return d
    except:
        return _api_cache["data"]

def api_gold():
    d = api()
    try: return int(d["activePlayer"]["currentGold"])
    except: return 0

def api_level():
    d = api()
    try: return int(d["activePlayer"]["level"])
    except: return -1

def api_health():
    d = api()
    try: return int(d["activePlayer"]["championStats"]["currentHealth"])
    except: return 100

def api_alive():
    d = api()
    if not d: return False, 8
    try:
        me = d["activePlayer"].get("riotIdGameName", "")
    except: return False, 8
    alive_count = 0
    for p in d["allPlayers"]:
        if not p.get("isDead"): alive_count += 1
        if p.get("riotIdGameName") == me and p.get("isDead"):
            return False, alive_count + 1
    return True, 0

# ── OCR ──
def fuzzy(t):
    if not t or len(t) < 2: return None
    best, sc = None, 0
    for n in ALL_C:
        s = SequenceMatcher(None, t.lower(), n.lower()).ratio()
        if s > sc: best, sc = n, s
    return best if sc >= 0.5 else None

def read_round():
    for box in [(640, 72, 740, 102), (650, 75, 730, 100)]:
        try:
            t = ocr.get_text(box, 3, 7, ocr.ROUND_WHITELIST)
            m = re.search(r'([1-7])-([1-7])', t or "")
            if m: return m.group(0)
        except: pass
    return ""

def read_shop():
    try:
        sp = screen_coords.SHOP_POS.get_coords()
        names = []
        for p in screen_coords.CHAMP_NAME_POS:
            cp = p.get_coords()
            t = ocr.get_text((sp[0]+cp[0], sp[1]+cp[1], sp[0]+cp[2], sp[1]+cp[3]), 3, 7, ocr.ALPHABET_WHITELIST)
            names.append(fuzzy(t))
        return names
    except: return [None]*5

def detect_popup():
    try:
        img = ocr._grab((0, 33, 1728, 1035))
        a = list(img.crop((500, 130, 1200, 180)).getdata())
        if sum(1 for p in a if p[0]>200 and p[1]>200 and p[2]>200) > len(a)*0.1: return "god"
        a2 = list(img.crop((400, 180, 600, 230)).getdata())
        if sum(1 for p in a2 if p[0]>180 and p[1]>180 and p[2]>180) > len(a2)*0.08: return "augment"
    except: pass
    return None

# ── Actions ──
def buy_slot(i): pyautogui.click(*BUY[i]); time.sleep(0.1)
def buy_xp(): pyautogui.press('f'); time.sleep(0.1)
def reroll_shop(): pyautogui.press('d'); time.sleep(0.1)
def sell_bench(i):
    pyautogui.moveTo(*BENCH[i]); time.sleep(0.15)
    pyautogui.press('e'); time.sleep(0.15)

def place_bench_to_board():
    lvl = api_level()
    if lvl <= 0: lvl = 8
    # Front row first, then back row
    pos = [21, 22, 23, 24, 25, 26, 27, 0, 1, 2, 3, 14]
    for i in range(min(9, lvl)):
        pyautogui.click(*BENCH[i]); time.sleep(0.12)
        pyautogui.click(*BOARD[pos[i % len(pos)]]); time.sleep(0.12)

def pickup_loot():
    for ly in range(Y_OFF + int(EFF_H*0.20), Y_OFF + int(EFF_H*0.65), 60):
        for lx in range(x + int(W*0.20), x + int(W*0.80), 80):
            pyautogui.rightClick(lx, ly); time.sleep(0.05)

def handle_popup():
    p = detect_popup()
    if p == "god":
        print("  🔮 God"); pyautogui.click(int(W*0.30), int(Y_OFF+EFF_H*0.25)); time.sleep(1.5)
        log("god"); return True
    if p == "augment":
        print("  ⭐ Aug"); pyautogui.click(*AUG_LOC[0]); time.sleep(1.5)
        log("augment"); return True
    return False

def slam_items():
    item_pos = [
        (295, 290), (330, 275), (365, 290),
        (280, 320), (315, 305), (350, 320),
        (295, 350), (330, 335), (365, 350),
        (315, 370),
    ]
    targets = [BOARD[21], BOARD[22], BOARD[23], BOARD[24], BOARD[0], BOARD[1], BOARD[14], BOARD[25], BOARD[2], BOARD[3]]
    for i, pos in enumerate(item_pos):
        t = targets[i % len(targets)]
        pyautogui.moveTo(*pos); time.sleep(0.15)
        pyautogui.mouseDown(button='left'); time.sleep(0.2)
        pyautogui.moveTo(*t, duration=0.3)
        time.sleep(0.15)
        pyautogui.mouseUp(button='left'); time.sleep(0.2)

# ── Smart buying ──
WANT = comps.EARLY_GAME_BUYS | comps.ROLLDOWN_BUYS
OWNED = {}  # name -> count (track for 2-star)

def smart_buy(shop, gold, phase):
    """Buy units intelligently based on phase and gold."""
    bought = []
    for i, ch in enumerate(shop):
        if not ch: continue
        cost = game_assets.CHAMPIONS.get(ch, {}).get("Gold", 99)
        if gold < cost: continue

        should_buy = False
        if phase == "EARLY":
            # Buy comp units + any 1-cost to build pairs
            if ch in WANT:
                should_buy = True
            elif cost == 1 and OWNED.get(ch, 0) in (1, 2):
                should_buy = True  # complete a pair/triple
        elif phase == "ROLLDOWN":
            if ch in comps.ROLLDOWN_BUYS or cost >= 4:
                should_buy = True
        elif phase == "LATEGAME":
            if ch in WANT or cost >= 4:
                should_buy = True
            elif OWNED.get(ch, 0) in (1, 2):
                should_buy = True

        if should_buy:
            buy_slot(i)
            gold -= cost
            OWNED[ch] = OWNED.get(ch, 0) + 1
            bought.append(ch)
            if gold <= 0: break
    return bought, gold

# ═══ MAIN ═══
print(f"═══ TFT Agent v8 | {GID} ═══")

# Wait for game API
for _w in range(60):
    if api_level() > 0: break
    print(f"  Waiting for game... ({_w*2}s)")
    time.sleep(2)

lvl = api_level()
if lvl <= 0:
    print("❌ Game API never came up"); save_log(); sys.exit(1)

rnd = read_round()
stage = int(rnd[0]) if rnd and rnd[0].isdigit() else 1

# Determine starting phase based on current game state
if lvl >= 8:
    phase = "LATEGAME"
elif stage >= 4 or lvl >= 7:
    phase = "ROLLDOWN"
else:
    phase = "EARLY"

print(f"Start: R{rnd} Lvl:{lvl} Gold:{api_gold()} HP:{api_health()} → {phase}")
log("startup", round=rnd, level=lvl, phase=phase, gold=api_gold(), hp=api_health())

last_rnd = ""; cycle = 0; start = time.time()
rolldown_done = False

try:
    while RUNNING:
        alive, placement = api_alive()
        if not alive:
            print(f"\n☠️ Placement: {placement}")
            log("game_over", placement=placement); save_history(placement)
            time.sleep(2)
            pyautogui.click(*screen_coords.EXIT_NOW_LOC.get_coords())
            time.sleep(1)
            break

        lvl = api_level()
        gold = api_gold()
        hp = api_health()
        rnd = read_round()
        stage = int(rnd[0]) if rnd and rnd[0].isdigit() else 0

        if rnd and rnd != last_rnd:
            print(f"\n[R{rnd}] Lvl:{lvl} Gold:{gold} HP:{hp} {phase} ({int(time.time()-start)}s)")
            log("round", round=rnd, level=lvl, gold=gold, hp=hp, phase=phase)
            last_rnd = rnd

        # Handle popups (god selection, augments)
        if handle_popup():
            time.sleep(1); pickup_loot(); cycle += 1; continue

        # Pickup loot after PVE rounds
        if cycle % 12 == 0 and cycle > 0: pickup_loot()

        # ── Phase transitions ──
        if phase == "EARLY" and (stage >= 4 or lvl >= 7):
            phase = "ROLLDOWN"
            print(f"\n🎯 → ROLLDOWN (stage={stage} lvl={lvl} gold={gold})")
            log("phase", phase="ROLLDOWN")

        if phase == "ROLLDOWN" and rolldown_done:
            phase = "LATEGAME"
            print(f"\n🏆 → LATEGAME")
            log("phase", phase="LATEGAME")

        # ── Panic mode: low HP ──
        if hp < 30 and phase == "LATEGAME":
            # Spend everything
            if gold > 10:
                reroll_shop()
                shop = read_shop()
                smart_buy(shop, gold, phase)
                place_bench_to_board()

        # ═══ EARLY: econ to 50g, buy only what we need ═══
        if phase == "EARLY":
            gold = api_gold()
            shop = read_shop()

            # Only buy comp units or cheap pairs — preserve econ
            if gold > 10 or any(ch in comps.EARLY_GAME_BUYS for ch in shop if ch):
                bought, gold = smart_buy(shop, gold, phase)
                if bought:
                    print(f"  🛒 Bought: {bought} (gold→{api_gold()})")
                    log("buy", champs=bought)

            # Buy XP at stage 3+ but only above 50g (preserve interest)
            if stage >= 3 and lvl < 7 and gold > 52 and cycle % 4 == 0:
                buy_xp(); buy_xp()
                print(f"  📈 XP (lvl→{api_level()} gold→{api_gold()})")

            # Place units periodically
            if cycle % 5 == 0: place_bench_to_board()
            if cycle % 8 == 0: slam_items()

        # ═══ ROLLDOWN: level to 8, roll for carries ═══
        elif phase == "ROLLDOWN" and not rolldown_done:
            print("  🎰 ROLLDOWN START")

            # Level to 8 first
            ct = 0
            while RUNNING and api_level() < 8 and ct < 30:
                g = api_gold()
                if g < 4: break
                buy_xp(); ct += 1; time.sleep(0.1)
            print(f"  Leveled to {api_level()} (gold→{api_gold()})")

            # Roll for carries
            found = []
            for roll in range(20):
                if not RUNNING: break
                g = api_gold()
                if g < 6: break  # keep some gold
                reroll_shop()
                shop = read_shop()
                bought, g = smart_buy(shop, g, phase)
                found.extend(bought)

            place_bench_to_board(); slam_items()
            print(f"  Rolldown result: {found} (gold→{api_gold()})")
            log("rolldown", found=found, gold=api_gold())
            rolldown_done = True

        # ═══ LATEGAME: maintain board, occasional upgrades ═══
        elif phase == "LATEGAME":
            gold = api_gold()
            # Only buy if we have spare gold above interest threshold
            if gold > 20 or hp < 30:
                shop = read_shop()
                bought, _ = smart_buy(shop, gold, phase)
                if bought:
                    print(f"  🛒 {bought} (gold→{api_gold()})")
                    place_bench_to_board()

            # Reroll occasionally if rich or desperate
            if (gold > 50 or hp < 20) and cycle % 4 == 0:
                reroll_shop()

            # Level to 9 if rich
            if lvl < 9 and gold > 60 and cycle % 6 == 0:
                buy_xp()

            if cycle % 10 == 0: slam_items()
            if cycle % 8 == 0: place_bench_to_board()

        pyautogui.moveTo(*DEFAULT); cycle += 1; time.sleep(0.5)

except KeyboardInterrupt:
    print("\n🛑 Stopped")
finally:
    save_log()
    elapsed = int(time.time()-start)
    print(f"📝 {LOG_DIR}/{GID}_log.json ({len(LOG)} events, {elapsed}s)")
