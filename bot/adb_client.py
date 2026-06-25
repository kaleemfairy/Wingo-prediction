import subprocess
import time
import io
from PIL import Image


class ADBClient:
    def __init__(self, host, port=5555, chrome_debug_port=9222):
        self.device = f'{host}:{port}'
        self.chrome_debug_port = chrome_debug_port

    def connect(self):
        result = subprocess.run(
            ['adb', 'connect', self.device],
            capture_output=True, text=True
        )
        out = result.stdout.lower()
        if 'connected' in out or 'already connected' in out:
            print(f'[ADB] Connected to {self.device}')
            return True
        print(f'[ADB] Failed: {result.stdout.strip()}')
        return False

    def forward_chrome_debug(self):
        """Forward phone's Chrome DevTools port to localhost."""
        subprocess.run([
            'adb', '-s', self.device, 'forward',
            f'tcp:{self.chrome_debug_port}',
            'localabstract:chrome_devtools_remote'
        ], check=True)
        print(f'[ADB] Chrome DevTools → localhost:{self.chrome_debug_port}')

    def wake(self):
        subprocess.run([
            'adb', '-s', self.device, 'shell',
            'input', 'keyevent', 'KEYCODE_WAKEUP'
        ])
        time.sleep(0.5)

    def open_url(self, url):
        subprocess.run([
            'adb', '-s', self.device, 'shell',
            'am', 'start', '-a', 'android.intent.action.VIEW', '-d', url
        ])
        time.sleep(2)

    def screenshot(self):
        data = subprocess.run(
            ['adb', '-s', self.device, 'exec-out', 'screencap', '-p'],
            capture_output=True
        ).stdout
        return Image.open(io.BytesIO(data))

    def tap(self, x, y):
        subprocess.run([
            'adb', '-s', self.device, 'shell', 'input', 'tap', str(x), str(y)
        ])
