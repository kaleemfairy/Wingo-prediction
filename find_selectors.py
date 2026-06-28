"""
Run this while on the Color Win game page.
Prints all buttons, inputs and text elements so you can verify selectors.

Usage:
    python find_selectors.py
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from config import GAME_URL

opts = Options()
opts.add_argument("--start-maximized")
opts.add_experimental_option("excludeSwitches", ["enable-automation"])
opts.add_experimental_option("useAutomationExtension", False)

local_driver = os.path.join(os.path.dirname(__file__), "chromedriver.exe")
if os.path.exists(local_driver):
    service = Service(local_driver)
else:
    service = Service(ChromeDriverManager().install())

print("Opening browser … Log in to Royalwin, then press Enter here.")
driver = webdriver.Chrome(service=service, options=opts)
driver.maximize_window()
driver.get("https://www.royalwin6.com")

input("\nLog in to Royalwin in the browser, then press Enter …")

print(f"\nNavigating to: {GAME_URL}")
driver.get(GAME_URL)
time.sleep(3)

print("\n" + "="*60)
print("CURRENT URL:", driver.current_url)
print("="*60)

print("\n── BUTTONS ─────────────────────────────────────────────────")
for el in driver.find_elements(By.TAG_NAME, "button"):
    try:
        text = el.text.strip()
        cls  = el.get_attribute("class") or ""
        _id  = el.get_attribute("id") or ""
        if text:
            print(f"  <button> class='{cls[:60]}'  id='{_id}'  → '{text}'")
    except Exception:
        pass

print("\n── INPUTS ──────────────────────────────────────────────────")
for el in driver.find_elements(By.TAG_NAME, "input"):
    try:
        t   = el.get_attribute("type") or ""
        ph  = el.get_attribute("placeholder") or ""
        cls = el.get_attribute("class") or ""
        val = el.get_attribute("value") or ""
        print(f"  <input type='{t}' placeholder='{ph}' value='{val}' class='{cls[:50]}'>")
    except Exception:
        pass

print("\n── ALL TEXT ELEMENTS ───────────────────────────────────────")
for el in driver.find_elements(By.XPATH, "//*[string-length(normalize-space(text()))>0]"):
    try:
        text = el.text.strip()
        tag  = el.tag_name
        cls  = el.get_attribute("class") or ""
        if text and "\n" not in text and len(text) < 60:
            print(f"  <{tag}> class='{cls[:50]}'  → '{text}'")
    except Exception:
        pass

print("\n" + "="*60)
print("Done. Share this output so selectors can be updated.")
driver.quit()
