# ── PHONE CONNECTION ──────────────────────────────────────────────────────────
PHONE_IP           = '192.168.1.100'  # Change: Settings → WiFi → tap network → IP address
PHONE_ADB_PORT     = 5555
CHROME_DEBUG_PORT  = 9222
SITE_URL_FILTER    = 'diuwin6.com'

# ── PREDICTION STRATEGY ───────────────────────────────────────────────────────
# 1 = Pattern ML (same as web app Strategy 1)
# 2 = Reverse on Wrong (same as web app Strategy 2)
STRATEGY = 1

# ── MONEY MANAGEMENT ──────────────────────────────────────────────────────────
MM_ENABLED   = True
MM_BALANCE   = 1000.0   # Starting balance
MM_START_BET = 10.0     # Level 1 bet amount
MM_MULT      = 1.25     # Multiplier  (same formula as web app)

# ── TIMING ────────────────────────────────────────────────────────────────────
# Place bet when countdown timer shows this many seconds remaining
BET_AT_SECONDS = 15
# Seconds to wait after round ends before reading result
RESULT_WAIT_SECONDS = 2
# Main loop poll interval (seconds)
POLL_INTERVAL = 0.5

# ── CSS SELECTORS ─────────────────────────────────────────────────────────────
# How to find these:
#   1. Open diuwin6.com in Chrome on your PC
#   2. Press F12 → click the element picker (top-left of DevTools)
#   3. Click each element on the page → note the CSS selector shown
#   4. Update the values below
SELECTORS = {
    'timer'       : '.van-count-down',      # countdown timer
    'period'      : '.period-number',       # round/period ID
    'big_btn'     : '.btn-big',             # BIG bet button
    'small_btn'   : '.btn-small',           # SMALL bet button
    'bet_input'   : '.input-amount input',  # bet amount field
    'confirm_btn' : '.btn-confirm',         # confirm bet (leave empty string if none)
    'result'      : '.result-label',        # result text shown after round ends
}
