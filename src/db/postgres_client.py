import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from config.settings import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Manages connections and transactions for Neon PostgreSQL (and local SQLite fallback).
    
    Silver Layer:
    - Normalizes dimension tables: platforms, countries, titles.
    - Loads daily rankings fact table.
    - Computes trend metrics: previous rank, rank change, days on chart, new debut.
    
    Gold Layer:
    - Provides aggregated analytical queries and views.
    """

    def __init__(self, database_url: Optional[str] = None):
        self.url = database_url or settings.DATABASE_URL
        # In modern SQLAlchemy, postgres:// must be postgresql://
        if self.url.startswith("postgres://"):
            self.url = self.url.replace("postgres://", "postgresql://", 1)
            
        connect_args = {}
        if "sqlite" in self.url:
            connect_args = {"check_same_thread": False}
            
        self.engine: Engine = create_engine(
            self.url,
            connect_args=connect_args,
            pool_pre_ping=True
        )
        self.is_postgres = "postgresql" in self.url

    def init_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        with self.engine.begin() as conn:
            if self.is_postgres:
                # PostgreSQL schema
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS platforms (
                    platform_id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    slug VARCHAR(100) NOT NULL UNIQUE,
                    color VARCHAR(20) DEFAULT '#E50914',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """))
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS countries (
                    country_id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    iso_code VARCHAR(10) NOT NULL UNIQUE,
                    region VARCHAR(50) DEFAULT 'Global',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """))
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS titles (
                    title_id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    content_type VARCHAR(20) NOT NULL,
                    slug VARCHAR(255),
                    release_year INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_title_type UNIQUE (name, content_type)
                );
                """))
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS rankings (
                    ranking_id SERIAL PRIMARY KEY,
                    chart_date DATE NOT NULL,
                    platform_id INT NOT NULL REFERENCES platforms(platform_id) ON DELETE CASCADE,
                    country_id INT NOT NULL REFERENCES countries(country_id) ON DELETE CASCADE,
                    title_id INT NOT NULL REFERENCES titles(title_id) ON DELETE CASCADE,
                    rank INT NOT NULL,
                    points INT DEFAULT 0,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_chart_entry UNIQUE (chart_date, platform_id, country_id, title_id)
                );
                """))
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS trends (
                    trend_id SERIAL PRIMARY KEY,
                    chart_date DATE NOT NULL,
                    platform_id INT NOT NULL REFERENCES platforms(platform_id) ON DELETE CASCADE,
                    country_id INT NOT NULL REFERENCES countries(country_id) ON DELETE CASCADE,
                    title_id INT NOT NULL REFERENCES titles(title_id) ON DELETE CASCADE,
                    current_rank INT NOT NULL,
                    previous_rank INT,
                    rank_change INT,
                    days_in_top_10 INT DEFAULT 1,
                    is_new_entry BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_trend_entry UNIQUE (chart_date, platform_id, country_id, title_id)
                );
                """))
            else:
                # SQLite schema (Local development)
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS platforms (
                    platform_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    slug TEXT NOT NULL UNIQUE,
                    color TEXT DEFAULT '#E50914',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """))
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS countries (
                    country_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    iso_code TEXT NOT NULL UNIQUE,
                    region TEXT DEFAULT 'Global',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """))
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS titles (
                    title_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    slug TEXT,
                    release_year INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, content_type)
                );
                """))
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS rankings (
                    ranking_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chart_date TEXT NOT NULL,
                    platform_id INTEGER NOT NULL REFERENCES platforms(platform_id),
                    country_id INTEGER NOT NULL REFERENCES countries(country_id),
                    title_id INTEGER NOT NULL REFERENCES titles(title_id),
                    rank INTEGER NOT NULL,
                    points INTEGER DEFAULT 0,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(chart_date, platform_id, country_id, title_id)
                );
                """))
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS trends (
                    trend_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chart_date TEXT NOT NULL,
                    platform_id INTEGER NOT NULL REFERENCES platforms(platform_id),
                    country_id INTEGER NOT NULL REFERENCES countries(country_id),
                    title_id INTEGER NOT NULL REFERENCES titles(title_id),
                    current_rank INTEGER NOT NULL,
                    previous_rank INTEGER,
                    rank_change INTEGER,
                    days_in_top_10 INTEGER DEFAULT 1,
                    is_new_entry BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(chart_date, platform_id, country_id, title_id)
                );
                """))
                
            # Indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rank_date ON rankings(chart_date);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rank_plat ON rankings(platform_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rank_ctry ON rankings(country_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rank_title ON rankings(title_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tr_date ON trends(chart_date);"))
            logger.info("Initialized database schema successfully.")

    def seed_initial_dimensions(self) -> None:
        """Seed default platforms and countries."""
        initial_platforms = [
            ("Netflix", "netflix", "#E50914"),
            ("Amazon Prime Video", "amazon-prime", "#00A8E1"),
            ("Disney+", "disney", "#113CCF"),
            ("Apple TV+", "apple-tv", "#7D7D7D"),
            ("HBO Max", "hbo-max", "#9900FF")
        ]
        initial_countries = [
            ("Worldwide", "world", "Global"),
            ("United States", "united-states", "North America"),
            ("United Kingdom", "united-kingdom", "Europe"),
            ("India", "india", "Asia"),
            ("Brazil", "brazil", "South America"),
            ("Japan", "japan", "Asia"),
            ("Germany", "germany", "Europe"),
            ("France", "france", "Europe"),
            ("Canada", "canada", "North America"),
            ("Australia", "australia", "Oceania")
        ]
        with self.engine.begin() as conn:
            for name, slug, color in initial_platforms:
                if self.is_postgres:
                    conn.execute(text("""
                    INSERT INTO platforms (name, slug, color) VALUES (:name, :slug, :color)
                    ON CONFLICT (slug) DO NOTHING;
                    """), {"name": name, "slug": slug, "color": color})
                else:
                    conn.execute(text("""
                    INSERT OR IGNORE INTO platforms (name, slug, color) VALUES (:name, :slug, :color);
                    """), {"name": name, "slug": slug, "color": color})
                    
            for name, iso, reg in initial_countries:
                if self.is_postgres:
                    conn.execute(text("""
                    INSERT INTO countries (name, iso_code, region) VALUES (:name, :iso, :reg)
                    ON CONFLICT (iso_code) DO NOTHING;
                    """), {"name": name, "iso": iso, "reg": reg})
                else:
                    conn.execute(text("""
                    INSERT OR IGNORE INTO countries (name, iso_code, region) VALUES (:name, :iso, :reg);
                    """), {"name": name, "iso": iso, "reg": reg})
        logger.info("Seeded initial platforms and countries.")

    def get_or_create_title(self, name: str, content_type: str, release_year: Optional[int] = None, conn: Optional[Any] = None) -> int:
        """Fetch title_id or create new title record."""
        clean_name = name.strip()
        clean_type = content_type.lower().strip()

        def _execute(connection):
            res = connection.execute(
                text("SELECT title_id FROM titles WHERE LOWER(name) = LOWER(:name) AND content_type = :content_type LIMIT 1"),
                {"name": clean_name, "content_type": clean_type}
            ).fetchone()
            if res:
                return res[0]
            
            slug = clean_name.lower().replace(" ", "-").replace(":", "").replace("'", "")[:100]
            if self.is_postgres:
                ins = connection.execute(
                    text("""
                    INSERT INTO titles (name, content_type, slug, release_year)
                    VALUES (:name, :content_type, :slug, :release_year)
                    RETURNING title_id
                    """),
                    {"name": clean_name, "content_type": clean_type, "slug": slug, "release_year": release_year}
                )
                return ins.fetchone()[0]
            else:
                connection.execute(
                    text("""
                    INSERT OR IGNORE INTO titles (name, content_type, slug, release_year)
                    VALUES (:name, :content_type, :slug, :release_year)
                    """),
                    {"name": clean_name, "content_type": clean_type, "slug": slug, "release_year": release_year}
                )
                row = connection.execute(
                    text("SELECT title_id FROM titles WHERE LOWER(name) = LOWER(:name) AND content_type = :content_type"),
                    {"name": clean_name, "content_type": clean_type}
                ).fetchone()
                return row[0]

        if conn is not None:
            return _execute(conn)
        with self.engine.begin() as c:
            return _execute(c)

    def get_platform_id(self, slug: str) -> Optional[int]:
        """Lookup platform_id by slug."""
        with self.engine.connect() as conn:
            row = conn.execute(text("SELECT platform_id FROM platforms WHERE slug = :slug"), {"slug": slug}).fetchone()
            return row[0] if row else None

    def get_country_id(self, iso_code: str) -> Optional[int]:
        """Lookup country_id by iso_code or slug."""
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT country_id FROM countries WHERE iso_code = :iso OR LOWER(name) = LOWER(:iso)"),
                {"iso": iso_code}
            ).fetchone()
            return row[0] if row else None

    def query_df(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Run SQL query and return results as a Pandas DataFrame."""
        with self.engine.connect() as conn:
            return pd.read_sql_query(text(query), conn, params=params)

def get_db_manager() -> DatabaseManager:
    """Factory helper for DatabaseManager."""
    return DatabaseManager()
