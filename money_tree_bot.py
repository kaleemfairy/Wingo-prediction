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
BET_OPTION           = "large"   # "large" or "small"  ← change per your prediction
TARGET_PROFIT        = 500       # stop when session profit reaches this
STOP_LOSS            = -1000     # stop when session loss reaches this
MAX_CONSECUTIVE_LOSS = 6         # stop after N losses in a row
BET_CUTOFF_SECONDS   = 12        # skip round if fewer than N seconds remain (3-step bet takes ~5s + 3s draw-close buffer)
WIN_MULTIPLIER       = 1.96      # payout multiplier shown on site (odds 1.96)
HEADLESS             = False
# ═══════════════════════════════════════════════════════


# ── Selectors (all XPath, confirmed from live page) ───────────────────────────
SEL = {
    # Sidebar countdown for Money Tree 30s
    "timer": [
        "//p[@class='name' and normalize-space(text())='Money Tree 30s']/following-sibling::span[contains(@class,'count-down')][1]",
        "//p[@class='name' and normalize-space(text())='Money Tree 30s']/../span[contains(@class,'count-down')]",
    ],

    # Most-recent draw ID (to detect new rounds)
    "draw_id": "(//span[@class='issue'])[1]",

    # Dice sum from latest draw history entry (e.g. '9' or '11')
    "result_sum": "(//span[contains(@class,'specialNum') and contains(@class,'small')])[1]",

    # LARGE / SMALL bet spans  (class confirmed: TOLARGE / TOSMALL)
    "large":  "//span[contains(@class,'TOLARGE')]",
    "small":  "//span[contains(@class,'TOSMALL')]",

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

    def _get_timer(self) -> int:
        for xpath in SEL["timer"]:
            try:
                els = self.driver.find_elements(By.XPATH, xpath)
                for el in els:
                    text = (el.text or el.get_attribute("textContent") or "").strip()
                    if not text or text.lower() == "closed":
                        return 0
                    m = re.search(r"(\d{1,2}):(\d{2}):(\d{2})", text)
                    if m:
                        val = int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3))
                        if val <= 120:
                            return val
                    m = re.search(r"(\d{1,2}):(\d{2})", text)
                    if m:
                        val = int(m.group(1))*60 + int(m.group(2))
                        if val <= 60:
                            return val
            except Exception:
                continue
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
        if el:
            try:
                # React/Ant input needs JS to trigger onChange
                self.driver.execute_script(
                    "arguments[0].value = arguments[1];"
                    "arguments[0].dispatchEvent(new Event('input',{bubbles:true}));"
                    "arguments[0].dispatchEvent(new Event('change',{bubbles:true}));",
                    el, str(amount)
                )
            except Exception:
                el.clear()
                el.send_keys(str(amount))

    def _place_bet(self, option: str, amount: int) -> bool:
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
        print(Fore.YELLOW + f"\n  Betting on : {BET_OPTION.upper()}")
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

        if timer < BET_CUTOFF_SECONDS:
            secs = max(timer, 0)
            print(Fore.YELLOW + f"  {secs}s left — waiting for next round …")
            # Sleep past the end of this round so next tick starts a fresh round
            time.sleep(min(secs + 5, 40))
            return

        # Check for a new result (from the round we bet on previously)
        draw_id, outcome = self._get_latest_result()
        if draw_id and draw_id != self._last_draw and self._pending is not None:
            self._last_draw = draw_id
            if outcome:
                won = (outcome == self._pending["option"])
                if won:
                    self._record_win(self._pending["amount"])
                else:
                    self._record_loss(self._pending["amount"])
            else:
                log.warning("Could not parse result for draw %s", draw_id)
            self._pending = None

        # Place bet for this round
        amount = min(self.current_bet, MAX_BET)
        print(Fore.CYAN + f"\n  Timer: {timer}s  |  Bet → {BET_OPTION.upper()}  Rs {amount}")
        ok = self._place_bet(BET_OPTION, amount)
        if ok:
            self._pending = {"option": BET_OPTION, "amount": amount}
            self.rounds += 1
            print(Fore.GREEN + "  Bet placed ✓")
        else:
            print(Fore.RED + "  Bet failed — run find_selectors.py to debug popup buttons")

        # Sleep past the end of this round so next tick starts a fresh round.
        # timer was read at the START of this tick (before placing bet ~5s ago),
        # so sleeping timer+2 guarantees we wake up a few seconds into the NEXT round.
        time.sleep(min(timer + 2, 40))

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
