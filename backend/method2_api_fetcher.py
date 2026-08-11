#!/usr/bin/env python3
"""
Method 2: Keyless REST API Fetch via Remotive & Arbeitnow

This script fetches job postings from two free, no-API-key-required sources:
- Remotive: https://remotive.com/api/remote-jobs
- Arbeitnow: https://www.arbeitnow.com/api/v1/jobs

Filters for job titles containing "Data" or "Analyst".

Requirements:
    pip install requests

Usage:
    python method2_api_fetcher.py
"""

import sys
import json
import time
from typing import List, Dict, Any, Optional

try:
    import requests
except ImportError:
    print("Error: requests not installed. Run: pip install requests")
    sys.exit(1)


# Configuration
REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"
ARBEITNOW_API_URL = "https://www.arbeitnow.com/api/job-board-api"  # Updated endpoint

# Search keywords (case-insensitive)
SEARCH_KEYWORDS = ["data", "analyst"]

# Request settings
REQUEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# User-Agent header to appear more like a real browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def fetch_with_retry(url: str, source_name: str) -> Optional[Dict[str, Any]]:
    """
    Fetch JSON data from API with retry logic.

    Args:
        url: API endpoint URL
        source_name: Name of the source (for logging)

    Returns:
        Parsed JSON response or None on failure
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"  Fetching from {source_name} (attempt {attempt}/{MAX_RETRIES})...")
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)

            if response.status_code == 200:
                print(f"  ✓ {source_name}: Success ({len(response.content)} bytes)")
                return response.json()

            elif response.status_code == 429:
                print(f"  ⚠ {source_name}: Rate limited (429). Waiting before retry...")
                time.sleep(RETRY_DELAY * attempt)
                continue

            elif response.status_code >= 500:
                print(f"  ⚠ {source_name}: Server error ({response.status_code}). Retrying...")
                time.sleep(RETRY_DELAY * attempt)
                continue

            else:
                print(f"  ✗ {source_name}: HTTP {response.status_code} - {response.reason}")
                return None

        except requests.exceptions.Timeout:
            print(f"  ⚠ {source_name}: Request timed out. Retrying...")
            time.sleep(RETRY_DELAY * attempt)

        except requests.exceptions.ConnectionError:
            print(f"  ⚠ {source_name}: Connection error. Retrying...")
            time.sleep(RETRY_DELAY * attempt)

        except requests.exceptions.RequestException as e:
            print(f"  ✗ {source_name}: Request failed - {type(e).__name__}: {e}")
            return None

        except json.JSONDecodeError as e:
            print(f"  ✗ {source_name}: Invalid JSON response - {e}")
            return None

    print(f"  ✗ {source_name}: Failed after {MAX_RETRIES} attempts")
    return None


def filter_jobs(jobs: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
    """
    Filter jobs for titles containing 'Data' or 'Analyst'.

    Args:
        jobs: List of job dictionaries from API
        source: Source name ("remotive" or "arbeitnow")

    Returns:
        Filtered and normalized job list
    """
    filtered = []
    keywords_lower = [k.lower() for k in SEARCH_KEYWORDS]

    for job in jobs:
        try:
            # Extract title based on source structure
            if source == "remotive":
                title = job.get("title", "")
                company = job.get("company_name", "")
                url = job.get("url", "")
                description = job.get("description", "")
                location = job.get("candidate_required_location", "Remote")
                job_type = job.get("job_type", "")

            elif source == "arbeitnow":
                title = job.get("title", "")
                company = job.get("company_name", "")
                url = job.get("url", "")
                description = job.get("description", "")
                location = job.get("location", "Remote")
                job_type = job.get("job_type", "")

            else:
                continue

            # Check if title matches keywords (case-insensitive)
            title_lower = title.lower()
            if any(keyword in title_lower for keyword in keywords_lower):
                filtered.append({
                    "source": source,
                    "title": title.strip(),
                    "company": company.strip(),
                    "location": location.strip(),
                    "url": url.strip(),
                    "description": description.strip(),
                    "job_type": job_type.strip() if job_type else "N/A"
                })

        except Exception as e:
            print(f"    Warning: Error processing job from {source}: {e}")
            continue

    return filtered


def print_jobs(jobs: List[Dict[str, Any]], max_display: int = 5) -> None:
    """
    Print jobs in a nicely formatted way.

    Args:
        jobs: List of filtered job dictionaries
        max_display: Maximum number of jobs to display
    """
    if not jobs:
        print("\n  No matching jobs found.")
        return

    print(f"\n  Found {len(jobs)} matching job(s). Displaying first {min(max_display, len(jobs))}:\n")

    for i, job in enumerate(jobs[:max_display], 1):
        print(f"  {'─' * 50}")
        print(f"  #{i} | {job['title']}")
        print(f"       Company: {job['company']}")
        print(f"       Location: {job['location']}")
        print(f"       Type: {job['job_type']}")
        print(f"       Source: {job['source'].capitalize()}")
        print(f"       Apply: {job['url']}")

        # Description preview (first 300 chars)
        desc = job['description']
        if desc and desc != "N/A":
            preview = desc[:300] + "..." if len(desc) > 300 else desc
            # Clean up HTML tags if present
            import re
            preview = re.sub(r'<[^>]+>', '', preview)
            preview = re.sub(r'\s+', ' ', preview).strip()
            print(f"       Description: {preview}")
        else:
            print(f"       Description: (No description available)")

    print(f"  {'─' * 50}")


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("Method 2: Keyless REST API Fetch (Remotive + Arbeitnow)")
    print("=" * 60)
    print(f"\nSearching for jobs with keywords: {', '.join(SEARCH_KEYWORDS)}")
    print("Sources: Remotive.io, Arbeitnow.com\n")

    all_filtered_jobs = []

    # --- Fetch from Remotive ---
    print("📡 Fetching from Remotive...")
    remotive_data = fetch_with_retry(REMOTIVE_API_URL, "Remotive")

    if remotive_data and "jobs" in remotive_data:
        remotive_jobs = remotive_data["jobs"]
        print(f"  Total jobs from Remotive: {len(remotive_jobs)}")
        filtered = filter_jobs(remotive_jobs, "remotive")
        print(f"  Matching 'Data/Analyst' jobs: {len(filtered)}")
        all_filtered_jobs.extend(filtered)
    else:
        print("  ✗ Failed to fetch or parse Remotive data")

    print()  # Spacer

    # --- Fetch from Arbeitnow ---
    print("📡 Fetching from Arbeitnow...")
    arbeitnow_data = fetch_with_retry(ARBEITNOW_API_URL, "Arbeitnow")

    if arbeitnow_data and "data" in arbeitnow_data:
        arbeitnow_jobs = arbeitnow_data["data"]
        print(f"  Total jobs from Arbeitnow: {len(arbeitnow_jobs)}")
        filtered = filter_jobs(arbeitnow_jobs, "arbeitnow")
        print(f"  Matching 'Data/Analyst' jobs: {len(filtered)}")
        all_filtered_jobs.extend(filtered)
    else:
        print("  ✗ Failed to fetch or parse Arbeitnow data")

    # --- Display Results ---
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    if all_filtered_jobs:
        print_jobs(all_filtered_jobs, max_display=5)
        print(f"\n✅ Total matching jobs found: {len(all_filtered_jobs)}")
    else:
        print("\n⚠ No matching jobs found with keywords 'Data' or 'Analyst'")
        print("\nTroubleshooting:")
        print("  - Try broader keywords (e.g., 'engineer', 'developer')")
        print("  - Check if APIs have changed their response format")
        print("  - Some jobs may not have 'Data' or 'Analyst' in title but in description")

    print("\n" + "=" * 60)
    print("TROUBLESHOOTING TIPS")
    print("=" * 60)
    print("""
If you encounter issues:

1. RATE LIMITS (HTTP 429):
   - Both APIs are free and may have rate limits
   - Wait 1-2 minutes before retrying
   - The script has built-in retry logic with exponential backoff

2. CONNECTION ERRORS:
   - Check your internet connection
   - Try with a VPN if your IP is blocked
   - Some corporate networks may block these domains

3. HTTP ERRORS (5xx):
   - Server-side issues - wait and retry later
   - The script retries up to 3 times automatically

4. NO MATCHING JOBS:
   - Keywords are case-insensitive but must appear in the TITLE
   - Try modifying SEARCH_KEYWORDS list at top of script
   - Some remote job boards may have fewer Data/Analyst roles

5. JSON PARSE ERRORS:
   - API response format may have changed
   - Print raw response to debug: print(json.dumps(data, indent=2))

6. TIMEOUT ERRORS:
   - Increase REQUEST_TIMEOUT constant (default 30s)
   - Network latency may be high
""")


if __name__ == "__main__":
    main()