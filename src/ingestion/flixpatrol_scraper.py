import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
from camoufox.sync_api import Camoufox
from config.settings import settings

logger = logging.getLogger(__name__)

class FlixPatrolScraper:
    """
    Production scraper for FlixPatrol streaming charts using Camoufox anti-detect browser.
    
    FlixPatrol protects its charts using Cloudflare Bot Management and Turnstile challenges.
    Standard requests or standard Playwright headless triggers a 403 Forbidden challenge page.
    Camoufox operates at the C++ engine level of Firefox, evading fingerprint detection and
    allowing automated ingestion of live Top 10 rankings.
    """

    BASE_URL = "https://flixpatrol.com"

    def __init__(self, headless: Optional[bool] = None, timeout: Optional[int] = None):
        self.headless = headless if headless is not None else settings.SCRAPER_HEADLESS
        self.timeout = (timeout or settings.SCRAPER_TIMEOUT_SECONDS) * 1000  # ms
        self.delay = settings.SCRAPER_REQUEST_DELAY_SECONDS

    def build_chart_url(self, platform: str, country: str, chart_date: Optional[str] = None) -> str:
        """
        Construct the FlixPatrol chart URL.
        Example: https://flixpatrol.com/top10/netflix/united-states/2026-09-30/
        """
        plat = platform.lower().strip()
        ctry = country.lower().strip()
        url = f"{self.BASE_URL}/top10/{plat}/{ctry}/"
        if chart_date:
            url += f"{chart_date}/"
        return url

    def parse_chart_html(self, html: str, platform: str, country: str, chart_date: str) -> List[Dict[str, Any]]:
        """
        Parse HTML returned by FlixPatrol to extract Top 10 movies and TV shows.
        """
        soup = BeautifulSoup(html, "html.parser")
        records: List[Dict[str, Any]] = []

        tables = soup.find_all("table")
        if not tables:
            logger.warning("No <table> tags found on FlixPatrol page for %s - %s", platform, country)
            return records

        for idx, table in enumerate(tables):
            # Check preceding headings to distinguish movies vs series
            parent = table.parent
            heading_text = ""
            while parent and not heading_text:
                heading_elem = parent.find(["h2", "h3", "h4"])
                if heading_elem:
                    heading_text = heading_elem.get_text(strip=True).lower()
                parent = parent.parent

            # Determine content type based on heading or table index
            content_type = "movie"
            if "show" in heading_text or "tv" in heading_text or "series" in heading_text or idx == 1:
                content_type = "series"
            elif "movie" in heading_text or "film" in heading_text or idx == 0:
                content_type = "movie"

            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if not cells or len(cells) < 2:
                    continue

                # Parse rank (e.g., '1.', '2')
                rank_str = cells[0].get_text(strip=True).replace(".", "")
                if not rank_str.isdigit():
                    continue
                rank = int(rank_str)

                # Parse title
                title_link = row.find("a")
                if title_link:
                    title = title_link.get_text(strip=True)
                    detail_url = title_link.get("href", "")
                else:
                    title = cells[1].get_text(strip=True)
                    detail_url = ""

                if not title:
                    continue

                # Parse points (usually in column 2 or 3)
                points = 0
                for c in cells[2:]:
                    txt = c.get_text(strip=True).replace(",", "").replace(".", "")
                    if txt.isdigit():
                        points = int(txt)
                        break

                records.append({
                    "platform": platform,
                    "country": country,
                    "chart_date": chart_date,
                    "content_type": content_type,
                    "rank": rank,
                    "title": title,
                    "points": points,
                    "detail_url": f"{self.BASE_URL}{detail_url}" if detail_url.startswith("/") else detail_url,
                    "scraped_at": datetime.now(timezone.utc).isoformat()
                })

        logger.info(
            "Parsed %d items for platform=%s, country=%s, date=%s", 
            len(records), platform, country, chart_date
        )
        return records

    def scrape_chart(self, platform: str, country: str, chart_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Scrape a single chart page for a given platform and country.
        """
        if not chart_date:
            chart_date = datetime.now().strftime("%Y-%m-%d")

        url = self.build_chart_url(platform, country)
        logger.info("Scraping FlixPatrol URL: %s", url)

        try:
            with Camoufox(headless=self.headless) as browser:
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)

                # Wait for Cloudflare verification redirect
                for _ in range(25):
                    time.sleep(1)
                    title = page.title()
                    if "Just a moment" not in title and "Loading" not in title:
                        time.sleep(2)  # Allow DOM to settle
                        break

                html = page.content()
                if "Just a moment" in page.title():
                    logger.error("Cloudflare challenge not bypassed for URL: %s", url)
                    return []

                return self.parse_chart_html(html, platform, country, chart_date)
        except Exception as e:
            logger.error("Error scraping %s: %s", url, e)
            return []

    def scrape_all_targets(
        self, 
        platforms: Optional[List[str]] = None, 
        countries: Optional[List[str]] = None,
        chart_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Iterate over all configured target platforms and countries with respectful delays.
        """
        target_platforms = platforms or settings.TARGET_PLATFORMS
        target_countries = countries or settings.TARGET_COUNTRIES
        chart_date = chart_date or datetime.now().strftime("%Y-%m-%d")

        all_records = []
        logger.info(
            "Starting ingestion run for %d platforms and %d countries on date %s",
            len(target_platforms), len(target_countries), chart_date
        )

        for platform in target_platforms:
            for country in target_countries:
                records = self.scrape_chart(platform, country, chart_date)
                all_records.extend(records)
                time.sleep(self.delay)

        return all_records
