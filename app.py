# app.py
"""EPL-1000 — Premier League Club Scoring Platform."""
import io
import json
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_logic import AXES_LABELS, LOGIC_DESC, score_all_clubs, fetch_club_news
from ui_components import inject_css, render_radar_chart
try:
    from pdf_report import generate_pdf
    _PDF_AVAILABLE = True
except ImportError:
    _PDF_AVAILABLE = False

SCORES_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "scores_history.json")


def _load_scores_history():
    if os.path.exists(SCORES_HISTORY_FILE):
        with open(SCORES_HISTORY_FILE, "r") as f:
            return json.load(f)
    return {}


def render_score_delta(name, current_total):
    history = _load_scores_history()
    if not history:
        return
    dates = sorted(history.keys(), reverse=True)
    prev = None
    for d in dates:
        s = history[d].get(name)
        if s is not None:
            prev = s
            break
    if prev is None:
        return
    delta = current_total - prev
    if delta > 0:
        color, arrow = "#10b981", "&#9650;"
    elif delta < 0:
        color, arrow = "#ef4444", "&#9660;"
    else:
        color, arrow = "#94a3b8", "&#9644;"
    st.markdown(
        f'<div style="text-align:center;font-size:1.1em;font-weight:700;color:{color};margin-top:-8px;margin-bottom:10px;">'
        f'{arrow} {delta:+d} from last record ({prev})</div>',
        unsafe_allow_html=True,
    )


def render_daily_tracker(name):
    history = _load_scores_history()
    if not history:
        return
    dates = sorted(history.keys())
    vals, vdates = [], []
    for d in dates:
        s = history[d].get(name)
        if s is not None:
            vdates.append(d)
            vals.append(s)
    if len(vdates) < 2:
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=vdates, y=vals, mode="lines+markers",
                             line=dict(color="#2E7BE6", width=2), marker=dict(size=5),
                             fill="tozeroy", fillcolor="rgba(46,123,230,0.05)"))
    fig.update_layout(yaxis=dict(range=[0, 1000], title="Score"), height=250,
                      margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="white",
                      hovermode="x unified", clickmode="none", dragmode=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=f"tracker_{name}")


def generate_excel(data, axes_labels, logic_desc, snapshot=None):
    rows = []
    for k in axes_labels:
        desc = logic_desc.get(k, "")
        rows.append({"Axis": k, "Score": int(data["axes"].get(k, 0)), "Description": desc})
    rows.append({"Axis": "TOTAL", "Score": int(data.get("total", 0)), "Description": ""})
    if snapshot:
        rows.append({"Axis": "", "Score": "", "Description": ""})
        for label, value in snapshot.items():
            rows.append({"Axis": label, "Score": value, "Description": ""})
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8")


# ── Page config ──
APP_TITLE = "EPL-1000 — Premier League Club Scoring Platform"
st.set_page_config(page_title=APP_TITLE, layout="wide")
inject_css()
st.markdown("""
<style>
.block-container { padding-top: 1rem !important; }
header[data-testid="stHeader"] { display: none !important; }
footer { display: none !important; }
#MainMenu { display: none !important; }
.stDeployButton { display: none !important; }
div[class*="stToolbar"] { display: none !important; }
div[data-testid="stStatusWidget"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── Load data ──
@st.cache_data(ttl=3600)
def load_data():
    return score_all_clubs()

all_clubs = load_data()
club_map = {c["name"]: c for c in all_clubs}

# ── Tabs ──
tab_dash, tab_detail, tab_rank = st.tabs(["Dashboard", "Club Detail", "Rankings"])

# ═══════════════════════════════════════════════════════════════
# TAB 1 — Dashboard
# ═══════════════════════════════════════════════════════════════
with tab_dash:
    st.markdown("""
    <h2 style='color:#1a3c6e; margin-bottom:2px;'>EPL-1000</h2>
    <p style='color:#555; font-size:1.05em; margin-bottom:2px;'>
    Every Premier League club scored on the same 0–1,000 scale across 5 dimensions:
    financial health, on-pitch ROI, transfer efficiency, revenue strength, and stability.
    Compare clubs side by side. A higher score means the club is in a stronger position as a business.</p>
    """, unsafe_allow_html=True)
    st.caption(f"{len(all_clubs)} clubs scored for 2024-25 season")

    # Top 5 / Bottom 5
    st.markdown("<div class='section-title'>Top 5</div>", unsafe_allow_html=True)
    cols_top = st.columns(5)
    for i, c in enumerate(all_clubs[:5]):
        with cols_top[i]:
            color = "#10b981" if i == 0 else "#2E7BE6"
            if c.get("logo"):
                st.image(c["logo"], width=50)
            st.markdown(
                f"<div style='text-align:center;'>"
                f"<div style='font-size:28px;font-weight:900;color:{color};'>{int(c['total'])}</div>"
                f"<div style='font-size:13px;color:#555;'>{c['name']}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div class='section-title'>Bottom 5</div>", unsafe_allow_html=True)
    cols_bot = st.columns(5)
    for i, c in enumerate(all_clubs[-5:]):
        with cols_bot[i]:
            if c.get("logo"):
                st.image(c["logo"], width=50)
            st.markdown(
                f"<div style='text-align:center;'>"
                f"<div style='font-size:28px;font-weight:900;color:#ef4444;'>{int(c['total'])}</div>"
                f"<div style='font-size:13px;color:#555;'>{c['name']}</div></div>",
                unsafe_allow_html=True,
            )

    # All clubs grid
    st.markdown("<div class='section-title'>All Clubs</div>", unsafe_allow_html=True)
    grid_cols = st.columns(5)
    for idx, c in enumerate(all_clubs):
        with grid_cols[idx % 5]:
            total = int(c["total"])
            if total >= 700:
                badge_color = "#10b981"
            elif total >= 500:
                badge_color = "#2E7BE6"
            elif total >= 350:
                badge_color = "#f59e0b"
            else:
                badge_color = "#ef4444"
            if c.get("logo"):
                st.image(c["logo"], width=35)
            st.markdown(
                f"<div class='card'><div style='font-size:11px;color:#999;'>#{idx+1}</div>"
                f"<div style='font-size:15px;font-weight:700;'>{c['name']}</div>"
                f"<span class='score-badge' style='background:{badge_color}22;color:{badge_color};'>{total}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

# ═══════════════════════════════════════════════════════════════
# TAB 2 — Club Detail
# ═══════════════════════════════════════════════════════════════
with tab_detail:
    club_names = [c["name"] for c in all_clubs]
    sel_name = st.selectbox("Select Club", club_names, key="sel_club")
    selected = club_map[sel_name]
    total = int(selected["total"])
    fin = selected["financials"]
    standing = selected.get("standing", {})

    # Compare
    compare_names = ["(none)"] + [n for n in club_names if n != sel_name]
    comp_name = st.selectbox("Compare with", compare_names, key="comp_club")
    compare_data = club_map.get(comp_name) if comp_name != "(none)" else None

    # Buttons
    bc1, bc2, bc3, bc4 = st.columns(4)
    with bc1:
        save_it = st.button("Save", key="btn_save")
    with bc2:
        clear_it = st.button("Clear", key="btn_clear")
    with bc3:
        if _PDF_AVAILABLE:
            snapshot = {
                "Owner": fin["owner"], "Manager": fin["manager"],
                "Stadium": fin["stadium"], "FFP Status": fin["ffp_status"],
                "Valuation": f"${fin['valuation_m']}M",
                "Position": standing.get("position", "N/A"),
            }
            pdf_bytes = generate_pdf(selected, AXES_LABELS, LOGIC_DESC, snapshot)
            if pdf_bytes:
                st.download_button("PDF", pdf_bytes, f"EPL_1000_{sel_name}.pdf", "application/pdf", key="btn_pdf")
    with bc4:
        excel_data = generate_excel(selected, AXES_LABELS, LOGIC_DESC)
        st.download_button("Excel", excel_data, f"EPL_1000_{sel_name}.csv", "text/csv", key="btn_excel")

    if save_it:
        st.session_state.saved_club = selected
        st.rerun()
    if clear_it:
        st.session_state.saved_club = None
        st.rerun()

    # Logo + Total Score
    if selected.get("logo"):
        img_col, score_col = st.columns([1, 2.5])
        with img_col:
            st.image(selected["logo"], width=120)
        with score_col:
            st.markdown(f"""
            <div style="text-align:center;margin:10px 0;">
                <div style="font-size:14px;letter-spacing:2px;color:#666;">TOTAL SCORE</div>
                <div style="font-size:80px;font-weight:800;color:#2E7BE6;line-height:1;">
                    {total}<span style="font-size:30px;color:#BBB;"> / 1000</span>
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="text-align:center;margin:10px 0;">
            <div style="font-size:14px;letter-spacing:2px;color:#666;">TOTAL SCORE</div>
            <div style="font-size:80px;font-weight:800;color:#2E7BE6;line-height:1;">
                {total}<span style="font-size:30px;color:#BBB;"> / 1000</span>
            </div>
        </div>""", unsafe_allow_html=True)

    render_score_delta(sel_name, total)

    # Radar + Score Metrics
    col_r, col_a = st.columns([1.5, 1])
    with col_r:
        st.markdown("<div style='font-size:1.1em;font-weight:bold;color:#333;margin-bottom:5px;'>Intelligence Radar</div>", unsafe_allow_html=True)
        fig_r = render_radar_chart(selected, compare_data, AXES_LABELS)
        st.plotly_chart(fig_r, use_container_width=True, config={"displayModeBar": False}, key="radar_detail")
    with col_a:
        st.markdown("<div style='font-size:0.9em;font-weight:bold;color:#333;margin-bottom:15px;border-left:3px solid #2E7BE6;padding-left:8px;'>SCORE METRICS</div>", unsafe_allow_html=True)
        for ax in AXES_LABELS:
            val = int(selected["axes"].get(ax, 0))
            pct = val / 200 * 100
            bar_color = "#10b981" if pct >= 70 else "#2E7BE6" if pct >= 40 else "#ef4444"
            st.markdown(
                f"<div style='margin-bottom:8px;'>"
                f"<div style='font-size:12px;color:#555;'>{ax}</div>"
                f"<div style='background:#eee;border-radius:6px;height:18px;'>"
                f"<div style='background:{bar_color};width:{pct}%;height:100%;border-radius:6px;text-align:right;padding-right:6px;color:white;font-size:11px;font-weight:700;line-height:18px;'>{val}</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

    # Club Snapshot
    st.markdown("<div class='section-title'>Club Snapshot</div>", unsafe_allow_html=True)
    s1, s2 = st.columns(2)
    with s1:
        st.markdown(f"""
        <div class='card'>
            <div style='font-size:11px;color:#999;'>OWNER</div>
            <div style='font-size:16px;font-weight:700;'>{fin['owner']}</div>
            <div style='font-size:11px;color:#999;margin-top:8px;'>MANAGER</div>
            <div style='font-size:16px;font-weight:700;'>{fin['manager']}</div>
            <div style='font-size:11px;color:#999;margin-top:8px;'>STADIUM</div>
            <div style='font-size:16px;font-weight:700;'>{fin['stadium']} ({fin['stadium_capacity']:,})</div>
            <div style='font-size:11px;color:#999;margin-top:8px;'>FOUNDED</div>
            <div style='font-size:16px;font-weight:700;'>{fin['founded']}</div>
        </div>""", unsafe_allow_html=True)
    with s2:
        ffp_color = "#10b981" if "Compliant" in fin["ffp_status"] else "#ef4444"
        st.markdown(f"""
        <div class='card'>
            <div style='font-size:11px;color:#999;'>VALUATION</div>
            <div style='font-size:16px;font-weight:700;'>${fin['valuation_m']:,}M</div>
            <div style='font-size:11px;color:#999;margin-top:8px;'>REVENUE</div>
            <div style='font-size:16px;font-weight:700;'>${fin['revenue_m']}M</div>
            <div style='font-size:11px;color:#999;margin-top:8px;'>NET TRANSFER SPEND</div>
            <div style='font-size:16px;font-weight:700;'>${fin['net_transfer_spend_m']}M</div>
            <div style='font-size:11px;color:#999;margin-top:8px;'>FFP STATUS</div>
            <div style='font-size:16px;font-weight:700;color:{ffp_color};'>{fin['ffp_status']}</div>
        </div>""", unsafe_allow_html=True)

    # Transfer Activity
    st.markdown("<div class='section-title'>Transfer Activity</div>", unsafe_allow_html=True)
    t1, t2 = st.columns(2)
    with t1:
        st.markdown("<div style='font-size:13px;font-weight:700;color:#10b981;'>KEY SIGNINGS</div>", unsafe_allow_html=True)
        for p in fin.get("key_signings", []):
            st.markdown(f"- {p}")
    with t2:
        st.markdown("<div style='font-size:13px;font-weight:700;color:#ef4444;'>KEY DEPARTURES</div>", unsafe_allow_html=True)
        for p in fin.get("key_departures", []):
            st.markdown(f"- {p}")

    # Score Summary Cards
    st.markdown("<div class='section-title'>Score Summary</div>", unsafe_allow_html=True)
    sorted_axes = sorted(selected["axes"].items(), key=lambda x: x[1], reverse=True)
    sc1, sc2, sc3 = st.columns(3)
    sc1.markdown(
        f'<div class="card"><div style="font-size:11px;color:#999;">STRONGEST AXIS</div>'
        f'<div style="font-size:18px;font-weight:900;"><span style="color:#10b981;">{sorted_axes[0][0]} ({sorted_axes[0][1]})</span></div></div>',
        unsafe_allow_html=True,
    )
    sc2.markdown(
        f'<div class="card"><div style="font-size:11px;color:#999;">LEAGUE POSITION</div>'
        f'<div style="font-size:18px;font-weight:900;">#{standing.get("position", "N/A")} ({standing.get("points", 0)} pts)</div></div>',
        unsafe_allow_html=True,
    )
    sc3.markdown(
        f'<div class="card"><div style="font-size:11px;color:#999;">WEAKEST AXIS</div>'
        f'<div style="font-size:18px;font-weight:900;"><span style="color:#ef4444;">{sorted_axes[-1][0]} ({sorted_axes[-1][1]})</span></div></div>',
        unsafe_allow_html=True,
    )

    # Score History
    history = _load_scores_history()
    if history:
        dates = sorted(history.keys())
        h_dates, h_vals = [], []
        for d in dates:
            s = history[d].get(sel_name)
            if s is not None:
                h_dates.append(d)
                h_vals.append(s)
        if len(h_dates) >= 1:
            st.markdown("<div class='section-title'>Score History</div>", unsafe_allow_html=True)
            fig_h = go.Figure()
            fig_h.add_trace(go.Scatter(x=h_dates, y=h_vals, mode="lines",
                                       line=dict(color="#2E7BE6", width=2),
                                       fill="tozeroy", fillcolor="rgba(46,123,230,0.05)"))
            fig_h.update_layout(yaxis=dict(range=[0, 1000], title="Score"), height=250,
                                margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="white",
                                hovermode="x unified", clickmode="none", dragmode=False)
            st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar": False}, key="hist_detail")

    # Daily Tracker
    st.markdown("<div class='section-title'>Daily Score Tracker</div>", unsafe_allow_html=True)
    render_daily_tracker(sel_name)

    # News
    st.markdown("<div class='section-title'>Latest News</div>", unsafe_allow_html=True)
    news = fetch_club_news(sel_name)
    if news:
        for n in news[:5]:
            st.markdown(f"- [{n['title']}]({n['link']}) — *{n['source']}*")
    else:
        st.caption("No recent news found.")

# ═══════════════════════════════════════════════════════════════
# TAB 3 — Rankings
# ═══════════════════════════════════════════════════════════════
with tab_rank:
    st.markdown("<div class='section-title'>EPL-1000 Rankings</div>", unsafe_allow_html=True)

    sort_by = st.selectbox("Sort by", ["Total Score"] + AXES_LABELS, key="rank_sort")

    if sort_by == "Total Score":
        sorted_clubs = sorted(all_clubs, key=lambda x: x["total"], reverse=True)
    else:
        sorted_clubs = sorted(all_clubs, key=lambda x: x["axes"].get(sort_by, 0), reverse=True)

    rows = []
    for i, c in enumerate(sorted_clubs):
        row = {
            "Rank": i + 1,
            "Club": c["name"],
            "Total Score": int(c["total"]),
        }
        for ax in AXES_LABELS:
            row[ax] = int(c["axes"].get(ax, 0))
        pos = c.get("standing", {}).get("position", "-")
        row["League Pos"] = pos
        rows.append(row)

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True, height=750)

    # Excel export
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button("Download Excel (All Clubs)", csv_buf.getvalue().encode(), "epl_1000_rankings.csv", "text/csv", key="btn_csv_rank")

    # Score Distribution
    st.markdown("<div class='section-title'>Score Distribution</div>", unsafe_allow_html=True)
    fig_dist = px.histogram(df, x="Total Score", nbins=10, color_discrete_sequence=["#2E7BE6"])
    fig_dist.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="white")
    st.plotly_chart(fig_dist, use_container_width=True, config={"displayModeBar": False}, key="dist_rank")

    # Axis Breakdown
    st.markdown("<div class='section-title'>Axis Comparison</div>", unsafe_allow_html=True)
    fig_bar = go.Figure()
    for ax in AXES_LABELS:
        fig_bar.add_trace(go.Bar(name=ax, x=[c["name"] for c in sorted_clubs], y=[c["axes"].get(ax, 0) for c in sorted_clubs]))
    fig_bar.update_layout(barmode="stack", height=450, margin=dict(l=0, r=0, t=10, b=0),
                          plot_bgcolor="white", legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False}, key="axis_rank")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#aaa;font-size:12px;'>"
    "This tool is for informational purposes only. Scores are derived from publicly available data. "
    "Not affiliated with the Premier League, any club, or the FA.</div>",
    unsafe_allow_html=True,
)
