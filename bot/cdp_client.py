import json
import threading
import time
import requests
import websocket


class CDPClient:
    """Chrome DevTools Protocol client — controls a Chrome tab via WebSocket."""

    def __init__(self, host='localhost', port=9222):
        self.host = host
        self.port = port
        self.ws = None
        self._msg_id = 0
        self._pending = {}  # id → response dict
        self._lock = threading.Lock()

    # ── connection ────────────────────────────────────────────────────────────

    def connect(self, url_filter=None):
        """Connect to the first Chrome tab whose URL contains url_filter."""
        tabs = requests.get(f'http://{self.host}:{self.port}/json', timeout=5).json()
        tab = None
        for t in tabs:
            if t.get('type') != 'page':
                continue
            if url_filter is None or url_filter in t.get('url', ''):
                tab = t
                break
        if not tab:
            raise RuntimeError(f'No tab found matching "{url_filter}"')

        self.ws = websocket.WebSocketApp(
            tab['webSocketDebuggerUrl'],
            on_message=self._on_message,
            on_error=lambda ws, e: print(f'[CDP] WS error: {e}'),
        )
        t = threading.Thread(target=self.ws.run_forever, daemon=True)
        t.start()
        time.sleep(0.8)
        print(f'[CDP] Connected: {tab["url"][:60]}')

    def _on_message(self, ws, raw):
        data = json.loads(raw)
        if 'id' in data:
            with self._lock:
                self._pending[data['id']] = data

    # ── core primitives ───────────────────────────────────────────────────────

    def _send(self, method, params=None, timeout=6):
        self._msg_id += 1
        mid = self._msg_id
        self.ws.send(json.dumps({'id': mid, 'method': method, 'params': params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                if mid in self._pending:
                    return self._pending.pop(mid)
            time.sleep(0.04)
        return None

    def evaluate(self, expr, timeout=6):
        """Evaluate JavaScript in the page and return the result value."""
        resp = self._send(
            'Runtime.evaluate',
            {'expression': expr, 'returnByValue': True, 'awaitPromise': False},
            timeout=timeout,
        )
        if resp is None:
            return None
        result = resp.get('result', {}).get('result', {})
        return result.get('value')

    # ── helpers ───────────────────────────────────────────────────────────────

    def get_text(self, selector):
        return self.evaluate(
            f'document.querySelector({json.dumps(selector)})?.textContent?.trim() ?? null'
        )

    def click(self, selector):
        return self.evaluate(
            f'(function(){{var el=document.querySelector({json.dumps(selector)});'
            f'if(el){{el.click();return true;}}return false;}})()'
        )

    def set_input(self, selector, value):
        """Set an input value and fire React/Vue change events."""
        js = f'''
        (function(){{
            var el = document.querySelector({json.dumps(selector)});
            if (!el) return false;
            var setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            setter.call(el, {json.dumps(str(value))});
            el.dispatchEvent(new Event('input',  {{bubbles:true}}));
            el.dispatchEvent(new Event('change', {{bubbles:true}}));
            return true;
        }})()
        '''
        return self.evaluate(js)

    def get_number(self, selector):
        text = self.get_text(selector)
        if text is None:
            return None
        digits = ''.join(c for c in text if c.isdigit() or c == ':')
        return digits or None
