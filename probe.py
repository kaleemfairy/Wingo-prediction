"""
Run this to find the correct API endpoints for royalwin6.com.
It tries many common WinGo endpoint patterns and prints what the server returns.

Usage:
    python probe.py
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL     = os.getenv("BASE_URL", "https://www.royalwin6.com")
COOKIE_CCT   = os.getenv("COOKIE_CCT", "")
COOKIE_R     = os.getenv("COOKIE_R", "")
COOKIE_JS    = os.getenv("COOKIE_JSESSIONID", "")

COOKIES = {"cct": COOKIE_CCT, "r": COOKIE_R, "JSESSIONID": COOKIE_JS}
HEADERS = {
    "Content-Type": "application/json;charset=UTF-8",
    "Accept": "application/json, text/plain, */*",
    "Referer": BASE_URL + "/",
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; Mobile) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Mobile Safari/537.36"
    ),
}

# Common WinGo endpoint patterns across different site versions
ENDPOINTS_TO_TRY = [
    # Game state / current issue
    ("POST", "/api/webapi/GetGameIssue",          {"typeId": "1"}),
    ("POST", "/api/webapi/GetGameIssue",          {"gameType": 1}),
    ("GET",  "/api/webapi/GetGameIssue?typeId=1", {}),
    ("POST", "/api/game/wingo/issue",             {"type": 1}),
    ("POST", "/api/wingo/getIssue",               {"type": 1}),
    ("GET",  "/api/wingo/current",                {}),
    ("POST", "/webapi/GetGameIssue",              {"typeId": "1"}),
    ("POST", "/api/v1/game/issue",                {"typeId": 1}),

    # Results list
    ("POST", "/api/webapi/GetEmerdList",          {"typeId": "1", "pageNo": 1, "pageSize": 5}),
    ("POST", "/api/webapi/GetMyEmerdList",        {"typeId": "1", "pageNo": 1, "pageSize": 5}),
    ("POST", "/api/wingo/result",                 {"type": 1, "page": 1}),
    ("GET",  "/api/wingo/history?type=1",         {}),

    # User info / balance
    ("POST", "/api/webapi/GetUserInfo",           {}),
    ("GET",  "/api/webapi/GetUserInfo",           {}),
    ("GET",  "/api/user/info",                    {}),
    ("POST", "/api/user/balance",                 {}),
]

print(f"Probing {BASE_URL} ...\n")
print(f"Cookies: cct={COOKIE_CCT[:8]}...  r={COOKIE_R}  JSESSIONID={COOKIE_JS[:20]}...\n")
print("=" * 70)

found = []

for method, path, payload in ENDPOINTS_TO_TRY:
    url = BASE_URL.rstrip("/") + path
    try:
        if method == "GET":
            resp = requests.get(url, headers=HEADERS, cookies=COOKIES, timeout=8)
        else:
            resp = requests.post(url, json=payload, headers=HEADERS, cookies=COOKIES, timeout=8)

        status = resp.status_code
        ctype  = resp.headers.get("Content-Type", "")
        text   = resp.text[:200].replace("\n", " ")

        is_json = "json" in ctype or (text.strip().startswith("{") or text.strip().startswith("["))

        marker = "✓ JSON" if is_json and status == 200 else f"✗ {status}"
        print(f"{marker}  {method} {path}")
        print(f"       {text}\n")

        if is_json and status == 200:
            try:
                found.append({"method": method, "path": path,
                              "payload": payload, "response": resp.json()})
            except Exception:
                pass

    except Exception as e:
        print(f"✗ ERR  {method} {path}  →  {e}\n")

print("=" * 70)
if found:
    print(f"\n✓ Found {len(found)} working endpoint(s):\n")
    for f in found:
        print(f"  {f['method']} {f['path']}")
        print(f"  Response: {json.dumps(f['response'], indent=2)[:300]}\n")
    with open("found_endpoints.json", "w") as fp:
        json.dump(found, fp, indent=2)
    print("Saved to found_endpoints.json")
else:
    print("\n✗ No JSON endpoints found.")
    print("  → Your cookies may have expired. Get fresh ones from the browser.")
    print("  → Or the site uses different URL patterns not in our list.")
