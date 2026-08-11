import asyncio
import aiohttp
from job_sources.jobbank import create_jobbank_source
from bs4 import BeautifulSoup

async def test():
    print("Testing JobBank search results...")
    
    # Create source just to build URL
    source = await create_jobbank_source({"rate_limit": 1.0, "max_pages": 1})
    
    # Very simple filters
    test_filters = {
        "primary_titles": ["Analyst"],
        "locations": ["Toronto"],
        "employment_types": ["Full-time"],
        "negative_keywords": []
    }
    
    print(f"Filters: {test_filters}")
    
    # Build the search URL
    url = source._build_search_url(test_filters, page=1)
    print(f"Search URL: {url}")
    
    # Fetch the search results page
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        print("Fetching search results...")
        async with session.get(url) as response:
            print(f"HTTP Status: {response.status}")
            if response.status == 200:
                html = await response.text()
                print(f"Successfully fetched {len(html)} characters of search results")
                
                # Save HTML for inspection
                with open('/tmp/jobbank_search_results.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                print("Saved search results to /tmp/jobbank_search_results.html")
                
                # Show first 3000 chars to see what we're getting
                print("\nFirst 3000 characters of search results:")
                print(html[:3000])
                print("...")
                
                # Show last 1000 chars too
                print("\nLast 1000 characters of search results:")
                print(html[-1000:])
                print("...")
                
                # Try to parse with BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")
                
                # Look for job cards using the current selector from the source
                job_cards = soup.find_all("article", class_="result-item")
                print(f"\nFound {len(job_cards)} job cards with 'article.result-item'")
                
                # Try other common selectors
                selectors = [
                    "div.job-search-result-item",
                    "section[data-testid='job-card']",
                    "div.result",
                    "li.search-result",
                    ".job-card",
                    ".search-result-item"
                ]
                
                for selector in selectors:
                    elements = soup.select(selector)
                    print(f"Found {len(elements)} elements with selector: {selector}")
                
                # Look for any text that might indicate no results
                no_results_indicators = [
                    "no results",
                    "not found",
                    "aucun résultat",
                    "aucune offre",
                    "empty",
                    "zero results"
                ]
                
                html_lower = html.lower()
                for indicator in no_results_indicators:
                    if indicator in html_lower:
                        print(f"Found '{indicator}' in HTML - might indicate no results")
                
                # Look for job titles in the HTML
                import re
                # Look for common job title patterns in the HTML
                title_patterns = [
                    r'"title"[^}]*?[A-Z][a-z]+.*?Analyst',
                    r'Analyst[^<]*?(?=<)',
                    r'[^<]*?Analyst[^<]*(?=<|&)'
                ]
                
                print("\nChecking for Analyst in HTML...")
                for pattern in title_patterns:
                    matches = re.findall(pattern, html, re.IGNORECASE)
                    if matches:
                        print(f"Found {len(matches)} matches for pattern: {pattern}")
                        # Show first few matches
                        for match in matches[:3]:
                            print(f"  {match[:100]}...")
                    else:
                        print(f"No matches for pattern: {pattern}")
                        
            else:
                print(f"HTTP Error: {response.status}")
                html = await response.text()
                print(f"Response: {html[:1000]}...")
    
    await source.close()
    print("Source closed")

print("Starting search results test...")
asyncio.run(test())
print("Search results test completed")
