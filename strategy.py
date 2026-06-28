"""Betting strategy logic."""

from config import BASE_BET, MAX_BET, STRATEGY, COLOR


class BettingStrategy:
    def __init__(self):
        self.current_bet  = BASE_BET
        self.total_profit = 0.0
        self.cons_losses  = 0
        self.cons_wins    = 0
        self.history      = []

    def next_bet(self) -> dict:
        return {"amount": min(self.current_bet, MAX_BET), "color": self._pick_color()}

    def record(self, bet_color: str, result_color: str, amount: float) -> float:
        win          = _is_win(bet_color, result_color)
        round_profit = amount * 1.92 if win else -amount
        self.total_profit += round_profit
        self.history.append({"bet": bet_color, "result": result_color,
                              "amount": amount, "profit": round_profit, "win": win})
        if win:
            self.cons_wins += 1;  self.cons_losses = 0;  self._on_win()
        else:
            self.cons_losses += 1; self.cons_wins  = 0;  self._on_loss()
        return round_profit

    @property
    def summary(self):
        n = len(self.history)
        wins = sum(1 for r in self.history if r["win"])
        return {"rounds": n, "wins": wins, "losses": n - wins,
                "win_rate": f"{wins/n*100:.1f}%" if n else "0%",
                "total_profit": self.total_profit}

    def _on_win(self):
        if   STRATEGY == "martingale":      self.current_bet = BASE_BET
        elif STRATEGY == "anti_martingale": self.current_bet = min(self.current_bet * 2, MAX_BET)

    def _on_loss(self):
        if   STRATEGY == "martingale":      self.current_bet = min(self.current_bet * 2, MAX_BET)
        elif STRATEGY == "anti_martingale": self.current_bet = BASE_BET

    def _pick_color(self) -> str:
        if STRATEGY != "pattern" or len(self.history) < 3:
            return COLOR
        last = [r["result"] for r in self.history[-5:]]
        if len(set(last[-3:])) == 1:
            return {"red": "green", "green": "red", "violet": "green"}.get(last[-1], COLOR)
        return COLOR


def _is_win(bet: str, result: str) -> bool:
    """Color Win 15s returns a digit 0-9.
    Mapping: 1,3,7,9 → green; 2,4,6,8 → red; 0 → red+violet; 5 → green+violet
    """
    r = result.strip()
    if r.isdigit():
        n = int(r)
        if bet == "violet": return n in (0, 5)
        if bet == "green":  return n in (1, 3, 5, 7, 9)
        if bet == "red":    return n in (0, 2, 4, 6, 8)
        return False
    # Fallback for plain colour text results
    if bet == result: return True
    if bet == "red"    and result == "0": return True
    if bet == "green"  and result == "5": return True
    return False
