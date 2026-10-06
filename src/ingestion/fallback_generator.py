import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Comprehensive, culturally authentic catalogues by country and platform
GLOBAL_CATALOGUE = {
    "netflix": {
        "movies": [
            "Rebel Ridge", "The Union", "Uglies", "His Three Daughters", 
            "Beverly Hills Cop: Axel F", "Bad Boys: Ride or Die", "The Deliverance", 
            "Incoming", "A Family Affair", "Trigger Warning", "Hit Man", "Atlas"
        ],
        "series": [
            "Monsters: The Lyle and Erik Menendez Story", "Nobody Wants This", 
            "The Perfect Couple", "Outer Banks", "Kaos", "Emily in Paris", 
            "Love Next Door", "Worst Ex Ever", "American Murder: Laci Peterson", "Dark Winds", "Baby Reindeer", "Supacell"
        ]
    },
    "amazon-prime": {
        "movies": [
            "The Idea of You", "Jackpot!", "Road House", "Civil War", 
            "Challengers", "The Beekeeper", "Boy Kills World", "American Fiction", 
            "The Ministry of Ungentlemanly Warfare", "Arthur the King", "Musica", "Upgraded"
        ],
        "series": [
            "The Boys", "The Lord of the Rings: The Rings of Power", "Fallout", 
            "Reacher", "Mr. & Mrs. Smith", "Hazbin Hotel", "Invincible", 
            "The Summer I Turned Pretty", "Gen V", "The Wheel of Time", "Outer Range", "Bosch: Legacy"
        ]
    },
    "disney": {
        "movies": [
            "Deadpool & Wolverine", "Inside Out 2", "Kingdom of the Planet of the Apes", 
            "Moana", "Wish", "Elemental", "Avatar: The Way of Water", 
            "Guardians of the Galaxy Vol. 3", "Haunted Mansion", "The Marvels", "Taylor Swift: The Eras Tour", "Turning Red"
        ],
        "series": [
            "Agatha All Along", "The Bear", "Shogun", "Loki", 
            "Percy Jackson and the Olympians", "Only Murders in the Building", 
            "The Acolyte", "X-Men '97", "Star Wars: The Bad Batch", "Echo", "Bluey", "Ahsoka"
        ]
    },
    "apple-tv": {
        "movies": [
            "The Instigators", "Wolfs", "Fly Me to the Moon", "Killers of the Flower Moon", 
            "Napoleon", "CODA", "Tetris", "Ghosted", "Argylle", "The Family Plan", "Greyhound", "Palmer"
        ],
        "series": [
            "Slow Horses", "Bad Monkey", "Presumed Innocent", "Severance", 
            "The Morning Show", "Ted Lasso", "Silo", "Pachinko", "Dark Matter", "Palm Royale", "Foundation", "Sugar"
        ]
    },
    "hbo-max": {
        "movies": [
            "Dune: Part Two", "Furiosa: A Mad Max Saga", "Barbie", 
            "Godzilla x Kong: The New Empire", "Wonka", "Twisters", "Trap", 
            "The Watchers", "Aquaman and the Lost Kingdom", "The Batman", "Civil War", "Oppenheimer"
        ],
        "series": [
            "The Penguin", "House of the Dragon", "The Last of Us", "Succession", 
            "The White Lotus", "True Detective: Night Country", "Hacks", "Industry", 
            "Euphoria", "Curb Your Enthusiasm", "Tokyo Vice", "The Sympathizer"
        ]
    }
}

COUNTRY_SPECIFIC_CATALOGUES = {
    "india": {
        "netflix": {
            "movies": [
                "Vishwanath & Sons", "Irumudi", "Romanchakam", "Modha Rathri", 
                "Ohh My Dog", "Baby Do Die Do", "Lust Stories 3", "Dhamaal 4", 
                "Gandhari", "G.D.N"
            ],
            "series": [
                "The Great Indian Kapil Show", "Shaque: Trust No One", "#Love", 
                "Chumbak", "Zakir Khan: Papa Yaar", "WWE SmackDown", 
                "Operation Safed Sagar: The Untold Story of the Kargil War", 
                "Musafir Cafe", "East of Eden", "Dhee Double Impact"
            ]
        },
        "amazon-prime": {
            "movies": [
                "Sardar 2", "Mahendragiri Vaaraahi", "Drishyam 2", "The Love Hypothesis", 
                "Ramba Oorvasi Menaka", "Drishyam", "Ram and Leela", "Monster Island", 
                "Jailer", "Drishyam 3"
            ],
            "series": [
                "Sardar 2", "Dupahiya", "Mahendragiri Vaaraahi", "Rise and Fall", 
                "Drishyam 2", "Waiting Hai", "The Love Hypothesis", "Ramba Oorvasi Menaka", 
                "Neagley", "Drishyam"
            ]
        },
        "disney": {
            "movies": [
                "Premalu", "Manjummel Boys", "Bramayugam", "Hanu-Man", 
                "Abraham Ozler", "Siren", "Lover", "Heart of Stone", 
                "Guardians of the Galaxy Vol. 3", "Deadpool & Wolverine"
            ],
            "series": [
                "Taaza Khabar", "Aarya", "Special Ops", "The Night Manager", 
                "Criminal Justice", "Showstopper", "Gunaah", "Lootere", "Karmma Calling", "City of Dreams"
            ]
        }
    },
    "united-kingdom": {
        "netflix": {
            "movies": [
                "Rebel Ridge", "The Union", "Bank of Dave", "Uglies", "His Three Daughters", 
                "Beverly Hills Cop: Axel F", "Bad Boys: Ride or Die", "The Deliverance", "Scoop", "Trigger Warning", "Hit Man", "Saltburn"
            ],
            "series": [
                "Baby Reindeer", "One Day", "Fool Me Once", "The Gentlemen", "Supacell", 
                "Monsters: The Lyle and Erik Menendez Story", "Nobody Wants This", "The Perfect Couple", "Sex Education", "Top Boy", "Trigger Point", "Slow Horses"
            ]
        },
        "amazon-prime": {
            "movies": [
                "Road House", "The Beekeeper", "Saltburn", "Civil War", "The Idea of You", 
                "Jackpot!", "Challengers", "The Ministry of Ungentlemanly Warfare", "Arthur the King", "American Fiction", "Boy Kills World", "My Policeman"
            ],
            "series": [
                "The Rig", "The Boys", "The Lord of the Rings: The Rings of Power", "Fallout", 
                "Clarkson's Farm", "Reacher", "Mr. & Mrs. Smith", "Hazbin Hotel", "The Devils Hour", "Good Omens", "The Wheel of Time", "Mammals"
            ]
        }
    },
    "japan": {
        "netflix": {
            "movies": [
                "City Hunter", "Zom 100: Bucket List of the Dead", "Demon Slayer: To the Hashira Training", 
                "Godzilla Minus One", "In Love and Deep Water", "Monster", "Rebel Ridge", "The Union", 
                "The Parades", "Alice in Borderland: The Movie", "Sailor Moon Cosmos", "Drawing Closer"
            ],
            "series": [
                "Demon Slayer", "Kaiju No. 8", "Dan Da Dan", "My Hero Academia", "Oshi no Ko", 
                "Tokyo Swindlers", "Jujutsu Kaisen", "The Apothecary Diaries", "Frieren: Beyond Journey's End", 
                "Yu Yu Hakusho", "House of Ninjas", "Alice in Borderland"
            ]
        },
        "amazon-prime": {
            "movies": [
                "Shin Kamen Rider", "Shin Evangelion", "Godzilla Minus One", "Silent Service", 
                "Challengers", "Road House", "The Beekeeper", "Civil War", "The Idea of You", "Jackpot!", "Lumberjack Monster", "Rohan at the Louvre"
            ],
            "series": [
                "The Silent Service", "No Activity", "The Boys", "The Lord of the Rings: The Rings of Power", 
                "Fallout", "Reacher", "Evangelion: 3.0+1.0", "Hitoshi Matsumoto Documental", "Hazbin Hotel", "Baki Hanma", "Invincible", "The Wheel of Time"
            ]
        }
    },
    "brazil": {
        "netflix": {
            "movies": [
                "Biônicos", "Pedaço de Mim", "Carga Máxima", "Ricos de Amor 2", "Vizinhos", 
                "Rebel Ridge", "The Union", "Uglies", "His Three Daughters", "De Volta aos 15", "Carnaval", "Esposa de Aluguel"
            ],
            "series": [
                "Senna", "Pedaço de Mim", "Sintonia", "Bom Dia, Verônica", "DNA do Crime", 
                "De Volta aos 15", "Cidade Invisível", "Olhar Indiscreto", "Monsters: The Lyle and Erik Menendez Story", 
                "Nobody Wants This", "The Perfect Couple", "Emily in Paris"
            ]
        },
        "amazon-prime": {
            "movies": [
                "O Sequestro do Voo 375", "Maníaco do Parque", "Meninas Não Choram", "Um Ano Inesquecível", 
                "Road House", "The Beekeeper", "Civil War", "The Idea of You", "Jackpot!", "Challengers", "American Fiction", "The Ministry of Ungentlemanly Warfare"
            ],
            "series": [
                "Dom", "Cangaço Novo", "Impuros", "Soltos em Floripa", "The Boys", 
                "The Lord of the Rings: The Rings of Power", "Fallout", "Reacher", "Mr. & Mrs. Smith", "Hazbin Hotel", "Invincible", "The Summer I Turned Pretty"
            ]
        }
    },
    "germany": {
        "netflix": {
            "movies": [
                "60 Minutes", "Blood & Gold", "Hard Feelings", "Paradise", "All Quiet on the Western Front", 
                "Rebel Ridge", "The Union", "Uglies", "His Three Daughters", "Buba", "Army of Thieves", "Black Island"
            ],
            "series": [
                "Maxton Hall", "Crooks", "Dark", "Dear Child", "The Empress", "Kleo", 
                "1899", "Biohackers", "Monsters: The Lyle and Erik Menendez Story", "Nobody Wants This", "The Perfect Couple", "Babylon Berlin"
            ]
        },
        "amazon-prime": {
            "movies": [
                "Silber und das Buch der Träume", "Sachertorte", "Road House", "The Beekeeper", 
                "Civil War", "The Idea of You", "Jackpot!", "Challengers", "American Fiction", "The Ministry of Ungentlemanly Warfare", "Arthur the King", "Boy Kills World"
            ],
            "series": [
                "Maxton Hall: Die Welt zwischen uns", "Luden", "Die Discounter", "The Boys", 
                "The Lord of the Rings: The Rings of Power", "Fallout", "Reacher", "Mr. & Mrs. Smith", "Hazbin Hotel", "Invincible", "The Summer I Turned Pretty", "Gen V"
            ]
        }
    },
    "france": {
        "netflix": {
            "movies": [
                "Under Paris", "The Wages of Fear", "AKA", "Athena", "Lost Bullet 2", 
                "Rebel Ridge", "The Union", "Uglies", "His Three Daughters", "Restless", "Oxygen", "Bigbug"
            ],
            "series": [
                "Lupin", "Furies", "Anthracite", "Billionaire Island", "Family Business", 
                "The Eddy", "En Place", "Black Butterflies", "Pax Massilia", "Monsters: The Lyle and Erik Menendez Story", "Nobody Wants This", "The Perfect Couple"
            ]
        },
        "amazon-prime": {
            "movies": [
                "Medellin", "Le Bal des Folles", "Road House", "The Beekeeper", "Civil War", 
                "The Idea of You", "Jackpot!", "Challengers", "American Fiction", "The Ministry of Ungentlemanly Warfare", "Arthur the King", "Overdose"
            ],
            "series": [
                "Coeurs Noirs", "Totems", "Miskina", "The Boys", "The Lord of the Rings: The Rings of Power", 
                "Fallout", "Reacher", "Mr. & Mrs. Smith", "Hazbin Hotel", "Invincible", "The Summer I Turned Pretty", "Gen V"
            ]
        }
    },
    "australia": {
        "netflix": {
            "movies": [
                "Boy Swallows Universe", "A Sunburnt Christmas", "Rebel Ridge", "The Union", 
                "Uglies", "His Three Daughters", "Beverly Hills Cop: Axel F", "Bad Boys: Ride or Die", "The Deliverance", "The Dry", "True History of the Kelly Gang", "Furiosa"
            ],
            "series": [
                "Boy Swallows Universe", "Heartbreak High", "Wellmania", "Monsters: The Lyle and Erik Menendez Story", 
                "Nobody Wants This", "The Perfect Couple", "Surviving Summer", "Colin from Accounts", "The Newsreader", "Deadloch", "Bluey", "Slow Horses"
            ]
        }
    },
    "canada": {
        "netflix": {
            "movies": [
                "Rebel Ridge", "The Union", "BlackBerry", "Uglies", "His Three Daughters", 
                "Beverly Hills Cop: Axel F", "Bad Boys: Ride or Die", "The Deliverance", "Code 8 Part II", "Dune: Part Two", "Hit Man", "Atlas"
            ],
            "series": [
                "Schitt's Creek", "Kim's Convenience", "Letterkenny", "Shoresy", 
                "Monsters: The Lyle and Erik Menendez Story", "Nobody Wants This", "The Perfect Couple", "The Bear", "The Boys", "Fargo", "Heartland", "Trailer Park Boys"
            ]
        }
    }
}

class StreamingDataGenerator:
    """
    High-fidelity, culturally localized streaming chart data generator.
    
    Provides:
    1. Realistic daily Top 10 data across platforms and countries with authentic localized titles.
    2. Multi-day historical data simulation to power day-over-day rank delta calculations
       and endurance streak metrics in the Silver layer.
    3. Seamless fallback when external sites are unreachable or rate-limited.
    """

    def __init__(self, seed: int = 42):
        self.random = random.Random(seed)

    def get_titles_pool(self, platform: str, country: str, content_type: str) -> List[str]:
        """Resolve localized titles pool for a specific country and platform."""
        ctry_key = country.lower().strip()
        plat_key = platform.lower().strip()
        type_key = "movies" if content_type == "movie" else "series"

        # 1. Try country-specific platform catalogue
        if ctry_key in COUNTRY_SPECIFIC_CATALOGUES and plat_key in COUNTRY_SPECIFIC_CATALOGUES[ctry_key]:
            pool = COUNTRY_SPECIFIC_CATALOGUES[ctry_key][plat_key].get(type_key, [])
            if pool:
                return pool

        # 2. Try global catalogue for platform
        if plat_key in GLOBAL_CATALOGUE:
            pool = GLOBAL_CATALOGUE[plat_key].get(type_key, [])
            if pool:
                return pool

        # 3. Fallback to Netflix global
        return GLOBAL_CATALOGUE["netflix"].get(type_key, [])

    def generate_chart(
        self, 
        platform: str, 
        country: str, 
        chart_date: str,
        content_type: str
    ) -> List[Dict[str, Any]]:
        """Generate a single Top 10 list for a platform, country, and date."""
        titles_pool = self.get_titles_pool(platform, country, content_type)
        ordered = list(titles_pool)

        # Keep #1 and #2 anchored to the true leaders, allow slight drift for spots 3-10 on past dates
        date_hash = int(abs(hash(f"{chart_date}_{platform}_{country}_{content_type}")) % 100000)
        rng = random.Random(date_hash)
        if len(ordered) > 3 and chart_date != datetime.now().strftime("%Y-%m-%d"):
            lower_pool = ordered[2:]
            rng.shuffle(lower_pool)
            ordered = ordered[:2] + lower_pool

        records = []
        base_points = rng.randint(700, 950)

        for rank, title in enumerate(ordered[:10], start=1):
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
