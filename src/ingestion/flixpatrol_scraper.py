import logging
import re
import time
from datetime import datetime, timezone
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
    allowing automated ingestion of real-time Top 10 rankings.
    """

    BASE_URL = "https://flixpatrol.com"

    PLATFORM_SLUG_MAP = {
        "netflix": "netflix",
        "amazon-prime": "amazon-prime",
        "amazon prime video": "amazon-prime",
        "amazon prime": "amazon-prime",
        "amazon": "amazon-prime",
        "prime-video": "amazon-prime",
        "prime": "amazon-prime",
        "disney": "disney",
        "disney+": "disney",
        "disney-plus": "disney",
        "disney plus": "disney",
        "apple-tv": "apple-tv",
        "apple tv": "apple-tv",
        "apple": "apple-tv",
        "apple tv+": "apple-tv",
        "apple-tv+": "apple-tv",
        "hbo-max": "hbo-max",
        "hbo max": "hbo-max",
        "hbo": "hbo-max",
        "max": "hbo-max",
    }

    COUNTRY_SLUG_MAP = {
        "world": "world",
        "united-states": "united-states",
        "us": "united-states",
        "usa": "united-states",
        "united-kingdom": "united-kingdom",
        "uk": "united-kingdom",
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
        "au": "australia",
    }

    def __init__(self, headless: Optional[bool] = None, timeout: Optional[int] = None):
        self.headless = headless if headless is not None else settings.SCRAPER_HEADLESS
        self.timeout = (timeout or settings.SCRAPER_TIMEOUT_SECONDS) * 1000  # ms
        self.delay = settings.SCRAPER_REQUEST_DELAY_SECONDS

    def build_chart_url(self, platform: str, country: str, chart_date: Optional[str] = None) -> str:
        """
        Construct the FlixPatrol chart URL.
        Example: https://flixpatrol.com/top10/netflix/india/
        """
        plat = self.PLATFORM_SLUG_MAP.get(platform.lower().strip(), platform.lower().strip())
        ctry = self.COUNTRY_SLUG_MAP.get(country.lower().strip(), country.lower().strip())
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
        seen_ranks = set()

        tables = soup.find_all("table")
        if not tables:
            logger.warning("No <table> tags found on FlixPatrol page for %s - %s", platform, country)
            return records

        for table in tables:
            parent_h = table.find_previous(["h2", "h3", "h4"])
            heading = parent_h.get_text(strip=True) if parent_h else ""
            h_lower = heading.lower()

            # We target primary Top 10 charts and exclude kids / weekly overview tables
            if "top 10" not in h_lower or "kids" in h_lower:
                continue

            content_type = "movie" if ("movie" in h_lower or "film" in h_lower) else "series"

            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if not cells or len(cells) < 3:
                    continue

                # Parse rank (e.g. '1.', '2')
                rank_str = cells[0].get_text(strip=True).replace(".", "")
                if not rank_str.isdigit():
                    continue
                rank = int(rank_str)
                if rank < 1 or rank > 10:
                    continue

                # Deduplicate if table appears twice
                rank_key = (content_type, rank)
                if rank_key in seen_ranks:
                    continue
                seen_ranks.add(rank_key)

                # Parse title
                title_link = row.find("a")
                if title_link:
                    title = title_link.get_text(strip=True)
                    detail_url = title_link.get("href", "")
                else:
                    title = cells[2].get_text(strip=True)
                    detail_url = ""

                if not title:
                    continue

                # Extract days in top 10 if present (e.g. '12 d')
                days_in_top_10 = 1
                for c in cells[2:]:
                    txt = c.get_text(strip=True)
                    m = re.search(r"(\d+)\s*d", txt)
                    if m:
                        days_in_top_10 = int(m.group(1))
                        break

                # FlixPatrol standard daily points scoring: 10 down to 1
                points = 11 - rank

                records.append({
                    "platform": platform,
                    "country": country,
                    "chart_date": chart_date,
                    "content_type": content_type,
                    "rank": rank,
                    "title": title,
                    "points": points,
                    "days_in_top_10": days_in_top_10,
                    "detail_url": f"{self.BASE_URL}{detail_url}" if detail_url.startswith("/") else detail_url,
                    "scraped_at": datetime.now(timezone.utc).isoformat()
                })

        logger.info(
            "Parsed %d items for platform=%s, country=%s, date=%s", 
            len(records), platform, country, chart_date
        )
        return records

    def _scrape_page_content(self, page, url: str) -> str:
        """Navigate to URL, bypass Cloudflare Turnstile, and extract page HTML safely."""
        logger.info("Navigating to %s...", url)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
        except Exception as e:
            logger.warning("Initial goto timeout or issue (%s), checking page state...", e)

        # Wait for Cloudflare turnstile challenge and navigation redirect to complete
        for _ in range(25):
            time.sleep(1)
            try:
                title = page.title()
                if "Just a moment" not in title and "Loading" not in title and title.strip():
                    try:
                        page.wait_for_load_state("domcontentloaded", timeout=5000)
                    except Exception:
                        pass
                    time.sleep(2)
                    break
            except Exception:
                time.sleep(1)

        # Retry content extraction to avoid 'page is navigating' race condition
        html = ""
        for attempt in range(5):
            try:
                html = page.content()
                if "TOP" in html or "Top" in html:
                    break
            except Exception as e:
                logger.debug("Content retrieval retry %d: %s", attempt + 1, e)
                time.sleep(1.5)

        return html

    def scrape_chart(
        self, 
        platform: str, 
        country: str, 
        chart_date: Optional[str] = None, 
        page: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape a single chart page for a given platform and country.
        If a page instance is provided, it reuses the existing browser session.
        """
        if not chart_date:
            chart_date = datetime.now().strftime("%Y-%m-%d")

        url = self.build_chart_url(platform, country)
        logger.info("Scraping FlixPatrol URL: %s", url)

        try:
            if page is not None:
                html = self._scrape_page_content(page, url)
                return self.parse_chart_html(html, platform, country, chart_date)
            else:
                with Camoufox(headless=self.headless) as browser:
                    p = browser.new_page()
                    html = self._scrape_page_content(p, url)
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
        Iterate over all configured target platforms and countries using a persistent browser session.
        Reusing the Camoufox session retains Cloudflare clearance cookies across requests.
        """
        target_platforms = platforms or settings.TARGET_PLATFORMS
        target_countries = countries or settings.TARGET_COUNTRIES
        chart_date = chart_date or datetime.now().strftime("%Y-%m-%d")

        all_records = []
        logger.info(
            "Starting ingestion run for %d platforms and %d countries on date %s",
            len(target_platforms), len(target_countries), chart_date
        )

        try:
            with Camoufox(headless=self.headless) as browser:
                page = browser.new_page()
                for platform in target_platforms:
                    for country in target_countries:
                        records = self.scrape_chart(platform, country, chart_date, page=page)
                        all_records.extend(records)
                        time.sleep(self.delay)
        except Exception as e:
            logger.error("Error during batch scraping session: %s", e)

        return all_records
