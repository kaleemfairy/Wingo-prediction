import time
import config
from predictor import seeded_history, get_next_pred
from money_manager import MoneyManager


class GameBot:
    def __init__(self, cdp):
        self.cdp = cdp

        # Predictor state
        self.history   = seeded_history()
        self.strategy  = config.STRATEGY
        self.last_pred = None
        self.last_hit  = None
        self.pred      = None
        self.round_num = 0
        self._refresh_pred()

        # Money management
        self.mm = None
        if config.MM_ENABLED:
            self.mm = MoneyManager(config.MM_BALANCE, config.MM_START_BET, config.MM_MULT)
            self._print_mm_table()

        # Runtime
        self._last_period = None
        self._bet_placed  = False
        self._result_read = False

    # ── prediction ────────────────────────────────────────────────────────────

    def _refresh_pred(self):
        self.pred = get_next_pred(self.history, self.strategy, self.last_pred, self.last_hit)

    def _pred_label(self):
        p = self.pred
        side = 'BIG' if p['prediction'] == 1 else 'SMALL'
        return f'{side} ({p["big_prob"]}% big / {p["small_prob"]}% small)'

    # ── game state ────────────────────────────────────────────────────────────

    def _get_timer(self):
        text = self.cdp.get_text(config.SELECTORS['timer'])
        if not text:
            return None
        try:
            parts = text.strip().split(':')
            return int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else int(parts[0])
        except (ValueError, IndexError):
            return None

    def _get_period(self):
        return self.cdp.get_text(config.SELECTORS['period'])

    def _read_result(self):
        text = self.cdp.get_text(config.SELECTORS['result'])
        if not text:
            return None
        t = text.upper()
        if 'BIG' in t:
            return 1
        if 'SMALL' in t:
            return 0
        return None

    # ── actions ───────────────────────────────────────────────────────────────

    def _place_bet(self):
        bet = self.mm.current_bet if self.mm else None
        pred = self.pred['prediction']
        side = 'BIG' if pred == 1 else 'SMALL'

        print(f'  ► Placing bet: {side}  |  Amount: ${bet:,.2f}' if bet else f'  ► Placing bet: {side}')

        # Set bet amount
        if bet and config.SELECTORS.get('bet_input'):
            ok = self.cdp.set_input(config.SELECTORS['bet_input'], f'{bet:.2f}')
            if not ok:
                print('  ! Could not set bet amount — check SELECTORS["bet_input"]')
            time.sleep(0.3)

        # Click BIG or SMALL
        sel = config.SELECTORS['big_btn'] if pred == 1 else config.SELECTORS['small_btn']
        ok = self.cdp.click(sel)
        if not ok:
            print(f'  ! Could not click {side} button — check SELECTORS')
            return False

        # Confirm if needed
        confirm = config.SELECTORS.get('confirm_btn', '').strip()
        if confirm:
            time.sleep(0.3)
            self.cdp.click(confirm)

        self._bet_placed  = True
        self._result_read = False
        return True

    def _process_result(self, actual: int):
        hit  = actual == self.pred['prediction']
        side = 'BIG' if actual == 1 else 'SMALL'
        self.round_num += 1

        if self.mm:
            if hit:
                self.mm.on_win()
            else:
                self.mm.on_loss()

        self.last_pred = self.pred['prediction']
        self.last_hit  = hit
        self.history.append(actual)
        self._refresh_pred()
        self._bet_placed  = False
        self._result_read = True

        status = '✓ WIN ' if hit else '✗ LOSS'
        mm_info = f'  |  {self.mm.summary()}' if self.mm else ''
        print(f'  {status}  Result: {side}{mm_info}')

        if self.mm and self.mm.at_max_level:
            print('  ⚠  MAX LEVEL REACHED — proceed with caution!')

        print(f'  Next pred: {self._pred_label()}\n')

    # ── main loop ─────────────────────────────────────────────────────────────

    def run(self):
        print('\nBot running — monitoring game...\n')
        while True:
            try:
                self._tick()
            except KeyboardInterrupt:
                print('\nBot stopped.')
                break
            except Exception as e:
                print(f'[ERR] {e}')
            time.sleep(config.POLL_INTERVAL)

    def _tick(self):
        period = self._get_period()
        timer  = self._get_timer()

        # New round detected
        if period and period != self._last_period:
            self._last_period = period
            self._bet_placed  = False
            self._result_read = False
            print(f'[Round {period}]  Timer: {timer}s  |  Pred: {self._pred_label()}')

        # Place bet at right moment
        bet_window = (
            timer is not None
            and config.BET_AT_SECONDS <= timer <= config.BET_AT_SECONDS + 4
            and not self._bet_placed
        )
        if bet_window:
            self._place_bet()

        # Read result after round ends
        if self._bet_placed and not self._result_read and timer is not None and timer <= 1:
            time.sleep(config.RESULT_WAIT_SECONDS)
            result = self._read_result()
            if result is not None:
                self._process_result(result)
            else:
                print('  ! Could not read result — check SELECTORS["result"]')

    # ── helpers ───────────────────────────────────────────────────────────────

    def _print_mm_table(self):
        print('Money Management — Level Ladder:')
        for i, b in enumerate(self.mm.bets, 1):
            print(f'  L{i:2d}: ${b:>10,.2f}')
        print()
