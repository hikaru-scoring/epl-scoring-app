# data_logic.py
"""EPL-1000 — Premier League Club Scoring Logic."""
import json
import math
import os
import requests
import xml.etree.ElementTree as ET

AXES_LABELS = [
    "Financial Health",
    "On-Pitch ROI",
    "Transfer Efficiency",
    "Revenue Strength",
    "Stability & Governance",
]

LOGIC_DESC = {
    "Financial Health": "Valuation growth, wage-to-revenue ratio, FFP compliance, debt management",
    "On-Pitch ROI": "Points per £M wage spend, league position vs wage rank, goal difference efficiency",
    "Transfer Efficiency": "Net spend vs position improvement, sell-on profit, squad value growth",
    "Revenue Strength": "Total revenue, commercial income, matchday income, broadcast income diversity",
    "Stability & Governance": "Manager tenure, ownership stability, fan engagement, stadium utilization",
}

FINANCIALS_FILE = os.path.join(os.path.dirname(__file__), "club_financials.json")

ESPN_PL_STANDINGS = "https://site.api.espn.com/apis/v2/sports/soccer/eng.1/standings?season=2024"


def _load_financials():
    with open(FINANCIALS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _fetch_standings():
    """Fetch 2024-25 PL standings from ESPN API."""
    try:
        r = requests.get(ESPN_PL_STANDINGS, timeout=15)
        r.raise_for_status()
        data = r.json()
        entries = data["children"][0]["standings"]["entries"]
        result = {}
        for e in entries:
            stats = {s["name"]: s["value"] for s in e.get("stats", []) if "value" in s}
            team_name = e["team"]["displayName"]
            logo = e["team"]["logos"][0]["href"] if e["team"].get("logos") else ""
            result[team_name] = {
                "position": int(stats.get("rank", 0)),
                "points": int(stats.get("points", 0)),
                "wins": int(stats.get("wins", 0)),
                "draws": int(stats.get("ties", 0)),
                "losses": int(stats.get("losses", 0)),
                "goals_for": int(stats.get("pointsFor", 0)),
                "goals_against": int(stats.get("pointsAgainst", 0)),
                "goal_difference": int(stats.get("pointDifferential", 0)),
                "games_played": int(stats.get("gamesPlayed", 0)),
                "deductions": int(stats.get("deductions", 0)),
                "logo": logo,
            }
        return result
    except Exception:
        return {}


# ESPN name -> club_financials.json name mapping
NAME_MAP = {
    "AFC Bournemouth": "AFC Bournemouth",
    "Brighton & Hove Albion": "Brighton & Hove Albion",
    "Wolverhampton Wanderers": "Wolverhampton Wanderers",
}


def _match_name(espn_name, financials):
    """Match ESPN team name to financials key."""
    if espn_name in financials:
        return espn_name
    mapped = NAME_MAP.get(espn_name)
    if mapped and mapped in financials:
        return mapped
    for key in financials:
        if key.lower() in espn_name.lower() or espn_name.lower() in key.lower():
            return key
    return None


def _clamp(val, lo=0, hi=200):
    return max(lo, min(hi, val))


def _score_financial_health(fin):
    """Score Financial Health (200 pts max)."""
    # Wage-to-revenue ratio (lower = healthier) — max 70
    wage_ratio = fin["wage_bill_m"] / max(fin["revenue_m"], 1)
    wage_score = _clamp((1.0 - wage_ratio) * 140, 0, 70)

    # Valuation (max 60) — higher = stronger
    val_score = _clamp((fin["valuation_m"] / 6200) * 60, 0, 60)

    # FFP compliance (max 40)
    ffp = fin.get("ffp_status", "Compliant")
    if "Compliant" in ffp:
        ffp_score = 40
    elif "At Risk" in ffp:
        ffp_score = 20
    elif "Investigation" in ffp:
        ffp_score = 10
    elif "Penalized" in ffp:
        ffp_score = 5
    else:
        ffp_score = 25

    # Revenue vs wage sustainability (max 30)
    surplus = fin["revenue_m"] - fin["wage_bill_m"]
    sus_score = _clamp((surplus / 400) * 30, 0, 30)

    return _clamp(int(wage_score + val_score + ffp_score + sus_score))


def _score_on_pitch_roi(fin, standing):
    """Score On-Pitch ROI (200 pts max)."""
    if not standing:
        return 100

    # Points per £M wage (max 80)
    ppw = standing["points"] / max(fin["wage_bill_m"], 1) * 100
    ppw_score = _clamp(ppw * 3.5, 0, 80)

    # Position score (max 60) — 1st=60, 20th=3
    pos_score = _clamp((21 - standing["position"]) * 3.15, 0, 60)

    # Position vs wage rank efficiency (max 30)
    # If finishing higher than wage rank = efficient
    wage_rank_bonus = 15  # neutral

    # Goal difference efficiency (max 30)
    gd_score = _clamp((standing["goal_difference"] + 60) / 120 * 30, 0, 30)

    return _clamp(int(ppw_score + pos_score + wage_rank_bonus + gd_score))


def _score_transfer_efficiency(fin, standing):
    """Score Transfer Efficiency (200 pts max)."""
    # Net spend efficiency (max 80) — less spend + better result = higher
    net = fin.get("net_transfer_spend_m", 0)
    if net <= 0:
        net_score = 80  # Profit or break-even = perfect
    else:
        net_score = _clamp(80 - (net / 400) * 80, 0, 80)

    # Position improvement vs spend (max 60)
    prev_pos = fin.get("prev_season_position", 10)
    curr_pos = standing["position"] if standing else 10
    if prev_pos == 0:  # Promoted team
        improvement = 20 - curr_pos  # Lower position = better for promoted
        imp_score = _clamp(improvement * 3, 0, 60)
    else:
        improvement = prev_pos - curr_pos
        imp_score = _clamp(30 + improvement * 6, 0, 60)

    # Sell-on ability (max 30) — income vs spend ratio
    if fin["transfer_spend_m"] > 0:
        sell_ratio = fin["transfer_income_m"] / fin["transfer_spend_m"]
        sell_score = _clamp(sell_ratio * 30, 0, 30)
    else:
        sell_score = 15

    # Squad age (max 30) — younger = more resale value
    avg_age = fin.get("squad_avg_age", 26)
    age_score = _clamp((30 - avg_age) * 7.5, 0, 30)

    return _clamp(int(net_score + imp_score + sell_score + age_score))


def _score_revenue_strength(fin):
    """Score Revenue Strength (200 pts max)."""
    # Total revenue (max 70)
    rev_score = _clamp((fin["revenue_m"] / 710) * 70, 0, 70)

    # Sponsor portfolio (max 50)
    sponsor_count = len(fin.get("major_sponsors", []))
    sp_score = _clamp((sponsor_count / 5) * 30, 0, 30)
    title_val = fin.get("title_sponsor_value_m", 0)
    title_score = _clamp((title_val / 75) * 20, 0, 20)

    # Social media / fan base (max 40)
    social = fin.get("social_media_followers_m", 0)
    social_score = _clamp((social / 200) * 40, 0, 40)

    # Stadium utilization (max 40)
    att_pct = fin.get("avg_attendance_pct", 90)
    att_score = _clamp((att_pct / 100) * 40, 0, 40)

    return _clamp(int(rev_score + sp_score + title_score + social_score + att_score))


def _score_stability_governance(fin):
    """Score Stability & Governance (200 pts max)."""
    # Manager stability (max 60) — fewer changes = better
    changes = fin.get("manager_changes_3yr", 0)
    if changes == 0:
        mgr_score = 60
    elif changes == 1:
        mgr_score = 45
    elif changes == 2:
        mgr_score = 25
    elif changes == 3:
        mgr_score = 10
    else:
        mgr_score = 0

    # Ownership type quality (max 50)
    owner_type = fin.get("owner_type", "")
    if "Sovereign Wealth" in owner_type:
        own_score = 45
    elif "Billionaire" in owner_type or "Investment Group" in owner_type:
        own_score = 40
    elif "Consortium" in owner_type or "PE" in owner_type:
        own_score = 35
    elif "Conglomerate" in owner_type:
        own_score = 30
    else:
        own_score = 25

    # Historical legacy (max 40)
    titles = fin.get("titles", 0) + fin.get("champions_league_titles", 0) * 2
    legacy_score = _clamp((titles / 26) * 40, 0, 40)

    # Fan engagement — attendance + social combined (max 50)
    att = fin.get("avg_attendance_pct", 90)
    social = fin.get("social_media_followers_m", 0)
    fan_score = _clamp((att / 100) * 25 + (social / 200) * 25, 0, 50)

    return _clamp(int(mgr_score + own_score + legacy_score + fan_score))


def score_all_clubs():
    """Score all 20 PL clubs and return sorted list."""
    financials = _load_financials()
    standings = _fetch_standings()
    results = []

    for club_name, fin in financials.items():
        # Find matching standing
        standing = None
        for espn_name, st in standings.items():
            matched = _match_name(espn_name, {club_name: fin})
            if matched:
                standing = st
                break

        # Also try direct
        if not standing:
            for espn_name, st in standings.items():
                if club_name.split()[0].lower() in espn_name.lower():
                    standing = st
                    break

        fh = _score_financial_health(fin)
        opr = _score_on_pitch_roi(fin, standing)
        te = _score_transfer_efficiency(fin, standing)
        rs = _score_revenue_strength(fin)
        sg = _score_stability_governance(fin)
        total = fh + opr + te + rs + sg

        results.append({
            "name": club_name,
            "total": total,
            "axes": {
                "Financial Health": fh,
                "On-Pitch ROI": opr,
                "Transfer Efficiency": te,
                "Revenue Strength": rs,
                "Stability & Governance": sg,
            },
            "standing": standing or {},
            "financials": fin,
            "logo": standing["logo"] if standing else "",
        })

    results.sort(key=lambda x: x["total"], reverse=True)
    return results


def fetch_club_news(club_name):
    """Fetch latest news for a club via Google News RSS."""
    try:
        query = f"{club_name} Premier League business transfer"
        url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
        r = requests.get(url, timeout=10, headers={"User-Agent": "EPL-1000/1.0"})
        root = ET.fromstring(r.text)
        items = root.findall(".//item")[:5]
        news = []
        for item in items:
            title = item.find("title").text
            link = item.find("link").text
            pub = item.find("pubDate")
            source = item.find("source")
            news.append({
                "title": title,
                "link": link,
                "date": pub.text if pub is not None else "",
                "source": source.text if source is not None else "",
            })
        return news
    except Exception:
        return []
