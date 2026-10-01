import argparse
import logging
import sys
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from config.settings import settings
from src.ingestion.flixpatrol_scraper import FlixPatrolScraper
from src.ingestion.fallback_generator import StreamingDataGenerator
from src.storage.r2_client import get_storage_manager
from src.processing.cleaner import DataCleaner
from src.processing.trend_detector import TrendProcessor
from src.db.postgres_client import get_db_manager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("PipelineRunner")

def run_ingestion_bronze(
    source: str = "hybrid", 
    days: int = 7, 
    platforms: Optional[List[str]] = None, 
    countries: Optional[List[str]] = None
) -> str:
    """
    Acquire raw data and store in Bronze Layer (Cloudflare R2 or local bronze storage).
    
    Args:
        source: 'live', 'synthetic', or 'hybrid'
        days: Number of historical days to simulate if synthetic
        platforms: Specific platforms to target
        countries: Specific countries to target
        
    Returns:
        Storage key or path to the saved batch.
    """
    logger.info("==================================================")
    logger.info("PHASE 1: BRONZE LAYER INGESTION (Source: %s)", source)
    logger.info("==================================================")
    
    storage = get_storage_manager()
    records: List[Dict[str, Any]] = []
    
    # Resolve target platforms and countries
    target_platforms = platforms or ["netflix", "amazon-prime"]
    target_countries = countries or ["india", "united-states", "world"]
    
    if source in ("live", "hybrid"):
        logger.info("Attempting live scrape via Camoufox on FlixPatrol for %s in %s...", target_platforms, target_countries)
        try:
            scraper = FlixPatrolScraper()
            live_records = scraper.scrape_all_targets(
                platforms=target_platforms,
                countries=target_countries
            )
            if live_records:
                records.extend(live_records)
                logger.info("Successfully scraped %d live records from FlixPatrol!", len(live_records))
            else:
                logger.warning("Live scraper returned 0 records.")
        except Exception as e:
            logger.error("Live scraping encountered an error: %s", e)

    if not records:
        if source == "live":
            logger.warning("Live scraping returned 0 records. Preserving existing database records without overwriting.")
            return None
        logger.info("Utilizing resilient streaming generator fallback to ensure pipeline continuity...")
        generator = StreamingDataGenerator()
        fallback_plats = target_platforms if target_platforms else settings.TARGET_PLATFORMS
        fallback_ctrys = target_countries if target_countries else settings.TARGET_COUNTRIES
        records = generator.generate_history(
            platforms=fallback_plats,
            countries=fallback_ctrys,
            days=days
        )
        logger.info("Generated %d fallback streaming records.", len(records))

    batch_id = str(uuid.uuid4())[:8]
    chart_date = datetime.now().strftime("%Y-%m-%d")
    batch_key = storage.save_batch(records, batch_id=batch_id, chart_date=chart_date)
    logger.info("Bronze ingestion complete. Batch key: %s", batch_key)
    return batch_key

def run_processing_silver_gold(batch_key_or_path: str) -> Dict[str, int]:
    """
    Read raw Bronze data, clean, detect trends, and load into Silver/Gold database.
    """
    logger.info("==================================================")
    logger.info("PHASE 2: SILVER & GOLD PROCESSING (%s)", batch_key_or_path)
    logger.info("==================================================")
    
    storage = get_storage_manager()
    db = get_db_manager()
    cleaner = DataCleaner()
    processor = TrendProcessor(db_manager=db)

    # 1. Initialize schema and seed dimensions
    db.init_schema()
    db.seed_initial_dimensions()

    # 2. Load Bronze batch
    batch_data = storage.load_batch(batch_key_or_path)
    raw_records = batch_data.get("records", [])
    logger.info("Loaded %d raw records from Bronze storage.", len(raw_records))

    # 3. Clean and standardize
    cleaned = cleaner.clean_batch(raw_records)

    # 4. Detect trends and load into fact tables
    stats = processor.process_and_load(cleaned)
    logger.info("Silver & Gold pipeline completed: %s", stats)
    return stats

def main():
    parser = argparse.ArgumentParser(description="Streaming Intelligence Data Pipeline")
    parser.add_argument(
        "--mode", 
        choices=["all", "scrape", "process"], 
        default="all", 
        help="Pipeline execution mode"
    )
    parser.add_argument(
        "--source", 
        choices=["live", "synthetic", "hybrid"], 
        default="hybrid", 
        help="Data acquisition source"
    )
    parser.add_argument(
        "--days", 
        type=int, 
        default=7, 
        help="Number of days of data to generate/process"
    )
    parser.add_argument(
        "--platforms",
        type=str,
        default=None,
        help="Comma-separated platforms to target (e.g. netflix,amazon-prime)"
    )
    parser.add_argument(
        "--countries",
        type=str,
        default=None,
        help="Comma-separated countries to target (e.g. india,united-states)"
    )
    parser.add_argument(
        "--batch-key", 
        type=str, 
        default=None, 
        help="Specific bronze batch path/key to process"
    )

    args = parser.parse_args()

    target_plats = [p.strip() for p in args.platforms.split(",")] if args.platforms else None
    target_ctrys = [c.strip() for c in args.countries.split(",")] if args.countries else None

    if args.mode in ("all", "scrape"):
        batch_key = run_ingestion_bronze(
            source=args.source, 
            days=args.days,
            platforms=target_plats,
            countries=target_ctrys
        )
    else:
        batch_key = args.batch_key
        if not batch_key:
            logger.error("Must provide --batch-key when running in 'process' mode.")
            sys.exit(1)

    if args.mode in ("all", "process"):
        run_processing_silver_gold(batch_key)

    logger.info("Pipeline execution finished successfully.")

if __name__ == "__main__":
    main()
