#!/usr/bin/env python3
"""
Debug script for JobBank source.
"""
import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from job_sources.jobbank import create_jobbank_source
from utils.logger import setup_logging, get_logger

# Setup logging with debug level
setup_logging(log_level="DEBUG")
logger = get_logger(__name__)

async def debug_jobbank_source():
    """Debug the JobBank source."""
    print("Debugging JobBank source...")

    # Create JobBank source
    jobbank_source = await create_jobbank_source({
        "rate_limit": 1.0,
        "max_pages": 2
    })

    # Very simple filters - just search for "analyst" in Toronto
    test_filters = {
        "primary_titles": ["Analyst"],
        "locations": ["Toronto"],
        "employment_types": ["Full-time"],
        "negative_keywords": []  # No negative keywords
    }

    try:
        print("Building search URL for page 1...")
        url = jobbank_source._build_search_url(test_filters, page=1)
        print(f"URL: {url}")

        session = await jobbank_source._get_session()
        await jobbank_source._rate_limit()
        print("Fetching URL...")
        async with session.get(url) as response:
            print(f"Status: {response.status}")
            if response.status == 200:
                html = await response.text()
                print(f"HTML length: {len(html)}")
                # Save the HTML for inspection
                with open("/tmp/jobbank_debug.html", "w", encoding="utf-8") as f:
                    f.write(html)
                print("Saved HTML to /tmp/jobbank_debug.html")
                # Check for job cards
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")
                job_cards = soup.find_all("article", class_="result-item")
                print(f"Found {len(job_cards)} job cards with class 'result-item'")
                if job_cards:
                    for i, card in enumerate(job_cards[:3]):
                        print(f"Card {i+1}:")
                        title_elem = card.find("a", class_="resultJobTitle")
                        if title_elem:
                            print(f"  Title: {title_elem.get_text(strip=True)}")
                        else:
                            print("  Title element not found")
                else:
                    print("No job cards found. Let's check for other possible selectors.")
                    # Try to find any article
                    articles = soup.find_all("article")
                    print(f"Found {len(articles)} article tags")
                    # Look for common patterns
                    divs = soup.find_all("div", class_=True)
                    print(f"Found {len(divs)} div tags with class")
                    # Print first 2000 chars of HTML to see structure
                    print("First 2000 chars of HTML:")
                    print(html[:2000])
            else:
                print(f"Failed to fetch: {response.status}")
                text = await response.text()
                print(f"Response text: {text[:500]}")

        await jobbank_source.close()

    except Exception as e:
        logger.error(f"Error debugging JobBank source: {e}", exc_info=True)
        await jobbank_source.close()

if __name__ == "__main__":
    asyncio.run(debug_jobbank_source())