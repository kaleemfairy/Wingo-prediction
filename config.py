"""
Bot configuration — edit before running.
Copy your token from the browser (see README for how to find it).
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Auth ───────────────────────────────────────────────────────────────────────
# Paste your login token/cookie from Royalwin here (or set in .env file).
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "PASTE_YOUR_TOKEN_HERE")

# ── API base URL ───────────────────────────────────────────────────────────────
# Common Royalwin / WinGo API base — update if different on your version.
BASE_URL = os.getenv("BASE_URL", "https://royalwin.com")

# ── Game type ──────────────────────────────────────────────────────────────────
# "wingo_1"  = 1-minute game
# "wingo_3"  = 3-minute game
# "wingo_5"  = 5-minute game
GAME_TYPE = "wingo_1"

# ── Bet settings ──────────────────────────────────────────────────────────────
BASE_BET  = 10       # minimum bet amount
MAX_BET   = 5000     # safety cap per round
COLOR     = "green"  # default color: "red", "green", or "violet"

# ── Strategy ──────────────────────────────────────────────────────────────────
# "flat"            — always bet BASE_BET
# "martingale"      — double on loss, reset on win
# "anti_martingale" — double on win, reset on loss
# "pattern"         — follow detected colour patterns
STRATEGY = "martingale"

# ── Session limits ─────────────────────────────────────────────────────────────
TARGET_PROFIT        = 500    # stop when total profit reaches this
STOP_LOSS            = -1000  # stop when total loss reaches this
MAX_CONSECUTIVE_LOSS = 6      # stop after N losses in a row

# ── Timing ─────────────────────────────────────────────────────────────────────
BET_CUTOFF_SECONDS = 5    # stop betting if less than N seconds left in round
POLL_INTERVAL      = 2    # seconds between API polls
