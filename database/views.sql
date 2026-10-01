-- ==============================================================================
-- Gold Layer Analytical Views
-- High-performance aggregated views for Streamlit Dashboard and BI Reporting
-- ==============================================================================

-- 1. Top Trending Titles by Country (Latest Snapshot)
CREATE VIEW IF NOT EXISTS v_top_trending_by_country AS
SELECT 
    c.name AS country_name,
    c.iso_code AS country_code,
    p.name AS platform_name,
    t.name AS title_name,
    t.content_type,
    r.rank,
    r.points,
    r.chart_date,
    tr.days_in_top_10,
    tr.rank_change,
    tr.is_new_entry
FROM rankings r
JOIN platforms p ON r.platform_id = p.platform_id
JOIN countries c ON r.country_id = c.country_id
JOIN titles t ON r.title_id = t.title_id
LEFT JOIN trends tr ON r.chart_date = tr.chart_date 
    AND r.platform_id = tr.platform_id 
    AND r.country_id = tr.country_id 
    AND r.title_id = tr.title_id
WHERE r.rank = 1;

-- 2. Platform Popularity Index (Aggregated reach & point share)
CREATE VIEW IF NOT EXISTS v_platform_popularity_index AS
SELECT 
    r.chart_date,
    p.name AS platform_name,
    p.slug AS platform_slug,
    COUNT(DISTINCT r.title_id) AS distinct_titles_charted,
    SUM(r.points) AS total_popularity_points,
    AVG(r.rank) AS avg_chart_rank,
    COUNT(r.ranking_id) AS total_chart_placements
FROM rankings r
JOIN platforms p ON r.platform_id = p.platform_id
GROUP BY r.chart_date, p.name, p.slug;

-- 3. Breakout Climbers (Biggest Positive Movers Today)
CREATE VIEW IF NOT EXISTS v_breakout_climbers AS
SELECT 
    tr.chart_date,
    p.name AS platform_name,
    c.name AS country_name,
    t.name AS title_name,
    t.content_type,
    tr.previous_rank,
    tr.current_rank,
    tr.rank_change,
    tr.days_in_top_10
FROM trends tr
JOIN platforms p ON tr.platform_id = p.platform_id
JOIN countries c ON tr.country_id = c.country_id
JOIN titles t ON tr.title_id = t.title_id
WHERE tr.rank_change > 0
ORDER BY tr.rank_change DESC;

-- 4. Endurance Champions (Longest Consecutive Streak in Top 10)
CREATE VIEW IF NOT EXISTS v_endurance_champions AS
SELECT 
    t.name AS title_name,
    t.content_type,
    p.name AS platform_name,
    c.name AS country_name,
    MAX(tr.days_in_top_10) AS max_days_on_chart,
    MIN(tr.current_rank) AS peak_rank,
    MAX(tr.chart_date) AS last_seen_date
FROM trends tr
JOIN titles t ON tr.title_id = t.title_id
JOIN platforms p ON tr.platform_id = p.platform_id
JOIN countries c ON tr.country_id = c.country_id
GROUP BY t.name, t.content_type, p.name, c.name
ORDER BY max_days_on_chart DESC;
