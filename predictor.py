# =========================================
# BDG BIG/SMALL Predictor -- Python ML Core
# =========================================
# NOTE ON REALITY:
# The "history" below is generated with random.randint(0, 1), i.e. pure
# coin flips with NO pattern. A model cannot learn a pattern that doesn't
# exist, so accuracy will sit at ~50%. This mirrors the real game: each
# round is effectively independent, so the previous 5 results carry no
# information about the next one. This script is a clean ML *learning
# exercise* -- it is NOT a way to beat the game. The live accuracy tracker
# is included specifically so you can watch it fail to beat 50%.
# =========================================

import random
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import time

# ----- Config -----
WINDOW = 5            # how many past results feed each prediction
N_HISTORY = 500       # size of initial training history
SLEEP_SECONDS = 30    # set to 0 or 1 while testing so you don't wait
MAX_ROUNDS = 50       # bounded loop instead of `while True` (so it ends)
RETRAIN = True        # actually re-fit as new results arrive ("learning")

FEATURES = [f"r{i}" for i in range(1, WINDOW + 1)]


def build_dataset(seq):
    """Turn a flat result sequence into (features, target) rows."""
    rows = []
    for i in range(WINDOW, len(seq)):
        row = {f"r{j+1}": seq[i - WINDOW + j] for j in range(WINDOW)}
        row["target"] = seq[i]
        rows.append(row)
    return pd.DataFrame(rows)


def train_model(seq):
    df = build_dataset(seq)
    X = df[FEATURES]
    y = df["target"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    acc = accuracy_score(y_test, model.predict(X_test))
    return model, acc


# INITIAL TRAINING
history = [random.randint(0, 1) for _ in range(N_HISTORY)]
model, holdout_acc = train_model(history)

print("\n=================================")
print("MODEL TRAINED")
print(f"Hold-out accuracy: {round(holdout_acc * 100, 2)} %")
print("(Expect ~50% -- the data is random by design.)")
print("=================================\n")

# REAL-TIME PREDICTION LOOP
live_results = history[-WINDOW:]
correct = 0
total = 0

for round_num in range(1, MAX_ROUNDS + 1):
    X_live = pd.DataFrame([live_results], columns=FEATURES)

    next_pred = model.predict(X_live)[0]
    proba = model.predict_proba(X_live)[0]

    class_to_idx = {c: i for i, c in enumerate(model.classes_)}
    big_prob   = round(proba[class_to_idx.get(1, 0)] * 100, 2)
    small_prob = round(proba[class_to_idx.get(0, 0)] * 100, 2)

    signal = "BIG" if next_pred == 1 else "SMALL"

    print(f"\n----- Round {round_num} -----")
    print("LAST 5 RESULTS :", live_results)
    print("PREDICTION     :", signal)
    print("BIG / SMALL    :", f"{big_prob}% / {small_prob}%")

    actual = random.randint(0, 1)
    actual_text = "BIG" if actual == 1 else "SMALL"
    print("ACTUAL         :", actual_text)

    total += 1
    if actual == next_pred:
        correct += 1
    print(f"LIVE ACCURACY  : {round(correct / total * 100, 2)}% ({correct}/{total})")

    live_results = live_results[1:] + [actual]
    history.append(actual)

    if RETRAIN:
        model, _ = train_model(history)

    if SLEEP_SECONDS:
        time.sleep(SLEEP_SECONDS)

print("\n=================================")
print(f"FINISHED. Final live accuracy: {round(correct / total * 100, 2)}% ({correct}/{total})")
print("=================================")
