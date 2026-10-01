-- ==============================================================================
-- Global Streaming Trend Intelligence Platform
-- PostgreSQL / Neon Database Schema (Silver & Gold Layers)
-- Compatible with PostgreSQL 13+ and SQLite 3.35+
-- ==============================================================================

-- 1. Platforms Dimension
CREATE TABLE IF NOT EXISTS platforms (
    platform_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    color VARCHAR(20) DEFAULT '#E50914',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Countries Dimension
CREATE TABLE IF NOT EXISTS countries (
    country_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    iso_code VARCHAR(10) NOT NULL UNIQUE,
    region VARCHAR(50) DEFAULT 'Global',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Titles Dimension
CREATE TABLE IF NOT EXISTS titles (
    title_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    content_type VARCHAR(20) NOT NULL, -- 'movie' or 'series'
    slug VARCHAR(255),
    release_year INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_title_type UNIQUE (name, content_type)
);

-- 4. Daily Rankings Fact Table (Silver Layer - Standardized Snapshots)
CREATE TABLE IF NOT EXISTS rankings (
    ranking_id SERIAL PRIMARY KEY,
    chart_date DATE NOT NULL,
    platform_id INT NOT NULL REFERENCES platforms(platform_id) ON DELETE CASCADE,
    country_id INT NOT NULL REFERENCES countries(country_id) ON DELETE CASCADE,
    title_id INT NOT NULL REFERENCES titles(title_id) ON DELETE CASCADE,
    rank INT NOT NULL CHECK (rank >= 1 AND rank <= 100),
    points INT DEFAULT 0,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_chart_entry UNIQUE (chart_date, platform_id, country_id, title_id)
);

-- 5. Trends & Movements Fact Table (Silver Layer - Delta Analytics)
CREATE TABLE IF NOT EXISTS trends (
    trend_id SERIAL PRIMARY KEY,
    chart_date DATE NOT NULL,
    platform_id INT NOT NULL REFERENCES platforms(platform_id) ON DELETE CASCADE,
    country_id INT NOT NULL REFERENCES countries(country_id) ON DELETE CASCADE,
    title_id INT NOT NULL REFERENCES titles(title_id) ON DELETE CASCADE,
    current_rank INT NOT NULL,
    previous_rank INT,
    rank_change INT, -- Positive = climbed, Negative = dropped, 0 = stable, NULL = debut
    days_in_top_10 INT DEFAULT 1,
    is_new_entry BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_trend_entry UNIQUE (chart_date, platform_id, country_id, title_id)
);

-- Indexes for lightning-fast queries in Streamlit
CREATE INDEX IF NOT EXISTS idx_rankings_date ON rankings(chart_date);
CREATE INDEX IF NOT EXISTS idx_rankings_platform ON rankings(platform_id);
CREATE INDEX IF NOT EXISTS idx_rankings_country ON rankings(country_id);
CREATE INDEX IF NOT EXISTS idx_rankings_title ON rankings(title_id);
CREATE INDEX IF NOT EXISTS idx_trends_date ON trends(chart_date);
CREATE INDEX IF NOT EXISTS idx_trends_movement ON trends(rank_change);
