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
from pynput import keyboard
from difflib import SequenceMatcher
from vec4 import Vec4
from vec2 import Vec2
from game import find_league_window
import screen_coords, ocr, mk_functions, game_assets, comps

# ── Stop hotkey: Cmd+= ──
RUNNING = True
_keys = set()
def _kp(key):
    global RUNNING; _keys.add(key)
    if keyboard.Key.cmd in _keys or keyboard.Key.cmd_r in _keys:
        try:
            if hasattr(key,'char') and key.char=='=':
                RUNNING=False; print("\n🛑 Stopped"); return False
        except: pass
def _kr(key): _keys.discard(key)
keyboard.Listener(on_press=_kp, on_release=_kr, daemon=True).start()

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
    lv=level()
    for i in range(min(9,lv)):
        mk_functions.left_click(screen_coords.BENCH_LOC[i].get_coords()); time.sleep(0.08)
        mk_functions.left_click(screen_coords.BOARD_LOC[21+(i%7)].get_coords()); time.sleep(0.08)

def sell_bench():
    for i in range(9): mk_functions.press_e(screen_coords.BENCH_LOC[i].get_coords()); time.sleep(0.04)

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
    """Drag items from item bench onto board carries"""
    print("  🔧 Equipping items")
    carries = [21,22,23,24,25,26]  # back row board positions
    carry_coords = [screen_coords.BOARD_LOC[s].get_coords() for s in carries]
    for i in range(min(10,len(screen_coords.ITEM_POS))):
        src = screen_coords.ITEM_POS[i][0].get_coords()
        dst = carry_coords[i%len(carry_coords)]
        drag(src, dst)

def click_popup():
    """Click center to dismiss popups / collect rewards"""
    pyautogui.click(W//2, Y_OFF+EFF_H//2); time.sleep(0.3)

def click_left_option():
    """Click left option for god selection"""
    pyautogui.click(int(W*0.30), Y_OFF+int(EFF_H*0.45)); time.sleep(0.5)

# ── Main Loop ──
phase = "ECON"
cycle = 0
try:
    while RUNNING:
        g = gold(); lv = level()
        planning = is_planning()

        if cycle%3==0:
            status = "⏳COMBAT" if not planning else "📋PLAN"
            print(f"[{phase}|{status}] C{cycle} G:{g} L:{lv}")

        # ── Combat phase: do nothing, just wait ──
        if not planning:
            time.sleep(1.5); cycle+=1; continue

        # ── Planning phase: act! ──

        # Dismiss popups / god selection every few cycles
        if cycle%12==0:
            click_left_option(); time.sleep(0.3)
            click_popup()

        # Loot sweep every 10 cycles
        if cycle%10==0 and cycle>0:
            sweep_loot()

        # Item equip every 12 cycles
        if cycle%12==6:
            equip_items()

        # ═══ ECON PHASE ═══
        if phase=="ECON":
            b = buy(comps.EARLY_GAME_BUYS)
            if b: print(f"  🛒 {b}"); place_bench()
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
                if b: print(f"  ⬆ {b}"); place_bench()
            if g>60 and lv<9: buy_xp()

        mk_functions.move_mouse(screen_coords.DEFAULT_LOC.get_coords())
        cycle+=1; time.sleep(2)

except KeyboardInterrupt: pass
print("Agent done.")
