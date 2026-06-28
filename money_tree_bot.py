"""
Royalwin Money Tree 30s Bot — Laptop / Selenium version.

Bets LARGE or SMALL.
  Win  → reset to BASE_BET
  Lose → next bet = prev_bet × 2.5  (prev_bet × 1.5 + prev_bet)

Confirmed selectors from live page scan (28-Jun-2026).

Usage:
    python money_tree_bot.py
"""

import logging
import os
import re
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager
from colorama import Fore, init as colorama_init

colorama_init(autoreset=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("money_tree_bot.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
#  SETTINGS  — edit these before running
# ═══════════════════════════════════════════════════════
GAME_URL             = "https://www.royalwin6.com/lottery-bet/SELF_MONEY_TREE_30S"
BASE_BET             = 10        # Rs — starting bet, also reset-to amount after a win
MAX_BET              = 5000      # never bet more than this
BET_OPTION           = "large"   # fallback side when strategy has no history yet
#
# ── STRATEGY options ──────────────────────────────────────────────────────────
#  "flat"       always bet BET_OPTION, no prediction
#  "anti_last"  bet opposite of last draw result  (BEST for variety — recommended)
#  "follow"     bet same as last draw result  (momentum / streak-following)
#  "alternate"  LARGE → SMALL → LARGE → … ignores results entirely
#  "pattern"    if last 2 draws same → flip; else bet opposite of last result
#  "frequency"  look at last 20 draws; bet whichever side appeared less often
# ─────────────────────────────────────────────────────────────────────────────
STRATEGY             = "anti_last"  # used only when STRATEGY_ROTATION is empty
#
# ── AUTO-ROTATION ─────────────────────────────────────────────────────────────
#  List strategies to cycle through automatically.
#  Every ROTATION_EVERY bets the bot moves to the next strategy in the list.
#  Set STRATEGY_ROTATION = [] to disable rotation and always use STRATEGY above.
# ─────────────────────────────────────────────────────────────────────────────
STRATEGY_ROTATION    = ["anti_last", "pattern", "frequency"]  # cycle order
ROTATION_EVERY       = 3          # switch strategy after this many bets
TARGET_PROFIT        = 500       # stop when session profit reaches this
STOP_LOSS            = -1000     # stop when session loss reaches this
MAX_CONSECUTIVE_LOSS = 6         # stop after N losses in a row
BET_START_SECONDS    = 20        # only bet when timer is AT OR BELOW this value
BET_STOP_SECONDS     = 5         # do NOT bet when timer is below this (draw closing)
WIN_MULTIPLIER       = 1.96      # payout multiplier shown on site (odds 1.96)
HEADLESS             = False
# ═══════════════════════════════════════════════════════


# ── Selectors (all XPath, confirmed from live page) ───────────────────────────
SEL = {
    # Sidebar countdown for Money Tree 30s
    "timer": [
        # following:: searches the whole document forward, not just siblings
        "//p[@class='name' and normalize-space()='Money Tree 30s']/following::span[contains(@class,'count-down')][1]",
        "//p[normalize-space()='Money Tree 30s']/following::span[contains(@class,'count-down')][1]",
    ],

    # Most-recent draw ID (to detect new rounds)
    "draw_id": "(//span[@class='issue'])[1]",

    # Dice sum from latest draw history entry (e.g. '9' or '11')
    "result_sum": "(//span[contains(@class,'specialNum') and contains(@class,'small')])[1]",

    # LARGE / SMALL bet spans — scoped to this game to avoid clicking number buttons
    "large":  "//span[contains(@class,'TOLARGE') and contains(@class,'SELF_MONEY_TREE_30S')]",
    "small":  "//span[contains(@class,'TOSMALL') and contains(@class,'SELF_MONEY_TREE_30S')]",

    # Clear button — removes all selected bets from the slip
    "clear":  "//button[contains(@class,'clear-btn')]",

    # Bet amount input  (class confirmed: money-set)
    "amount": "//input[contains(@class,'money-set')]",

    # Step 1 — red Submit button
    "submit1": "//button[contains(@class,'submit-btn')]",

    # Step 2 — yellow Submit inside confirmation popup (Ant Design modal)
    "submit2": [
        "//div[contains(@class,'ant-modal')]//button[contains(@class,'ant-btn-primary')]",
        "//div[contains(@class,'ant-modal-confirm-btns')]//button[last()]",
        "//div[contains(@class,'ant-modal-footer')]//button[contains(@class,'ant-btn-primary')]",
        "//div[contains(@class,'modal')]//button[normalize-space()='Submit']",
        "//div[contains(@class,'modal')]//button[normalize-space()='Confirm']",
    ],

    # Step 3 — OK on success popup
    "ok": [
        "//div[contains(@class,'ant-modal')]//button[normalize-space()='OK']",
        "//button[normalize-space()='OK']",
        "//div[contains(@class,'ant-modal-confirm')]//button[contains(@class,'ant-btn-primary')]",
    ],
}


class MoneyTreeBot:
    def __init__(self):
        self.driver       = None
        self.current_bet  = BASE_BET
        self.total_profit = 0.0
        self.cons_losses  = 0
        self.rounds       = 0
        self.wins         = 0
        self._last_draw   = ""
        self._pending     = None   # {"option": "large", "amount": 10}
        self._results     = []     # history of "large"/"small" outcomes for prediction
        self._last_placed = BET_OPTION  # tracks last side placed (for alternate strategy)
        self._strat_idx   = 0     # current index into STRATEGY_ROTATION
        self._strat_count = 0     # bets placed under current strategy

    # ── Driver ────────────────────────────────────────────────────────────────

    def start(self):
        opts = Options()
        if HEADLESS:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--start-maximized")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)

        local_driver = os.path.join(os.path.dirname(__file__), "chromedriver.exe")
        if os.path.exists(local_driver):
            log.info("Using local chromedriver.exe")
            service = Service(local_driver)
        else:
            log.info("Downloading chromedriver via webdriver-manager …")
            service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=opts)
        self.driver.get(GAME_URL)
        log.info("Browser opened at %s", GAME_URL)

    def quit(self):
        if self.driver:
            try: self.driver.quit()
            except Exception: pass

    # ── Element helpers ───────────────────────────────────────────────────────

    def _find_one(self, xpath: str, timeout: int = 5):
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
        except Exception:
            return None

    def _find_any(self, xpaths: list, timeout: int = 6):
        wait_each = max(1, timeout // len(xpaths))
        for xpath in xpaths:
            try:
                el = WebDriverWait(self.driver, wait_each).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                if el:
                    return el
            except Exception:
                continue
        return None

    def _click(self, xpath_or_list, timeout: int = 5) -> bool:
        el = (self._find_any(xpath_or_list, timeout)
              if isinstance(xpath_or_list, list)
              else self._find_one(xpath_or_list, timeout))
        if el:
            try:
                self.driver.execute_script("arguments[0].scrollIntoView(true);", el)
                el.click()
                return True
            except Exception:
                try:
                    self.driver.execute_script("arguments[0].click();", el)
                    return True
                except Exception:
                    pass
        return False

    # ── Timer ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_countdown(text: str) -> int:
        """Parse 'HH:MM:SS' or 'MM:SS' into total seconds. Returns -1 on failure."""
        text = text.strip()
        if not text or text.lower() == "closed":
            return 0
        m = re.search(r"(\d{1,2}):(\d{2}):(\d{2})", text)
        if m:
            return int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3))
        m = re.search(r"(\d{1,2}):(\d{2})", text)
        if m:
            return int(m.group(1))*60 + int(m.group(2))
        return -1

    def _get_timer(self) -> int:
        # ── Approach 1: count-down span following "Money Tree 30s" label ─────────
        for xpath in SEL["timer"]:
            try:
                el = self.driver.find_element(By.XPATH, xpath)
                text = (el.text or el.get_attribute("textContent") or "").strip()
                val = self._parse_countdown(text)
                if val == 0:
                    return 0          # "Closed"
                if 0 < val <= 35:
                    return val
            except Exception:
                continue

        # ── Approach 2: scan ALL count-down spans, accept values ≤ 35s ───────────
        try:
            for el in self.driver.find_elements(By.XPATH, "//span[contains(@class,'count-down')]"):
                text = (el.text or el.get_attribute("textContent") or "").strip()
                val = self._parse_countdown(text)
                if 0 < val <= 35:
                    return val
        except Exception:
            pass

        # ── Approach 3: wagerEndTime vs system clock ──────────────────────────────
        try:
            el = self.driver.find_element(By.XPATH, "//span[@class='wagerEndTime']")
            text = (el.text or "").strip()
            m = re.search(r"(\d{2}):(\d{2}):(\d{2})", text)
            if m:
                from datetime import datetime
                now = datetime.now()
                dl_secs  = int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3))
                now_secs = now.hour*3600 + now.minute*60 + now.second
                remaining = dl_secs - now_secs
                if remaining < 0:
                    remaining += 86400
                if 0 <= remaining <= 35:
                    return remaining
        except Exception:
            pass

        return 99

    # ── Result detection ──────────────────────────────────────────────────────

    def _get_latest_result(self):
        """Returns (draw_id, 'large'|'small'|'') from the most recent history row."""
        try:
            draw_el = self._find_one(SEL["draw_id"], timeout=3)
            draw_id = (draw_el.text or "").strip() if draw_el else ""

            sum_el = self._find_one(SEL["result_sum"], timeout=3)
            if sum_el:
                raw = (sum_el.text or sum_el.get_attribute("textContent") or "").strip()
                if raw.isdigit():
                    total = int(raw)
                    # Sum 11-18 → LARGE, Sum 3-10 → SMALL
                    return draw_id, "large" if total >= 11 else "small"
            return draw_id, ""
        except Exception:
            return "", ""

    # ── Betting ───────────────────────────────────────────────────────────────

    def _set_amount(self, amount: int):
        el = self._find_one(SEL["amount"])
        if not el:
            return
        try:
            # React controlled inputs ignore direct .value assignment.
            # Use the native HTMLInputElement setter so React's onChange fires.
            self.driver.execute_script("""
                var nativeSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value').set;
                nativeSetter.call(arguments[0], arguments[1]);
                arguments[0].dispatchEvent(new Event('input',  {bubbles: true}));
                arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
            """, el, str(amount))
        except Exception:
            try:
                from selenium.webdriver.common.keys import Keys
                el.click()
                el.send_keys(Keys.CONTROL + 'a')
                el.send_keys(str(amount))
            except Exception:
                pass

    def _get_strategy(self) -> str:
        """Priority: strategy.txt (manual override) → STRATEGY_ROTATION → STRATEGY constant."""
        # 1. Manual override via file — edit while bot is running
        try:
            path = os.path.join(os.path.dirname(__file__), "strategy.txt")
            if os.path.exists(path):
                val = open(path).read().strip().lower()
                if val in ("flat", "anti_last", "follow", "alternate", "pattern", "frequency"):
                    return val
        except Exception:
            pass
        # 2. Auto-rotation
        if STRATEGY_ROTATION:
            return STRATEGY_ROTATION[self._strat_idx % len(STRATEGY_ROTATION)]
        # 3. Fixed constant
        return STRATEGY

    def _pick_side(self) -> str:
        strategy = self._get_strategy()
        hist = self._results
        flip = {"large": "small", "small": "large"}

        if strategy == "flat" or not hist:
            return BET_OPTION

        if strategy == "anti_last":
            # Always bet opposite of what just came out
            return flip[hist[-1]]

        if strategy == "follow":
            # Ride the streak — bet same as last result
            return hist[-1]

        if strategy == "alternate":
            # Ignore results; just flip from the last BET placed
            return flip.get(self._last_placed, BET_OPTION)

        if strategy == "pattern":
            # If last 2 draws identical → flip; otherwise bet opposite of last
            if len(hist) >= 2 and hist[-1] == hist[-2]:
                return flip[hist[-1]]
            return flip[hist[-1]]

        if strategy == "frequency":
            # Bet whichever side appeared LESS in last 20 draws (expect balance)
            window = hist[-20:]
            large_n = window.count("large")
            small_n = window.count("small")
            if large_n > small_n:
                return "small"
            if small_n > large_n:
                return "large"
            return BET_OPTION

        return BET_OPTION

    def _place_bet(self, option: str, amount: int) -> bool:
        # 0. Clear any previously selected bets (prevents number bets sneaking in)
        self._click(SEL["clear"], timeout=3)
        time.sleep(0.3)

        # 1. Set amount
        self._set_amount(amount)
        time.sleep(0.4)

        # 2. Click LARGE or SMALL
        if not self._click(SEL[option]):
            log.warning("Could not click %s button", option.upper())
            return False
        time.sleep(0.4)

        # 3. Click red Submit button
        if not self._click(SEL["submit1"]):
            log.warning("Could not click Submit button")
            return False
        time.sleep(1.5)  # wait for confirmation popup

        # 4. Click yellow Submit in confirmation popup
        confirmed = self._click(SEL["submit2"], timeout=8)
        if not confirmed:
            log.warning("Yellow confirm popup not found — trying OK")
            confirmed = self._click(SEL["ok"], timeout=4)
        if not confirmed:
            log.warning("Could not find confirm button in popup")
            return False
        time.sleep(1.0)

        # 5. Click OK on success popup (non-critical — bet is already placed)
        self._click(SEL["ok"], timeout=5)
        time.sleep(0.5)

        return True

    # ── Strategy ──────────────────────────────────────────────────────────────

    def _record_win(self, amount: int):
        profit = round(amount * (WIN_MULTIPLIER - 1), 2)
        self.total_profit += profit
        self.wins += 1
        self.cons_losses = 0
        self.current_bet = BASE_BET
        print(Fore.GREEN + f"  WIN  +{profit:.2f}  |  Total: {self.total_profit:+.2f}  |  Next bet: {self.current_bet}")

    def _record_loss(self, amount: int):
        self.total_profit -= amount
        self.cons_losses += 1
        self.current_bet = min(round(self.current_bet * 2.5), MAX_BET)
        print(Fore.RED + f"  LOSS -{amount}  |  Total: {self.total_profit:+.2f}  |  Next bet: {self.current_bet}")

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        print(Fore.CYAN + "=" * 55)
        print(Fore.CYAN + "  Royalwin Money Tree 30s Bot")
        print(Fore.CYAN + "=" * 55)
        print(Fore.YELLOW + "\n  LOG IN to Royalwin in the browser window.")
        print(Fore.YELLOW + "  After login, come back here and press Enter.")
        if STRATEGY_ROTATION:
            print(Fore.YELLOW + f"\n  Strategy   : AUTO-ROTATE every {ROTATION_EVERY} bets")
            print(Fore.YELLOW + f"  Cycle      : {' → '.join(STRATEGY_ROTATION)}")
        else:
            print(Fore.YELLOW + f"\n  Strategy   : {STRATEGY}  |  Fallback: {BET_OPTION.upper()}")
        print(Fore.YELLOW + f"  Base bet   : {BASE_BET}  |  Max bet: {MAX_BET}")
        print(Fore.YELLOW +  "  On loss    : bet × 2.5  (prev × 1.5 + prev)")
        input(Fore.WHITE + "\n  [Press Enter after you are logged in] ")

        self.driver.get(GAME_URL)
        time.sleep(4)
        print(Fore.GREEN + "  On Money Tree 30s page. Starting bot …\n")

        try:
            while True:
                self._tick()
                if self._check_stop():
                    break
        except KeyboardInterrupt:
            print(Fore.YELLOW + "\nStopped by user.")
        except WebDriverException as e:
            log.error("Browser error: %s", e)
        finally:
            self._print_summary()

    def _tick(self):
        timer = self._get_timer()

        # Timer element not found — retry quickly
        if timer == 99:
            print(Fore.YELLOW + "  Timer not detected — retrying …")
            time.sleep(3)
            return

        # Too early: wait until we enter the betting window (BET_START_SECONDS)
        if timer > BET_START_SECONDS:
            wait = timer - BET_START_SECONDS
            print(Fore.YELLOW + f"  {timer}s — waiting {wait}s for betting window …")
            time.sleep(wait)
            return

        # Too late: draw closing soon, sleep past end of round into next
        if timer < BET_STOP_SECONDS:
            print(Fore.YELLOW + f"  {timer}s — draw closing, waiting for next round …")
            time.sleep(timer + 6)
            return

        # ── Betting window: BET_STOP_SECONDS ≤ timer ≤ BET_START_SECONDS ────────

        # Check result from the previous round
        draw_id, outcome = self._get_latest_result()
        if draw_id and draw_id != self._last_draw and self._pending is not None:
            self._last_draw = draw_id
            if outcome:
                self._results.append(outcome)
                won = (outcome == self._pending["option"])
                if won:
                    self._record_win(self._pending["amount"])
                else:
                    self._record_loss(self._pending["amount"])
            else:
                log.warning("Could not parse result for draw %s", draw_id)
            self._pending = None

        # Pick side using pattern prediction
        side   = self._pick_side()
        amount = min(self.current_bet, MAX_BET)
        live_strat = self._get_strategy()
        last_res   = f"  last={self._results[-1].upper()}" if self._results else ""
        print(Fore.CYAN + f"\n  Timer: {timer}s  |  [{live_strat}]{last_res}  →  Bet {side.upper()}  Rs {amount}")
        ok = self._place_bet(side, amount)
        if ok:
            self._pending     = {"option": side, "amount": amount}
            self._last_placed = side
            self.rounds      += 1
            self._strat_count += 1
            print(Fore.GREEN + "  Bet placed ✓")

            # Auto-rotate strategy every ROTATION_EVERY bets
            if STRATEGY_ROTATION and self._strat_count >= ROTATION_EVERY:
                self._strat_count = 0
                self._strat_idx   = (self._strat_idx + 1) % len(STRATEGY_ROTATION)
                next_s = STRATEGY_ROTATION[self._strat_idx]
                print(Fore.MAGENTA + f"  ↻  Strategy rotated → {next_s.upper()}  (every {ROTATION_EVERY} bets)")
        else:
            print(Fore.RED + "  Bet failed — check selectors")

        # Sleep past the end of this round.
        # timer was read before the bet (~5s of actions), so timer+8 puts us
        # ~8s into the NEXT round with ~22s remaining — well inside betting window.
        time.sleep(timer + 8)

    def _check_stop(self) -> bool:
        p  = self.total_profit
        cl = self.cons_losses
        nb = min(self.current_bet, MAX_BET)
        if p  >= TARGET_PROFIT:        print(Fore.GREEN + f"\nTarget profit reached ({p:.0f}). Stopping."); return True
        if p  <= STOP_LOSS:            print(Fore.RED   + f"\nStop loss hit ({p:.0f}). Stopping.");         return True
        if cl >= MAX_CONSECUTIVE_LOSS: print(Fore.RED   + f"\n{cl} losses in a row. Stopping.");            return True
        if nb >  MAX_BET:              print(Fore.RED   + f"\nNext bet {nb} > max {MAX_BET}. Stopping.");   return True
        return False

    def _print_summary(self):
        losses = self.rounds - self.wins
        rate = f"{self.wins/self.rounds*100:.1f}%" if self.rounds else "0%"
        print(Fore.CYAN + "\n" + "=" * 55)
        print(Fore.CYAN + "  SESSION SUMMARY")
        print(f"  Rounds : {self.rounds}   Wins: {self.wins}   Losses: {losses}")
        print(f"  Win rate : {rate}")
        c = Fore.GREEN if self.total_profit >= 0 else Fore.RED
        print(c + f"  Total P/L : {self.total_profit:+.2f}")
        print(Fore.CYAN + "=" * 55)


def main():
    bot = MoneyTreeBot()
    try:
        bot.start()
        bot.run()
    finally:
        bot.quit()


if __name__ == "__main__":
    main()
