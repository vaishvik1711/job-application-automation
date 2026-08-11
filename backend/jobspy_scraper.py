#!/usr/bin/env python3
"""
Method 1: Multi-Platform Scraping via python-jobspy
Scrapes job postings from LinkedIn, Indeed, and ZipRecruiter for "Data Analyst" roles in Canada.
"""

import pandas as pd
from jobspy import scrape_jobs
import sys
import traceback


def main():
    # Configuration parameters
    search_term = "Data Analyst"
    location = "Canada"
    results_wanted = 10
    site_names = ["linkedin", "indeed", "zip_recruiter"]

    print(f"🔍 Searching for '{search_term}' in '{location}' across {site_names}...")
    print(f"   Target results: {results_wanted}")
    print("-" * 60)

    try:
        # Scrape jobs with jobspy
        jobs = scrape_jobs(
            site_name=site_names,
            search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            hours_old=720,  # Last 30 days
            country_indeed="Canada",  # Specific for Indeed
            linkedin_fetch_description=True,  # Get full descriptions from LinkedIn
        )

        if jobs is None or jobs.empty:
            print("❌ No jobs found!")
            return

        # Select required columns (handle missing columns gracefully)
        required_columns = ['site', 'title', 'company', 'location', 'job_url', 'description']
        available_columns = [col for col in required_columns if col in jobs.columns]
        missing_columns = [col for col in required_columns if col not in jobs.columns]

        if missing_columns:
            print(f"⚠️  Missing columns (will be filled with N/A): {missing_columns}")
            for col in missing_columns:
                jobs[col] = "N/A"

        # Select and reorder columns
        jobs_output = jobs[required_columns].copy()

        # Export to CSV
        output_file = "jobspy_results.csv"
        jobs_output.to_csv(output_file, index=False)
        print(f"✅ Exported {len(jobs_output)} jobs to '{output_file}'")

        # Print summary
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        print(f"Total jobs found: {len(jobs_output)}")
        print(f"Sources: {jobs_output['site'].value_counts().to_dict()}")
        print(f"\nColumns: {list(jobs_output.columns)}")

        # Print first job description preview (first 200 chars)
        if len(jobs_output) > 0:
            first_desc = jobs_output.iloc[0]['description']
            if pd.notna(first_desc) and first_desc != "N/A":
                preview = str(first_desc)[:200]
                print(f"\n📝 First job description preview (200 chars):")
                print(f"   {preview}...")
            else:
                print("\n📝 First job description: Not available")

        # Show first few rows
        print("\n📋 First 3 jobs:")
        for idx, row in jobs_output.head(3).iterrows():
            print(f"   {idx+1}. [{row['site']}] {row['title']} at {row['company']} - {row['location']}")
            print(f"      URL: {row['job_url']}")

    except Exception as e:
        print(f"❌ Error during scraping: {type(e).__name__}: {e}")
        print("\n🔍 Full traceback:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()