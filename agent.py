#!/usr/bin/env python3 -u
"""TFT Agent v5 — action-first, no gold gating.
Just buy good units (game rejects if you can't afford), always place, always loot.
Press Cmd+= to stop.
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

# ── Stop via Ctrl+C ──
RUNNING = True

# ── Window ──
w = find_league_window()
if not w: print("NO GAME WINDOW"); sys.exit(1)
x, y, W, H = w
Y_OFF = y + round(H * 0.028)
EFF_H = H - round(H * 0.028)
Vec4.setup_screen(x, Y_OFF, W, EFF_H)
Vec2.setup_screen(x, Y_OFF, W, EFF_H)
pyautogui.FAILSAFE = False

# ── Coords ──
BUY = [b.get_coords() for b in screen_coords.BUY_LOC]
BENCH = [b.get_coords() for b in screen_coords.BENCH_LOC]
BOARD = [b.get_coords() for b in screen_coords.BOARD_LOC]
BUY_XP = screen_coords.BUY_XP_LOC.get_coords()
REROLL = screen_coords.REFRESH_LOC.get_coords()
DEFAULT = screen_coords.DEFAULT_LOC.get_coords()
AUG_LOC = [a.get_coords() for a in screen_coords.AUGMENT_LOC]
ALL_C = set(game_assets.CHAMPIONS.keys())

# ── Logging ──
LOG_DIR = os.path.expanduser("~/intelligent-tft/game_logs")
os.makedirs(LOG_DIR, exist_ok=True)
GID = time.strftime("%Y%m%d_%H%M%S")
LOG = []
HISTORY_FILE = os.path.expanduser("~/intelligent-tft/game_history.jsonl")

def log(ev, **kw):
    LOG.append({"t": time.strftime("%H:%M:%S"), "ev": ev, **kw})
    if ev in ("round", "game_over", "phase"):
        try: ocr._grab((0, 33, 1728, 1035)).save(f"{LOG_DIR}/{GID}_{ev}_{len(LOG)}.png")
        except: pass

def save_log():
    with open(f"{LOG_DIR}/{GID}_log.json", "w") as f:
        json.dump(LOG, f, indent=1)

def save_history(placement):
    with open(HISTORY_FILE, "a") as f:
        f.write(json.dumps({"time": time.strftime("%Y-%m-%d %H:%M"), "gid": GID,
                             "placement": placement, "events": len(LOG)}) + "\n")

# ── API ──
def api_data():
    try:
        return requests.get("https://127.0.0.1:2999/liveclientdata/allgamedata",
                            timeout=3, verify=False).json()
    except: return None

def api_level():
    d = api_data()
    return int(d["activePlayer"]["level"]) if d else -1

def api_alive():
    d = api_data()
    if d is None: return False, 8
    me = d["activePlayer"].get("riotIdGameName", "")
    for p in d["allPlayers"]:
        if p.get("riotIdGameName") == me and p.get("isDead"):
            return False, sum(1 for pl in d["allPlayers"] if not pl.get("isDead")) + 1
    return True, 0

# ── OCR ──
def fuzzy(t):
    if not t or len(t) < 2: return None
    best, score = None, 0
    for n in ALL_C:
        sc = SequenceMatcher(None, t.lower(), n.lower()).ratio()
        if sc > score: best, score = n, sc
    return best if score >= 0.55 else None

def read_round():
    """Try multiple boxes for round — OCR is finicky"""
    for box in [(640, 72, 740, 102), (640, 75, 740, 100), (650, 75, 730, 100)]:
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
            t = ocr.get_text((sp[0]+cp[0], sp[1]+cp[1], sp[0]+cp[2], sp[1]+cp[3]),
                             3, 7, ocr.ALPHABET_WHITELIST)
            names.append(fuzzy(t))
        return names
    except: return [None] * 5

def detect_popup():
    try:
        img = ocr._grab((0, 33, 1728, 1035))
        a = list(img.crop((500, 130, 1200, 180)).getdata())
        if sum(1 for p in a if p[0]>200 and p[1]>200 and p[2]>200) > len(a)*0.1:
            return "god"
        a2 = list(img.crop((400, 180, 600, 230)).getdata())
        if sum(1 for p in a2 if p[0]>180 and p[1]>180 and p[2]>180) > len(a2)*0.08:
            return "augment"
    except: pass
    return None

# ── Actions ──
def click(cx, cy, delay=0.15):
    pyautogui.click(cx, cy); time.sleep(delay)

def buy_slot(i):
    """Click buy slot — game will reject if can't afford, that's fine"""
    click(*BUY[i], 0.25)

def buy_xp():
    click(*BUY_XP, 0.15)

def reroll_shop():
    click(*REROLL, 0.2)

def place_bench_to_board():
    """Place units: first 4 bench → front row (tanks), rest → back row (carries)
    Board rows 21-27 (y=423) = FRONT (meets enemy first)
    Board rows 0-6 (y=651) = BACK (safe for carries)"""
    level = api_level()
    if level <= 0: level = 8
    positions = [21, 22, 23, 24, 0, 1, 2, 3, 14]
    for i in range(min(9, level)):
        pyautogui.click(*BENCH[i]); time.sleep(0.3)
        pyautogui.click(*BOARD[positions[i]]); time.sleep(0.3)

def pickup_loot():
    """Quick sweep for orbs — stay inside game window"""
    y_start = Y_OFF + int(EFF_H * 0.30)
    y_end = Y_OFF + int(EFF_H * 0.60)
    x_start = x + int(W * 0.30)
    x_end = x + int(W * 0.70)
    for ly in range(y_start, y_end, 80):
        for lx in range(x_start, x_end, 100):
            pyautogui.rightClick(lx, ly); time.sleep(0.01)

def handle_popup():
    popup = detect_popup()
    if popup == "god":
        print("  🔮 God → left")
        click(int(W * 0.30), int(Y_OFF + EFF_H * 0.25), 2)
        log("god"); return True
    if popup == "augment":
        print("  ⭐ Augment → first")
        click(*AUG_LOC[0], 2)
        log("augment"); return True
    return False

# ── Target lists ──
# "Strongest board" strategy: buy good units at every cost tier
# Early: any 1-2 cost unit (build pairs for upgrades)
# Mid: any 2-3 cost unit
# Rolldown: any 3-4-5 cost unit
ALWAYS_BUY = set(game_assets.CHAMPIONS.keys())  # buy everything the game offers
EARLY_CHEAP = {n for n, d in game_assets.CHAMPIONS.items() if d.get("Gold", 99) <= 2}

# ═══ MAIN ═══
print(f"═══ TFT Agent v5 | {GID} ═══")
print(f"Window: {W}x{H} at ({x},{y})")

level = api_level()
rnd = read_round()
stage = int(rnd[0]) if rnd and rnd[0].isdigit() else 0

if stage >= 5 or (stage >= 4 and level >= 8):
    phase = "LATEGAME"
elif stage >= 4:
    phase = "ROLLDOWN"
else:
    phase = "EARLY"

print(f"Start: R{rnd} Lvl:{level} → {phase}")
log("startup", round=rnd, level=level, phase=phase)

last_rnd = ""
cycle = 0
start_time = time.time()
last_place_cycle = -10
rolldown_done = False

try:
    while RUNNING:
        # ── Alive check ──
        alive, placement = api_alive()
        if not alive:
            print(f"\n☠️ Game over! Placement: {placement}")
            log("game_over", placement=placement)
            save_history(placement)
            break

        level = api_level()
        rnd = read_round()
        stage = int(rnd[0]) if rnd and rnd[0].isdigit() else 0

        if rnd and rnd != last_rnd:
            elapsed = int(time.time() - start_time)
            print(f"\n[R{rnd}] Lvl:{level} {phase} ({elapsed}s)")
            log("round", round=rnd, level=level, phase=phase)
            last_rnd = rnd

        # ── Always handle popups ──
        if handle_popup():
            time.sleep(1); pickup_loot()
            cycle += 1; continue

        # ── Pick up loot every 10 cycles ──
        if cycle % 10 == 0:
            pickup_loot()

        # ── Phase transitions ──
        if phase == "EARLY" and stage >= 4:
            phase = "ROLLDOWN"
            print(f"\n🎯 → ROLLDOWN")
            log("phase", phase="ROLLDOWN")
            rolldown_done = False

        if phase == "ROLLDOWN" and rolldown_done:
            phase = "LATEGAME"
            print(f"\n🏆 → LATEGAME")

        # ═══ EARLY: buy 1-2 cost units, build pairs ═══
        if phase == "EARLY":
            shop = read_shop()
            bought = False
            for i, ch in enumerate(shop):
                if not ch: continue
                cost = game_assets.CHAMPIONS.get(ch, {}).get("Gold", 99)
                # Buy any 1-2 cost unit — pairs upgrade to 2-star
                if cost <= 2:
                    buy_slot(i)
                    bought = True
                    print(f"  💰 {ch} ({cost}g)")
                    log("buy", champ=ch, cost=cost)

            if bought or (cycle - last_place_cycle >= 4):
                place_bench_to_board()
                last_place_cycle = cycle

            # Buy XP sparingly in stage 3
            if stage >= 3 and level < 6 and cycle % 6 == 0:
                buy_xp()
                print(f"  📈 XP (lvl {level})")

        # ═══ ROLLDOWN: level to 8, roll for carries ═══
        elif phase == "ROLLDOWN" and not rolldown_done:
            # Level to 8
            prev_lvl = api_level()
            xp_count, stall = 0, 0
            while RUNNING and api_level() < 8:
                buy_xp(); xp_count += 1
                time.sleep(0.15)
                if api_level() == prev_lvl:
                    stall += 1
                    if stall > 5: break  # no gold to buy XP
                else:
                    prev_lvl = api_level(); stall = 0
                if xp_count > 30: break
            print(f"  Leveled to {api_level()} ({xp_count} xp buys)")

            # Roll and buy everything good
            found = []
            for roll in range(20):
                if not RUNNING: break
                reroll_shop()
                shop = read_shop()
                for i, ch in enumerate(shop):
                    if not ch: continue
                    cost = game_assets.CHAMPIONS.get(ch, {}).get("Gold", 99)
                    if ch in ALWAYS_BUY or cost >= 4:
                        buy_slot(i)
                        found.append(ch)
                        print(f"  🎯 {ch} ({cost}g)")
                        log("buy", champ=ch, cost=cost)

            place_bench_to_board()
            print(f"  Rolldown: {len(found)} units bought")
            log("rolldown", found=found)
            rolldown_done = True

        # ═══ LATEGAME: opportunistic buys + level 9 ═══
        elif phase == "LATEGAME":
            shop = read_shop()
            for i, ch in enumerate(shop):
                if not ch: continue
                cost = game_assets.CHAMPIONS.get(ch, {}).get("Gold", 99)
                if ch in ALWAYS_BUY or cost >= 4:
                    buy_slot(i)
                    print(f"  ⬆️ {ch} ({cost}g)")
                    log("buy", champ=ch, cost=cost)

            if cycle % 4 == 0:
                place_bench_to_board()

            # Try to level to 9 occasionally
            if level < 9 and cycle % 5 == 0:
                buy_xp()

            # Reroll occasionally with spare gold
            if cycle % 3 == 0:
                reroll_shop()

        # ── Reset mouse ──
        pyautogui.moveTo(*DEFAULT)
        cycle += 1
        time.sleep(0.8)

except KeyboardInterrupt:
    print("\n🛑 Stopped")
finally:
    save_log()
    elapsed = int(time.time() - start_time)
    print(f"📝 {LOG_DIR}/{GID}_log.json ({len(LOG)} events, {elapsed}s)")
