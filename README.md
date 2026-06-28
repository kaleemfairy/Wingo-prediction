# Royalwin Wingo Mobile Automation

Python + Appium bot that automates Wingo colour-prediction rounds on an Android device.

---

## Prerequisites

| Tool | Install |
|------|---------|
| Python 3.10+ | https://python.org |
| Node.js 18+ | https://nodejs.org |
| Appium 2 | `npm install -g appium` |
| UiAutomator2 driver | `appium driver install uiautomator2` |
| Android SDK / ADB | Android Studio → SDK Tools |
| Chrome on device | must match version expected by Chromedriver |

---

## Quick Start

### 1. Enable USB Debugging on your phone

Settings → About Phone → tap **Build Number** 7 times  
Settings → Developer Options → **USB Debugging ON**

Connect phone via USB and confirm the prompt on the device.

```bash
adb devices        # should list your device UDID
```

### 2. Clone and install dependencies

```bash
git clone <repo-url>
cd Wingo-prediction
pip install -r requirements.txt
```

### 3. Configure `config.py`

```python
CAPABILITIES = {
    "appium:udid": "YOUR_DEVICE_UDID",   # from `adb devices`
    ...
}
GAME_URL = "https://royalwin.com/..."    # exact Wingo game page
BASE_BET_AMOUNT = 10
STRATEGY = "martingale"                  # or flat / anti_martingale / pattern
```

### 4. Find the correct element selectors

```bash
python inspect_selectors.py
```

This prints all visible elements on the game page.  
Update `SELECTORS` in `automation.py` to match what you see.

You can also use **Appium Inspector** (GUI) or open  
`chrome://inspect` in desktop Chrome while the device is connected.

### 5. Start Appium server

```bash
appium --relaxed-security
```

### 6. Run the bot

```bash
python automation.py
```

Press **Ctrl+C** to stop. A session summary is printed and logged to `wingo_bot.log`.

---

## Strategies

| Name | Behaviour |
|------|-----------|
| `flat` | Always bet `BASE_BET_AMOUNT` |
| `martingale` | Double on loss, reset to base on win |
| `anti_martingale` | Double on win, reset to base on loss |
| `pattern` | Follows detected streak / alternating patterns |

---

## File Overview

```
automation.py          Main bot loop
strategy.py            Betting strategy logic
config.py              All configurable settings
inspect_selectors.py   Helper to discover XPaths on live page
requirements.txt       Python dependencies
wingo_bot.log          Auto-created log file
```

---

## Safety Limits (set in `config.py`)

- `MAX_BET_AMOUNT` — never bets more than this per round  
- `MAX_CONSECUTIVE_LOSSES` — stops after N losses in a row  
- `TARGET_PROFIT` — stops when session profit reaches this  
- `STOP_LOSS` — stops when total loss reaches this  

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `adb devices` shows nothing | Re-plug cable; enable USB debugging; accept prompt on phone |
| Chromedriver version mismatch | Set `appium:chromedriverAutodownload: True` in config |
| Elements not found | Run `inspect_selectors.py` and update `SELECTORS` in `automation.py` |
| Session expires / login prompt | Set `appium:noReset: False` once to log in; then `True` to reuse cookies |
| Appium connection refused | Make sure `appium` is running in another terminal |
