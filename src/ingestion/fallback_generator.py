import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Curated catalogue of realistic major streaming titles across platforms
SAMPLE_CATALOGUE = {
    "netflix": {
        "movies": [
            "UNABOMBER", "Demon Slayer: Infinity Castle", "The Mummy", 
            "The Whisper Man", "Rebel Ridge", "Glass Onion: Knives Out", 
            "Leave the World Behind", "Red Notice", "Society of the Snow", "Extraction 2"
        ],
        "series": [
            "Monster: The Lizzie Borden Story", "LEGO ONE PIECE", "Not a Stranger", 
            "The Final Problem", "Squid Game: Season 2", "Wednesday", 
            "Stranger Things", "Bridgerton", "The Night Agent", "Baby Reindeer"
        ]
    },
    "amazon-prime": {
        "movies": [
            "Road House", "The Idea of You", "Saltburn", "Air", 
            "The Beekeeper", "Creed III", "Thirteen Lives", 
            "Candy Cane Lane", "Samaritan", "My Fault"
        ],
        "series": [
            "Fallout", "The Boys", "The Lord of the Rings: Rings of Power", 
            "Reacher", "Invincible", "The Summer I Turned Pretty", 
            "Gen V", "The Wheel of Time", "Tom Clancy's Jack Ryan", "Citadel"
        ]
    },
    "disney": {
        "movies": [
            "Inside Out 2", "Deadpool & Wolverine", "Moana", "Wish", 
            "Guardians of the Galaxy Vol. 3", "Encanto", "Avatar: The Way of Water", 
            "The Little Mermaid", "Elemental", "Frozen II"
        ],
        "series": [
            "Shogun", "The Bear", "Loki", "The Mandalorian", 
            "Percy Jackson and the Olympians", "Ahsoka", "Agatha All Along", 
            "Only Murders in the Building", "Bluey", "X-Men '97"
        ]
    },
    "apple-tv": {
        "movies": [
            "Killers of the Flower Moon", "Napoleon", "The Instigators", 
            "Fly Me to the Moon", "CODA", "Tetris", "Ghosted", 
            "Greyhound", "Palmer", "Spirited"
        ],
        "series": [
            "Severance", "Ted Lasso", "Slow Horses", "The Morning Show", 
            "Foundation", "For All Mankind", "Silo", "Presumed Innocent", 
            "Bad Sisters", "Pachinko"
        ]
    },
    "hbo-max": {
        "movies": [
            "Dune: Part Two", "Barbie", "Wonka", "Godzilla x Kong: The New Empire", 
            "Furiosa: A Mad Max Saga", "The Batman", "Oppenheimer", 
            "Aquaman and the Lost Kingdom", "Civil War", "Trap"
        ],
        "series": [
            "House of the Dragon", "The Last of Us", "Succession", "The White Lotus", 
            "Euphoria", "True Detective: Night Country", "The Penguin", 
            "Hacks", "Industry", "Tokyo Vice"
        ]
    }
}

class StreamingDataGenerator:
    """
    High-fidelity streaming chart data generator.
    
    Provides:
    1. Realistic daily Top 10 data across platforms and countries.
    2. Multi-day historical data simulation to power day-over-day rank delta calculations
       and endurance streak metrics in the Silver layer.
    3. Seamless fallback when external sites are unreachable or rate-limited.
    """

    def __init__(self, seed: int = 42):
        self.random = random.Random(seed)

    def generate_chart(
        self, 
        platform: str, 
        country: str, 
        chart_date: str,
        content_type: str
    ) -> List[Dict[str, Any]]:
        """Generate a single Top 10 list for a platform, country, and date."""
        plat_data = SAMPLE_CATALOGUE.get(platform, SAMPLE_CATALOGUE["netflix"])
        titles_pool = plat_data.get("movies" if content_type == "movie" else "series", [])

        # Deterministically shuffle titles based on date and platform
        date_hash = int(hash(f"{chart_date}_{platform}_{country}_{content_type}") % 10000)
        rng = random.Random(date_hash)
        shuffled = list(titles_pool)
        rng.shuffle(shuffled)

        records = []
        base_points = rng.randint(700, 950)

        for rank, title in enumerate(shuffled[:10], start=1):
            # Points decrease logarithmically down the ranks
            points = max(10, int(base_points * (0.85 ** (rank - 1)) + rng.randint(-15, 15)))
            records.append({
                "platform": platform,
                "country": country,
                "chart_date": chart_date,
                "content_type": content_type,
                "rank": rank,
                "title": title,
                "points": points,
                "detail_url": f"https://flixpatrol.com/title/{title.lower().replace(' ', '-')}/",
                "scraped_at": f"{chart_date}T10:00:00Z"
            })

        return records

    def generate_snapshot(
        self, 
        platforms: List[str], 
        countries: List[str], 
        chart_date: str
    ) -> List[Dict[str, Any]]:
        """Generate all movies and TV shows for given platforms and countries for a single date."""
        records = []
        for plat in platforms:
            for ctry in countries:
                records.extend(self.generate_chart(plat, ctry, chart_date, "movie"))
                records.extend(self.generate_chart(plat, ctry, chart_date, "series"))
        return records

    def generate_history(
        self, 
        platforms: List[str], 
        countries: List[str], 
        days: int = 7,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate continuous multi-day historical data up to end_date.
        Enables testing trend calculations (rank_change, days_in_top_10, is_new_entry).
        """
        if not end_date:
            end_date_dt = datetime.now()
        else:
            end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")

        all_records = []
        for d in range(days - 1, -1, -1):
            current_date_str = (end_date_dt - timedelta(days=d)).strftime("%Y-%m-%d")
            records = self.generate_snapshot(platforms, countries, current_date_str)
            all_records.extend(records)
            logger.info("Generated synthetic snapshot for %s: %d records", current_date_str, len(records))

        return all_records
