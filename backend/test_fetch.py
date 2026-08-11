print("Hello from fetch test")
import asyncio
from job_sources.jobbank import create_jobbank_source
from bs4 import BeautifulSoup

async def test():
    print("Creating JobBank source...")
    source = await create_jobbank_source({"rate_limit": 1.0, "max_pages": 1})
    print("Source created")
    
    # Very simple filters
    test_filters = {
        "primary_titles": ["Analyst"],
        "locations": ["Toronto"],
        "employment_types": ["Full-time"],
        "negative_keywords": []
    }
    
    print(f"Filters: {test_filters}")
    
    # Build URL to see what we're requesting
    url = source._build_search_url(test_filters, page=1)
    print(f"URL: {url}")
    
    # Fetch the page directly
    import aiohttp
    session = await source._get_session()
    
    print("Fetching page...")
    async with session.get(url) as response:
        print(f"HTTP Status: {response.status}")
        if response.status == 200:
            html = await response.text()
            print(f"HTML length: {len(html)} characters")
            
            # Save HTML for inspection
            with open('/tmp/jobbank_fetch.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("Saved HTML to /tmp/jobbank_fetch.html")
            
            # Show first 2000 chars
            print("\nFirst 2000 characters of HTML:")
            print(html[:2000])
            print("...")
            
            # Try to parse with BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            
            # Look for job cards using the current selector
            job_cards = soup.find_all("article", class_="result-item")
            print(f"\nFound {len(job_cards)} job cards with 'article.result-item'")
            
            # If we found some, let's see what they look like
            if job_cards:
                card = job_cards[0]
                print(f"\nFirst job card HTML snippet:")
                print(str(card)[:500])
            else:
                # Try to find any elements that might be job listings
                print("\nTrying to find job listings with other selectors...")
                
                # Look for common job listing patterns
                selectors_to_try = [
                    "div.job-search-result-item",
                    "section.job-card",
                    "div[data-testid='job-card']",
                    "li.search-result",
                    "div.result",
                    "article.job",
                    ".search-result",
                    ".job-listing",
                    ".result-item"
                ]
                
                for selector in selectors_to_try:
                    elements = soup.select(selector)
                    if elements:
                        print(f"Found {len(elements)} elements with selector: {selector}")
                        # Show first element
                        if elements:
                            print(f"  First element: {str(elements[0])[:200]}...")
                    else:
                        print(f"Found 0 elements with selector: {selector}"
        else:
            print(f"HTTP Error: {response.status}")
            html = await response.text()
            print(f"Response: {html[:1000]}...")
    
    await source.close()
    print("Source closed")

print("Starting test...")
asyncio.run(test())
print("Test completed")
