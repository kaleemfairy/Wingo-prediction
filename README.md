# Royalwin WinGo Bot — Laptop Guide

Controls a real Chrome browser on your laptop using Selenium.
No phone, no cookies to copy, no API needed.

---

## Step 1 — Install Python

Download from https://python.org/downloads  
During install: **tick "Add Python to PATH"**

Verify:
```
python --version
```

---

## Step 2 — Download the bot

Open **Command Prompt** (Windows) or **Terminal** (Mac/Linux):

```bash
git clone https://github.com/kaleemfairy/Wingo-prediction.git
cd Wingo-prediction
git checkout claude/royalwin-mobile-automation-rlixzl
```

---

## Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs Selenium and `undetected-chromedriver` (automatically downloads the right ChromeDriver for your Chrome version — no manual setup needed).

---

## Step 4 — Configure settings

Open `config.py` in any text editor (Notepad, VS Code, etc.):

```python
GAME_URL  = "https://www.royalwin6.com"   # already set correctly
BASE_BET  = 10        # your starting bet
MAX_BET   = 5000      # maximum bet per round
COLOR     = "green"   # "red", "green", or "violet"
STRATEGY  = "martingale"
TARGET_PROFIT        = 500
STOP_LOSS            = -1000
MAX_CONSECUTIVE_LOSS = 6
HEADLESS  = False     # keep False so you can see the browser
```

---

## Step 5 — Run the bot

```bash
python bot.py
```

A Chrome browser window opens automatically.

1. **Log in** to Royalwin in that browser window
2. **Navigate** to the Wingo game (Lottery → Win Go)
3. Come back to the terminal and **press Enter**

The bot starts placing bets automatically.

Press **Ctrl+C** anytime to stop. A summary is shown at the end.

---

## Step 6 — If bet buttons are not found

The bot uses CSS selectors to find buttons. If they don't match, run:

```bash
python find_selectors.py
```

This prints all buttons and inputs on the live page.  
Update the `SEL` dictionary in `bot.py` with the correct class names.

---

## Strategies

| Strategy | Behaviour |
|----------|-----------|
| `flat` | Always bet BASE_BET |
| `martingale` | Double after loss, reset after win |
| `anti_martingale` | Double after win, reset after loss |
| `pattern` | Follow colour streak patterns |

---

## Safety Limits (in config.py)

| Setting | Default | Meaning |
|---------|---------|---------|
| `TARGET_PROFIT` | 500 | Stop when you win this much |
| `STOP_LOSS` | -1000 | Stop when you lose this much |
| `MAX_CONSECUTIVE_LOSS` | 6 | Stop after N losses in a row |
| `MAX_BET` | 5000 | Never bet more than this |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `python` not found | Re-install Python and tick "Add to PATH" |
| Chrome doesn't open | Run `pip install --upgrade undetected-chromedriver` |
| Bet buttons not clicked | Run `python find_selectors.py` and update `SEL` in `bot.py` |
| Bot keeps saying timer=99 | Timer element selector is wrong — run `find_selectors.py` |
| Chrome version mismatch | Update Chrome to latest version |
