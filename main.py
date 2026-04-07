"""
Where the bot execution starts & contains the game loop that keeps the bot running indefinitely
macOS version: tkinter runs on main thread, game logic runs in a background thread.
"""

import threading
import queue
import auto_queue
from game import Game
import settings


def game_loop(ui_queue):
    """Keeps the program running indefinitely by calling queue and game start in a loop"""
    while True:
        auto_queue.queue()
        Game(ui_queue)


if __name__ == "__main__":
    if settings.LEAGUE_CLIENT_PATH is None:
        raise ValueError("No league client path specified. Please set the path in settings.py")

    message_queue = queue.Queue()

    print("TFT OCR Bot (macOS) | https://github.com/Xuan-1998/tft-ocr-bot")
    print("Press Ctrl+C to stop")

    game_thread = threading.Thread(target=game_loop, args=(message_queue,), daemon=True)
    game_thread.start()

    # On macOS, skip the tkinter overlay — it causes issues with multiprocessing/spawn.
    # Just let the game thread run and print status to console.
    try:
        game_thread.join()
    except KeyboardInterrupt:
        print("\n[!] Bot stopped by user")
