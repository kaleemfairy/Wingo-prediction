"""
Configuration for Royalwin Wingo Mobile Automation.
Edit the values below to match your device and account.
"""

# ── Appium Server ──────────────────────────────────────────────────────────────
APPIUM_HOST = "http://127.0.0.1:4723"

# ── Android Device Capabilities ───────────────────────────────────────────────
# Run `adb devices` to get your device UDID.
CAPABILITIES = {
    "platformName": "Android",
    "appium:automationName": "UiAutomator2",
    "appium:deviceName": "Android Device",
    "appium:udid": "YOUR_DEVICE_UDID",       # e.g. "emulator-5554" or "R5CT21ABCDE"
    "appium:browserName": "Chrome",           # uses Chrome on device
    "appium:chromedriverAutodownload": True,
    "appium:newCommandTimeout": 120,
    "appium:noReset": True,                   # keep session/cookies between runs
}

# ── Game URL ───────────────────────────────────────────────────────────────────
GAME_URL = "https://royalwin.com"            # update to the exact Wingo page URL

# ── Betting Config ─────────────────────────────────────────────────────────────
BASE_BET_AMOUNT = 10          # smallest bet unit (in game currency)
MAX_BET_AMOUNT = 5000         # safety cap — bot stops if next bet exceeds this
MAX_CONSECUTIVE_LOSSES = 6    # stop session after N losses in a row
TARGET_PROFIT = 500           # stop session once profit reaches this value
STOP_LOSS = -1000             # stop session if total loss hits this value

# ── Strategy ───────────────────────────────────────────────────────────────────
# "martingale"      — double bet on loss, reset on win
# "anti_martingale" — double bet on win, reset on loss
# "flat"            — always bet BASE_BET_AMOUNT
# "pattern"         — follow detected streak/alternating patterns
STRATEGY = "martingale"

# ── Default Bet Color ──────────────────────────────────────────────────────────
# "red", "green", or "violet"
DEFAULT_COLOR = "green"

# ── Timing ─────────────────────────────────────────────────────────────────────
ROUND_WAIT_BUFFER = 3         # extra seconds after timer hits 0 before reading result
BET_PLACE_BEFORE = 5          # place bet this many seconds before round ends
POLL_INTERVAL = 1             # seconds between UI state polls

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_FILE = "wingo_bot.log"
SCREENSHOT_ON_ERROR = True    # save screenshot when an unexpected error occurs
