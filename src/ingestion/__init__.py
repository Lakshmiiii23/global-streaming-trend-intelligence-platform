"""Ingestion package for scraping and acquiring Bronze streaming data."""
from .flixpatrol_scraper import FlixPatrolScraper
from .fallback_generator import StreamingDataGenerator

__all__ = ["FlixPatrolScraper", "StreamingDataGenerator"]
