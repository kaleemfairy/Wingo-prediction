"""
Royalwin Wingo Mobile Automation
─────────────────────────────────
Requires:
  • Appium Server running locally  (npm i -g appium && appium)
  • UiAutomator2 driver            (appium driver install uiautomator2)
  • Android device with USB debugging enabled (or emulator)
  • Chrome on device

Usage:
    python automation.py
"""

import logging
import time
import re
import sys
from datetime import datetime
from pathlib import Path

from appium import webdriver
from appium.options import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import config
from strategy import BettingStrategy

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ── XPath / CSS selectors (update these after inspecting the live page) ────────
# Use Appium Inspector or Chrome DevTools (chrome://inspect) to verify selectors.

SELECTORS = {
    # Countdown timer displayed during each round
    "timer":          "//div[contains(@class,'game-time') or contains(@class,'countdown')]",
    # Last result number/color displayed after each round
    "last_result":    "//div[contains(@class,'result-num') or contains(@class,'last-result')]",
    # Bet amount input field
    "bet_input":      "//input[@type='number' or contains(@placeholder,'amount')]",
    # Color bet buttons
    "btn_green":      "//button[normalize-space()='Green' or contains(@class,'btn-green')]",
    "btn_red":        "//button[normalize-space()='Red'   or contains(@class,'btn-red')]",
    "btn_violet":     "//button[normalize-space()='Violet' or contains(@class,'btn-violet')]",
    # Number buttons 0–9
    "btn_number":     "//button[contains(@class,'num-btn') and normalize-space()='{n}']",
    # Confirm / Place bet button
    "btn_confirm":    "//button[normalize-space()='Confirm' or normalize-space()='Place Bet' "
                      "or contains(@class,'confirm-btn')]",
    # Balance display
    "balance":        "//span[contains(@class,'balance') or contains(@class,'wallet')]",
    # Login fields (if session expires)
    "login_user":     "//input[@type='text'   or @name='username' or @name='phone']",
    "login_pass":     "//input[@type='password']",
    "login_submit":   "//button[@type='submit' or normalize-space()='Login']",
}


class WingoBot:
    def __init__(self):
        self.driver: webdriver.Remote | None = None
        self.strategy = BettingStrategy()
        self.rounds_played = 0
        self._running = True

    # ── Driver ────────────────────────────────────────────────────────────────

    def start(self):
        log.info("Connecting to Appium at %s …", config.APPIUM_HOST)
        options = AppiumOptions()
        options.load_capabilities(config.CAPABILITIES)
        self.driver = webdriver.Remote(config.APPIUM_HOST, options=options)
        self.driver.implicitly_wait(10)
        log.info("Connected. Opening game URL …")
        self.driver.get(config.GAME_URL)
        time.sleep(3)
        log.info("Page loaded.")

    def quit(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    # ── Element helpers ───────────────────────────────────────────────────────

    def _find(self, xpath: str, timeout: int = 8):
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((AppiumBy.XPATH, xpath))
            )
        except TimeoutException:
            return None

    def _click(self, xpath: str, timeout: int = 8) -> bool:
        el = self._find(xpath, timeout)
        if el:
            el.click()
            return True
        log.warning("Element not found: %s", xpath[:80])
        return False

    def _text(self, xpath: str) -> str:
        el = self._find(xpath)
        return el.text.strip() if el else ""

    # ── Game state ────────────────────────────────────────────────────────────

    def _get_timer_seconds(self) -> int:
        """Parse countdown timer text like '00:23' → 23."""
        text = self._text(SELECTORS["timer"])
        match = re.search(r"(\d+):(\d+)", text)
        if match:
            return int(match.group(1)) * 60 + int(match.group(2))
        # fallback: plain number
        match = re.search(r"\d+", text)
        return int(match.group()) if match else 0

    def _get_last_result(self) -> str:
        """Return the last round's result as a string: '0'–'9' or 'red'/'green'/'violet'."""
        return self._text(SELECTORS["last_result"]).lower()

    def _get_balance(self) -> float:
        text = self._text(SELECTORS["balance"])
        nums = re.findall(r"[\d.]+", text.replace(",", ""))
        return float(nums[0]) if nums else 0.0

    # ── Betting actions ───────────────────────────────────────────────────────

    def _set_bet_amount(self, amount: int):
        inp = self._find(SELECTORS["bet_input"])
        if inp:
            inp.clear()
            inp.send_keys(str(amount))
        else:
            log.warning("Bet input not found; amount %s not set.", amount)

    def _click_color(self, color: str) -> bool:
        key = f"btn_{color}"
        if key not in SELECTORS:
            log.error("Unknown color: %s", color)
            return False
        return self._click(SELECTORS[key])

    def _confirm_bet(self) -> bool:
        return self._click(SELECTORS["btn_confirm"])

    def _place_bet(self, amount: int, color: str) -> bool:
        log.info("Placing bet  color=%-6s  amount=%d", color.upper(), amount)
        self._set_bet_amount(amount)
        time.sleep(0.3)
        if not self._click_color(color):
            return False
        time.sleep(0.3)
        if not self._confirm_bet():
            return False
        log.info("Bet placed successfully.")
        return True

    # ── Screenshot helper ─────────────────────────────────────────────────────

    def _screenshot(self, label: str = "error"):
        path = Path(f"screenshot_{label}_{datetime.now():%Y%m%d_%H%M%S}.png")
        try:
            self.driver.save_screenshot(str(path))
            log.info("Screenshot saved: %s", path)
        except Exception:
            pass

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _wait_for_betting_window(self):
        """Block until there are at least BET_PLACE_BEFORE seconds left on timer."""
        log.info("Waiting for betting window …")
        while self._running:
            secs = self._get_timer_seconds()
            if secs >= config.BET_PLACE_BEFORE:
                log.info("Timer: %ds — betting window open.", secs)
                return secs
            log.debug("Timer %ds — too close to cutoff; waiting for next round.", secs)
            time.sleep(config.POLL_INTERVAL)

    def _wait_for_result(self, timer_at_bet: int):
        """Wait for the round to finish and return the result string."""
        wait_secs = timer_at_bet + config.ROUND_WAIT_BUFFER
        log.info("Waiting %ds for result …", wait_secs)
        time.sleep(wait_secs)
        result = self._get_last_result()
        log.info("Result: %s", result if result else "(not detected)")
        return result

    def _check_stop_conditions(self) -> bool:
        profit = self.strategy.total_profit
        next_bet = self.strategy.next_bet()["amount"]
        consecutive = self.strategy.consecutive_losses

        if profit >= config.TARGET_PROFIT:
            log.info("TARGET PROFIT reached (%.2f). Stopping.", profit)
            return True
        if profit <= config.STOP_LOSS:
            log.info("STOP LOSS hit (%.2f). Stopping.", profit)
            return True
        if consecutive >= config.MAX_CONSECUTIVE_LOSSES:
            log.info("Max consecutive losses (%d) reached. Stopping.", consecutive)
            return True
        if next_bet > config.MAX_BET_AMOUNT:
            log.info("Next bet (%d) exceeds MAX_BET_AMOUNT (%d). Stopping.",
                     next_bet, config.MAX_BET_AMOUNT)
            return True
        return False

    def run(self):
        log.info("=" * 60)
        log.info("Wingo Bot starting  |  strategy=%s  |  base_bet=%d",
                 config.STRATEGY, config.BASE_BET_AMOUNT)
        log.info("=" * 60)

        try:
            while self._running:
                # 1. Wait until we're inside the betting window
                timer_secs = self._wait_for_betting_window()

                # 2. Decide next bet
                bet = self.strategy.next_bet()
                bet_amount = bet["amount"]
                bet_color = bet["color"]

                # 3. Place bet
                placed = self._place_bet(bet_amount, bet_color)
                if not placed:
                    log.warning("Bet placement failed — skipping round.")
                    if config.SCREENSHOT_ON_ERROR:
                        self._screenshot("bet_fail")
                    time.sleep(timer_secs + config.ROUND_WAIT_BUFFER)
                    continue

                # 4. Wait for result
                result = self._wait_for_result(timer_secs)
                if not result:
                    log.warning("Could not read result — skipping update.")
                    continue

                # 5. Record result + update strategy
                round_profit = self.strategy.record_result(bet_color, result, bet_amount)
                self.rounds_played += 1

                sign = "+" if round_profit >= 0 else ""
                log.info(
                    "Round %d done  |  bet=%s  result=%s  round=%s%.2f  total=%+.2f",
                    self.rounds_played, bet_color, result,
                    sign, round_profit, self.strategy.total_profit,
                )

                # 6. Check stop conditions
                if self._check_stop_conditions():
                    break

                # 7. Brief pause before next round
                time.sleep(1)

        except KeyboardInterrupt:
            log.info("Interrupted by user.")
        except WebDriverException as exc:
            log.error("Appium/WebDriver error: %s", exc)
            if config.SCREENSHOT_ON_ERROR and self.driver:
                self._screenshot("webdriver_error")
        finally:
            self._print_summary()

    def _print_summary(self):
        s = self.strategy.session_summary
        log.info("=" * 60)
        log.info("SESSION SUMMARY")
        log.info("  Rounds played : %d", s["rounds"])
        log.info("  Wins          : %d", s["wins"])
        log.info("  Losses        : %d", s["losses"])
        log.info("  Win rate      : %s", s["win_rate"])
        log.info("  Total P/L     : %+.2f", s["total_profit"])
        log.info("=" * 60)


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    bot = WingoBot()
    try:
        bot.start()
        bot.run()
    finally:
        bot.quit()
        log.info("Driver closed.")


if __name__ == "__main__":
    main()
