#!/usr/bin/env python3
"""
Simple test script for JobBank source with minimal filters.
"""
import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from job_sources.jobbank import create_jobbank_source
from utils.logger import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)

async def test_jobbank_source_simple():
    """Test the JobBank source with very simple filters."""
    print("Testing JobBank source with simple filters...")

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
        print("Searching for jobs...")
        jobs = await jobbank_source.search(test_filters, limit=10)

        print(f"\nFound {len(jobs)} jobs:")
        for i, job in enumerate(jobs, 1):
            print(f"{i}. {job.title} at {job.company}")
            print(f"   Location: {job.location}")
            print(f"   URL: {job.url[:100]}...")
            if i >= 3:  # Only show first 3
                print("   ... and more")
                break
            print()

        await jobbank_source.close()
        return len(jobs) > 0

    except Exception as e:
        logger.error(f"Error testing JobBank source: {e}", exc_info=True)
        await jobbank_source.close()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_jobbank_source_simple())
    if result:
        print("SUCCESS: JobBank source is working!")
        sys.exit(0)
    else:
        print("FAILED: JobBank source returning 0 jobs")
        sys.exit(1)