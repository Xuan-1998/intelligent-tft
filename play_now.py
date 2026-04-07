"""
TFT Set 17 Bot v5 - Mecha Fast 8 - SIMPLIFIED
Just works. No fancy detection. Acts every cycle.
Cmd+= to stop.
"""
import time, sys, os
import warnings
warnings.filterwarnings("ignore")  # suppress SSL warnings
os.environ["PYTHONWARNINGS"] = "ignore"

import pyautogui
import comps, game_assets, mk_functions, screen_coords, ocr
from vec4 import Vec4
from vec2 import Vec2
from game import find_league_window
from difflib import SequenceMatcher
from pynput import keyboard
import requests, urllib3
urllib3.disable_warnings()

# --- Cmd+= to stop ---
BOT_RUNNING = True
_keys = set()
def _on_press(key):
    global BOT_RUNNING
    _keys.add(key)
    if keyboard.Key.cmd in _keys or keyboard.Key.cmd_r in _keys:
        try:
            if hasattr(key, 'char') and key.char == '=':
                BOT_RUNNING = False
                print("\n🛑 Cmd+= — STOPPED\n")
                return False
        except: pass
def _on_release(key):
    _keys.discard(key)
keyboard.Listener(on_press=_on_press, on_release=_on_release, daemon=True).start()

# --- Setup ---
w = find_league_window()
if not w:
    print("No game window!")
    sys.exit(1)

x, y, W, H = w
Y_OFF = y + round(H * 0.028)
EFF_H = H - round(H * 0.028)
Vec4.setup_screen(x, Y_OFF, W, EFF_H)
Vec2.setup_screen(x, Y_OFF, W, EFF_H)

pyautogui.FAILSAFE = False
pyautogui.click(W//2, H//2)
time.sleep(0.3)

print("=== TFT BOT v5 | Mecha Fast 8 | Cmd+= to stop ===\n")

# --- API helpers ---
def api_data():
    try:
        r = requests.get('https://127.0.0.1:2999/liveclientdata/allgamedata', timeout=3, verify=False)
        return r.json()
    except: return None

def get_gold():
    d = api_data()
    return int(d['activePlayer']['currentGold']) if d else 0

def get_level():
    d = api_data()
    return int(d['activePlayer']['level']) if d else 1

def get_health():
    try:
        d = api_data()
        # TFT API doesn't always have health, estimate from player list
        return 100  # fallback
    except: return 100

# --- OCR helpers ---
def fuzzy(raw):
    raw = raw.strip()
    if not raw or len(raw) < 2: return ""
    if raw in game_assets.CHAMPIONS: return raw
    best, best_r = "", 0
    for c in game_assets.CHAMPIONS:
        r = SequenceMatcher(a=c.lower(), b=raw.lower()).ratio()
        if r > best_r: best_r, best = r, c
    return best if best_r >= 0.55 else ""

def read_shop():
    try:
        img = ocr._grab(screen_coords.SHOP_POS.get_coords())
        shop = []
        for idx, np in enumerate(screen_coords.CHAMP_NAME_POS):
            crop = img.crop(np.get_coords())
            raw = ocr.get_text_from_image(crop).strip()
            shop.append((idx, fuzzy(raw)))
        return shop
    except: return []

# --- Actions ---
def buy_from_shop(targets):
    shop = read_shop()
    gold = get_gold()
    bought = []
    for slot, name in shop:
        if name in targets and gold >= game_assets.CHAMPIONS.get(name, {}).get("Gold", 99):
            mk_functions.left_click(screen_coords.BUY_LOC[slot].get_coords())
            time.sleep(0.2)
            bought.append(name)
            gold -= game_assets.CHAMPIONS[name]["Gold"]
    return bought

def reroll():
    mk_functions.left_click(screen_coords.REFRESH_LOC.get_coords())
    time.sleep(0.3)

def buy_xp():
    mk_functions.left_click(screen_coords.BUY_XP_LOC.get_coords())
    time.sleep(0.15)

def place_bench():
    level = get_level()
    for i in range(min(9, level)):
        mk_functions.left_click(screen_coords.BENCH_LOC[i].get_coords())
        time.sleep(0.08)
        mk_functions.left_click(screen_coords.BOARD_LOC[21 + (i % 7)].get_coords())
        time.sleep(0.08)

def sell_bench():
    # Sell all bench units (clean slate)
    for i in range(9):
        mk_functions.press_e(screen_coords.BENCH_LOC[i].get_coords())
        time.sleep(0.05)

def drag_item(src, dst):
    """Drag from src coords to dst coords"""
    pyautogui.moveTo(src[0], src[1])
    time.sleep(0.08)
    pyautogui.mouseDown()
    time.sleep(0.05)
    pyautogui.moveTo(dst[0], dst[1], duration=0.15)
    time.sleep(0.05)
    pyautogui.mouseUp()
    time.sleep(0.1)

def pickup_loot():
    # Dense sweep of entire board to grab all orbs/loot/god rewards
    print("  📦 Sweeping board for loot...")
    for py in range(200, 750, 35):
        for px in range(250, 1500, 50):
            mk_functions.right_click((px, py))
            time.sleep(0.04)
    pyautogui.click(W//2, Y_OFF + EFF_H//2)
    time.sleep(0.3)

def place_items():
    """Drag items from item bench onto carry champions."""
    print("  🔧 Dragging items onto carries")
    carry_slots = [14, 24, 0, 25, 26]
    carry_coords = [screen_coords.BOARD_LOC[s].get_coords() for s in carry_slots]

    for i in range(min(10, len(screen_coords.ITEM_POS))):
        src = screen_coords.ITEM_POS[i][0].get_coords()
        dst = carry_coords[i % len(carry_coords)]
        drag_item(src, dst)

def click_center():
    """Click center of game — used for god selection, augments, loot collection"""
    pyautogui.click(W//2, Y_OFF + EFF_H//2)
    time.sleep(0.5)

def click_left_option():
    """Click left side option (god blessing, augment)"""
    pyautogui.click(int(W * 0.30), Y_OFF + int(EFF_H * 0.45))
    time.sleep(0.5)

# ============ MAIN LOOP ============
phase = "ECON"
cycle = 0
last_action_time = 0

try:
    while BOT_RUNNING:
        gold = get_gold()
        level = get_level()

        if cycle % 5 == 0:
            print(f"[{phase}] C{cycle} Gold:{gold} Lvl:{level}")

        # --- Every 10 cycles: try clicking center to dismiss popups/collect loot ---
        if cycle % 10 == 0:
            click_center()
            time.sleep(0.3)

        # --- Every 15 cycles: try clicking left option for god/augment ---
        if cycle % 15 == 0:
            click_left_option()
            time.sleep(0.5)
            click_center()  # collect rewards after
            time.sleep(0.3)

        # --- Every 8 cycles: pickup loot ---
        if cycle % 8 == 0 and cycle > 0:
            pickup_loot()

        # --- Every 10 cycles: place items on carries ---
        if cycle % 10 == 0 and cycle > 0:
            place_items()

        # === ECON PHASE: save gold, buy cheap frontline ===
        if phase == "ECON":
            bought = buy_from_shop(comps.EARLY_GAME_BUYS)
            if bought:
                print(f"  Bought: {bought}")
                place_bench()

            # Buy XP only above 50 gold
            if gold > 54 and level < 5:
                buy_xp()

            # Transition: enough gold + high enough level, or low HP
            if (gold >= 50 and level >= 5 and cycle > 30):
                phase = "ROLLDOWN"
                print("\n🚀 ROLLDOWN — leveling to 8 and rolling!\n")

        # === ROLLDOWN PHASE: level 8, roll for carries ===
        elif phase == "ROLLDOWN":
            # Level to 8
            while get_level() < 8 and get_gold() > 4:
                buy_xp()
            print(f"  Level: {get_level()}")

            sell_bench()
            time.sleep(0.3)

            # Roll for core
            found = []
            all_targets = comps.ROLLDOWN_BUYS | comps.EARLY_GAME_BUYS
            rolls = 0
            while get_gold() > 10 and rolls < 25 and BOT_RUNNING:
                reroll()
                b = buy_from_shop(all_targets)
                if b:
                    found.extend(b)
                    print(f"  Found: {b}")
                rolls += 1

            place_bench()
            place_items()
            print(f"  Rolled {rolls}x, total found: {found}")
            phase = "LATEGAME"
            print("\n🏆 LATEGAME\n")

        # === LATEGAME: upgrade + level 9 ===
        elif phase == "LATEGAME":
            if gold > 30:
                reroll()
                b = buy_from_shop(comps.ROLLDOWN_BUYS | comps.EARLY_GAME_BUYS)
                if b:
                    print(f"  Upgrade: {b}")
                    place_bench()
            if gold > 60 and level < 9:
                buy_xp()

        mk_functions.move_mouse(screen_coords.DEFAULT_LOC.get_coords())
        cycle += 1
        time.sleep(2)

except KeyboardInterrupt:
    pass

print("Bot done.")
