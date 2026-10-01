import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any

PLATFORM_COLORS = {
    "Netflix": "#E50914",
    "Amazon Prime Video": "#00A8E1",
    "Disney+": "#113CCF",
    "Apple TV+": "#A2AAAD",
    "HBO Max": "#9900FF"
}

def format_trend_badge(rank_change: Any, is_new: bool) -> str:
    """Format a clean markdown badge for rank movements."""
    if is_new or pd.isna(rank_change):
        return '<span style="color: #38bdf8; font-weight: bold; background: rgba(56, 189, 248, 0.15); padding: 2px 6px; border-radius: 4px;">★ NEW</span>'
    
    val = int(rank_change)
    if val > 0:
        return f'<span style="color: #4ade80; font-weight: bold; background: rgba(74, 222, 128, 0.15); padding: 2px 6px; border-radius: 4px;">▲ +{val}</span>'
    elif val < 0:
        return f'<span style="color: #f87171; font-weight: bold; background: rgba(248, 113, 113, 0.15); padding: 2px 6px; border-radius: 4px;">▼ {val}</span>'
    else:
        return '<span style="color: #94a3b8; font-weight: bold; background: rgba(148, 163, 184, 0.15); padding: 2px 6px; border-radius: 4px;">— 0</span>'

def plot_platform_share(df: pd.DataFrame) -> go.Figure:
    """Donut chart showing share of total popularity points by platform."""
    if df.empty:
        return go.Figure()

    grouped = df.groupby("platform_name")["points"].sum().reset_index()
    colors = [PLATFORM_COLORS.get(name, "#6366f1") for name in grouped["platform_name"]]

    fig = go.Figure(data=[go.Pie(
        labels=grouped["platform_name"],
        values=grouped["points"],
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="#0f172a", width=2)),
        textinfo="label+percent",
        hoverinfo="label+value+percent"
    )])
    fig.update_layout(
        title="Streaming Share of Popularity Points",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f8fafc", family="sans-serif"),
        margin=dict(t=40, b=20, l=20, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    return fig

def plot_rank_history(df: pd.DataFrame, title_name: str) -> go.Figure:
    """Line chart showing rank trajectory over time (inverted Y-axis where rank 1 is top)."""
    fig = go.Figure()
    if df.empty:
        return fig

    # Invert Y-axis so rank 1 is on top
    fig.add_trace(go.Scatter(
        x=df["chart_date"],
        y=df["current_rank"],
        mode="lines+markers",
        name=title_name,
        line=dict(color="#38bdf8", width=3),
        marker=dict(size=8, color="#38bdf8")
    ))
    fig.update_layout(
        title=f"Historical Rank Trajectory: {title_name}",
        xaxis_title="Chart Date",
        yaxis_title="Rank Position (1 is Highest)",
        yaxis=dict(autorange="reversed", dtick=1, range=[10.5, 0.5]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f8fafc"),
        margin=dict(t=40, b=40, l=40, r=40)
    )
    return fig

def plot_points_bar(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart for top 10 titles by points."""
    if df.empty:
        return go.Figure()

    df_sorted = df.sort_values(by="points", ascending=True)
    fig = px.bar(
        df_sorted,
        x="points",
        y="title_name",
        orientation="h",
        color="platform_name",
        color_discrete_map=PLATFORM_COLORS,
        text="points",
        labels={"points": "Popularity Points", "title_name": "Title", "platform_name": "Platform"}
    )
    fig.update_layout(
        title="Top Titles by Popularity Points",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f8fafc"),
        margin=dict(t=40, b=20, l=20, r=20),
        xaxis=dict(showgrid=True, gridcolor="#334155"),
        yaxis=dict(showgrid=False)
    )
    return fig
