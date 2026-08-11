print("Hello from search test")
import asyncio
from job_sources.jobbank import create_jobbank_source
from utils.logger import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

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
    
    print("Searching for jobs...")
    jobs = await source.search(test_filters, limit=5)
    print(f"Found {len(jobs)} jobs")
    
    if jobs:
        for i, job in enumerate(jobs, 1):
            print(f"{i}. {job.title} at {job.company}")
            print(f"   Location: {job.location}")
            print(f"   URL: {job.url}")
    else:
        print("No jobs found")
        
    await source.close()
    print("Source closed")

print("Starting test...")
asyncio.run(test())
print("Test completed")
