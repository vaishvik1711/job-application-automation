#!/usr/bin/env python3
"""
Test script to verify JobBank source.
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

async def test_jobbank_source():
    """Test the JobBank source with sample filters."""
    print("Testing JobBank source...")

    # Create JobBank source
    jobbank_source = await create_jobbank_source({
        "rate_limit": 1.0,
        "max_pages": 2  # Limit to 2 pages for quick test
    })

    # Test filters similar to what the system uses
    test_filters = {
        "primary_titles": ["Data Analyst", "Business Analyst"],
        "secondary_titles": ["Analyst", "BI Developer"],
        "strong_skills": ["SQL", "Power BI", "Python", "Excel"],
        "locations": ["Toronto, ON", "Remote Canada"],
        "remote_preferences": ["Remote", "Hybrid"],
        "employment_types": ["Full-time"],
        "negative_keywords": [
            "nursing license",
            "CISSP required",
            "PhD required",
            "5+ years experience required",
            "security clearance",
            "CPA required",
            "expert Java",
            "government clearance",
            "mandatory certification"
        ]
    }

    try:
        print("Searching for jobs...")
        jobs = await jobbank_source.search(test_filters, limit=10)

        print(f"\nFound {len(jobs)} jobs:")
        for i, job in enumerate(jobs, 1):
            print(f"{i}. {job.title} at {job.company}")
            print(f"   Location: {job.location}")
            print(f"   URL: {job.url[:100]}...")
            print()

        await jobbank_source.close()
        return len(jobs) > 0

    except Exception as e:
        logger.error(f"Error testing JobBank source: {e}", exc_info=True)
        await jobbank_source.close()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_jobbank_source())
    if result:
        print("SUCCESS: JobBank source is working!")
        sys.exit(0)
    else:
        print("FAILED: JobBank source having issues")
        sys.exit(1)