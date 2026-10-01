import pytest
from src.ingestion.flixpatrol_scraper import FlixPatrolScraper

SAMPLE_HTML = """
<html>
<body>
<h2>TOP 10 Movies on Netflix in India</h2>
<table class="card-table">
  <tr>
    <td>1.</td><td>•</td><td><a href="/title/sample-movie/">Sample Movie Alpha</a></td><td>5 d</td>
  </tr>
  <tr>
    <td>2.</td><td>•</td><td><a href="/title/sample-movie-2/">Sample Movie Beta</a></td><td>1 d</td>
  </tr>
</table>

<h2>TOP 10 TV Shows on Netflix in India</h2>
<table class="card-table">
  <tr>
    <td>1.</td><td>•</td><td><a href="/title/sample-show/">Sample Show Alpha</a></td><td>12 d</td>
  </tr>
</table>

<h2>Top ranked Movies</h2>
<table>
  <tr><td>40</td><td>Calendar Row</td></tr>
</table>
</body>
</html>
"""

def test_parse_chart_html_structure():
    scraper = FlixPatrolScraper()
    records = scraper.parse_chart_html(SAMPLE_HTML, "netflix", "india", "2026-10-01")
    assert len(records) == 3
    
    # Check Movie 1
    assert records[0]["content_type"] == "movie"
    assert records[0]["rank"] == 1
    assert records[0]["title"] == "Sample Movie Alpha"
    assert records[0]["points"] == 10
    assert records[0]["days_in_top_10"] == 5

    # Check Movie 2
    assert records[1]["content_type"] == "movie"
    assert records[1]["rank"] == 2
    assert records[1]["title"] == "Sample Movie Beta"
    assert records[1]["points"] == 9
    assert records[1]["days_in_top_10"] == 1

    # Check Series 1
    assert records[2]["content_type"] == "series"
    assert records[2]["rank"] == 1
    assert records[2]["title"] == "Sample Show Alpha"
    assert records[2]["points"] == 10
    assert records[2]["days_in_top_10"] == 12

def test_build_chart_url_slugs():
    scraper = FlixPatrolScraper()
    assert scraper.build_chart_url("Netflix", "India") == "https://flixpatrol.com/top10/netflix/india/"
    assert scraper.build_chart_url("Amazon Prime Video", "USA") == "https://flixpatrol.com/top10/amazon-prime/united-states/"
    assert scraper.build_chart_url("Disney+", "UK") == "https://flixpatrol.com/top10/disney/united-kingdom/"
    assert scraper.build_chart_url("HBO Max", "US") == "https://flixpatrol.com/top10/hbo-max/united-states/"
