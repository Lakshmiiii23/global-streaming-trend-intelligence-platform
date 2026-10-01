import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
from datetime import datetime
from src.db.postgres_client import get_db_manager
from src.dashboard.components import (
    PLATFORM_COLORS, format_trend_badge, plot_platform_share, 
    plot_rank_history, plot_points_bar
)
from run_pipeline import run_ingestion_bronze, run_processing_silver_gold

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="Global Streaming Trend Intelligence Platform",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern dark UI
st.markdown("""
<style>
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .metric-title {
        font-size: 0.85rem;
        color: #94a3b8;
        font-weight: 500;
        text-transform: uppercase;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #f8fafc;
        margin-top: 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .metric-delta {
        font-size: 0.85rem;
        margin-top: 4px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        border-radius: 6px;
    }
    .custom-leaderboard-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.88rem;
    }
    .custom-leaderboard-table th {
        background-color: #1e293b;
        color: #94a3b8;
        padding: 10px 12px;
        text-align: left;
        border-bottom: 2px solid #334155;
        font-weight: 600;
    }
    .custom-leaderboard-table td {
        padding: 10px 12px;
        border-bottom: 1px solid #1e293b;
        color: #f1f5f9;
    }
    .custom-leaderboard-table tr:hover {
        background-color: #1e293b66;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Database connection
db = get_db_manager()

# Sidebar: Controls & Filters
st.sidebar.image("https://img.icons8.com/color/96/movie-projector.png", width=64)
st.sidebar.title("🎬 Trend Intelligence")
st.sidebar.markdown(f"**Database:** `{'Neon PostgreSQL' if db.is_postgres else 'SQLite (Local)'}`")

# Fetch available dates
dates_df = db.query_df("SELECT DISTINCT chart_date FROM rankings ORDER BY chart_date DESC")
available_dates = dates_df["chart_date"].astype(str).tolist() if not dates_df.empty else [datetime.now().strftime("%Y-%m-%d")]

selected_date = st.sidebar.selectbox("📅 Chart Date", available_dates, index=0)

# Fetch platforms and countries
platforms_df = db.query_df("SELECT name, slug FROM platforms ORDER BY name")
all_platforms = ["All Platforms"] + platforms_df["name"].tolist()
selected_platform = st.sidebar.selectbox("📺 Streaming Platform", all_platforms, index=0)

countries_df = db.query_df("SELECT name, iso_code FROM countries ORDER BY name")
all_countries = ["All Countries"] + countries_df["name"].tolist()
selected_country = st.sidebar.selectbox("🌍 Country / Region", all_countries, index=0)

content_type_filter = st.sidebar.radio("🎞️ Content Type", ["All", "Movies Only", "TV Shows Only"])

st.sidebar.markdown("---")
scrape_live = st.sidebar.checkbox("Scrape Live FlixPatrol (requires ~20s)", value=True)
if st.sidebar.button("🔄 Trigger Pipeline Refresh", help="Run ingestion and trend detection"):
    source_mode = "live" if scrape_live else "synthetic"
    
    # Target selected platform/country or defaults
    p_targets = None
    if selected_platform != "All Platforms":
        matched_plat = platforms_df.loc[platforms_df["name"] == selected_platform, "slug"]
        if not matched_plat.empty:
            p_targets = [matched_plat.iloc[0]]
            
    c_targets = None
    if selected_country != "All Countries":
        matched_ctry = countries_df.loc[countries_df["name"] == selected_country, "iso_code"]
        if not matched_ctry.empty:
            c_targets = [matched_ctry.iloc[0]]
            
    with st.sidebar.status(f"Running pipeline ({source_mode})...", expanded=True) as status:
        st.write("Ingesting Bronze layer from FlixPatrol...")
        batch_key = run_ingestion_bronze(
            source=source_mode, 
            days=1, 
            platforms=p_targets, 
            countries=c_targets
        )
        st.write("Processing Silver & Gold layers...")
        run_processing_silver_gold(batch_key)
        status.update(label="Live pipeline run complete!", state="complete", expanded=False)
    st.rerun()

# Build SQL query filter clauses
platform_clause = ""
if selected_platform != "All Platforms":
    platform_clause = f"AND p.name = '{selected_platform}'"

country_clause = ""
if selected_country != "All Countries":
    country_clause = f"AND c.name = '{selected_country}'"

type_clause = ""
if content_type_filter == "Movies Only":
    type_clause = "AND t.content_type = 'movie'"
elif content_type_filter == "TV Shows Only":
    type_clause = "AND t.content_type = 'series'"

# Fetch active dataset for the chosen filters
active_query = f"""
    SELECT 
        r.chart_date,
        p.name AS platform_name,
        c.name AS country_name,
        t.name AS title_name,
        t.content_type,
        r.rank AS current_rank,
        r.points,
        tr.previous_rank,
        tr.rank_change,
        tr.days_in_top_10,
        tr.is_new_entry
    FROM rankings r
    JOIN platforms p ON r.platform_id = p.platform_id
    JOIN countries c ON r.country_id = c.country_id
    JOIN titles t ON r.title_id = t.title_id
    LEFT JOIN trends tr ON r.chart_date = tr.chart_date 
        AND r.platform_id = tr.platform_id 
        AND r.country_id = tr.country_id 
        AND r.title_id = tr.title_id
    WHERE r.chart_date = '{selected_date}'
    {platform_clause}
    {country_clause}
    {type_clause}
    ORDER BY r.rank ASC, r.points DESC
"""
active_df = db.query_df(active_query)

# Title Header
st.title("🎯 Global Streaming Trend Intelligence Platform")
st.markdown(
    f"Tracking popularity shifts, day-over-day rank delta, and chart endurance across "
    f"**{selected_platform}** in **{selected_country}** on **{selected_date}**."
)

if active_df.empty:
    st.warning("⚠️ No records found for the selected filter combination. Try selecting **All Platforms** or **All Countries**.")
    st.stop()

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Global Trend Pulse", 
    "🏆 Top 10 Leaderboards", 
    "🚀 Trend Velocity & Movers", 
    "🗺️ Cross-Country Intel", 
    "⚙️ Medallion Architecture"
])

# ==============================================================================
# TAB 1: GLOBAL TREND PULSE
# ==============================================================================
with tab1:
    col1, col2, col3, col4 = st.columns(4)

    # Top Movie (by rank or highest points)
    movie_candidates = active_df[active_df["content_type"] == "movie"].sort_values(by=["current_rank", "points"], ascending=[True, False])
    top_movie_title = movie_candidates.iloc[0]["title_name"] if not movie_candidates.empty else "N/A"
    top_movie_plat = movie_candidates.iloc[0]["platform_name"] if not movie_candidates.empty else ""
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🥇 Top Movie Today</div>
            <div class="metric-value">{top_movie_title}</div>
            <div class="metric-delta" style="color: #38bdf8;">{top_movie_plat}</div>
        </div>
        """, unsafe_allow_html=True)

    # Top Series
    series_candidates = active_df[active_df["content_type"] == "series"].sort_values(by=["current_rank", "points"], ascending=[True, False])
    top_series_title = series_candidates.iloc[0]["title_name"] if not series_candidates.empty else "N/A"
    top_series_plat = series_candidates.iloc[0]["platform_name"] if not series_candidates.empty else ""
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">📺 Top TV Series Today</div>
            <div class="metric-value">{top_series_title}</div>
            <div class="metric-delta" style="color: #a78bfa;">{top_series_plat}</div>
        </div>
        """, unsafe_allow_html=True)

    # Top Climber
    gainers = active_df[active_df["rank_change"] > 0].sort_values(by="rank_change", ascending=False)
    top_gainer_title = gainers.iloc[0]["title_name"] if not gainers.empty else "None"
    top_gainer_delta = f"+{int(gainers.iloc[0]['rank_change'])} spots" if not gainers.empty else "—"
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🚀 Fastest Climber</div>
            <div class="metric-value">{top_gainer_title}</div>
            <div class="metric-delta" style="color: #4ade80;">▲ {top_gainer_delta}</div>
        </div>
        """, unsafe_allow_html=True)

    # Longest Streak
    streakers = active_df.sort_values(by="days_in_top_10", ascending=False)
    top_streak_title = streakers.iloc[0]["title_name"] if not streakers.empty else "N/A"
    top_streak_days = f"{int(streakers.iloc[0]['days_in_top_10'])} days" if not streakers.empty else "0"
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">👑 Endurance Leader</div>
            <div class="metric-value">{top_streak_title}</div>
            <div class="metric-delta" style="color: #facc15;">⏱️ {top_streak_days} in Top 10</div>
        </div>
        """, unsafe_allow_html=True)

    # Visualizations Row
    chart_col1, chart_col2 = st.columns([1, 1.2])
    with chart_col1:
        st.plotly_chart(plot_platform_share(active_df, selected_platform), use_container_width=True)
    with chart_col2:
        st.plotly_chart(plot_points_bar(active_df), use_container_width=True)

# ==============================================================================
# TAB 2: TOP 10 LEADERBOARDS
# ==============================================================================
with tab2:
    st.subheader(f"Top 10 Rankings on {selected_date}")
    tcol1, tcol2 = st.columns(2)

    def render_table(sub_df, title_header):
        st.markdown(f"### {title_header}")
        if sub_df.empty:
            st.info("No titles match current filter criteria.")
            return

        # If All Countries selected, group by title to avoid repeated rows
        if selected_country == "All Countries":
            grouped = sub_df.groupby(["title_name", "platform_name"]).agg({
                "points": "sum",
                "current_rank": "min",
                "previous_rank": "min",
                "rank_change": "max",
                "days_in_top_10": "max",
                "is_new_entry": "min"
            }).reset_index().sort_values(by=["current_rank", "points"], ascending=[True, False])
            items_to_render = grouped.head(10)
        else:
            items_to_render = sub_df.sort_values(by="current_rank", ascending=True).head(10)

        display_rows = []
        for _, row in items_to_render.iterrows():
            badge = format_trend_badge(row.get("rank_change"), bool(row.get("is_new_entry", 0)))
            prev = f"#{int(row['previous_rank'])}" if pd.notna(row.get("previous_rank")) else "Debut"
            days = int(row["days_in_top_10"]) if pd.notna(row.get("days_in_top_10")) else 1
            pts = int(row["points"]) if pd.notna(row.get("points")) else 0
            cur_rank = int(row["current_rank"]) if pd.notna(row.get("current_rank")) else 1
            
            row_dict = {
                "Rank": f"#{cur_rank}",
                "Title": row["title_name"]
            }
            if selected_platform == "All Platforms":
                row_dict["Platform"] = row["platform_name"]
            row_dict.update({
                "Points": f"{pts:,}",
                "Trend": badge,
                "Yesterday": prev,
                "Days on Chart": f"{days}d"
            })
            display_rows.append(row_dict)
        
        display_df = pd.DataFrame(display_rows)
        html_table = display_df.to_html(escape=False, index=False, classes="custom-leaderboard-table")
        st.markdown(f'''
        <div style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 12px; overflow-x: auto; margin-bottom: 24px;">
            {html_table}
        </div>
        ''', unsafe_allow_html=True)

    with tcol1:
        movies_df = active_df[active_df["content_type"] == "movie"]
        render_table(movies_df, "🎬 TOP 10 Movies")

    with tcol2:
        series_df = active_df[active_df["content_type"] == "series"]
        render_table(series_df, "📺 TOP 10 TV Series")

# ==============================================================================
# TAB 3: TREND VELOCITY & MOVERS
# ==============================================================================
with tab3:
    st.subheader("Day-over-Day Velocity & Movers")
    
    mcol1, mcol2 = st.columns(2)
    with mcol1:
        st.markdown("#### 🚀 Biggest Positive Climbers")
        climbers = active_df[active_df["rank_change"] > 0].sort_values(by="rank_change", ascending=False).drop_duplicates(subset=["title_name"])
        if climbers.empty:
            st.info("No titles gained rank on this chart date.")
        else:
            st.dataframe(
                climbers[["title_name", "platform_name", "content_type", "previous_rank", "current_rank", "rank_change", "days_in_top_10"]].rename(
                    columns={"title_name": "Title", "platform_name": "Platform", "content_type": "Type", "previous_rank": "Was", "current_rank": "Now", "rank_change": "Climbed (+)", "days_in_top_10": "Days on Chart"}
                ),
                use_container_width=True,
                hide_index=True
            )

    with mcol2:
        st.markdown("#### 🔻 Steepest Drops")
        droppers = active_df[active_df["rank_change"] < 0].sort_values(by="rank_change", ascending=True).drop_duplicates(subset=["title_name"])
        if droppers.empty:
            st.info("No titles dropped rank on this chart date.")
        else:
            st.dataframe(
                droppers[["title_name", "platform_name", "content_type", "previous_rank", "current_rank", "rank_change", "days_in_top_10"]].rename(
                    columns={"title_name": "Title", "platform_name": "Platform", "content_type": "Type", "previous_rank": "Was", "current_rank": "Now", "rank_change": "Fell (-)", "days_in_top_10": "Days on Chart"}
                ),
                use_container_width=True,
                hide_index=True
            )

    st.markdown("---")
    st.subheader("📈 Title Trajectory Explorer")
    title_options = sorted(active_df["title_name"].unique().tolist())
    if title_options:
        chosen_title = st.selectbox("Select title to inspect trajectory:", title_options)
        hist_query = f"""
            SELECT 
                r.chart_date,
                ROUND(AVG(r.rank), 1) AS current_rank,
                SUM(r.points) AS points
            FROM rankings r
            JOIN titles t ON r.title_id = t.title_id
            JOIN countries c ON r.country_id = c.country_id
            WHERE t.name = '{chosen_title}'
            {country_clause}
            GROUP BY r.chart_date
            ORDER BY r.chart_date ASC
        """
        hist_df = db.query_df(hist_query)
        st.plotly_chart(plot_rank_history(hist_df, chosen_title), use_container_width=True)

# ==============================================================================
# TAB 4: CROSS-COUNTRY INTEL
# ==============================================================================
with tab4:
    st.subheader("🌍 Cross-Country Streaming Dominance")
    st.markdown("Inspect which titles are dominating multiple countries simultaneously.")
    
    cross_query = f"""
        SELECT 
            t.name AS title_name,
            t.content_type,
            COUNT(DISTINCT r.country_id) AS countries_charted,
            MIN(r.rank) AS peak_rank,
            SUM(r.points) AS global_points
        FROM rankings r
        JOIN titles t ON r.title_id = t.title_id
        WHERE r.chart_date = '{selected_date}'
        GROUP BY t.name, t.content_type
        ORDER BY countries_charted DESC, global_points DESC
        LIMIT 15
    """
    cross_df = db.query_df(cross_query)
    st.dataframe(
        cross_df.rename(columns={
            "title_name": "Title",
            "content_type": "Type",
            "countries_charted": "Countries Charted",
            "peak_rank": "Peak Rank",
            "global_points": "Total Points"
        }),
        use_container_width=True,
        hide_index=True
    )

# ==============================================================================
# TAB 5: MEDALLION ARCHITECTURE & DATA LINEAGE
# ==============================================================================
with tab5:
    st.subheader("🏗️ System Architecture & Medallion Pipeline")
    
    st.markdown("""
    This platform follows industry-standard **Medallion Data Architecture**:
    
    ```mermaid
    flowchart LR
        subgraph Ingestion
            FP[FlixPatrol Scraper] -->|Raw JSON| Bronze[(Bronze Layer: Cloudflare R2)]
            SYN[Resilient Generator] -.->|Fallback JSON| Bronze
        end
        
        subgraph Processing
            Bronze -->|Clean & Deduplicate| Cleaner[Data Cleaner]
            Cleaner -->|Enrich & Delta Analytics| Trends[Trend Detector]
            Trends -->|Load Facts & Dims| Silver[(Silver Layer: Neon PostgreSQL)]
        end
        
        subgraph Serving
            Silver -->|Materialized Queries| Gold[(Gold Analytical Views)]
            Gold -->|Streamlit SDK| UI[Streamlit Intelligence App]
        end
    ```
    
    - **Bronze Layer (Cloudflare R2)**: Immutable, append-only raw JSON storage for auditing and replayability.
    - **Silver Layer (Neon PostgreSQL)**: Cleaned, deduplicated relational dimensions (`titles`, `platforms`, `countries`) and facts (`rankings`, `trends`).
    - **Gold Layer (Analytical Views)**: Pre-aggregated SQL views for sub-second dashboard latency.
    - **Serving Layer (Streamlit Community Cloud)**: Real-time public intelligence interface.
    """)

    st.markdown("#### 🔍 Raw Data Explorer")
    st.dataframe(active_df.head(50), use_container_width=True)
    csv = active_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download Filtered Data as CSV",
        data=csv,
        file_name=f"streaming_trends_{selected_date}.csv",
        mime="text/csv"
    )
