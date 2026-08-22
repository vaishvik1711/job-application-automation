"""
Local LinkedIn scraper — scrapes LinkedIn from YOUR machine/network and sends fresh, relevant jobs to Railway/Backend.

Why this works:
  1. Local/residential IP avoids datacenter IP blocks (HTTP 429/999).
  2. Uses anti-bot header rotation, jitter delays, and freshness filters (24h/7d).
  3. Relevance filtering ensures off-topic sponsored posts are stripped.
  4. Uploads jobs via /jobs/bulk-import and triggers automated candidate matching.

Usage:
  # Fresh jobs from past 24 hours
  python run_linkedin_scraper.py --search "Data Analyst" --location "Toronto, ON" --hours-old 24 --limit 25

  # Remote Canada jobs from past 7 days
  python run_linkedin_scraper.py --search "Full Stack Developer" --location "Remote Canada" --remote --limit 30

  # Target custom backend (local or production)
  python run_linkedin_scraper.py --search "Business Analyst" --api-url "http://localhost:8000"

Requires: pip install python-jobspy requests beautifulsoup4
"""
import argparse
import json
import random
import re
import sys
import time
from datetime import datetime
from urllib.parse import quote_plus

try:
    import requests
except ImportError:
    print("ERROR: requests is required. Run: pip install requests")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: beautifulsoup4 is required. Run: pip install beautifulsoup4")
    sys.exit(1)

RAILWAY_URL = "https://job-application-automation-production.up.railway.app"

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Stealth scraper for fresh and relevant LinkedIn jobs")
    parser.add_argument("--search", default="Data Analyst", help="Job search term (default: Data Analyst)")
    parser.add_argument("--location", default="Ontario, Canada", help="Location (default: Ontario, Canada)")
    parser.add_argument("--limit", type=int, default=25, help="Max results (default: 25)")
    parser.add_argument("--hours-old", type=int, default=168, help="Max hours since posting: 24=1 day, 72=3 days, 168=7 days (default: 168)")
    parser.add_argument("--remote", action="store_true", help="Filter for remote jobs only")
    parser.add_argument("--api-url", default=RAILWAY_URL, help=f"Backend URL (default: {RAILWAY_URL})")
    parser.add_argument("--no-match", action="store_true", help="Skip triggering automated matching after import")
    return parser.parse_args()


def get_random_headers():
    ua = random.choice(USER_AGENTS)
    is_mac = "Macintosh" in ua
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"' if is_mac else '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Referer": "https://www.linkedin.com/jobs/search/",
    }


def is_relevant(title: str, search_query: str) -> bool:
    """Filter out irrelevant sponsored ads and off-topic job cards."""
    if not title or not search_query:
        return True
    t_lower = title.lower()
    keywords = [k.lower().strip('"\'') for k in search_query.split() if len(k.strip('"\'')) > 2]
    if not keywords:
        return True

    # Direct keyword check
    if any(k in t_lower for k in keywords):
        return True

    # Semantic stem check
    stems = {
        "analyst": ["analytics", "analyst", "intelligence", "bi", "data", "business", "consultant"],
        "developer": ["engineer", "developer", "programmer", "software", "architect", "full stack"],
        "scientist": ["science", "scientist", "researcher", "ml", "ai", "machine learning"],
    }
    for k in keywords:
        if k in stems and any(alias in t_lower for alias in stems[k]):
            return True

    return False


def parse_relative_date(text: str):
    """Parse relative date string like '1 day ago', '3 hours ago', '2 weeks ago'."""
    if not text:
        return None
    text_lower = text.lower().strip()
    now = datetime.utcnow()
    try:
        m = re.search(r"(\d+)\s*(minute|hour|day|week|month|year)", text_lower)
        if not m:
            if "today" in text_lower or "just now" in text_lower:
                return now.isoformat()
            if "yesterday" in text_lower:
                return (now - timedelta(days=1)).isoformat()
            return None
        val = int(m.group(1))
        unit = m.group(2)
        if "minute" in unit:
            return (now - timedelta(minutes=val)).isoformat()
        if "hour" in unit:
            return (now - timedelta(hours=val)).isoformat()
        if "day" in unit:
            return (now - timedelta(days=val)).isoformat()
        if "week" in unit:
            return (now - timedelta(weeks=val)).isoformat()
        if "month" in unit:
            return (now - timedelta(days=val * 30)).isoformat()
        if "year" in unit:
            return (now - timedelta(days=val * 365)).isoformat()
    except Exception:
        pass
    return None


def scrape_linkedin_guest(search: str, location: str, limit: int, hours_old: int, remote: bool):
    """Direct scraping of LinkedIn Guest Jobs endpoint with anti-blocking defenses."""
    jobs = []
    seen = set()
    start = 0
    page_size = 10
    max_pages = max(1, (limit + page_size - 1) // page_size)
    f_tpr = f"r{hours_old * 3600}"

    session = requests.Session()
    session.headers.update(get_random_headers())

    # Warm-up request
    try:
        session.get("https://www.linkedin.com/jobs/search", timeout=10)
    except Exception:
        pass

    for page in range(max_pages):
        if len(jobs) >= limit:
            break

        url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        params = {
            "keywords": search,
            "location": location,
            "start": str(start),
            "f_TPR": f_tpr,
        }
        if remote:
            params["f_WT"] = "2"

        print(f"   Fetching page {page+1} (offset {start})... ", end="", flush=True)

        resp = None
        for attempt in range(3):
            try:
                resp = session.get(url, params=params, headers=get_random_headers(), timeout=20)
                if resp.status_code == 200:
                    break
                elif resp.status_code in (429, 999):
                    wait = (attempt + 1) * 3 + random.uniform(1, 2)
                    print(f"[Rate-limit 429: wait {wait:.1f}s] ", end="", flush=True)
                    time.sleep(wait)
            except Exception as e:
                time.sleep(2)

        if not resp or resp.status_code != 200:
            print("❌ Failed or challenged")
            break

        # Near-empty 200 response signals no more results
        if len(resp.text.strip()) < 200:
            print("⚠️  No more results (end of pagination)")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.find_all("li")
        if not cards:
            print("⚠️  No cards found")
            break

        page_count = 0
        for card in cards:
            title_elem = (
                card.find(class_="base-search-card__title")
                or card.find("h3")
                or card.find("span", class_="sr-only")
            )
            title = title_elem.get_text(strip=True) if title_elem else ""

            link_elem = (
                card.find("a", class_="base-card__full-link")
                or card.find("a", href=re.compile(r"/jobs/view/"))
                or card.find("a")
            )
            href = link_elem.get("href", "") if link_elem else ""

            if not title or not href:
                continue

            if not is_relevant(title, search):
                continue

            # URN / Href ID extraction
            urn_elem = card.find(attrs={"data-entity-urn": True})
            urn = urn_elem.get("data-entity-urn", "") if urn_elem else ""
            
            posting_id = None
            if urn:
                urn_match = re.search(r"(\d{6,})", urn)
                if urn_match:
                    posting_id = urn_match.group(1)

            if not posting_id and href:
                href_match = re.search(r"/jobs/view/(?:[^/?#]*?-)?(\d{6,})", href)
                if href_match:
                    posting_id = href_match.group(1)

            if not posting_id:
                id_match = re.search(r"view/(\d+)", href) or re.search(r"-(\d+)(?:\?|$)", href)
                posting_id = id_match.group(1) if id_match else href.split("?")[0]

            job_url = f"https://www.linkedin.com/jobs/view/{posting_id}/" if posting_id and posting_id.isdigit() else href.split("?")[0]

            if job_url in seen:
                continue
            seen.add(job_url)

            # Company
            sub_elem = card.find(class_="base-search-card__subtitle") or card.find("h4")
            company = sub_elem.get_text(strip=True) if sub_elem else "Unknown"

            # Location
            loc_elem = card.find(class_="job-search-card__location")
            loc = loc_elem.get_text(strip=True) if loc_elem else location

            # Salary
            salary_elem = card.find(class_="job-search-card__salary-info")
            salary = salary_elem.get_text(strip=True) if salary_elem else None

            # Date posted
            time_elem = card.find("time")
            posted_at = None
            if time_elem:
                dt_attr = time_elem.get("datetime")
                if dt_attr:
                    posted_at = dt_attr
                else:
                    posted_at = parse_relative_date(time_elem.get_text(strip=True))

            remote_type = "remote" if remote or "remote" in (loc + " " + title).lower() else "on_site"
            is_easy_apply = bool(re.search(r"easy apply", card.get_text(), re.I))

            desc_parts = [f"{title} at {company} in {loc}."]
            if salary:
                desc_parts.append(f"Salary: {salary}.")
            if is_easy_apply:
                desc_parts.append("Supports LinkedIn Easy Apply.")
            desc_parts.append("Discover and apply on LinkedIn.")

            job = {
                "title": title,
                "company": company,
                "location": loc,
                "description": " ".join(desc_parts),
                "url": job_url,
                "source_job_id": str(posting_id),
                "currency": "CAD",
                "remote_type": remote_type,
                "employment_type": "full_time",
                "source": "linkedin",
                "date_posted": posted_at,
            }
            jobs.append(job)
            page_count += 1

            if len(jobs) >= limit:
                break

        print(f"✅ {page_count} fresh jobs parsed")
        
        if len(cards) < page_size:
            break

        start += len(cards)
        time.sleep(random.uniform(0.8, 1.8))

    return jobs


def scrape_linkedin_jobspy(search: str, location: str, limit: int, hours_old: int):
    """Fallback scraping using python-jobspy with stealth flags."""
    try:
        from jobspy import scrape_jobs
    except ImportError:
        return []

    print("   Running JobSpy engine in stealth mode... ", end="", flush=True)
    try:
        jobs_df = scrape_jobs(
            site_name=["linkedin"],
            search_term=search,
            location=location,
            results_wanted=limit,
            hours_old=hours_old,
            linkedin_fetch_description=False,  # Stealth mode
        )
    except Exception as e:
        print(f"❌ JobSpy failed: {e}")
        return []

    if jobs_df is None or jobs_df.empty:
        print("⚠️  No jobs found")
        return []

    jobs = []
    for _, row in jobs_df.iterrows():
        def safe(v):
            return str(v).strip() if v is not None and not (hasattr(v, "empty") and v.empty) else ""

        title = safe(row.get("title"))
        company = safe(row.get("company"))
        job_url = safe(row.get("job_url"))
        if not title or not company or not job_url:
            continue
        if not is_relevant(title, search):
            continue

        jobs.append({
            "title": title,
            "company": company,
            "location": safe(row.get("location")) or location,
            "description": safe(row.get("description")) or f"{title} at {company} (LinkedIn)",
            "url": job_url,
            "source_job_id": safe(row.get("job_id")) or job_url,
            "currency": "CAD",
            "remote_type": "remote" if "remote" in (safe(row.get("location")) + " " + title).lower() else "on_site",
            "employment_type": "full_time",
            "source": "linkedin",
        })

    print(f"✅ {len(jobs)} jobs extracted via JobSpy")
    return jobs


def main():
    args = parse_args()

    print(f"\n{'='*65}")
    print(f"🔍 Stealth LinkedIn Scraper")
    print(f"🎯 Role: {args.search}")
    print(f"📍 Location: {args.location} {'[REMOTE ONLY]' if args.remote else ''}")
    print(f"⏱️  Freshness: Past {args.hours_old} hours ({args.hours_old/24:.1f} days)")
    print(f"📊 Target limit: {args.limit}")
    print(f"{'='*65}\n")

    start_time = time.time()
    print("🚀 Scraping LinkedIn (Direct Guest API Engine)...")
    jobs = scrape_linkedin_guest(
        search=args.search,
        location=args.location,
        limit=args.limit,
        hours_old=args.hours_old,
        remote=args.remote,
    )

    # Fallback to JobSpy if direct engine had zero results
    if not jobs:
        print("⚠️  Direct engine returned 0 results. Trying JobSpy fallback...")
        jobs = scrape_linkedin_jobspy(
            search=args.search,
            location=args.location,
            limit=args.limit,
            hours_old=args.hours_old,
        )

    elapsed = time.time() - start_time

    if not jobs:
        print(f"\n⚠️  No relevant LinkedIn jobs found in {elapsed:.1f}s. Try widening search terms or location.")
        return

    # Deduplicate
    seen_urls = set()
    unique_jobs = []
    for j in jobs:
        if j["url"] not in seen_urls:
            seen_urls.add(j["url"])
            unique_jobs.append(j)

    print(f"\n✅ Total fresh & relevant jobs discovered: {len(unique_jobs)} (in {elapsed:.1f}s)")

    # Upload to Backend API
    api_url = args.api_url.rstrip("/")
    print(f"\n📤 Uploading to {api_url}/jobs/bulk-import ... ", end="", flush=True)

    try:
        resp = requests.post(
            f"{api_url}/jobs/bulk-import",
            json={"jobs": unique_jobs, "source": "linkedin"},
            timeout=120,
        )
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to backend at {api_url}")
        print("   Make sure the server is online or check status at https://railway.app")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Upload error: {e}")
        sys.exit(1)

    if resp.status_code not in (200, 201):
        print(f"❌ Backend returned HTTP {resp.status_code}: {resp.text[:300]}")
        sys.exit(1)

    res_json = resp.json()
    data = res_json.get("data", {})
    imported = data.get("imported", 0)
    total = data.get("total", 0)
    print(f"✅ {imported}/{total} jobs imported successfully!")

    # Auto-match
    if not args.no_match and imported > 0:
        print(f"\n🤖 Triggering AI candidate matching on {imported} jobs... ", end="", flush=True)
        try:
            m_resp = requests.post(
                f"{api_url}/jobs/search",
                json={
                    "filters": {
                        "primary_titles": [args.search],
                        "sources": ["linkedin", "jobbank"],
                    },
                    "max_results_per_source": imported,
                },
                timeout=180,
            )
            if m_resp.status_code == 200:
                print("✅ AI matching triggered!")
            else:
                print(f"⚠️  Matching queued (HTTP {m_resp.status_code})")
        except Exception as e:
            print(f"⚠️  Matching request notice: {e}")

    print(f"\n{'='*65}")
    print(f"🎉 Complete! {imported} fresh LinkedIn jobs added.")
    print(f"   View and inspect your matches on the web app at: /jobs")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
