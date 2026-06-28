"""Betting strategy implementations for Wingo bot."""

from config import BASE_BET_AMOUNT, MAX_BET_AMOUNT, STRATEGY, DEFAULT_COLOR


class BettingStrategy:
    """
    Tracks session state and decides the next bet (amount + color) based
    on the configured STRATEGY.
    """

    def __init__(self):
        self.current_bet = BASE_BET_AMOUNT
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.total_profit = 0.0
        self.history = []          # list of {"color": str, "result": str, "profit": float}
        self.strategy = STRATEGY
        self.next_color = DEFAULT_COLOR

    # ── Public API ─────────────────────────────────────────────────────────────

    def next_bet(self) -> dict:
        """Return {"amount": int, "color": str} for the next round."""
        color = self._pick_color()
        return {"amount": min(self.current_bet, MAX_BET_AMOUNT), "color": color}

    def record_result(self, bet_color: str, result_color: str, bet_amount: float):
        """
        Call this after each round.
        result_color: the color/number that actually came up.
        Returns profit/loss for that round (positive = win).
        """
        win = self._is_win(bet_color, result_color)
        round_profit = bet_amount * 1.92 if win else -bet_amount   # ~1.92x payout on color

        self.total_profit += round_profit
        self.history.append({
            "bet_color": bet_color,
            "result": result_color,
            "amount": bet_amount,
            "profit": round_profit,
            "win": win,
        })

        if win:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            self._on_win()
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
            self._on_loss()

        return round_profit

    @property
    def session_summary(self) -> dict:
        rounds = len(self.history)
        wins = sum(1 for r in self.history if r["win"])
        return {
            "rounds": rounds,
            "wins": wins,
            "losses": rounds - wins,
            "win_rate": f"{wins / rounds * 100:.1f}%" if rounds else "0%",
            "total_profit": self.total_profit,
            "current_bet": self.current_bet,
        }

    # ── Internal ───────────────────────────────────────────────────────────────

    def _on_win(self):
        if self.strategy == "martingale":
            self.current_bet = BASE_BET_AMOUNT
        elif self.strategy == "anti_martingale":
            self.current_bet = min(self.current_bet * 2, MAX_BET_AMOUNT)
        # flat / pattern: no change

    def _on_loss(self):
        if self.strategy == "martingale":
            self.current_bet = min(self.current_bet * 2, MAX_BET_AMOUNT)
        elif self.strategy == "anti_martingale":
            self.current_bet = BASE_BET_AMOUNT
        # flat / pattern: no change

    def _pick_color(self) -> str:
        if self.strategy != "pattern" or len(self.history) < 3:
            return DEFAULT_COLOR

        last_results = [r["result"] for r in self.history[-5:]]

        # Streak: if same color appeared 3+ times, bet opposite
        if len(set(last_results[-3:])) == 1:
            streak_color = last_results[-1]
            opposites = {"red": "green", "green": "red", "violet": "green"}
            return opposites.get(streak_color, DEFAULT_COLOR)

        # Alternating: red-green-red → bet green
        if len(last_results) >= 2 and last_results[-1] != last_results[-2]:
            return last_results[-1]  # follow last

        return DEFAULT_COLOR

    @staticmethod
    def _is_win(bet_color: str, result_color: str) -> bool:
        """
        Wingo color rules:
          Numbers 2,4,6,8  → Red
          Numbers 1,3,5,7,9 → Green
          Numbers 0,5      → Violet  (0 = Red+Violet, 5 = Green+Violet)
        Betting Red wins on Red numbers, Green wins on Green numbers, etc.
        When betting Red/Green and result is Violet (0 or 5), half-win applies;
        simplified here as a loss for the color bet.
        """
        if bet_color == result_color:
            return True
        # 0 → violet+red overlap: a "red" bet still wins half (treated as win)
        if bet_color == "red" and result_color in ("0",):
            return True
        # 5 → violet+green overlap
        if bet_color == "green" and result_color in ("5",):
            return True
        return False
