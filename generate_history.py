#!/usr/bin/env python3
"""Generate backtest score history for EPL-1000 using historical data."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from data_logic import (
    _score_financial_health, _score_on_pitch_roi, _score_transfer_efficiency,
    _score_revenue_strength, _score_stability_governance, _clamp,
)

HIST_STANDINGS = os.path.join(os.path.dirname(__file__), "historical_standings.json")
HIST_FINANCIALS = os.path.join(os.path.dirname(__file__), "historical_financials.json")
SCORES_HISTORY = os.path.join(os.path.dirname(__file__), "scores_history.json")

# Season end dates (approximate)
SEASON_END_DATES = {
    "2020-2021": "2021-05-23",
    "2021-2022": "2022-05-22",
    "2022-2023": "2023-05-28",
    "2023-2024": "2024-05-19",
    "2024-2025": "2025-05-25",
}


def main():
    with open(HIST_STANDINGS) as f:
        standings = json.load(f)
    with open(HIST_FINANCIALS) as f:
        financials = json.load(f)

    # Load existing history
    if os.path.exists(SCORES_HISTORY):
        with open(SCORES_HISTORY) as f:
            history = json.load(f)
    else:
        history = {}

    for season_key, season_standings in standings.items():
        date = SEASON_END_DATES.get(season_key)
        if not date:
            continue

        season_fin = financials.get(season_key, {})
        if not season_fin:
            print(f"No financial data for {season_key}, skipping")
            continue

        # Build wage rank lookup for this season (1 = highest wage bill)
        wage_sorted = sorted(season_fin.items(), key=lambda x: x[1].get("wage_bill_m", 0), reverse=True)
        wage_ranks = {name: rank + 1 for rank, (name, _) in enumerate(wage_sorted)}

        day_scores = {}
        for team_name, standing in season_standings.items():
            fin = season_fin.get(team_name)
            if not fin:
                continue

            # Add missing fields with defaults
            fin.setdefault("owner_type", "Unknown")
            fin.setdefault("major_sponsors", [])
            fin.setdefault("squad_avg_age", 26.0)
            fin.setdefault("transfer_spend_m", max(fin.get("net_transfer_spend_m", 0), 0) + 20)
            fin.setdefault("transfer_income_m", 20)
            fin.setdefault("stadium_capacity", 30000)
            fin.setdefault("prev_season_position", 10)

            wage_rank = wage_ranks.get(team_name)

            fh = _score_financial_health(fin)
            opr = _score_on_pitch_roi(fin, standing, wage_rank=wage_rank)
            te = _score_transfer_efficiency(fin, standing)
            rs = _score_revenue_strength(fin)
            sg = _score_stability_governance(fin)
            total = fh + opr + te + rs + sg

            day_scores[team_name] = total
            print(f"  {season_key} | {team_name}: {total}")

        history[date] = day_scores
        print(f"{season_key} ({date}): {len(day_scores)} clubs scored")

    # Sort by date
    history = dict(sorted(history.items()))

    with open(SCORES_HISTORY, "w") as f:
        json.dump(history, f, indent=2)
    print(f"\nSaved {len(history)} dates to scores_history.json")


if __name__ == "__main__":
    main()
