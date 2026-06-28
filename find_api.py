"""
Sniff Royalwin API endpoints using a local MITM proxy.

Run this script in Termux BEFORE opening the game.
It starts an HTTP proxy on port 8080, intercepts all traffic,
and prints any JSON requests made by the Royalwin page.

Steps:
  1. Run this script:      python find_api.py
  2. Set your phone's WiFi proxy to 127.0.0.1:8080
     (Settings → WiFi → long-press network → Modify → Advanced → Proxy)
  3. Open Royalwin in your browser and place ONE manual bet.
  4. Come back here — you will see all API calls printed below.
  5. Copy the URLs + token into config.py and api_client.py.
  6. Reset WiFi proxy to "None" when done.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen, Request
from urllib.error import URLError

PROXY_PORT = 8080
captured = []


class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass  # suppress default log

    def do_CONNECT(self):
        # HTTPS tunnelling — for HTTPS you need mitmproxy instead (see README)
        self.send_response(200, "Connection Established")
        self.end_headers()

    def _forward(self, body=None):
        url = self.path
        headers = {k: v for k, v in self.headers.items()
                   if k.lower() not in ("host", "content-length")}
        try:
            req  = Request(url, data=body, headers=headers, method=self.command)
            resp = urlopen(req, timeout=15)
            data = resp.read()
            self.send_response(resp.status)
            for k, v in resp.headers.items():
                if k.lower() not in ("transfer-encoding",):
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)

            if b"application/json" in (resp.headers.get("Content-Type", "").encode()):
                try:
                    parsed = json.loads(data)
                    entry  = {"url": url, "method": self.command, "response": parsed}
                    if body:
                        try: entry["request_body"] = json.loads(body)
                        except Exception: pass
                    captured.append(entry)
                    print(f"\n{'='*60}")
                    print(f"  {self.command} {url}")
                    if "request_body" in entry:
                        print(f"  BODY: {json.dumps(entry['request_body'], indent=2)}")
                    print(f"  RESP: {json.dumps(parsed, indent=2)[:500]}")
                except Exception:
                    pass
        except URLError as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def do_GET(self):  self._forward()
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length) if length else None
        self._forward(body)


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PROXY_PORT), ProxyHandler)
    print(f"Proxy listening on port {PROXY_PORT}")
    print("Set your phone WiFi proxy to 127.0.0.1:8080")
    print("Then open Royalwin and place a bet. Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print(f"\nCaptured {len(captured)} JSON API calls:")
        for i, c in enumerate(captured, 1):
            print(f"  {i}. {c['method']} {c['url']}")
        with open("captured_api.json", "w") as f:
            json.dump(captured, f, indent=2)
        print("\nSaved to captured_api.json")
