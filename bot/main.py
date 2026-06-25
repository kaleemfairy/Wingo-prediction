"""Entry point — run this to start the bot.

Setup:
  1. Android: Settings → Developer options → Wireless debugging → enable
     Android < 11: connect USB first, run `adb tcpip 5555`, then unplug
  2. Find your phone IP: Settings → WiFi → tap network name → IP address
  3. Update PHONE_IP in config.py
  4. Open diuwin6.com in Chrome on your phone
  5. Run:  python main.py
"""

import sys
import time
import config
from adb_client import ADBClient
from cdp_client import CDPClient
from game_bot import GameBot


def main():
    print('=' * 50)
    print('  BDG Prediction Bot')
    print('=' * 50)
    print(f'  Phone  : {config.PHONE_IP}:{config.PHONE_ADB_PORT}')
    print(f'  Strategy: {config.STRATEGY}')
    if config.MM_ENABLED:
        print(f'  MM     : start=${config.MM_START_BET}  mult=x{config.MM_MULT}  balance=${config.MM_BALANCE}')
    print('=' * 50 + '\n')

    # 1. WiFi ADB
    adb = ADBClient(config.PHONE_IP, config.PHONE_ADB_PORT, config.CHROME_DEBUG_PORT)
    if not adb.connect():
        print('\nFix: ensure WiFi debugging is on and phone IP is correct in config.py')
        sys.exit(1)

    # 2. Wake phone + forward Chrome debug port
    adb.wake()
    time.sleep(0.5)
    adb.forward_chrome_debug()
    time.sleep(1)

    # 3. Connect to Chrome tab on phone
    cdp = CDPClient(port=config.CHROME_DEBUG_PORT)
    try:
        cdp.connect(url_filter=config.SITE_URL_FILTER)
    except RuntimeError as e:
        print(f'\n[CDP] {e}')
        print('Fix: open diuwin6.com in Chrome on your phone, then re-run the bot.')
        sys.exit(1)

    # 4. Run bot
    bot = GameBot(cdp)
    bot.run()


if __name__ == '__main__':
    main()
