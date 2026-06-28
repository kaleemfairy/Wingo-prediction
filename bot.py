"""
Royalwin WinGo Bot — runs entirely on Android via Termux.
No PC needed.

Usage (inside Termux):
    python bot.py
"""

import logging
import sys
import time
from colorama import Fore, Style, init as colorama_init

import api_client as api
from config import (
    GAME_TYPE, BET_CUTOFF_SECONDS, POLL_INTERVAL,
    TARGET_PROFIT, STOP_LOSS, MAX_CONSECUTIVE_LOSS, MAX_BET,
)
from strategy import BettingStrategy

colorama_init(autoreset=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("wingo_bot.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


def cprint(msg: str, color=Fore.WHITE):
    print(color + msg + Style.RESET_ALL)


class WingoBot:
    def __init__(self):
        self.strategy = BettingStrategy()
        self._last_issue = None
        self._rounds = 0

    # ── Core loop ─────────────────────────────────────────────────────────────

    def run(self):
        cprint("=" * 50, Fore.CYAN)
        cprint(" Royalwin WinGo Bot  (Termux edition)", Fore.CYAN)
        cprint("=" * 50, Fore.CYAN)

        try:
            while True:
                self._tick()
                if self._should_stop():
                    break
        except KeyboardInterrupt:
            cprint("\nStopped by user.", Fore.YELLOW)
        finally:
            self._print_summary()

    def _tick(self):
        # 1. Fetch current round state
        try:
            state = api.get_game_state(GAME_TYPE)
        except api.APIError as e:
            log.warning("Could not fetch game state: %s", e)
            time.sleep(POLL_INTERVAL)
            return

        issue     = state.get("issueNumber") or state.get("issue")
        left_time = int(state.get("leftTime") or state.get("countdown") or 0)
        status    = (state.get("status") or "").lower()

        # 2. If same round, just poll again
        if issue == self._last_issue:
            time.sleep(POLL_INTERVAL)
            return

        # 3. New round detected — wait for result of previous round first
        if self._last_issue is not None:
            self._read_result()

        # 4. Wait until we're inside the betting window
        cprint(f"\nRound {issue}  |  {left_time}s left", Fore.CYAN)

        while left_time < BET_CUTOFF_SECONDS:
            cprint(f"  Waiting for next round (only {left_time}s left) …", Fore.YELLOW)
            time.sleep(POLL_INTERVAL)
            try:
                state     = api.get_game_state(GAME_TYPE)
                left_time = int(state.get("leftTime") or state.get("countdown") or 0)
                issue     = state.get("issueNumber") or state.get("issue")
            except api.APIError:
                time.sleep(POLL_INTERVAL)
                return

        # 5. Place bet
        bet = self.strategy.next_bet()
        cprint(
            f"  Placing bet → {bet['color'].upper()}  amount={bet['amount']}  "
            f"({left_time}s left)",
            Fore.GREEN,
        )
        try:
            api.place_bet(GAME_TYPE, issue, bet["color"], bet["amount"])
            cprint("  Bet placed ✓", Fore.GREEN)
        except api.APIError as e:
            cprint(f"  Bet failed: {e}", Fore.RED)

        self._last_issue  = issue
        self._pending_bet = bet

        # 6. Wait for round to finish
        cprint(f"  Waiting {left_time}s for result …", Fore.WHITE)
        time.sleep(left_time + 3)

    def _read_result(self):
        try:
            result = api.get_last_result(GAME_TYPE)
        except api.APIError as e:
            log.warning("Could not read result: %s", e)
            return

        result_color  = (result.get("color") or "").lower()
        result_number = str(result.get("number") or "")

        if not hasattr(self, "_pending_bet") or not result_color:
            return

        bet   = self._pending_bet
        p_l   = self.strategy.record(bet["color"], result_color, bet["amount"])
        self._rounds += 1

        color_display = Fore.GREEN if result_color == "green" else \
                        Fore.RED   if result_color == "red"   else Fore.MAGENTA
        win = p_l > 0
        outcome_str = (Fore.GREEN + "WIN ") if win else (Fore.RED + "LOSS")

        cprint(
            f"  Result: {result_number} "
            f"({color_display}{result_color.upper()}{Style.RESET_ALL})  "
            f"{outcome_str}  "
            f"P/L: {'+' if p_l>=0 else ''}{p_l:.0f}  "
            f"Total: {self.strategy.total_profit:+.0f}",
            Fore.WHITE,
        )

    # ── Stop conditions ───────────────────────────────────────────────────────

    def _should_stop(self) -> bool:
        p = self.strategy.total_profit
        cl = self.strategy.cons_losses
        nb = self.strategy.next_bet()["amount"]

        if p >= TARGET_PROFIT:
            cprint(f"\nTarget profit {TARGET_PROFIT} reached! Stopping.", Fore.GREEN)
            return True
        if p <= STOP_LOSS:
            cprint(f"\nStop loss {STOP_LOSS} hit. Stopping.", Fore.RED)
            return True
        if cl >= MAX_CONSECUTIVE_LOSS:
            cprint(f"\n{cl} consecutive losses. Stopping.", Fore.RED)
            return True
        if nb > MAX_BET:
            cprint(f"\nNext bet {nb} exceeds max {MAX_BET}. Stopping.", Fore.RED)
            return True
        return False

    # ── Summary ───────────────────────────────────────────────────────────────

    def _print_summary(self):
        s = self.strategy.summary
        cprint("\n" + "=" * 50, Fore.CYAN)
        cprint(" SESSION SUMMARY", Fore.CYAN)
        cprint(f"  Rounds   : {s['rounds']}", Fore.WHITE)
        cprint(f"  Wins     : {s['wins']}", Fore.GREEN)
        cprint(f"  Losses   : {s['losses']}", Fore.RED)
        cprint(f"  Win rate : {s['win_rate']}", Fore.WHITE)
        cprint(
            f"  Total P/L: {s['total_profit']:+.2f}",
            Fore.GREEN if s["total_profit"] >= 0 else Fore.RED,
        )
        cprint("=" * 50, Fore.CYAN)


if __name__ == "__main__":
    WingoBot().run()
