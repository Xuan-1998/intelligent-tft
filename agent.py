#!/usr/bin/env python3 -u
"""TFT Agent v7 — scout opponents, buy during planning only, proper econ.
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
BUY_XP = screen_coords.BUY_XP_LOC.get_coords()
REROLL = screen_coords.REFRESH_LOC.get_coords()
DEFAULT = screen_coords.DEFAULT_LOC.get_coords()
AUG_LOC = [a.get_coords() for a in screen_coords.AUGMENT_LOC]
ALL_C = set(game_assets.CHAMPIONS.keys())
GOLD_BOX = (830, 845, 890, 885)
PORTRAITS = [(1355, y) for y in range(204, 580, 54)]

# ── Logging ──
LOG_DIR = os.path.expanduser("~/intelligent-tft/game_logs")
SCOUT_DIR = os.path.expanduser("~/intelligent-tft/scout_logs")
os.makedirs(LOG_DIR, exist_ok=True); os.makedirs(SCOUT_DIR, exist_ok=True)
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

# ── API ──
def api():
    try: return requests.get("https://127.0.0.1:2999/liveclientdata/allgamedata", timeout=3, verify=False).json()
    except: return None

def api_level():
    d = api(); return int(d["activePlayer"]["level"]) if d else -1

def api_alive():
    d = api()
    if not d: return False, 8
    me = d["activePlayer"].get("riotIdGameName", "")
    for p in d["allPlayers"]:
        if p.get("riotIdGameName") == me and p.get("isDead"):
            return False, sum(1 for pl in d["allPlayers"] if not pl.get("isDead")) + 1
    return True, 0

# ── OCR ──
def fuzzy(t):
    if not t or len(t) < 2: return None
    best, sc = None, 0
    for n in ALL_C:
        s = SequenceMatcher(None, t.lower(), n.lower()).ratio()
        if s > sc: best, sc = n, s
    return best if sc >= 0.5 else None

def read_gold():
    try:
        t = ocr.get_text(GOLD_BOX, 3, 7, '0123456789')
        return int(t) if t and t.isdigit() else -1
    except: return -1

def read_round():
    for box in [(640, 72, 740, 102), (650, 75, 730, 100)]:
        try:
            t = ocr.get_text(box, 3, 7, ocr.ROUND_WHITELIST)
            m = re.search(r'([1-7])-([1-7])', t or "")
            if m: return m.group(0)
        except: pass
    return ""

def is_planning():
    return read_gold() >= 0

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
def buy_slot(i): pyautogui.click(*BUY[i]); time.sleep(0.25)
def buy_xp(): pyautogui.click(*BUY_XP); time.sleep(0.2)
def reroll_shop(): pyautogui.click(*REROLL); time.sleep(0.25)

def place_bench_to_board():
    lvl = api_level()
    if lvl <= 0: lvl = 8
    pos = [21, 22, 23, 24, 0, 1, 2, 3, 14]
    for i in range(min(9, lvl)):
        pyautogui.click(*BENCH[i]); time.sleep(0.3)
        pyautogui.click(*BOARD[pos[i]]); time.sleep(0.3)

def pickup_loot():
    for ly in range(Y_OFF + int(EFF_H*0.25), Y_OFF + int(EFF_H*0.65), 70):
        for lx in range(x + int(W*0.25), x + int(W*0.75), 90):
            pyautogui.rightClick(lx, ly); time.sleep(0.01)

def handle_popup():
    p = detect_popup()
    if p == "god":
        print("  🔮 God → left"); pyautogui.click(int(W*0.30), int(Y_OFF+EFF_H*0.25)); time.sleep(2)
        log("god"); return True
    if p == "augment":
        print("  ⭐ Augment → first"); pyautogui.click(*AUG_LOC[0]); time.sleep(2)
        log("augment"); return True
    return False

def slam_items():
    slots = [p[0].get_coords() for p in screen_coords.ITEM_POS]
    targets = [BOARD[21], BOARD[22], BOARD[0], BOARD[1]]
    for i, s in enumerate(slots):
        t = targets[i % len(targets)]
        pyautogui.moveTo(*s); time.sleep(0.05)
        pyautogui.mouseDown(); time.sleep(0.05)
        pyautogui.moveTo(*t, duration=0.1); pyautogui.mouseUp(); time.sleep(0.1)

def scout_opponents():
    ts = time.strftime('%Y%m%d_%H%M%S')
    for i, (px, py) in enumerate(PORTRAITS[:7]):
        pyautogui.click(px, py); time.sleep(0.8)
        try: ocr._grab((0, 33, 1370, 850)).save(f'{SCOUT_DIR}/{ts}_p{i+1}.png')
        except: pass
    pyautogui.press('space'); time.sleep(0.5)
    print(f"  🔍 Scouted 7 opponents")
    log("scout")

# ═══ MAIN ═══
print(f"═══ TFT Agent v7 | {GID} ═══")
rnd = read_round(); lvl = api_level(); gold = read_gold()
stage = int(rnd[0]) if rnd and rnd[0].isdigit() else 0

if stage >= 5 or lvl >= 8: phase = "LATEGAME"
elif stage >= 4 or lvl >= 6: phase = "ROLLDOWN"
else: phase = "EARLY"

print(f"Start: R{rnd} G:{gold} Lvl:{lvl} → {phase}")
log("startup", round=rnd, gold=gold, level=lvl, phase=phase)

last_rnd = ""; cycle = 0; start = time.time(); scouted = False

try:
    while RUNNING:
        alive, placement = api_alive()
        if not alive:
            print(f"\n☠️ Placement: {placement}")
            log("game_over", placement=placement); save_history(placement); break

        lvl = api_level(); gold = read_gold()
        rnd = read_round(); stage = int(rnd[0]) if rnd and rnd[0].isdigit() else 0

        if rnd and rnd != last_rnd:
            print(f"\n[R{rnd}] G:{gold} Lvl:{lvl} {phase} ({int(time.time()-start)}s)")
            log("round", round=rnd, gold=gold, level=lvl, phase=phase)
            last_rnd = rnd; scouted = False

        if handle_popup():
            time.sleep(1); pickup_loot(); cycle += 1; continue

        if cycle % 10 == 0 and cycle > 0: pickup_loot()

        planning = is_planning()

        # ── Phase transitions ──
        if phase == "EARLY" and (stage >= 4 or lvl >= 7):
            phase = "ROLLDOWN"
            print(f"\n🎯 → ROLLDOWN (g={gold} lvl={lvl})")
            log("phase", phase="ROLLDOWN")

        # ═══ EARLY: buy cheap comp units, preserve interest ═══
        if phase == "EARLY" and planning:
            shop = read_shop()
            for i, ch in enumerate(shop):
                if not ch: continue
                cost = game_assets.CHAMPIONS.get(ch, {}).get("Gold", 99)
                g = read_gold()
                if g < 0 or cost > g: continue
                floor = (g // 10) * 10
                if ch in comps.EARLY_GAME_BUYS and cost <= 2 and (g - cost) >= floor:
                    buy_slot(i)
                    print(f"  💰 {ch} ({cost}g)")
                    log("buy", champ=ch, cost=cost)

            # XP only if excess gold (>50) in stage 3
            if stage >= 3 and gold > 50 and lvl < 7:
                for _ in range(2): buy_xp()
                print(f"  📈 XP→{api_level()}")

            if cycle % 4 == 0: place_bench_to_board()
            if cycle % 6 == 0: slam_items()
            if not scouted and stage >= 3:
                scout_opponents(); scouted = True

        # ═══ ROLLDOWN: level 8, roll for carries ═══
        elif phase == "ROLLDOWN" and planning:
            ct = 0
            while RUNNING and api_level() < 8 and ct < 40:
                g = read_gold()
                if g >= 0 and g < 4: break
                buy_xp(); ct += 1; time.sleep(0.2)
            print(f"  Leveled to {api_level()}")

            targets = comps.ROLLDOWN_BUYS | comps.EARLY_GAME_BUYS
            found = []
            for roll in range(25):
                if not RUNNING: break
                g = read_gold()
                if g >= 0 and g < 10: break
                reroll_shop()
                shop = read_shop()
                for i, ch in enumerate(shop):
                    if not ch: continue
                    cost = game_assets.CHAMPIONS.get(ch, {}).get("Gold", 99)
                    if ch in targets or cost >= 4:
                        buy_slot(i); found.append(ch)
                        print(f"  🎯 {ch} ({cost}g)")
                        log("buy", champ=ch, cost=cost)

            place_bench_to_board(); slam_items()
            print(f"  Rolldown: {found}")
            log("rolldown", found=found)
            phase = "LATEGAME"; print(f"\n🏆 → LATEGAME")

        # ═══ LATEGAME: slow roll upgrades ═══
        elif phase == "LATEGAME" and planning:
            g = read_gold()
            if g > 30:
                reroll_shop()
                shop = read_shop()
                for i, ch in enumerate(shop):
                    if not ch: continue
                    cost = game_assets.CHAMPIONS.get(ch, {}).get("Gold", 99)
                    if cost >= 3: buy_slot(i); print(f"  ⬆️ {ch}")
                place_bench_to_board()
            if g > 50 and lvl < 9: buy_xp()
            if cycle % 8 == 0: slam_items()
            if not scouted: scout_opponents(); scouted = True

        pyautogui.moveTo(*DEFAULT); cycle += 1; time.sleep(1.5)

except KeyboardInterrupt:
    print("\n🛑 Stopped")
finally:
    save_log()
    print(f"📝 {LOG_DIR}/{GID}_log.json ({len(LOG)} events, {int(time.time()-start)}s)")
    print(f"📸 Scouts: {SCOUT_DIR}/")
