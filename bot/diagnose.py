#!/usr/bin/env python3
"""Run this ONCE to find the real CSS selectors for diuwin6.com.
Output tells you exactly what to put in config.py SELECTORS."""

import json
import subprocess
import threading
import time

import requests
import websocket

import config

PHONE   = f'{config.PHONE_IP}:{config.PHONE_ADB_PORT}'
CDP_URL = f'http://localhost:{config.CHROME_DEBUG_PORT}'

# ── ADB connect + port forward ────────────────────────────────────────────────
print(f'[ADB] Connecting to {PHONE} ...')
subprocess.run(['adb', 'connect', PHONE], capture_output=True)
time.sleep(1)
# Chrome on Android exposes DevTools via a Unix abstract socket, not a TCP port
subprocess.run(
    ['adb', '-s', PHONE, 'forward',
     f'tcp:{config.CHROME_DEBUG_PORT}', 'localabstract:chrome_devtools_remote'],
    capture_output=True,
)
time.sleep(1)
print(f'[ADB] Chrome DevTools -> localhost:{config.CHROME_DEBUG_PORT}')

# ── find tab ──────────────────────────────────────────────────────────────────
print('[CDP] Listing tabs ...')
try:
    tabs = requests.get(f'{CDP_URL}/json', timeout=5).json()
except Exception as e:
    print(f'ERROR: cannot reach CDP — {e}')
    print('Make sure Chrome is open on the betting phone with diuwin6.com.')
    raise SystemExit(1)

tab = None
for t in tabs:
    if t.get('type') == 'page' and config.SITE_URL_FILTER in t.get('url', ''):
        tab = t
        break

if not tab:
    print('ERROR: No tab found. Open diuwin6.com in Chrome on the betting phone.')
    raise SystemExit(1)

print(f'[CDP] Tab: {tab["url"][:80]}')

# ── WebSocket ─────────────────────────────────────────────────────────────────
_pending = {}
_lock    = threading.Lock()
_mid     = [0]

def _on_msg(ws, raw):
    d = json.loads(raw)
    if 'id' in d:
        with _lock:
            _pending[d['id']] = d

ws = websocket.WebSocketApp(
    tab['webSocketDebuggerUrl'],
    header={'Origin': 'http://localhost'},
    on_message=_on_msg,
    on_error=lambda ws, e: None,
)
threading.Thread(target=ws.run_forever, daemon=True).start()
time.sleep(1.5)

def _send(method, params=None, timeout=8):
    _mid[0] += 1
    mid = _mid[0]
    if not ws.sock:
        return None
    ws.send(json.dumps({'id': mid, 'method': method, 'params': params or {}}))
    deadline = time.time() + timeout
    while time.time() < deadline:
        with _lock:
            if mid in _pending:
                return _pending.pop(mid)
        time.sleep(0.05)
    return None

def evaluate(expr, timeout=8):
    resp = _send('Runtime.evaluate',
                 {'expression': expr, 'returnByValue': True, 'awaitPromise': False},
                 timeout=timeout)
    if resp is None:
        return None
    return resp.get('result', {}).get('result', {}).get('value')

if not ws.sock:
    print('ERROR: WebSocket did not connect. Check ADB forward & Chrome debug port.')
    raise SystemExit(1)

print('[CDP] WebSocket connected\n')

# ── probe selectors ───────────────────────────────────────────────────────────
CANDIDATES = [
    # --- timer / countdown ---
    '.van-count-down', '.count-down', '.countdown', '.van-count-down__text',
    '[class*="count"]', '[class*="time"]', '[class*="timer"]', '[class*="countdown"]',
    '[class*="Count"]', '[class*="Time"]',
    # --- period / issue number ---
    '.period-number', '.period', '.issue', '.game-num', '.round-num',
    '[class*="period"]', '[class*="issue"]', '[class*="number"]',
    '[class*="Period"]', '[class*="Issue"]',
    # --- bet buttons ---
    '.btn-big', '.btn-small', '.big', '.small',
    '[class*="big"]', '[class*="Big"]', '[class*="small"]', '[class*="Small"]',
    '.van-button', 'button',
    # --- bet input ---
    '.van-field__control', 'input[type="number"]', 'input[type="text"]', 'input',
    '[class*="amount"]', '[class*="Amount"]', '[class*="bet"]', '[class*="Bet"]',
    # --- confirm button ---
    '.btn-confirm', '.confirm', '[class*="confirm"]', '[class*="Confirm"]',
    '[class*="submit"]', '[class*="Submit"]',
    # --- result ---
    '.result-label', '.result', '[class*="result"]', '[class*="Result"]',
    '[class*="outcome"]', '[class*="Outcome"]',
]

print('='*60)
print('SELECTOR PROBE')
print('='*60)

found = []
for sel in CANDIDATES:
    js = f'''(function(){{
        var el = document.querySelector({json.dumps(sel)});
        if (!el) return null;
        var txt = (el.textContent || '').trim().replace(/\\s+/g,' ').slice(0,60);
        return el.tagName+'|'+el.className+'|'+txt;
    }})()'''
    val = evaluate(js)
    if val:
        tag, cls, txt = (val.split('|') + ['','',''])[:3]
        print(f'  FOUND  {sel:<40}  tag={tag}  text={repr(txt[:40])}')
        found.append((sel, tag, cls, txt))
    else:
        print(f'  none   {sel}')

# ── dump all buttons ──────────────────────────────────────────────────────────
print('\n' + '='*60)
print('ALL BUTTONS ON PAGE')
print('='*60)
btn_info = evaluate('''(function(){
    var out = [];
    document.querySelectorAll('button,[role="button"],[class*="btn"],[class*="Btn"],[class*="button"],[class*="Button"]').forEach(function(el){
        var txt = (el.textContent||'').trim().replace(/\\s+/g,' ').slice(0,40);
        out.push(el.tagName+'|'+el.className+'|'+txt);
    });
    return out.slice(0,40).join('\\n');
})()''')
if btn_info:
    for line in btn_info.split('\n'):
        if line.strip():
            parts = line.split('|')
            print(f'  {parts[0]:<8} class={repr(parts[1][:50])}  text={repr(parts[2][:30] if len(parts)>2 else "")}')

# ── dump all inputs ───────────────────────────────────────────────────────────
print('\n' + '='*60)
print('ALL INPUTS ON PAGE')
print('='*60)
input_info = evaluate('''(function(){
    var out = [];
    document.querySelectorAll('input,textarea').forEach(function(el){
        out.push(el.tagName+'|'+el.className+'|'+el.type+'|'+el.placeholder);
    });
    return out.slice(0,20).join('\\n');
})()''')
if input_info:
    for line in input_info.split('\n'):
        if line.strip():
            parts = (line.split('|') + ['','','',''])[:4]
            print(f'  {parts[0]:<8} class={repr(parts[1][:50])}  type={parts[2]}  placeholder={repr(parts[3][:30])}')

# ── dump simplified DOM ───────────────────────────────────────────────────────
print('\n' + '='*60)
print('PAGE HTML SNIPPET (first 4000 chars, scripts removed)')
print('='*60)
html = evaluate('''(function(){
    var clone = document.body.cloneNode(true);
    clone.querySelectorAll('script,style,svg,img,noscript').forEach(function(e){e.remove();});
    return clone.innerHTML.slice(0, 4000);
})()''')
if html:
    print(html)
else:
    print('(could not get HTML)')

print('\n' + '='*60)
print('DONE — paste this output here so I can update config.py selectors.')
print('='*60)
ws.close()
