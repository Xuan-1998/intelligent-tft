"""
Handles sending input to the game, coords contain a cartesian ordered pair (x, y)
"""

import random
import pyautogui

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.03


def left_click(coords: tuple) -> None:
    """Left clicks at argument ones coordinates"""
    offset: int = random.randint(-3, 3)
    pyautogui.click(coords[0] + offset, coords[1] + offset)


def right_click(coords: tuple) -> None:
    """Right clicks at argument ones coordinates"""
    offset: int = random.randint(-3, 3)
    pyautogui.click(coords[0] + offset, coords[1] + offset, button="right")


def press_e(coords: tuple) -> None:
    """Presses e at argument ones coordinates"""
    offset: int = random.randint(-3, 3)
    pyautogui.moveTo(coords[0] + offset, coords[1] + offset)
    pyautogui.press("e")


def move_mouse(coords: tuple) -> None:
    """Moves mouse to argument ones coordinates"""
    pyautogui.moveTo(coords[0], coords[1])


def buy_xp() -> None:
    """Presses hotkey to purchase XP"""
    pyautogui.press("f")


def reroll() -> None:
    """Presses hotkey to purchase reroll"""
    pyautogui.press("d")


def press_esc() -> None:
    """Presses escape key"""
    pyautogui.press("esc")
