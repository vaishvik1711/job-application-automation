"""
Local Indeed scraper — scrapes Indeed from YOUR machine and sends jobs to Railway.

Railway's cloud IPs are blocked by Indeed, but jobspy works fine from your
local network. This script:
  1. Scrapes Indeed using python-jobspy (your local IP)
  2. Bulk-imports the jobs into the Railway database
  3. Triggers auto-matching on the imported jobs

Usage:
  python run_indeed_scraper.py --search "Data Analyst" --location "Toronto, ON" --limit 25
  python run_indeed_scraper.py --search "Business Analyst" --location "Remote Canada" --limit 15

Defaults: "Data Analyst" in "Toronto, ON", 25 results.

Requires: pip install python-jobspy requests
"""
import argparse
import json
import sys
import time
from datetime import datetime

try:
    import requests
except ImportError:
    print("ERROR: requests is required. Run: pip install requests")
    sys.exit(1)

try:
    from jobspy import scrape_jobs
except ImportError:
    print("ERROR: python-jobspy is required. Run: pip install python-jobspy")
    sys.exit(1)


RAILWAY_URL = "https://job-application-automation-production.up.railway.app"


def parse_args():
    parser = argparse.ArgumentParser(description="Scrape Indeed from your local machine and push to Railway")
    parser.add_argument("--search", default="Data Analyst", help="Job search term (default: Data Analyst)")
    parser.add_argument("--location", default="Toronto, ON", help="Location (default: Toronto, ON)")
    parser.add_argument("--limit", type=int, default=25, help="Max results (default: 25)")
    parser.add_argument("--hours-old", type=int, default=168, help="Max hours since posting (default: 168 = 7 days)")
    parser.add_argument("--api-url", default=RAILWAY_URL, help=f"Backend URL (default: {RAILWAY_URL})")
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"\n{'='*60}")
    print(f"🔍 Scraping Indeed for: {args.search}")
    print(f"📍 Location: {args.location}")
    print(f"📊 Max results: {args.limit}")
    print(f"{'='*60}\n")

    # --- Step 1: Scrape Indeed ---
    start = time.time()
    print("Scraping Indeed... ", end="", flush=True)

    try:
        jobs_df = scrape_jobs(
            site_name=["indeed"],
            search_term=args.search,
            location=args.location,
            results_wanted=args.limit,
            hours_old=args.hours_old,
            country_indeed="Canada",
        )
    except Exception as e:
        print(f"❌ FAILED: {e}")
        sys.exit(1)

    elapsed = time.time() - start

    if jobs_df is None or jobs_df.empty:
        print(f"⚠️  No jobs found in {elapsed:.1f}s")
        return

    print(f"✅ {len(jobs_df)} jobs found in {elapsed:.1f}s\n")

    # --- Step 2: Convert to JSON ---
    jobs = []
    for _, row in jobs_df.iterrows():
        def safe(v):
            return str(v).strip() if v is not None and not (hasattr(v, 'empty') and v.empty) else ""

        job = {
            "title": safe(row.get("title")),
            "company": safe(row.get("company")),
            "location": safe(row.get("location")),
            "description": safe(row.get("description"))[:10000],
            "url": safe(row.get("job_url")),
            "source_job_id": safe(row.get("job_id")) or safe(row.get("job_url")),
            "salary_min": int(row.get("salary_min")) if pd_notna(row, "salary_min") else None,
            "salary_max": int(row.get("salary_max")) if pd_notna(row, "salary_max") else None,
            "currency": "CAD",
            "remote_type": safe(row.get("remote_type")).lower() or "on_site",
            "employment_type": safe(row.get("employment_type")).lower() or "full_time",
            "requirements": safe(row.get("requirements"))[:5000],
        }
        jobs.append(job)

    print(f"📦 Prepared {len(jobs)} jobs for import\n")

    # --- Step 3: Upload to Railway ---
    api_url = args.api_url.rstrip("/")
    print(f"📤 Uploading to {api_url}/jobs/bulk-import ... ", end="", flush=True)

    try:
        resp = requests.post(
            f"{api_url}/jobs/bulk-import",
            json={"jobs": jobs, "source": "indeed"},
            timeout=120,
        )
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot reach {api_url}")
        print("   Make sure the Railway backend is running.")
        print("   Check status at https://railway.app/project")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        sys.exit(1)

    result = resp.json()
    if not result.get("success"):
        print(f"❌ API error: {result.get('message', 'unknown')}")
        print(json.dumps(result, indent=2)[:500])
        sys.exit(1)

    data = result.get("data", {})
    imported = data.get("imported", 0)
    total = data.get("total", 0)
    errors = data.get("errors", [])
    print(f"✅ {imported}/{total} imported")
    if errors:
        print(f"   ⚠️  {len(errors)} errors (first 3):")
        for e in errors[:3]:
            print(f"      - {e}")

    # --- Step 4: Trigger matching ---
    if imported > 0:
        print(f"\n🤖 Triggering auto-matching on {imported} jobs... ", end="", flush=True)
        try:
            match_resp = requests.post(
                f"{api_url}/jobs/search",
                json={
                    "filters": {
                        "primary_titles": [args.search],
                        "sources": ["jobbank"],
                    },
                    "max_results_per_source": imported,
                },
                timeout=300,
            )
            if match_resp.status_code == 200:
                match_data = match_resp.json().get("data", {})
                matched = sum(1 for j in match_data.get("jobs", []) if j.get("match_score") is not None)
                print(f"✅ {matched} jobs matched")
            else:
                print(f"⚠️  Matching triggered but returned HTTP {match_resp.status_code} — "
                      f"matching will happen automatically on next search")
        except Exception as e:
            print(f"⚠️  Matching attempt failed: {e}")
    else:
        print("\n⚠️  No new jobs to match")

    # --- Summary ---
    print(f"\n{'='*60}")
    print(f"✅ Done! {imported} Indeed jobs added to Railway.")
    print(f"   Refresh your Job Search page to see them.")
    print(f"{'='*60}\n")


def pd_notna(row, key):
    """Safe pandas not-na check."""
    try:
        import pandas as pd
        val = row.get(key)
        return val is not None and pd.notna(val)
    except Exception:
        return False


if __name__ == "__main__":
    main()