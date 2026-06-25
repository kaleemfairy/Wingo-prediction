"""Python port of the web app's cumulative recovery money management system.

Formula (same as web app):
  L1  = start_bet
  LN  = L(N-1) * mult + sum(L1 ... L(N-1))

Each level's bet covers all previous losses when won.
"""

MM_LEVELS = 10


def compute_bets(start_bet: float, mult: float, levels: int = MM_LEVELS) -> list:
    bets = [start_bet]
    for _ in range(1, levels):
        sum_prev = sum(bets)
        bets.append(bets[-1] * mult + sum_prev)
    return bets


class MoneyManager:
    def __init__(self, balance: float, start_bet: float, mult: float):
        self.init_balance = balance
        self.balance      = balance
        self.start_bet    = start_bet
        self.mult         = mult
        self.bets         = compute_bets(start_bet, mult)
        self.level        = 1  # 1-indexed

    @property
    def current_bet(self) -> float:
        return self.bets[self.level - 1]

    @property
    def pnl(self) -> float:
        return self.balance - self.init_balance

    @property
    def at_max_level(self) -> bool:
        return self.level >= MM_LEVELS

    def on_win(self):
        self.balance += self.current_bet
        self.level    = 1

    def on_loss(self):
        self.balance -= self.current_bet
        if self.level < MM_LEVELS:
            self.level += 1

    def reset(self):
        self.balance = self.init_balance
        self.level   = 1

    def summary(self) -> str:
        return (
            f'Balance: ${self.balance:,.2f}  '
            f'Level: L{self.level}/{MM_LEVELS}  '
            f'Bet: ${self.current_bet:,.2f}  '
            f'P&L: {"+" if self.pnl >= 0 else ""}{self.pnl:,.2f}'
        )
