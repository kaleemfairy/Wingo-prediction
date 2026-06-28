"""
Royalwin WinGo Bot — Laptop / Selenium version.

Controls a real Chrome browser on your laptop.
No cookies, no API, no phone needed.

Usage:
    python bot.py
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
from colorama import Fore, Style, init as colorama_init

from config import (
    GAME_URL, HEADLESS, BET_CUTOFF_SECONDS,
    POLL_INTERVAL, TARGET_PROFIT, STOP_LOSS,
    MAX_CONSECUTIVE_LOSS, MAX_BET,
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


# ── Selectors (XPath) ─────────────────────────────────────────────────────────
# Based on royalwin6.com Color Win game layout.
# XPath is used throughout — supports text matching unlike CSS.

SEL = {
    # countdown timer — the 3-part "00 : 00 : 04" display
    "timer": [
        "//*[contains(@class,'time') or contains(@class,'countdown') or contains(@class,'clock')]",
        "//span[contains(@class,'num') and string-length(normalize-space())>0]",
        "//*[@class and contains(text(),':')]",
    ],
    # last winning result (number or colour text after round ends)
    "result": [
        "//*[contains(@class,'result') or contains(@class,'winning') or contains(@class,'lastNum')]",
        "//*[contains(@class,'history')]//*[1]",
    ],
    # bet amount input  (labelled "Point" on this site)
    "amount": [
        "//input[@type='number']",
        "//input[contains(@placeholder,'point') or contains(@placeholder,'Point') or contains(@placeholder,'amount')]",
        "//input[contains(@class,'input') or contains(@class,'point')]",
    ],
    # colour bet buttons
    "green":  [
        "//button[normalize-space()='Green']",
        "//div[normalize-space()='Green']",
        "//span[normalize-space()='Green']",
        "//*[contains(@class,'green')]",
    ],
    "red":    [
        "//button[normalize-space()='Red']",
        "//div[normalize-space()='Red']",
        "//span[normalize-space()='Red']",
        "//*[contains(@class,'red')]",
    ],
    "violet": [
        "//button[normalize-space()='Violet']",
        "//div[normalize-space()='Violet']",
        "//span[normalize-space()='Violet']",
        "//*[contains(@class,'violet')]",
    ],
    # submit button — labelled "Submit" on royalwin6
    "confirm": [
        "//button[normalize-space()='Submit']",
        "//button[normalize-space()='Confirm']",
        "//button[contains(@class,'submit')]",
        "//button[contains(@class,'confirm')]",
        "//*[contains(@class,'submit-btn')]",
    ],
}


class WingoBot:
    def __init__(self):
        self.driver   = None
        self.strategy = BettingStrategy()
        self._last_result_text = ""

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

        log.info("Opening Chrome …")
        # Uses chromedriver.exe from the same folder as bot.py
        local_driver = os.path.join(os.path.dirname(__file__), "chromedriver.exe")
        if os.path.exists(local_driver):
            log.info("Using local chromedriver.exe")
            service = Service(local_driver)
        else:
            log.info("Local chromedriver.exe not found — trying auto-download …")
            service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=opts)
        self.driver.get(GAME_URL)
        log.info("Browser opened at %s", GAME_URL)

    def quit(self):
        if self.driver:
            try: self.driver.quit()
            except Exception: pass

    # ── Element helpers ───────────────────────────────────────────────────────

    def _find(self, selectors: list, timeout: int = 6):
        """Try each XPath selector in order, return first match."""
        wait_each = max(1, timeout // len(selectors))
        for sel in selectors:
            try:
                by = By.XPATH if sel.startswith("/") else By.CSS_SELECTOR
                el = WebDriverWait(self.driver, wait_each).until(
                    EC.presence_of_element_located((by, sel))
                )
                if el:
                    return el
            except (TimeoutException, NoSuchElementException):
                continue
        return None

    def _click(self, selectors: list) -> bool:
        el = self._find(selectors)
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

    def _text(self, selectors: list) -> str:
        el = self._find(selectors)
        return (el.text or el.get_attribute("textContent") or "").strip() if el else ""

    # ── Game state ────────────────────────────────────────────────────────────

    def _get_timer(self) -> int:
        # Parse the countdown from the full page text — handles HH:MM:SS and MM:SS
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            # HH:MM:SS
            m = re.search(r"\b(\d{1,2})\s*:\s*(\d{2})\s*:\s*(\d{2})\b", body_text)
            if m:
                return int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3))
            # MM:SS
            m = re.search(r"\b(\d{1,2})\s*:\s*(\d{2})\b", body_text)
            if m:
                return int(m.group(1))*60 + int(m.group(2))
        except Exception:
            pass
        return 99

    def _get_result(self) -> str:
        text = self._text(SEL["result"]).lower().strip()
        return text

    # ── Betting ───────────────────────────────────────────────────────────────

    def _set_amount(self, amount: int):
        el = self._find(SEL["amount"])
        if el:
            el.clear()
            el.send_keys(str(amount))

    def _place_bet(self, color: str, amount: int) -> bool:
        self._set_amount(amount)
        time.sleep(0.3)
        if not self._click(SEL[color]):
            log.warning("Could not click %s button", color)
            return False
        time.sleep(0.3)
        if not self._click(SEL["confirm"]):
            log.warning("Could not click confirm button")
            return False
        return True

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        print(Fore.CYAN + "=" * 55)
        print(Fore.CYAN + "  Royalwin WinGo Bot  (Laptop / Selenium)")
        print(Fore.CYAN + "=" * 55)
        print(Fore.YELLOW + "\n  LOG IN to Royalwin in the browser window.")
        print(Fore.YELLOW + "  After login, come back here and press Enter.")
        print(Fore.YELLOW + "  The bot will navigate to the Color Win game automatically.")
        input(Fore.WHITE  + "\n  [Press Enter after you are logged in] ")

        # Navigate to the game page after login
        print(Fore.CYAN + f"\n  Navigating to game: {GAME_URL}")
        self.driver.get(GAME_URL)
        time.sleep(4)
        print(Fore.GREEN + "  On game page. Starting bot …\n")

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

        # Wait if too close to end of round
        if timer < BET_CUTOFF_SECONDS:
            print(Fore.YELLOW + f"  {timer}s left — waiting for next round …")
            time.sleep(timer + 3)
            return

        # Check for a new result
        result_now = self._get_result()
        if result_now and result_now != self._last_result_text:
            self._handle_result(result_now)

        # Place bet
        bet = self.strategy.next_bet()
        print(Fore.CYAN + f"\n  Timer: {timer}s  |  Bet → {bet['color'].upper()}  amount={bet['amount']}")
        ok = self._place_bet(bet["color"], bet["amount"])
        if ok:
            print(Fore.GREEN + "  Bet placed ✓")
        else:
            print(Fore.RED + "  Bet failed — check selectors (run find_selectors.py)")

        self._pending = bet
        # Wait for round to finish
        time.sleep(timer + 2)

    def _handle_result(self, result_text: str):
        self._last_result_text = result_text
        if not hasattr(self, "_pending"):
            return

        bet = self._pending
        p_l = self.strategy.record(bet["color"], result_text, bet["amount"])
        win = p_l > 0
        col = Fore.GREEN if win else Fore.RED
        sign = "+" if p_l >= 0 else ""
        print(col + f"  Result: {result_text.upper()}  {'WIN' if win else 'LOSS'}  "
              f"P/L: {sign}{p_l:.0f}  Total: {self.strategy.total_profit:+.0f}")

    def _check_stop(self) -> bool:
        p  = self.strategy.total_profit
        cl = self.strategy.cons_losses
        nb = self.strategy.next_bet()["amount"]
        if p  >= TARGET_PROFIT:        print(Fore.GREEN + f"\nTarget profit reached ({p:.0f}). Stopping."); return True
        if p  <= STOP_LOSS:            print(Fore.RED   + f"\nStop loss hit ({p:.0f}). Stopping.");         return True
        if cl >= MAX_CONSECUTIVE_LOSS: print(Fore.RED   + f"\n{cl} losses in a row. Stopping.");            return True
        if nb >  MAX_BET:              print(Fore.RED   + f"\nNext bet {nb} > max {MAX_BET}. Stopping.");   return True
        return False

    def _print_summary(self):
        s = self.strategy.summary
        print(Fore.CYAN + "\n" + "=" * 55)
        print(Fore.CYAN + "  SESSION SUMMARY")
        print(f"  Rounds : {s['rounds']}   Wins: {s['wins']}   Losses: {s['losses']}")
        print(f"  Win rate : {s['win_rate']}")
        c = Fore.GREEN if s["total_profit"] >= 0 else Fore.RED
        print(c + f"  Total P/L : {s['total_profit']:+.2f}")
        print(Fore.CYAN + "=" * 55)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    bot = WingoBot()
    try:
        bot.start()
        bot.run()
    finally:
        bot.quit()


if __name__ == "__main__":
    main()
