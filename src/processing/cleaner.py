import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

logger = logging.getLogger(__name__)

PLATFORM_NORMALIZATION_MAP = {
    "netflix": "netflix",
    "amazon": "amazon-prime",
    "prime": "amazon-prime",
    "amazon-prime": "amazon-prime",
    "amazon prime video": "amazon-prime",
    "disney": "disney",
    "disney+": "disney",
    "disney-plus": "disney",
    "apple": "apple-tv",
    "apple-tv": "apple-tv",
    "apple tv+": "apple-tv",
    "hbo": "hbo-max",
    "hbo-max": "hbo-max",
    "max": "hbo-max"
}

COUNTRY_NORMALIZATION_MAP = {
    "world": "world",
    "worldwide": "world",
    "united states": "united-states",
    "united-states": "united-states",
    "usa": "united-states",
    "us": "united-states",
    "united kingdom": "united-kingdom",
    "united-kingdom": "united-kingdom",
    "uk": "united-kingdom",
    "great britain": "united-kingdom",
    "india": "india",
    "in": "india",
    "brazil": "brazil",
    "br": "brazil",
    "japan": "japan",
    "jp": "japan",
    "germany": "germany",
    "de": "germany",
    "france": "france",
    "fr": "france",
    "canada": "canada",
    "ca": "canada",
    "australia": "australia",
    "au": "australia"
}

class DataCleaner:
    """
    Silver Layer Data Cleaner and Normalizer.
    
    Transforms raw scraped JSON into high-quality, standardized records:
    - Deduplicates identical chart placements.
    - Normalizes platform and country slugs.
    - Standardizes title formatting (stripping extra whitespace, cleaning artifacts).
    - Validates schema constraints (rank 1-100, points >= 0, valid date).
    """

    @staticmethod
    def normalize_platform(platform_raw: str) -> str:
        clean = platform_raw.lower().strip()
        return PLATFORM_NORMALIZATION_MAP.get(clean, clean)

    @staticmethod
    def normalize_country(country_raw: str) -> str:
        clean = country_raw.lower().strip()
        return COUNTRY_NORMALIZATION_MAP.get(clean, clean)

    @staticmethod
    def clean_title(title_raw: str) -> str:
        """Strip surrounding spaces, tabs, and unprintable characters."""
        if not title_raw:
            return ""
        # Remove consecutive whitespaces
        title = re.sub(r"\s+", " ", title_raw).strip()
        return title

    @staticmethod
    def validate_record(rec: Dict[str, Any]) -> bool:
        """Check if record meets minimum data quality standards."""
        if not rec.get("title") or not rec.get("platform") or not rec.get("chart_date"):
            return False
        
        # Validate rank
        try:
            rank = int(rec.get("rank", 0))
            if rank < 1 or rank > 100:
                return False
        except (ValueError, TypeError):
            return False

        # Validate date format (YYYY-MM-DD)
        try:
            datetime.strptime(rec["chart_date"], "%Y-%m-%d")
        except ValueError:
            return False

        return True

    def clean_batch(self, raw_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process and clean a list of raw records.
        """
        seen_keys = set()
        cleaned_records = []
        rejected_count = 0

        for r in raw_records:
            if not self.validate_record(r):
                rejected_count += 1
                continue

            platform = self.normalize_platform(r["platform"])
            country = self.normalize_country(r["country"])
            title = self.clean_title(r["title"])
            content_type = "movie" if "movie" in str(r.get("content_type", "")).lower() else "series"
            chart_date = r["chart_date"]
            rank = int(r["rank"])
            points = max(0, int(r.get("points") or 0))

            # Deduplication key: a title cannot occupy multiple ranks in same chart
            dedup_key = (chart_date, platform, country, content_type, rank)
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            cleaned_records.append({
                "chart_date": chart_date,
                "platform": platform,
                "country": country,
                "content_type": content_type,
                "title": title,
                "rank": rank,
                "points": points,
                "detail_url": r.get("detail_url", "")
            })

        logger.info(
            "Cleaning finished: %d valid records retained, %d rejected or duplicates dropped",
            len(cleaned_records), rejected_count
        )
        return cleaned_records
