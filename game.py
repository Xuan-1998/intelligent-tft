"""
Handles tasks that happen each game round
"""

from time import sleep, perf_counter
import random
import multiprocessing
import settings
import game_assets
import game_functions
from arena import Arena
from vec4 import Vec4
from vec2 import Vec2

# macOS: use Quartz to find game window
from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID,
)


def find_league_window():
    """Find the League of Legends game window on macOS using Quartz"""
    windows = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
    for win in windows:
        name = win.get("kCGWindowName", "") or ""
        if "League of Legends (TM) Client" in name and win.get("kCGWindowBounds"):
            bounds = win["kCGWindowBounds"]
            x = int(bounds["X"])
            y = int(bounds["Y"])
            w = int(bounds["Width"])
            h = int(bounds["Height"])
            if w > 200 and h > 200:
                return (x, y, w, h)
    return None


class Game:
    """Game class that handles game logic such as round tasks"""

    def __init__(self, message_queue: multiprocessing.Queue) -> None:
        self.message_queue = message_queue
        self.arena = Arena(self.message_queue)
        self.round = "0-0"
        self.time: None = None
        self.forfeit_time: int = settings.FORFEIT_TIME + random.randint(50, 150)

        print("\n[!] Searching for game window")
        result = None
        while result is None:
            print("  Did not find window, trying again...")
            result = find_league_window()
            if result is None:
                sleep(1)

        x_pos, y_pos, width, height = result
        print(f"  Window found")
        print(f"  Location: ({x_pos}, {y_pos})")
        print(f"  Size: ({width}, {height})")

        # macOS: the game renders with a title bar / top padding.
        # Calibrate by computing the effective Y offset from the known
        # round-indicator position (original 1080p coord y=10).
        # Empirically the game content starts ~28px below the window top
        # on non-1080p macOS displays.  Adjust offset so the 1920x1080
        # coordinate system maps correctly.
        y_offset = y_pos + round(height * 0.028)   # ~28px at 1000h
        eff_height = height - round(height * 0.028)
        Vec4.setup_screen(x_pos, y_offset, width, eff_height)
        Vec2.setup_screen(x_pos, y_offset, width, eff_height)
        self.loading_screen()

    def loading_screen(self) -> None:
        """Loop that runs while the game is in the loading screen"""
        game_functions.default_pos()
        while game_functions.get_round() != "1-1":
            sleep(1)
        self.start_time: float = perf_counter()
        self.game_loop()

    def game_loop(self) -> None:
        """Loop that runs while the game is active, handles calling the correct tasks for round and exiting game"""
        ran_round: str = None
        while game_functions.check_alive():
            self.round: str = game_functions.get_round()
            if settings.FORFEIT:
                if perf_counter() - self.start_time > self.forfeit_time:
                    game_functions.forfeit()
                    return

            if self.round != ran_round and self.round in game_assets.CAROUSEL_ROUND:
                self.carousel_round()
                ran_round: str = self.round
            elif self.round != ran_round and self.round in game_assets.PVE_ROUND:
                game_functions.default_pos()
                self.pve_round()
                ran_round: str = self.round
            elif self.round != ran_round and self.round in game_assets.PVP_ROUND:
                game_functions.default_pos()
                self.pvp_round()
                ran_round: str = self.round
            sleep(0.5)
        self.message_queue.put("CLEAR")
        game_functions.exit_game()

    def carousel_round(self) -> None:
        """Handles tasks for carousel rounds"""
        print(f"\n[Carousel Round] {self.round}")
        self.message_queue.put("CLEAR")
        if self.round == "3-4":
            self.arena.final_comp = True
        self.arena.check_health()
        print("  Getting a champ from the carousel")
        game_functions.get_champ_carousel(self.round)

    def pve_round(self) -> None:
        """Handles tasks for PVE rounds"""
        print(f"\n[PvE Round] {self.round}")
        self.message_queue.put("CLEAR")
        sleep(0.5)
        if self.round in game_assets.AUGMENT_ROUNDS:
            sleep(1)
            self.arena.pick_augment()
            sleep(2.5)
        if self.round == "1-3":
            sleep(1.5)
            self.arena.fix_unknown()
            self.arena.tacticians_crown_check()
        elif self.round == "4-7":
            game_functions.select_shop()
        self.arena.fix_bench_state()
        self.arena.spend_gold()
        self.arena.move_champions()
        self.arena.replace_unknown()
        if self.arena.final_comp:
            self.arena.final_comp_check()
        self.arena.bench_cleanup()
        self.end_round_tasks()

    def pvp_round(self) -> None:
        """Handles tasks for PVP rounds"""
        print(f"\n[PvP Round] {self.round}")
        self.message_queue.put("CLEAR")
        sleep(0.5)
        if self.round in game_assets.AUGMENT_ROUNDS:
            sleep(1)
            self.arena.pick_augment()
            sleep(2.5)
        if self.round in ("2-1", "2-5"):
            self.arena.buy_xp_round()
        if self.round in game_assets.PICKUP_ROUNDS:
            print("  Picking up items")
            game_functions.pickup_items()
        self.arena.fix_bench_state()
        self.arena.bench_cleanup()
        if self.round in game_assets.ANVIL_ROUNDS:
            self.arena.clear_anvil()
        self.arena.spend_gold()
        self.arena.move_champions()
        self.arena.replace_unknown()
        if self.arena.final_comp:
            self.arena.final_comp_check()
        self.arena.bench_cleanup()
        if self.round in game_assets.ITEM_PLACEMENT_ROUNDS:
            sleep(1)
            self.arena.place_items()
        self.end_round_tasks()

    def end_round_tasks(self) -> None:
        """Common tasks across rounds that happen at the end"""
        self.arena.check_health()
        self.arena.get_label()
        game_functions.default_pos()
