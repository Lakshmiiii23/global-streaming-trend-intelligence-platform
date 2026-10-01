import pytest
from src.processing.cleaner import DataCleaner

def test_clean_title_and_whitespace():
    cleaner = DataCleaner()
    assert cleaner.clean_title("  Stranger  Things: Season 4 \n") == "Stranger Things: Season 4"
    assert cleaner.clean_title("") == ""

def test_platform_and_country_normalization():
    cleaner = DataCleaner()
    assert cleaner.normalize_platform("Netflix") == "netflix"
    assert cleaner.normalize_platform("Amazon Prime Video") == "amazon-prime"
    assert cleaner.normalize_platform("Disney+") == "disney"
    
    assert cleaner.normalize_country("USA") == "united-states"
    assert cleaner.normalize_country("UK") == "united-kingdom"
    assert cleaner.normalize_country("Worldwide") == "world"

def test_clean_batch_deduplication():
    cleaner = DataCleaner()
    raw = [
        {
            "chart_date": "2026-10-01",
            "platform": "Netflix",
            "country": "US",
            "content_type": "movie",
            "title": "UNABOMBER",
            "rank": 1,
            "points": 900
        },
        # Duplicate with messy spacing
        {
            "chart_date": "2026-10-01",
            "platform": "netflix",
            "country": "united-states",
            "content_type": "movie",
            "title": "  UNABOMBER  ",
            "rank": 1,
            "points": 900
        },
        # Corrupt rank
        {
            "chart_date": "2026-10-01",
            "platform": "Netflix",
            "country": "US",
            "content_type": "movie",
            "title": "Corrupt Film",
            "rank": "invalid",
            "points": 50
        }
    ]
    cleaned = cleaner.clean_batch(raw)
    assert len(cleaned) == 1
    assert cleaned[0]["title"] == "UNABOMBER"
    assert cleaned[0]["rank"] == 1
