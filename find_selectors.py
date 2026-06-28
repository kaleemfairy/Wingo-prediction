"""
Run this while logged in on the Wingo game page.
It prints all visible elements so you can find the correct
CSS selectors to put in bot.py → SEL dictionary.

Usage:
    python find_selectors.py
"""

import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from config import GAME_URL

print("Opening browser … Log in and go to Wingo game, then come back here.")
driver = uc.Chrome()
driver.maximize_window()
driver.get(GAME_URL)

input("\nNavigate to the Wingo game page, then press Enter here …")

print("\n── All visible text elements ──────────────────────────────")
els = driver.find_elements(By.XPATH, "//*[string-length(normalize-space(text()))>0]")
for el in els:
    try:
        text = el.text.strip()
        tag  = el.tag_name
        cls  = el.get_attribute("class") or ""
        _id  = el.get_attribute("id") or ""
        if text and len(text) < 80:
            print(f"  <{tag}> class='{cls[:50]}'  id='{_id}'  → '{text}'")
    except Exception:
        pass

print("\n── Input fields ───────────────────────────────────────────")
for el in driver.find_elements(By.TAG_NAME, "input"):
    try:
        t   = el.get_attribute("type") or ""
        ph  = el.get_attribute("placeholder") or ""
        cls = el.get_attribute("class") or ""
        print(f"  <input type='{t}' placeholder='{ph}' class='{cls[:50]}'>")
    except Exception:
        pass

print("\n── Buttons ────────────────────────────────────────────────")
for el in driver.find_elements(By.TAG_NAME, "button"):
    try:
        text = el.text.strip()
        cls  = el.get_attribute("class") or ""
        if text:
            print(f"  <button class='{cls[:60]}'> → '{text}'")
    except Exception:
        pass

driver.quit()
print("\nDone. Update SEL in bot.py with the classes you see above.")
