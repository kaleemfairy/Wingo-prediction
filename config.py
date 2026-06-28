"""
Bot configuration — edit before running.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Auth (Cookie-based) ────────────────────────────────────────────────────────
# Paste each cookie value you got from javascript:alert(document.cookie)
# Example values from your browser:
#   cct=9de496d68d98815735b27a7457bc7716
#   r=1562811
#   JSESSIONID=node0w5enf4vhjzcg1h9oin5kljya31689948.node0
COOKIE_CCT       = os.getenv("COOKIE_CCT",        "PASTE_cct_VALUE_HERE")
COOKIE_R         = os.getenv("COOKIE_R",           "PASTE_r_VALUE_HERE")
COOKIE_JSESSION  = os.getenv("COOKIE_JSESSIONID",  "PASTE_JSESSIONID_VALUE_HERE")

# ── API base URL ───────────────────────────────────────────────────────────────
BASE_URL = os.getenv("BASE_URL", "https://www.royalwin6.com")

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
