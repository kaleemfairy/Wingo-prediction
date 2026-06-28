"""
Run this on the Money Tree 30s game page to find all selectors.
Also clicks the Large button and waits so you can see popup selectors.

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

MONEY_TREE_URL = "https://www.royalwin6.com/lottery-bet/SELF_MONEY_TREE_30S"

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

print(f"\nNavigating to: {MONEY_TREE_URL}")
driver.get(MONEY_TREE_URL)
time.sleep(4)

print("\n" + "="*60)
print("CURRENT URL:", driver.current_url)
print("="*60)

def dump_page(label=""):
    if label:
        print(f"\n{'─'*10} {label} {'─'*10}")

    print("\n── BUTTONS ─────────────────────────────────────────────────")
    for el in driver.find_elements(By.TAG_NAME, "button"):
        try:
            text = el.text.strip()
            cls  = el.get_attribute("class") or ""
            _id  = el.get_attribute("id") or ""
            style = el.get_attribute("style") or ""
            if text:
                print(f"  <button> class='{cls[:70]}'  style='{style[:40]}'  → '{text}'")
        except Exception:
            pass

    print("\n── INPUTS ──────────────────────────────────────────────────")
    for el in driver.find_elements(By.TAG_NAME, "input"):
        try:
            t   = el.get_attribute("type") or ""
            ph  = el.get_attribute("placeholder") or ""
            cls = el.get_attribute("class") or ""
            val = el.get_attribute("value") or ""
            print(f"  <input type='{t}' placeholder='{ph}' value='{val}' class='{cls[:60]}'>")
        except Exception:
            pass

    print("\n── ALL TEXT ELEMENTS ───────────────────────────────────────")
    for el in driver.find_elements(By.XPATH, "//*[string-length(normalize-space(text()))>0]"):
        try:
            text = el.text.strip()
            tag  = el.tag_name
            cls  = el.get_attribute("class") or ""
            if text and "\n" not in text and len(text) < 80:
                print(f"  <{tag}> class='{cls[:60]}'  → '{text}'")
        except Exception:
            pass

# ── Scan initial page ────────────────────────────────────────────────────────
dump_page("INITIAL PAGE")

# ── Click Large button and scan popup ────────────────────────────────────────
print("\n" + "="*60)
print("Trying to click Large button …")
clicked = False
for xpath in [
    "//span[contains(@class,'TOLarge')]",
    "//div[normalize-space()='Large']",
    "//span[normalize-space()='Large']",
    "//button[normalize-space()='Large']",
    "//*[contains(text(),'Large')]",
]:
    els = driver.find_elements(By.XPATH, xpath)
    if els:
        try:
            driver.execute_script("arguments[0].click();", els[0])
            print(f"  Clicked via: {xpath}")
            clicked = True
            break
        except Exception:
            pass

if not clicked:
    print("  Could not click Large — check elements above manually")

time.sleep(2)
dump_page("AFTER CLICKING LARGE (popup/modal elements)")

print("\n" + "="*60)
print("Done. Share this full output so selectors can be updated.")
input("Press Enter to close the browser …")
driver.quit()
