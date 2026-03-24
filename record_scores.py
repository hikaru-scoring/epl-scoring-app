#!/usr/bin/env python3
"""
Daily score recorder for EPL-1000 — runs via GitHub Actions.
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from data_logic import score_all_clubs

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "scores_history.json")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def main():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
    else:
        history = {}

    if TODAY in history:
        print(f"Scores already recorded for {TODAY}")
        return

    print(f"Recording EPL-1000 scores for {TODAY}")
    clubs = score_all_clubs()
    day_scores = {}
    for c in clubs:
        day_scores[c["name"]] = int(c["total"])
        print(f"  {c['name']}: {int(c['total'])}")

    history[TODAY] = day_scores

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)
    print(f"Saved {len(day_scores)} club scores for {TODAY}")


if __name__ == "__main__":
    main()
