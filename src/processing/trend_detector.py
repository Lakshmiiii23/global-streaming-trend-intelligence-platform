import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import text
from src.db.postgres_client import DatabaseManager, get_db_manager

logger = logging.getLogger(__name__)

class TrendProcessor:
    """
    Silver & Gold Layer Trend Detection Engine.
    
    Computes key data intelligence metrics:
    - rank_change: Difference vs yesterday (positive = climber, negative = dropper)
    - is_new_entry: Whether title is debuting in Top 10 today
    - days_in_top_10: Cumulative consecutive/historical tenure in chart
    - Loads dimensions and facts into Neon PostgreSQL (or local SQLite) with high throughput.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or get_db_manager()

    def process_and_load(self, cleaned_records: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Process a list of cleaned records and load into Silver tables (rankings, trends).
        Uses in-memory dimension caching to avoid N+1 query bottlenecks.
        """
        if not cleaned_records:
            logger.info("No records to process.")
            return {"rankings_inserted": 0, "trends_inserted": 0}

        # Sort chronologically so trends compute properly day-by-day
        records_sorted = sorted(
            cleaned_records, 
            key=lambda r: (r["chart_date"], r["platform"], r["country"], r["rank"])
        )
        
        rankings_count = 0
        trends_count = 0

        with self.db.engine.begin() as conn:
            # 1. Preload dimension caches
            plat_rows = conn.execute(text("SELECT slug, platform_id FROM platforms")).fetchall()
            platform_cache = {row[0]: row[1] for row in plat_rows}

            ctry_rows = conn.execute(text("SELECT iso_code, country_id FROM countries")).fetchall()
            country_cache = {row[0]: row[1] for row in ctry_rows}

            title_rows = conn.execute(text("SELECT LOWER(name), content_type, title_id FROM titles")).fetchall()
            title_cache: Dict[Tuple[str, str], int] = {(row[0], row[1]): row[2] for row in title_rows}

            # Cache for fast day-over-day lookups: (chart_date, plat_id, ctry_id, title_id) -> (rank, days_in_top_10)
            history_cache: Dict[Tuple[str, int, int, int], Tuple[int, int]] = {}
            
            # Preload any existing trends from the DB into history_cache
            existing_history = conn.execute(text("""
                SELECT chart_date, platform_id, country_id, title_id, current_rank, days_in_top_10
                FROM trends
            """)).fetchall()
            for r in existing_history:
                d_str = str(r[0])
                history_cache[(d_str, r[1], r[2], r[3])] = (r[4], r[5] or 1)

            # Purge prior rankings/trends for incoming (chart_date, platform, country) combinations to prevent duplicate ranks
            cleared_batches = set()
            for rec in records_sorted:
                p_slug = rec["platform"]
                c_iso = rec["country"]
                p_id = platform_cache.get(p_slug) or self.db.get_platform_id(p_slug) or 1
                c_id = country_cache.get(c_iso) or self.db.get_country_id(c_iso) or 1
                b_key = (str(rec["chart_date"]), p_id, c_id)
                if b_key not in cleared_batches:
                    cleared_batches.add(b_key)
                    conn.execute(text("""
                        DELETE FROM rankings WHERE chart_date = :d AND platform_id = :p AND country_id = :c
                    """), {"d": b_key[0], "p": p_id, "c": c_id})
                    conn.execute(text("""
                        DELETE FROM trends WHERE chart_date = :d AND platform_id = :p AND country_id = :c
                    """), {"d": b_key[0], "p": p_id, "c": c_id})

            # 2. Iterate through records and compute deltas
            for rec in records_sorted:
                chart_date_str = str(rec["chart_date"])
                plat_slug = rec["platform"]
                ctry_iso = rec["country"]
                title_name = rec["title"]
                content_type = rec["content_type"]
                current_rank = rec["rank"]
                points = rec["points"]

                # Resolve Platform ID
                platform_id = platform_cache.get(plat_slug)
                if not platform_id:
                    platform_id = self.db.get_platform_id(plat_slug) or 1
                    platform_cache[plat_slug] = platform_id

                # Resolve Country ID
                country_id = country_cache.get(ctry_iso)
                if not country_id:
                    country_id = self.db.get_country_id(ctry_iso) or 1
                    country_cache[ctry_iso] = country_id

                # Resolve or Create Title ID
                title_key = (title_name.lower().strip(), content_type)
                if title_key in title_cache:
                    title_id = title_cache[title_key]
                else:
                    title_id = self.db.get_or_create_title(title_name, content_type, conn=conn)
                    title_cache[title_key] = title_id

                # 3. Upsert Fact Table: rankings
                if self.db.is_postgres:
                    conn.execute(text("""
                        INSERT INTO rankings (chart_date, platform_id, country_id, title_id, rank, points)
                        VALUES (:date, :plat, :ctry, :title, :rank, :points)
                        ON CONFLICT (chart_date, platform_id, country_id, title_id)
                        DO UPDATE SET rank = EXCLUDED.rank, points = EXCLUDED.points;
                    """), {
                        "date": chart_date_str,
                        "plat": platform_id,
                        "ctry": country_id,
                        "title": title_id,
                        "rank": current_rank,
                        "points": points
                    })
                else:
                    conn.execute(text("""
                        INSERT OR REPLACE INTO rankings (chart_date, platform_id, country_id, title_id, rank, points)
                        VALUES (:date, :plat, :ctry, :title, :rank, :points);
                    """), {
                        "date": chart_date_str,
                        "plat": platform_id,
                        "ctry": country_id,
                        "title": title_id,
                        "rank": current_rank,
                        "points": points
                    })
                rankings_count += 1

                # 4. Compute Trend Metrics (Look back at previous day)
                chart_dt = datetime.strptime(chart_date_str, "%Y-%m-%d")
                prev_date_str = (chart_dt - timedelta(days=1)).strftime("%Y-%m-%d")
                
                prev_key = (prev_date_str, platform_id, country_id, title_id)
                if prev_key in history_cache:
                    previous_rank, prev_days = history_cache[prev_key]
                    rank_change = previous_rank - current_rank  # Positive = climbed
                    days_in_top_10 = prev_days + 1
                    is_new_entry = False
                else:
                    previous_rank = None
                    rank_change = None
                    days_in_top_10 = int(rec.get("days_in_top_10") or 1)
                    is_new_entry = (days_in_top_10 <= 1)

                # Update history cache with current day's position
                history_cache[(chart_date_str, platform_id, country_id, title_id)] = (current_rank, days_in_top_10)

                # 5. Upsert Fact Table: trends
                if self.db.is_postgres:
                    conn.execute(text("""
                        INSERT INTO trends (
                            chart_date, platform_id, country_id, title_id, 
                            current_rank, previous_rank, rank_change, days_in_top_10, is_new_entry
                        )
                        VALUES (:date, :plat, :ctry, :title, :cur_rank, :prev_rank, :change, :days, :new_entry)
                        ON CONFLICT (chart_date, platform_id, country_id, title_id)
                        DO UPDATE SET 
                            current_rank = EXCLUDED.current_rank,
                            previous_rank = EXCLUDED.previous_rank,
                            rank_change = EXCLUDED.rank_change,
                            days_in_top_10 = EXCLUDED.days_in_top_10,
                            is_new_entry = EXCLUDED.is_new_entry;
                    """), {
                        "date": chart_date_str,
                        "plat": platform_id,
                        "ctry": country_id,
                        "title": title_id,
                        "cur_rank": current_rank,
                        "prev_rank": previous_rank,
                        "change": rank_change,
                        "days": days_in_top_10,
                        "new_entry": is_new_entry
                    })
                else:
                    conn.execute(text("""
                        INSERT OR REPLACE INTO trends (
                            chart_date, platform_id, country_id, title_id, 
                            current_rank, previous_rank, rank_change, days_in_top_10, is_new_entry
                        )
                        VALUES (:date, :plat, :ctry, :title, :cur_rank, :prev_rank, :change, :days, :new_entry);
                    """), {
                        "date": chart_date_str,
                        "plat": platform_id,
                        "ctry": country_id,
                        "title": title_id,
                        "cur_rank": current_rank,
                        "prev_rank": previous_rank,
                        "change": rank_change,
                        "days": days_in_top_10,
                        "new_entry": 1 if is_new_entry else 0
                    })
                trends_count += 1

        logger.info("Successfully loaded %d rankings and %d trend calculations.", rankings_count, trends_count)
        return {"rankings_inserted": rankings_count, "trends_inserted": trends_count}
