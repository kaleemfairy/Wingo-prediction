# Royalwin WinGo Bot — Android / Termux (No PC needed)

Runs 100% on your Android phone using **Termux**.  
No PC, no Appium, no USB cable required.

---

## Step 1 — Install Termux

Download **Termux** from **F-Droid** (NOT Play Store — the Play Store version is outdated):

> https://f-droid.org/en/packages/com.termux/

---

## Step 2 — Install Python inside Termux

Open Termux and run these commands one by one:

```bash
pkg update -y
pkg install python git -y
pip install requests colorama python-dotenv
```

---

## Step 3 — Download the bot

```bash
git clone https://github.com/kaleemfairy/Wingo-prediction.git
cd Wingo-prediction
```

---

## Step 4 — Find your Auth Token

The bot needs your login token to place bets via the API.

**How to get it:**

1. Open **Chrome** on your phone
2. Go to Royalwin and **log in**
3. Open the Wingo game
4. In the URL bar type:  `chrome://inspect`  ← won't work on mobile

**Easier method — use Chrome DevTools on phone:**
1. Open Chrome → three-dot menu → **Settings** → **Privacy and security** → nothing there

**Simplest method:**
1. Open Royalwin in Chrome
2. Tap the address bar, type:
   ```
   javascript:alert(document.cookie)
   ```
   or
   ```
   javascript:alert(localStorage.getItem('token'))
   ```
3. A popup shows your token — copy it

OR use the **find_api.py** proxy script (Step 4b below).

---

## Step 4b — Find API endpoints with the proxy (optional but recommended)

```bash
python find_api.py
```

Then in your phone WiFi settings:
- Long-press your WiFi network → Modify → Advanced → Proxy: **Manual**
- Host: `127.0.0.1`  Port: `8080`

Open Royalwin in Chrome, place one manual bet.  
Go back to Termux — all API calls are printed and saved to `captured_api.json`.

Reset WiFi proxy to **None** when done.

Update the `EP_*` paths in `api_client.py` with the captured URLs.

---

## Step 5 — Configure the bot

```bash
cp .env.example .env
nano .env
```

Paste your token:
```
AUTH_TOKEN=eyJhbGci...your_token_here
BASE_URL=https://royalwin.com
```

Save: press `Ctrl+X` → `Y` → `Enter`

Then edit `config.py` to set your bet size and strategy:
```bash
nano config.py
```

Key settings:
| Setting | Default | Meaning |
|---------|---------|---------|
| `BASE_BET` | 10 | Starting bet amount |
| `MAX_BET` | 5000 | Never bet more than this |
| `STRATEGY` | martingale | flat / martingale / anti_martingale / pattern |
| `COLOR` | green | Which colour to bet on |
| `TARGET_PROFIT` | 500 | Stop when you win this much |
| `STOP_LOSS` | -1000 | Stop when you lose this much |

---

## Step 6 — Run the bot

```bash
python bot.py
```

Press **Ctrl+C** to stop anytime. Session summary is shown and saved to `wingo_bot.log`.

---

## Strategies Explained

| Strategy | How it works |
|----------|-------------|
| `flat` | Always bet the same amount (safest) |
| `martingale` | Double bet after each loss, reset after win |
| `anti_martingale` | Double bet after each win, reset after loss |
| `pattern` | Detects colour streaks and bets accordingly |

---

## Files

```
bot.py            Main bot (run this)
api_client.py     HTTP API calls to Royalwin
config.py         All settings
strategy.py       Betting strategy logic
find_api.py       Proxy tool to discover API endpoints
.env.example      Token template (copy to .env)
wingo_bot.log     Auto-created log file
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError` | Run `pip install requests colorama python-dotenv` |
| `APIError: 401` | Token expired — log in again and get a new token |
| `APIError: All attempts failed` | Check internet; verify BASE_URL in config.py |
| Result colour not reading | Update `color` key in `api_client.py` to match captured JSON field name |
| Bot places bet but shows loss every time | The color/colorId mapping may be wrong — check `color_map` in api_client.py |
