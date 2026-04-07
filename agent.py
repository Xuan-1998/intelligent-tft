#!/usr/bin/env python3 -u
"""
Intelligent TFT Agent v1 — Mecha Fast 8
Cmd+= to stop
"""
import warnings; warnings.filterwarnings("ignore")
import os; os.environ["PYTHONWARNINGS"] = "ignore"
import time, sys
import pyautogui
import requests, urllib3; urllib3.disable_warnings()
from difflib import SequenceMatcher
from vec4 import Vec4
from vec2 import Vec2
from game import find_league_window
import screen_coords, ocr, mk_functions, game_assets, comps

# --- Stop: Ctrl+C ---
RUNNING = True

# ── Window setup ──
w = find_league_window()
if not w: print("No game!"); sys.exit(1)
x,y,W,H = w
Y_OFF = y+round(H*0.028); EFF_H = H-round(H*0.028)
Vec4.setup_screen(x,Y_OFF,W,EFF_H); Vec2.setup_screen(x,Y_OFF,W,EFF_H)
pyautogui.FAILSAFE = False
pyautogui.click(W//2,H//2); time.sleep(0.3)

print("═══ Intelligent TFT Agent ═══")
print(f"Window: {W}x{H} at ({x},{y})")
print("Strategy: Mecha Fast 8")
print("Cmd+= to stop\n")

# ── API ──
def api():
    try:
        r=requests.get('https://127.0.0.1:2999/liveclientdata/allgamedata',timeout=2,verify=False)
        return r.json()
    except: return None

def gold():
    d=api(); return int(d['activePlayer']['currentGold']) if d else 0

def level():
    d=api(); return int(d['activePlayer']['level']) if d else 1

# ── Planning phase detection ──
def is_planning():
    """Check if 'Planning' text is visible at top of screen"""
    try:
        # Planning text appears around top-center, y~130-170 in game coords
        txt = ocr.get_text(screenxy=(600,120,870,170), scale=3, psm=7)
        return 'lanning' in txt or 'Planning' in txt
    except: return False

# ── OCR ──
def fuzzy(raw):
    raw=raw.strip()
    if not raw or len(raw)<2: return ""
    if raw in game_assets.CHAMPIONS: return raw
    best,br="",0
    for c in game_assets.CHAMPIONS:
        r=SequenceMatcher(a=c.lower(),b=raw.lower()).ratio()
        if r>br: br,best=r,c
    return best if br>=0.55 else ""

def read_shop():
    img=ocr._grab(screen_coords.SHOP_POS.get_coords())
    return [(i,fuzzy(ocr.get_text_from_image(img.crop(n.get_coords())).strip())) for i,n in enumerate(screen_coords.CHAMP_NAME_POS)]

# ── Actions ──
def buy(targets):
    shop=read_shop(); g=gold(); bought=[]
    for slot,name in shop:
        if name in targets and g>=game_assets.CHAMPIONS.get(name,{}).get("Gold",99):
            mk_functions.left_click(screen_coords.BUY_LOC[slot].get_coords())
            time.sleep(0.2); bought.append(name); g-=game_assets.CHAMPIONS[name]["Gold"]
    return bought

def reroll(): mk_functions.left_click(screen_coords.REFRESH_LOC.get_coords()); time.sleep(0.3)
def buy_xp(): mk_functions.left_click(screen_coords.BUY_XP_LOC.get_coords()); time.sleep(0.15)

def place_bench():
    """Move bench units to board. 
    In TFT: drag a bench champ to a board hex to place them.
    If the hex is occupied, they swap. So we drag each bench slot
    to specific board positions to fill the board."""
    lv=level()
    # Drag each bench unit to a board position
    for i in range(min(9,lv)):
        src = screen_coords.BENCH_LOC[i].get_coords()
        # Place in back row positions first (21-27), then front row
        pos = 21 + (i % 7)
        dst = screen_coords.BOARD_LOC[pos].get_coords()
        drag(src, dst)

def sell_bench():
    for i in range(9): mk_functions.press_e(screen_coords.BENCH_LOC[i].get_coords()); time.sleep(0.04)

def swap_bench_to_board():
    """Drag ALL bench units onto board positions to swap/place them.
    TFT auto-swaps if the position is occupied."""
    print("  🔄 Swapping bench → board")
    for i in range(9):
        src = screen_coords.BENCH_LOC[i].get_coords()
        # Alternate between different board positions
        pos = 21 + (i % 7)
        dst = screen_coords.BOARD_LOC[pos].get_coords()
        drag(src, dst)

def sweep_loot():
    """Right-click across entire board to pick up all orbs"""
    print("  📦 Sweeping loot")
    for py in range(200,700,40):
        for px in range(300,1400,55):
            mk_functions.right_click((px,py)); time.sleep(0.03)

def drag(src,dst):
    pyautogui.moveTo(src[0],src[1]); time.sleep(0.06)
    pyautogui.mouseDown(); time.sleep(0.04)
    pyautogui.moveTo(dst[0],dst[1],duration=0.12)
    pyautogui.mouseUp(); time.sleep(0.08)

def equip_items():
    """In Set 17, items come from loot/popups and sit on bench champions or item slots.
    To equip: items on the bench can be dragged to board champions.
    We also need to handle the item component slots if they exist."""
    print("  🔧 Equipping items")
    # Board carry positions (back row where our units should be)
    carries = [screen_coords.BOARD_LOC[s].get_coords() for s in [21,22,23,24,25,26]]

    # Try dragging from each bench slot to carries
    # If a bench champ has items, clicking them picks up the item
    for i in range(9):
        src = screen_coords.BENCH_LOC[i].get_coords()
        dst = carries[i % len(carries)]
        drag(src, dst)

def click_popup():
    """Click center to dismiss popups / collect rewards.
    Also look for 'Take All' button from trait mechanics (Anima, etc)"""
    # Take All button appears at ~57% x, ~71% y when trait popups show
    pyautogui.click(int(W*0.57), int(Y_OFF+EFF_H*0.71)); time.sleep(0.3)
    # Also click center
    pyautogui.click(W//2, Y_OFF+EFF_H//2); time.sleep(0.3)

def click_left_option():
    """Click left god blessing — confirmed working at 30% x, 25% y"""
    pyautogui.click(int(W*0.30), int(Y_OFF+EFF_H*0.25)); time.sleep(0.5)

def detect_screen():
    """Detect what screen we're on by checking pixel brightness in key areas.
    Returns: 'normal', 'popup', 'god', or 'augment'"""
    import numpy as np
    try:
        # Check center of board area — normally bright (green/brown board)
        # During popups/god/augment — dark overlay
        center = ocr._grab((W//2-50, Y_OFF+EFF_H//3, W//2+50, Y_OFF+EFF_H//3+30))
        avg = np.array(center).mean()

        # Check bottom area for shop visibility
        shop = ocr._grab((int(W*0.3), int(Y_OFF+EFF_H*0.85), int(W*0.7), int(Y_OFF+EFF_H*0.9)))
        shop_avg = np.array(shop).mean()

        # Check for augment cards (3 bright rectangles in center)
        mid = ocr._grab((int(W*0.25), int(Y_OFF+EFF_H*0.4), int(W*0.75), int(Y_OFF+EFF_H*0.6)))
        mid_avg = np.array(mid).mean()

        if avg < 60:  # very dark center = god screen or special overlay
            return 'god'
        if shop_avg < 50 and mid_avg > 80:  # no shop but bright center cards = augment
            return 'augment'
        if shop_avg > 100:  # shop visible = normal or popup over board
            # Check for purple popup (Tech Resupply etc)
            bottom = ocr._grab((int(W*0.3), int(Y_OFF+EFF_H*0.65), int(W*0.7), int(Y_OFF+EFF_H*0.75)))
            bottom_arr = np.array(bottom)
            # Purple-ish = high blue+red, lower green
            if bottom_arr[:,:,2].mean() > 100 and bottom_arr[:,:,0].mean() > 80:
                return 'popup'
        return 'normal'
    except:
        return 'normal'

def handle_special_screen(screen_type):
    """Handle non-normal screens"""
    if screen_type == 'god':
        print("  ⚡ GOD SCREEN — clicking left god")
        click_left_option()
        time.sleep(2)
        click_popup()
        time.sleep(1)
    elif screen_type == 'augment':
        print("  🎯 AUGMENT — picking first option")
        # Augment cards: left ~30%, center ~50%, right ~70% of screen, ~45% y
        pyautogui.click(int(W*0.30), int(Y_OFF+EFF_H*0.45))
        time.sleep(1.5)
    elif screen_type == 'popup':
        print("  📦 POPUP — clicking Take All")
        # Take All button at ~57% x, ~71% y
        pyautogui.click(int(W*0.57), int(Y_OFF+EFF_H*0.71))
        time.sleep(0.5)
        click_popup()
        time.sleep(0.3)

# ── Main Loop ──
phase = "ECON"
cycle = 0
try:
    while RUNNING:
        g = gold(); lv = level()

        if cycle%3==0:
            print(f"[{phase}] C{cycle} G:{g} L:{lv}")

        # ── Try to act regardless of phase ──
        # During combat, shop clicks won't work anyway (shop is locked)
        # So it's safe to try buying — it just won't do anything during combat

        # ── Detect and handle special screens ──
        screen = detect_screen()
        if screen != 'normal':
            handle_special_screen(screen)
            cycle+=1; time.sleep(1); continue

        # ── Planning phase: act! ──

        # Dismiss popups / Take All every 5 cycles
        if cycle%5==0:
            click_popup()

        # Loot sweep every 8 cycles
        if cycle%8==0 and cycle>0:
            sweep_loot()

        # Item equip every 10 cycles
        if cycle%10==5:
            equip_items()

        # ═══ ECON PHASE ═══
        if phase=="ECON":
            b = buy(comps.EARLY_GAME_BUYS)
            if b: print(f"  🛒 {b}"); swap_bench_to_board()
            if g>54 and lv<5: buy_xp()
            if (g>=50 and lv>=5 and cycle>30) or (cycle>50):
                phase="ROLLDOWN"; print("\n🚀 ROLLDOWN\n")

        # ═══ ROLLDOWN PHASE ═══
        elif phase=="ROLLDOWN":
            while level()<8 and gold()>4: buy_xp()
            print(f"  Level {level()}")
            sell_bench(); time.sleep(0.3)
            found=[]; rolls=0
            targets = comps.ROLLDOWN_BUYS | comps.EARLY_GAME_BUYS
            while gold()>10 and rolls<25 and RUNNING:
                reroll()
                b=buy(targets)
                if b: found.extend(b); print(f"  ✨ {b}")
                rolls+=1
            place_bench(); equip_items()
            print(f"  Rolled {rolls}x → {found}")
            phase="LATE"; print("\n🏆 LATEGAME\n")

        # ═══ LATEGAME ═══
        elif phase=="LATE":
            if g>30:
                reroll()
                b=buy(comps.ROLLDOWN_BUYS|comps.EARLY_GAME_BUYS)
                if b: print(f"  ⬆ {b}"); swap_bench_to_board()
            if g>60 and lv<9: buy_xp()

        mk_functions.move_mouse(screen_coords.DEFAULT_LOC.get_coords())
        cycle+=1; time.sleep(2)

except KeyboardInterrupt: pass
print("Agent done.")
