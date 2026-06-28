"""
Royalwin / WinGo HTTP API client.

HOW TO FIND YOUR API ENDPOINTS
───────────────────────────────
1. Open Royalwin in Chrome on your phone.
2. Tap the three-dot menu → "Desktop site" (sometimes shows more DevTools).
   Better: install "HTTP Canary" or "PCAPdroid" from Play Store.
3. Open the Wingo game, place one manual bet.
4. In HTTP Canary you will see POST requests like:
      /api/webapi/GetGameIssue
      /api/webapi/WinGoPlaceBet
      /api/webapi/GetMyEmerdList
5. Copy the exact URLs + request bodies and replace the placeholders below.
"""

import time
import logging
import requests
from config import COOKIE_CCT, COOKIE_R, COOKIE_JSESSION, BASE_URL

log = logging.getLogger(__name__)

# Build cookie string from the three values you copied from your browser.
_COOKIES = {
    "cct":       COOKIE_CCT,
    "r":         COOKIE_R,
    "JSESSIONID": COOKIE_JSESSION,
}

_HEADERS = {
    "Content-Type": "application/json;charset=UTF-8",
    "Accept": "application/json, text/plain, */*",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/",
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; Mobile) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Mobile Safari/537.36"
    ),
}

# ── Endpoint paths ─────────────────────────────────────────────────────────────
# Replace these with the exact paths captured by HTTP Canary / PCAPdroid.
EP_GAME_STATE  = "/api/webapi/GetGameIssue"       # returns timer + issue number
EP_PLACE_BET   = "/api/webapi/WinGoPlaceBet"      # places a colour/number bet
EP_RESULT_LIST = "/api/webapi/GetEmerdList"        # recent results list
EP_BALANCE     = "/api/webapi/GetUserInfo"         # user balance


class APIError(Exception):
    pass


def _post(endpoint: str, payload: dict, retries: int = 3) -> dict:
    url = BASE_URL.rstrip("/") + endpoint
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, json=payload, headers=_HEADERS,
                                 cookies=_COOKIES, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            # Most WinGo clones wrap response in {"code": 0, "data": {...}}
            if data.get("code") not in (0, 200, None):
                raise APIError(f"API error code {data.get('code')}: {data.get('msg')}")
            return data.get("data") or data
        except (requests.RequestException, APIError) as exc:
            log.warning("Attempt %d/%d failed: %s", attempt, retries, exc)
            if attempt < retries:
                time.sleep(2 ** attempt)
    raise APIError(f"All {retries} attempts failed for {endpoint}")


# ── Public functions ──────────────────────────────────────────────────────────

def get_game_state(game_type: str) -> dict:
    """
    Returns something like:
      {"issueNumber": "20240628001", "leftTime": 23, "status": "betting"}
    """
    return _post(EP_GAME_STATE, {"typeId": game_type})


def place_bet(game_type: str, issue: str, color: str, amount: int) -> dict:
    """
    Place a colour bet.
    color: "red" | "green" | "violet"  (or "0"–"9" for number bets)
    """
    # Map colour names to the IDs used by the API (adjust from your captured traffic).
    color_map = {"green": 1, "violet": 2, "red": 3}
    color_id  = color_map.get(color, color)   # fall back to raw value for number bets

    payload = {
        "typeId":      game_type,
        "issueNumber": issue,
        "colorId":     color_id,
        "amount":      amount,
        "multilple":   1,        # bet multiplier
        "contract":    1,        # agree to contract
    }
    return _post(EP_PLACE_BET, payload)


def get_last_result(game_type: str) -> dict:
    """
    Returns the most recent completed round result, e.g.:
      {"issueNumber": "20240628000", "number": "3", "color": "green"}
    """
    data = _post(EP_RESULT_LIST, {"typeId": game_type, "pageNo": 1, "pageSize": 1})
    # unwrap list if needed
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict) and "list" in data:
        lst = data["list"]
        return lst[0] if lst else {}
    return data


def get_balance() -> float:
    try:
        data = _post(EP_BALANCE, {})
        return float(data.get("balance") or data.get("money") or 0)
    except APIError:
        return 0.0
