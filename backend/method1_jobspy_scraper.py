#!/usr/bin/env python3
"""
Method 1: Multi-Platform Job Scraping via python-jobspy

This script uses jobspy to scrape job postings from LinkedIn, Indeed, and ZipRecruiter.
Searches for "Data Analyst" roles in Canada (including remote).

Requirements:
    pip install python-jobspy pandas

Usage:
    python method1_jobspy_scraper.py
"""

import csv
import sys
from typing import List, Dict, Any

try:
    from jobspy import scrape_jobs
except ImportError:
    print("Error: python-jobspy not installed. Run: pip install python-jobspy pandas")
    sys.exit(1)

import pandas as pd


def scrape_data_analyst_jobs() -> List[Dict[str, Any]]:
    """
    Scrape Data Analyst jobs from multiple platforms using jobspy.

    Returns:
        List of job dictionaries with standardized fields.
    """
    print("=" * 60)
    print("Method 1: Scraping via python-jobspy")
    print("=" * 60)
    print("\nSearching for 'Data Analyst' jobs in Canada...")
    print("Sources: LinkedIn, Indeed, ZipRecruiter")
    print("Limit: 10 results per source\n")

    try:
        # Scrape jobs from multiple sites
        jobs_df = scrape_jobs(
            site_name=["linkedin", "indeed", "zip_recruiter"],
            search_term="Data Analyst",
            location="Canada",
            results_wanted=10,  # 10 per site = up to 30 total
            hours_old=720,  # Last 30 days (720 hours)
            country_indeed="Canada",  # Specific to Indeed
            linkedin_fetch_description=True,  # Get full descriptions from LinkedIn
        )

        print(f"✓ Successfully scraped {len(jobs_df)} total jobs")

    except Exception as e:
        print(f"✗ Error during scraping: {type(e).__name__}: {e}")
        return []

    # Convert DataFrame to list of dictionaries with selected fields
    jobs_list = []
    required_fields = ['site', 'title', 'company', 'location', 'job_url', 'description']

    for _, row in jobs_df.iterrows():
        job = {}
        for field in required_fields:
            try:
                value = row.get(field)
                # Handle NaN/None values
                if pd.isna(value):
                    job[field] = "N/A"
                else:
                    job[field] = str(value).strip()
            except Exception as e:
                print(f"  Warning: Could not extract '{field}': {e}")
                job[field] = "N/A"
        jobs_list.append(job)

    return jobs_list


def export_to_csv(jobs: List[Dict[str, Any]], filename: str = "jobspy_results.csv") -> bool:
    """
    Export jobs to CSV file.

    Args:
        jobs: List of job dictionaries
        filename: Output CSV filename

    Returns:
        True if successful, False otherwise
    """
    if not jobs:
        print("No jobs to export.")
        return False

    fieldnames = ['site', 'title', 'company', 'location', 'job_url', 'description']

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(jobs)

        print(f"✓ Exported {len(jobs)} jobs to '{filename}'")
        return True

    except Exception as e:
        print(f"✗ Error exporting to CSV: {type(e).__name__}: {e}")
        return False


def print_summary(jobs: List[Dict[str, Any]]) -> None:
    """Print a summary of scraped jobs."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total jobs found: {len(jobs)}")

    # Count by site
    site_counts = {}
    for job in jobs:
        site = job.get('site', 'Unknown')
        site_counts[site] = site_counts.get(site, 0) + 1

    print("\nJobs per site:")
    for site, count in sorted(site_counts.items()):
        print(f"  {site}: {count}")

    # Show first job description preview
    if jobs:
        first_job = jobs[0]
        desc = first_job.get('description', '')
        preview = desc[:200] + "..." if len(desc) > 200 else desc
        print(f"\nFirst job description preview (first 200 chars):")
        print(f"  Title: {first_job.get('title', 'N/A')}")
        print(f"  Company: {first_job.get('company', 'N/A')}")
        print(f"  Location: {first_job.get('location', 'N/A')}")
        print(f"  Description: {preview}")


def main():
    """Main entry point."""
    print("\n🔍 Starting JobSpy Multi-Platform Scraper\n")

    # Scrape jobs
    jobs = scrape_data_analyst_jobs()

    if not jobs:
        print("\n⚠ No jobs found. This could be due to:")
        print("  - Rate limiting from job sites")
        print("  - Network connectivity issues")
        print("  - Site structure changes")
        print("\nTroubleshooting tips:")
        print("  1. Wait a few minutes and try again (rate limits reset)")
        print("  2. Check your internet connection")
        print("  3. Try reducing 'results_wanted' parameter")
        print("  4. Use a VPN if IP is blocked")
        sys.exit(1)

    # Export to CSV
    export_to_csv(jobs)

    # Print summary
    print_summary(jobs)

    print("\n✅ Done!")


if __name__ == "__main__":
    main()