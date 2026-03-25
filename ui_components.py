# ui_components.py
"""Shared UI helpers for EPL-1000."""
import plotly.graph_objects as go
import streamlit as st


def inject_css():
    st.markdown("""
    <style>
    .section-title {
        font-size: 1.2em; font-weight: 800; color: #1a3c6e;
        text-transform: uppercase; letter-spacing: 1px;
        margin: 28px 0 12px 0; padding-bottom: 4px;
        border-bottom: 2px solid #e0e0e0;
    }
    .card {
        background: #f9fafb; border-radius: 10px; padding: 14px 18px;
        margin-bottom: 8px; border: 1px solid #eee;
    }
    .score-badge {
        display: inline-block; padding: 3px 12px; border-radius: 20px;
        font-weight: 800; font-size: 1.05em;
    }
    </style>
    """, unsafe_allow_html=True)


def render_radar_chart(data, compare_data, axes_labels):
    categories = axes_labels + [axes_labels[0]]
    values = [data["axes"].get(a, 0) for a in axes_labels] + [data["axes"].get(axes_labels[0], 0)]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values, theta=categories, fill="toself",
        name=data["name"],
        line=dict(color="#2E7BE6", width=2),
        fillcolor="rgba(46,123,230,0.15)",
    ))
    if compare_data:
        cvals = [compare_data["axes"].get(a, 0) for a in axes_labels] + [compare_data["axes"].get(axes_labels[0], 0)]
        fig.add_trace(go.Scatterpolar(
            r=cvals, theta=categories, fill="toself",
            name=compare_data["name"],
            line=dict(color="#f59e0b", width=2),
            fillcolor="rgba(245,158,11,0.10)",
        ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 200], gridcolor="#F0F0F0"),
            angularaxis=dict(rotation=90, direction="clockwise"),
        ),
        showlegend=bool(compare_data),
        height=380, margin=dict(l=60, r=60, t=40, b=40),
    )
    return fig
