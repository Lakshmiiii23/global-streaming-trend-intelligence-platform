import pytest
from src.db.postgres_client import DatabaseManager
from src.processing.trend_detector import TrendProcessor

def test_trend_calculation_delta_and_streak(tmp_path):
    # Use temporary sqlite database for isolated testing
    db_file = tmp_path / "test_trends.db"
    db = DatabaseManager(database_url=f"sqlite:///{db_file}")
    db.init_schema()
    db.seed_initial_dimensions()

    processor = TrendProcessor(db_manager=db)

    # Day 1: "Show A" debuts at rank 5
    day1_records = [{
        "chart_date": "2026-09-30",
        "platform": "netflix",
        "country": "united-states",
        "content_type": "series",
        "title": "Show A",
        "rank": 5,
        "points": 500
    }]
    processor.process_and_load(day1_records)

    day1_trend = db.query_df("SELECT * FROM trends WHERE chart_date = '2026-09-30'").iloc[0]
    assert day1_trend["current_rank"] == 5
    assert day1_trend["previous_rank"] is None or str(day1_trend["previous_rank"]) == "nan"
    assert day1_trend["is_new_entry"] == 1
    assert day1_trend["days_in_top_10"] == 1

    # Day 2: "Show A" climbs to rank 2 (+3 rank change)
    day2_records = [{
        "chart_date": "2026-10-01",
        "platform": "netflix",
        "country": "united-states",
        "content_type": "series",
        "title": "Show A",
        "rank": 2,
        "points": 850
    }]
    processor.process_and_load(day2_records)

    day2_trend = db.query_df("SELECT * FROM trends WHERE chart_date = '2026-10-01'").iloc[0]
    assert day2_trend["current_rank"] == 2
    assert day2_trend["previous_rank"] == 5
    assert day2_trend["rank_change"] == 3  # Climbed by 3 spots!
    assert day2_trend["is_new_entry"] == 0
    assert day2_trend["days_in_top_10"] == 2  # 2nd day in Top 10!
