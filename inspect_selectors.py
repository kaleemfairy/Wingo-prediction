"""
Helper script: connect to the device, open the game page, and print
all visible element text + XPaths so you can update SELECTORS in automation.py.

Usage:
    python inspect_selectors.py
"""

import time
from appium import webdriver
from appium.options import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy

import config

options = AppiumOptions()
options.load_capabilities(config.CAPABILITIES)

print("Connecting to Appium …")
driver = webdriver.Remote(config.APPIUM_HOST, options=options)
driver.implicitly_wait(10)

print(f"Opening {config.GAME_URL} …")
driver.get(config.GAME_URL)
time.sleep(5)

print("\n── Page source (first 4000 chars) ──")
print(driver.page_source[:4000])

print("\n── Visible text elements ──")
elements = driver.find_elements(AppiumBy.XPATH, "//*[string-length(normalize-space(text()))>0]")
for el in elements:
    try:
        text = el.text.strip()
        tag  = el.tag_name
        cls  = el.get_attribute("class") or ""
        if text:
            print(f"  <{tag} class='{cls[:40]}'> {text[:60]}")
    except Exception:
        pass

driver.quit()
print("\nDone — update SELECTORS in automation.py with the values above.")
