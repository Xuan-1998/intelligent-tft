#!/usr/bin/env python3 -u
"""TFT Agent v4 — calibrated OCR + API level, Mecha Fast 8, evolution log
Press Cmd+= to stop at any time.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, time, re
os.environ["PYTHONWARNINGS"] = "ignore"

import pyautogui
import requests, urllib3; urllib3.disable_warnings()
from difflib import SequenceMatcher
from pynput import keyboard

from vec4 import Vec4
from vec2 import Vec2
from game import find_league_window
import screen_coords, ocr, game_assets, comps

# ── Cmd+= global stop ──
RUNNING = True
_keys = set()
def _on_press(key):
    global RUNNING
    _keys.add(key)
    if (keyboard.Key.cmd in _keys or keyboard.Key.cmd_r in _keys):
        try:
            if hasattr(key, 'char') and key.char == '=':
                RUNNING = False
                print("\n🛑 Cmd+= pressed — stopping after this cycle")
                return False
        except: pass
def _on_release(key):
    _keys.discard(key)
keyboard.Listener(on_press=_on_press, on_release=_on_release, daemon=True).start()

# ── Window setup ──
w = find_league_window()
if not w:
    print("NO GAME WINDOW"); sys.exit(1)
x, y, W, H = w
Y_OFF = y + round(H * 0.028)
EFF_H = H - round(H * 0.028)
Vec4.setup_screen(x, Y_OFF, W, EFF_H)
Vec2.setup_screen(x, Y_OFF, W, EFF_H)
pyautogui.FAILSAFE = False

# ── Precompute coords ──
BUY = [b.get_coords() for b in screen_coords.BUY_LOC]
BENCH = [b.get_coords() for b in screen_coords.BENCH_LOC]
BOARD = [b.get_coords() for b in screen_coords.BOARD_LOC]
BUY_XP = screen_coords.BUY_XP_LOC.get_coords()
REROLL = screen_coords.REFRESH_LOC.get_coords()
DEFAULT = screen_coords.DEFAULT_LOC.get_coords()
AUG_LOC = [a.get_coords() for a in screen_coords.AUGMENT_LOC]
ALL_C = set(game_assets.CHAMPIONS.keys())

# ── Calibrated OCR boxes (absolute screen coords for 1728x1002 window at 0,33) ──
# These are hardcoded to the actual pixel positions on this display.
# Gold number (right of coin icon in bottom HUD)
GOLD_BOX = (830, 845, 890, 885)
# Round indicator (top center bar, e.g. "3-1")
ROUND_BOX = (640, 72, 740, 102)

# ── Logging ──
LOG_DIR = os.path.expanduser("~/intelligent-tft/game_logs")
os.makedirs(LOG_DIR, exist_ok=True)
GID = time.strftime("%Y%m%d_%H%M%S")
LOG = []
HISTORY_FILE = os.path.expanduser("~/intelligent-tft/game_history.jsonl")

def log(ev, **kw):
    LOG.append({"t": time.strftime("%H:%M:%S"), "ev": ev, **kw})
    # Screenshot on key events
    if ev in ("round", "god", "augment", "game_over", "phase", "rolldown"):
        try:
            ocr._grab((0, 33, 1728, 1035)).save(f"{LOG_DIR}/{GID}_{ev}_{len(LOG)}.png")
        except: pass

def log_state(gold, level, rnd, phase, cycle, shop=None, action=None):
    """Detailed state log for evolution review"""
    entry = {"t": time.strftime("%H:%M:%S"), "ev": "tick",
             "gold": gold, "level": level, "round": rnd,
             "phase": phase, "cycle": cycle}
    if shop: entry["shop"] = [s for s in shop if s]
    if action: entry["action"] = action
    LOG.append(entry)

def save_log():
    with open(f"{LOG_DIR}/{GID}_log.json", "w") as f:
        json.dump(LOG, f, indent=1)

def save_history(placement):
    with open(HISTORY_FILE, "a") as f:
        f.write(json.dumps({"time": time.strftime("%Y-%m-%d %H:%M"), "gid": GID,
                             "placement": placement, "events": len(LOG)}) + "\n")

def load_history():
    if not os.path.exists(HISTORY_FILE): return []
    with open(HISTORY_FILE) as f:
        return [json.loads(l) for l in f if l.strip()]

# ── API helpers ──
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

# ── OCR helpers ──
def fuzzy(t):
    if not t or len(t) < 2: return None
    best, score = None, 0
    for n in ALL_C:
        sc = SequenceMatcher(None, t.lower(), n.lower()).ratio()
        if sc > score: best, score = n, sc
    return best if score >= 0.55 else None

def read_gold():
    try:
        t = ocr.get_text(GOLD_BOX, 3, 7, '0123456789')
        return int(t) if t and t.isdigit() else -1
    except: return -1

def read_round():
    try:
        t = ocr.get_text(ROUND_BOX, 3, 7, ocr.ROUND_WHITELIST)
        m = re.search(r'([1-7])-([1-7])', t or "")
        return m.group(0) if m else ""
    except: return ""

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

def buy_champion(slot_idx):
    click(*BUY[slot_idx], 0.25)

def buy_xp():
    click(*BUY_XP, 0.15)

def reroll_shop():
    click(*REROLL, 0.2)

def place_bench_to_board():
    """Move bench units to board — only if board has room"""
    level = api_level()
    if level <= 0: level = 8
    # Try to place up to (level) units, stop if board is full
    for i in range(min(9, level)):
        pyautogui.click(*BENCH[i])
        time.sleep(0.3)
        pyautogui.click(*BOARD[21 + (i % 7)])
        time.sleep(0.3)

def pickup_loot():
    for ly in range(300, 650, 60):
        for lx in range(400, 1400, 80):
            pyautogui.rightClick(lx, ly); time.sleep(0.02)

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

# ── Evolution ──
def get_econ_threshold():
    hist = load_history()
    if len(hist) < 3: return 50
    avg = sum(g["placement"] for g in hist[-5:]) / min(len(hist), 5)
    if avg > 5: return 30
    if avg < 3: return 60
    return 50

# ── Main loop ──
print(f"═══ TFT Agent v4 | {GID} ═══")
econ_target = get_econ_threshold()
print(f"Econ target: {econ_target}g | Window: {W}x{H} at ({x},{y})")

# Detect current game state on startup
init_rnd = read_round()
init_level = api_level()
init_gold = read_gold()
init_stage = int(init_rnd[0]) if init_rnd and init_rnd[0].isdigit() else 0

if init_stage >= 5 or (init_stage >= 4 and init_level >= 8):
    phase = "LATEGAME"
elif init_stage >= 4:
    phase = "ROLLDOWN"
else:
    phase = "EARLY"

print(f"Start: R{init_rnd} G:{init_gold} Lvl:{init_level} → {phase}")
log("startup", round=init_rnd, gold=init_gold, level=init_level, phase=phase)
last_rnd = ""
cycle = 0
buys_total = 0
start_time = time.time()

try:
    while RUNNING:
        alive, placement = api_alive()
        if not alive:
            print(f"\n☠️ Game over! Placement: {placement}")
            log("game_over", placement=placement)
            save_history(placement)
            break

        gold = read_gold()
        level = api_level()
        rnd = read_round()
        stage = int(rnd[0]) if rnd and rnd[0].isdigit() else 0

        if rnd and rnd != last_rnd:
            elapsed = int(time.time() - start_time)
            print(f"\n[R{rnd}] G:{gold} Lvl:{level} {phase} ({elapsed}s)")
            log("round", round=rnd, gold=gold, level=level, phase=phase)
            last_rnd = rnd

        # Log state every 5 cycles for evolution review
        if cycle % 5 == 0:
            log_state(gold, level, rnd, phase, cycle)

        # ── Popups ──
        if handle_popup():
            time.sleep(1); pickup_loot()
            cycle += 1; continue

        # ── Loot on PvE starts ──
        if rnd and rnd.endswith("-1") and cycle % 4 == 0:
            pickup_loot()

        # ── Phase transitions (only roll down at stage 4+) ──
        if phase == "EARLY" and stage >= 4:
            phase = "ROLLDOWN"
            print(f"\n🎯 → ROLLDOWN (g={gold} lvl={level})")
            log("phase", phase="ROLLDOWN")

        # ── EARLY: save gold, only buy 1-cost frontline if it won't break econ ──
        if phase == "EARLY":
            shop = read_shop()
            for i, ch in enumerate(shop):
                if not ch: continue
                cost = game_assets.CHAMPIONS.get(ch, {}).get("Gold", 99)
                if gold < 0 or cost > gold: continue
                # Only buy 1-cost units, and only if we stay above interest threshold
                # Interest breakpoints: 10,20,30,40,50
                next_threshold = ((gold // 10)) * 10
                if ch in comps.EARLY_GAME_BUYS and cost == 1 and gold - cost >= next_threshold:
                    buy_champion(i); gold -= cost; buys_total += 1
                    print(f"  💰 {ch} ({cost}g) [g→{gold}]")
                    log("buy", champ=ch, cost=cost)

            if buys_total > 0 and cycle % 3 == 0:
                place_bench_to_board()

            # No XP buying in early game — pure econ

        # ── ROLLDOWN: level 8, roll for carries ──
        elif phase == "ROLLDOWN":
            xp_count = 0
            while RUNNING and api_level() < 8 and read_gold() > 4:
                buy_xp(); xp_count += 1
                if xp_count > 20: break
            print(f"  Level: {api_level()}")

            targets = comps.ROLLDOWN_BUYS | comps.EARLY_GAME_BUYS
            rolls, found = 0, []
            while RUNNING and read_gold() > 10 and rolls < 30:
                reroll_shop()
                shop = read_shop()
                for i, ch in enumerate(shop):
                    if not ch: continue
                    cost = game_assets.CHAMPIONS.get(ch, {}).get("Gold", 99)
                    g = read_gold()
                    if g < 0 or cost > g: continue
                    # Buy targets + any 4/5-cost (strong at lvl 8)
                    if ch in targets or cost >= 4:
                        buy_champion(i); found.append(ch)
                        print(f"  🎯 {ch} ({cost}g)")
                        log("buy", champ=ch, cost=cost)
                rolls += 1

            place_bench_to_board()
            print(f"  Rolled {rolls}x, found: {found}")
            log("rolldown", rolls=rolls, found=found)
            phase = "LATEGAME"
            print(f"\n🏆 → LATEGAME")

        # ── LATEGAME: upgrade + level 9 ──
        elif phase == "LATEGAME":
            g = read_gold()
            if g > 30:
                reroll_shop()
                shop = read_shop()
                targets = comps.ROLLDOWN_BUYS | comps.EARLY_GAME_BUYS
                for i, ch in enumerate(shop):
                    if ch and ch in targets:
                        cost = game_assets.CHAMPIONS.get(ch, {}).get("Gold", 99)
                        if cost <= g:
                            buy_champion(i); g -= cost
                            print(f"  ⬆️ {ch} ({cost}g)")
                            log("buy", champ=ch, cost=cost)
                place_bench_to_board()
            if g > 60 and api_level() < 9:
                buy_xp(); print("  📈 XP→9")

        # ── Periodic: dismiss stray popups ──
        if cycle % 10 == 0 and cycle > 0:
            pyautogui.click(W // 2, Y_OFF + EFF_H // 2)
            time.sleep(0.3)

        pyautogui.moveTo(*DEFAULT)
        cycle += 1
        time.sleep(1.5)

except KeyboardInterrupt:
    print("\n🛑 Stopped")
finally:
    save_log()
    elapsed = int(time.time() - start_time)
    print(f"📝 {LOG_DIR}/{GID}_log.json ({len(LOG)} events, {elapsed}s)")
    hist = load_history()
    if hist:
        recent = hist[-5:]
        print(f"📊 Last {len(recent)} games avg: {sum(g['placement'] for g in recent)/len(recent):.1f}")
