import os
from pathlib import Path
from dotenv import load_dotenv

# Base Project Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

class Settings:
    """Central configuration for the Streaming Intelligence Platform."""
    
    # Environment & Logging
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Storage Configuration (Cloudflare R2 or Local)
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local").lower()
    R2_ACCOUNT_ID: str = os.getenv("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET_NAME: str = os.getenv("R2_BUCKET_NAME", "streaming-trends-bronze")
    R2_ENDPOINT_URL: str = os.getenv(
        "R2_ENDPOINT_URL", 
        f"https://{os.getenv('R2_ACCOUNT_ID', '')}.r2.cloudflarestorage.com"
    )
    
    # Local Data Directories
    BRONZE_DIR: Path = BASE_DIR / "data" / "bronze"
    SILVER_DIR: Path = BASE_DIR / "data" / "silver"
    GOLD_DIR: Path = BASE_DIR / "data" / "gold"
    
    # Database Configuration (Neon PostgreSQL with SQLite local fallback)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{BASE_DIR / 'data' / 'streaming_intelligence.db'}"
    )
    
    # Scraper Configuration
    SCRAPER_HEADLESS: bool = os.getenv("SCRAPER_HEADLESS", "true").lower() == "true"
    SCRAPER_TIMEOUT_SECONDS: int = int(os.getenv("SCRAPER_TIMEOUT_SECONDS", "45"))
    SCRAPER_REQUEST_DELAY_SECONDS: float = float(os.getenv("SCRAPER_REQUEST_DELAY_SECONDS", "3.0"))
    
    # Target Platforms and Countries
    TARGET_PLATFORMS: list[str] = [
        p.strip() for p in os.getenv("TARGET_PLATFORMS", "netflix,amazon-prime,disney,apple-tv,hbo-max").split(",") if p.strip()
    ]
    TARGET_COUNTRIES: list[str] = [
        c.strip() for c in os.getenv(
            "TARGET_COUNTRIES", 
            "world,united-states,united-kingdom,india,brazil,japan,germany,australia,canada,france"
        ).split(",") if c.strip()
    ]

    def ensure_directories(self) -> None:
        """Ensure all local data directories exist."""
        for path in [self.BRONZE_DIR, self.SILVER_DIR, self.GOLD_DIR]:
            path.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.ensure_directories()
