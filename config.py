"""
Bot configuration — edit these values before running.
"""

# ── Game URL ───────────────────────────────────────────────────────────────────
GAME_URL = "https://www.royalwin6.com"   # homepage — bot will navigate to Wingo

# ── Bet settings ───────────────────────────────────────────────────────────────
BASE_BET = 10       # starting bet amount
MAX_BET  = 5000     # never bet more than this per round
COLOR    = "green"  # default colour to bet: "red", "green", or "violet"

# ── Strategy ──────────────────────────────────────────────────────────────────
# "flat"            — always bet BASE_BET
# "martingale"      — double on loss, reset on win
# "anti_martingale" — double on win, reset on loss
# "pattern"         — follow colour streak patterns
STRATEGY = "martingale"

# ── Session limits ─────────────────────────────────────────────────────────────
TARGET_PROFIT        = 500    # stop when profit reaches this
STOP_LOSS            = -1000  # stop when loss reaches this
MAX_CONSECUTIVE_LOSS = 6      # stop after N losses in a row

# ── Timing ─────────────────────────────────────────────────────────────────────
BET_CUTOFF_SECONDS = 5    # don't bet if less than N seconds left in round
POLL_INTERVAL      = 1    # seconds between page polls

# ── Browser ────────────────────────────────────────────────────────────────────
HEADLESS = False   # False = you can see the browser; True = runs in background
