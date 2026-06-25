"""Python port of the web app's pattern-frequency ML predictor.

Matches the JS seededRng (LCG) and predict() function exactly so the
bot produces the same predictions as the web app.
"""

WINDOW_SIZE          = 5
INITIAL_HISTORY_SIZE = 500


def _seeded_rng(seed: int):
    """Linear Congruential Generator matching JS seededRng(seed)."""
    s = seed & 0xFFFFFFFF

    def next_val():
        nonlocal s
        s = (s * 1664525 + 1013904223) & 0xFFFFFFFF
        return s / 0x100000000

    return next_val


def seeded_history(seed: int = 42, size: int = INITIAL_HISTORY_SIZE):
    """Generate the same 500-item seeded history as the web app."""
    rng = _seeded_rng(seed)
    return [1 if rng() > 0.5 else 0 for _ in range(size)]


def predict(history: list) -> dict:
    """Frequency-based pattern predictor (mirrors the JS predict() function)."""
    win = history[-WINDOW_SIZE:]
    key = tuple(win)
    big_after = 0
    matches   = 0

    for i in range(WINDOW_SIZE, len(history)):
        w = tuple(history[i - WINDOW_SIZE:i])
        if w == key:
            matches += 1
            if history[i] == 1:
                big_after += 1

    if matches < 3:
        big_prob = history.count(1) / len(history)
    else:
        big_prob = big_after / matches

    alpha    = min(matches, 20) / 20
    big_prob = big_prob * alpha + 0.5 * (1 - alpha)
    big_p    = round(big_prob * 100)

    return {
        'prediction': 1 if big_p >= 50 else 0,
        'big_prob':   big_p,
        'small_prob': 100 - big_p,
    }


def get_next_pred(history: list, strategy: int = 1,
                 last_pred=None, last_hit=None) -> dict:
    """Apply strategy logic on top of the base predictor."""
    if strategy == 1:
        return predict(history)
    # Strategy 2: flip on wrong prediction
    if last_pred is not None and last_hit is False:
        opp = 0 if last_pred == 1 else 1
        return {
            'prediction': opp,
            'big_prob':   68 if opp == 1 else 32,
            'small_prob': 32 if opp == 1 else 68,
        }
    return predict(history)
