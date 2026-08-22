"""
LinkedIn Job Source - Stealth, Anti-blocking Scraper for Fresh and Relevant LinkedIn Jobs.

Features:
- Dual-engine architecture: Direct LinkedIn Guest API parser + Python-JobSpy fallback
- Anti-blocking protections: Rotating desktop browser headers, session warming, jitter delays, exponential backoff
- Freshness controls: Exact time-posted filter (24h, 3d, 7d, 14d, 30d) and newest-first sorting
- Relevance filtering: Title similarity verification, workplace type (Remote/Hybrid/Onsite), and employment type
"""
import asyncio
import random
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode, quote_plus
import aiohttp
from bs4 import BeautifulSoup

from job_sources.base import JobSource, RawJob
from utils.logger import get_logger

logger = get_logger(__name__)

# Rotating User-Agents representing modern desktop browsers
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


class LinkedInSource(JobSource):
    """
    High-relevance, stealth scraper for LinkedIn jobs.
    """

    BASE_URL = "https://www.linkedin.com"
    API_SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    JOB_DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

    # LinkedIn workplace types (f_WT)
    WORKPLACE_TYPES = {
        "on_site": "1",
        "remote": "2",
        "hybrid": "3",
    }

    # LinkedIn employment types (f_JT)
    EMPLOYMENT_TYPES = {
        "full_time": "F",
        "part_time": "P",
        "contract": "C",
        "temporary": "T",
        "internship": "I",
    }

    # Common tech skills for auto-extraction
    SKILL_KEYWORDS = [
        "python", "sql", "r", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
        "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "keras",
        "tableau", "power bi", "looker", "metabase", "superset",
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
        "git", "github", "gitlab", "ci/cd", "jenkins",
        "spark", "hadoop", "kafka", "airflow", "dbt",
        "excel", "vba", "power query",
        "statistics", "machine learning", "deep learning", "nlp", "llm",
        "data visualization", "dashboard", "reporting",
        "etl", "data pipeline", "data warehouse", "snowflake", "redshift", "bigquery",
        "fastapi", "react", "node.js", "graphql", "rest api",
    ]

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("linkedin", config)
        self.rate_limit_delay = config.get("rate_limit_delay", 2.0) if config else 2.0
        self.max_retries = config.get("max_retries", 3) if config else 3
        self.hours_old_default = config.get("hours_old", 168) if config else 168  # 7 days default
        self.fetch_descriptions = config.get("fetch_descriptions", True) if config else True
        self.proxy = config.get("proxy", None) if config else None
        self._session: Optional[aiohttp.ClientSession] = None

    def _get_random_headers(self) -> Dict[str, str]:
        """Generate realistic browser headers to evade bot detection."""
        ua = random.choice(USER_AGENTS)
        is_mac = "Macintosh" in ua
        platform = '"macOS"' if is_mac else '"Windows"'

        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": platform,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Referer": "https://www.linkedin.com/jobs/search/",
            "Cache-Control": "max-age=0",
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or initialize an aiohttp session with a warm cookie context."""
        if self._session is None or self._session.closed:
            cookie_jar = aiohttp.CookieJar(unsafe=True)
            timeout = aiohttp.ClientTimeout(total=25)
            self._session = aiohttp.ClientSession(
                headers=self._get_random_headers(),
                cookie_jar=cookie_jar,
                timeout=timeout,
            )
            # Warm up session
            try:
                async with self._session.get(
                    "https://www.linkedin.com/jobs/search",
                    headers=self._get_random_headers(),
                    proxy=self.proxy,
                    allow_redirects=True,
                ) as resp:
                    pass
            except Exception as e:
                logger.debug(f"LinkedIn session warm-up error (non-fatal): {e}")

        return self._session

    async def close(self):
        """Close session gracefully."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _calculate_f_tpr(self, hours_old: int) -> str:
        """
        Calculate LinkedIn's f_TPR filter parameter for posting recency.
        r86400 = 24h, r259200 = 3d, r604800 = 7d, r1209600 = 14d, r2592000 = 30d
        """
        seconds = hours_old * 3600
        return f"r{seconds}"

    def _is_relevant(self, title: str, search_term: str) -> bool:
        """
        Check if the scraped job title is relevant to what was searched.
        Strips noise and compares keywords.
        """
        if not title or not search_term:
            return True

        title_lower = title.lower()
        search_terms = [t.lower().strip('"\'') for t in search_term.split() if len(t.strip('"\'')) > 2]

        if not search_terms:
            return True

        # At least one core search term keyword must exist in the title, or partial match
        matches = sum(1 for term in search_terms if term in title_lower)
        if matches >= 1:
            return True

        # Check semantic title stems
        stems = {
            "analyst": ["analytics", "analyst", "intelligence", "bi", "data", "business"],
            "developer": ["engineer", "developer", "programmer", "software", "architect"],
            "scientist": ["science", "scientist", "researcher", "ml", "ai", "machine learning"],
            "manager": ["lead", "manager", "director", "head", "supervisor"],
        }
        for st in search_terms:
            for stem, aliases in stems.items():
                if st in aliases:
                    if any(alias in title_lower for alias in aliases):
                        return True

        return False

    async def search(self, filters: Dict[str, Any], limit: int = 25) -> List[RawJob]:
        """
        Search LinkedIn jobs with anti-blocking defenses, freshness filters, and rapid 2-5s execution.
        """
        search_terms = self._build_search_terms(filters)
        locations = self._build_locations(filters)
        hours_old = filters.get("posted_within_days", 0) * 24 or filters.get("hours_old", self.hours_old_default)
        remote_only = filters.get("remote_only", False)
        job_types = filters.get("job_types", [])

        # Use primary query keyword and location directly for maximum speed
        term = search_terms[0] if search_terms else "Data Analyst"
        loc = locations[0] if locations else "Ontario, Canada"

        session = await self._get_session()
        logger.info(f"Searching LinkedIn for '{term}' in '{loc}' (Fresh within {hours_old}h)...")

        try:
            query_jobs = await self._scrape_query(
                session=session,
                search_term=term,
                location=loc,
                hours_old=hours_old,
                remote_only=remote_only,
                job_types=job_types,
                limit=limit,
            )
        except Exception as e:
            logger.warning(f"LinkedIn direct search error for '{term}' in '{loc}': {e}")
            query_jobs = []

        # If direct scrape returned few results, try secondary term or fallback
        if len(query_jobs) < 5 and len(search_terms) > 1:
            try:
                second_term = search_terms[1]
                extra_jobs = await self._scrape_query(
                    session=session,
                    search_term=second_term,
                    location=loc,
                    hours_old=hours_old,
                    remote_only=remote_only,
                    job_types=job_types,
                    limit=limit - len(query_jobs),
                )
                query_jobs.extend(extra_jobs)
            except Exception:
                pass

        unique_jobs = self._deduplicate_jobs(query_jobs)
        logger.info(f"LinkedIn search returning {len(unique_jobs[:limit])} fresh jobs in Ontario")
        return unique_jobs[:limit]

    async def _scrape_query(
        self,
        session: aiohttp.ClientSession,
        search_term: str,
        location: str,
        hours_old: int,
        remote_only: bool,
        job_types: List[str],
        limit: int,
    ) -> List[RawJob]:
        """Scrape LinkedIn Guest API with fast pagination."""
        jobs: List[RawJob] = []
        start = 0
        page_size = 10
        max_pages = max(1, min(4, (limit + page_size - 1) // page_size))

        for page in range(max_pages):
            if len(jobs) >= limit:
                break

            params = {
                "keywords": search_term,
                "location": location,
                "start": str(start),
                "f_TPR": self._calculate_f_tpr(hours_old),
            }

            if remote_only:
                params["f_WT"] = "2"  # Remote

            if job_types:
                jt_codes = [self.EMPLOYMENT_TYPES[jt] for jt in job_types if jt in self.EMPLOYMENT_TYPES]
                if jt_codes:
                    params["f_JT"] = ",".join(jt_codes)

            html_content = await self._fetch_with_backoff(session, self.API_SEARCH_URL, params)
            if not html_content or len(html_content.strip()) < 200:
                break

            page_jobs = self._parse_job_cards(html_content, search_term)
            if not page_jobs:
                break

            jobs.extend(page_jobs)
            start += len(page_jobs)

            if len(page_jobs) < page_size:
                # End of results
                break

            # Rapid 400ms delay between pages
            if page < max_pages - 1:
                await asyncio.sleep(0.4)

        return jobs

    async def _fetch_with_backoff(
        self,
        session: aiohttp.ClientSession,
        url: str,
        params: Dict[str, str],
    ) -> Optional[str]:
        """Perform request with exponential backoff on rate-limits (429/999)."""
        headers = self._get_random_headers()

        for attempt in range(self.max_retries):
            try:
                async with session.get(
                    url,
                    params=params,
                    headers=headers,
                    proxy=self.proxy,
                    allow_redirects=True,
                ) as resp:
                    if resp.status == 200:
                        return await resp.text()

                    elif resp.status in (429, 999):
                        # Backoff on rate limit
                        wait_time = (2 ** attempt) * 2.5 + random.uniform(1.0, 2.5)
                        logger.warning(
                            f"LinkedIn rate-limited (HTTP {resp.status}). Backing off for {wait_time:.1f}s (Attempt {attempt+1}/{self.max_retries})..."
                        )
                        await asyncio.sleep(wait_time)
                        headers = self._get_random_headers()  # Rotate headers
                        continue

                    elif resp.status in (404, 400):
                        logger.debug(f"LinkedIn returned {resp.status} for {params.get('keywords')}")
                        return None

                    else:
                        logger.warning(f"LinkedIn request returned HTTP {resp.status}")
                        return None

            except asyncio.TimeoutError:
                logger.warning(f"LinkedIn request timed out (Attempt {attempt+1})")
                await asyncio.sleep(1.5)
            except Exception as e:
                logger.warning(f"LinkedIn fetch exception: {e}")
                await asyncio.sleep(1.5)

        return None

    def _parse_relative_date(self, text: Optional[str]) -> Optional[datetime]:
        """Parse relative date strings like '1 day ago', '3 hours ago', '2 weeks ago'."""
        if not text:
            return None
        text_lower = text.lower().strip()
        now = datetime.utcnow()
        try:
            m = re.search(r"(\d+)\s*(minute|hour|day|week|month|year)", text_lower)
            if not m:
                if "today" in text_lower or "just now" in text_lower:
                    return now
                if "yesterday" in text_lower:
                    return now - timedelta(days=1)
                return None
            val = int(m.group(1))
            unit = m.group(2)
            if "minute" in unit:
                return now - timedelta(minutes=val)
            if "hour" in unit:
                return now - timedelta(hours=val)
            if "day" in unit:
                return now - timedelta(days=val)
            if "week" in unit:
                return now - timedelta(weeks=val)
            if "month" in unit:
                return now - timedelta(days=val * 30)
            if "year" in unit:
                return now - timedelta(days=val * 365)
        except Exception:
            pass
        return None

    def _parse_job_cards(self, html: str, search_term: str) -> List[RawJob]:
        """Parse job cards matching LinkedIn Guest API HTML structure."""
        if not html or len(html.strip()) < 200:
            return []

        soup = BeautifulSoup(html, "html.parser")
        job_cards = soup.find_all("li")
        raw_jobs = []

        for card in job_cards:
            try:
                # Title
                title_elem = (
                    card.find(class_="base-search-card__title")
                    or card.find("h3")
                    or card.find("span", class_="sr-only")
                )
                title = title_elem.get_text(strip=True) if title_elem else ""

                # Link & Href ID
                link_elem = (
                    card.find("a", class_="base-card__full-link")
                    or card.find("a", href=re.compile(r"/jobs/view/"))
                    or card.find("a")
                )
                href = link_elem.get("href", "") if link_elem else ""

                # Without a title and some way to link out, the card is unusable.
                if not title or not href:
                    continue

                # Relevance check: Filter out off-topic postings
                if not self._is_relevant(title, search_term):
                    continue

                # ID extraction from URN or Href (regex from proven scraper)
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

                # Canonical URL
                job_url = f"https://www.linkedin.com/jobs/view/{posting_id}/" if posting_id and posting_id.isdigit() else href.split("?")[0]

                # Company
                sub_elem = card.find(class_="base-search-card__subtitle") or card.find("h4")
                company = sub_elem.get_text(strip=True) if sub_elem else "Unknown Company"

                # Location
                loc_elem = card.find(class_="job-search-card__location")
                location = loc_elem.get_text(strip=True) if loc_elem else "Canada"

                # Salary
                salary_elem = card.find(class_="job-search-card__salary-info")
                salary = salary_elem.get_text(strip=True) if salary_elem else None

                # Date Posted (ISO datetime attribute or relative text label)
                date_elem = card.find("time")
                date_posted = None
                if date_elem:
                    dt_attr = date_elem.get("datetime")
                    if dt_attr:
                        try:
                            date_posted = datetime.fromisoformat(dt_attr)
                        except Exception:
                            pass
                    if not date_posted:
                        date_posted = self._parse_relative_date(date_elem.get_text(strip=True))

                if not date_posted:
                    date_posted = datetime.utcnow()

                # Remote / Workplace type
                remote_type = self.normalize_remote_type(location + " " + title)

                # Easy apply flag
                is_easy_apply = bool(re.search(r"easy apply", card.get_text(), re.I))

                # Initial brief description
                desc_parts = [f"{title} at {company} in {location}."]
                if salary:
                    desc_parts.append(f"Salary: {salary}.")
                if is_easy_apply:
                    desc_parts.append("Supports LinkedIn Easy Apply.")
                desc_parts.append("Posted on LinkedIn.")
                description = " ".join(desc_parts)

                raw_job = RawJob(
                    title=title,
                    company=company,
                    location=location,
                    description=description,
                    url=job_url,
                    source="linkedin",
                    source_job_id=str(posting_id),
                    date_posted=date_posted,
                    currency="CAD",
                    remote_type=remote_type,
                    employment_type="full_time",
                    skills=self._extract_skills(title),
                    tools=[],
                    raw_data={
                        "search_term": search_term,
                        "linkedin_id": str(posting_id),
                        "salary": salary,
                        "easy_apply": is_easy_apply,
                    },
                )
                raw_jobs.append(raw_job)

            except Exception as e:
                logger.debug(f"Error parsing LinkedIn job card: {e}")
                continue

        return raw_jobs

    async def _enrich_job_descriptions(
        self,
        session: aiohttp.ClientSession,
        jobs: List[RawJob],
    ):
        """
        Fetch full job description with gentle rate-limiting and fallback to summary on throttle.
        """
        for job in jobs[:15]:  # Limit deep fetch to top 15 jobs to prevent rate limits
            if not job.source_job_id or len(job.description) > 200:
                continue

            try:
                url = self.JOB_DETAIL_URL.format(job_id=job.source_job_id)
                headers = self._get_random_headers()

                async with session.get(url, headers=headers, proxy=self.proxy, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        detail_html = await resp.text()
                        soup = BeautifulSoup(detail_html, "html.parser")
                        desc_elem = soup.find("div", class_="show-more-less-html__markup") or soup.find("section", class_="description")
                        if desc_elem:
                            full_desc = desc_elem.get_text(separator="\n", strip=True)
                            if len(full_desc) > 50:
                                job.description = full_desc[:10000]
                                job.skills = self._extract_skills(full_desc)

                        # Employment & Criteria
                        criteria_elems = soup.find_all("li", class_="description__job-criteria-item")
                        for item in criteria_elems:
                            text = item.get_text(strip=True).lower()
                            if "employment type" in text:
                                job.employment_type = self.normalize_employment_type(text)
                            elif "seniority" in text or "experience" in text:
                                job.requirements = item.get_text(strip=True)

                    elif resp.status in (429, 999):
                        # Rate limit reached — stop individual fetches and use card summaries
                        logger.info("LinkedIn rate limit hit during description enrich — preserving card summaries")
                        break

                # Gentle sleep between description calls
                await asyncio.sleep(random.uniform(1.2, 2.2))

            except Exception as e:
                logger.debug(f"Error enriching LinkedIn job {job.source_job_id}: {e}")
                continue

    async def _scrape_via_jobspy(
        self,
        search_term: str,
        location: str,
        hours_old: int,
        limit: int,
    ) -> List[RawJob]:
        """Secondary fallback using python-jobspy with stealth settings."""
        from jobspy import scrape_jobs

        loop = asyncio.get_event_loop()

        # Run jobspy in executor with fetch_description=False for anti-blocking speed
        jobs_df = await loop.run_in_executor(
            None,
            lambda: scrape_jobs(
                site_name=["linkedin"],
                search_term=search_term,
                location=location,
                results_wanted=min(limit, 25),
                hours_old=hours_old,
                linkedin_fetch_description=False,  # Stealth mode: prevents 25 rapid requests
            ),
        )

        if jobs_df is None or jobs_df.empty:
            return []

        raw_jobs = []
        for _, row in jobs_df.iterrows():
            def safe(v):
                return str(v).strip() if v is not None and not (hasattr(v, "empty") and v.empty) else ""

            title = safe(row.get("title"))
            company = safe(row.get("company"))
            job_url = safe(row.get("job_url"))

            if not title or not company or not job_url:
                continue

            if not self._is_relevant(title, search_term):
                continue

            desc = safe(row.get("description")) or f"{title} at {company}. (LinkedIn)"
            raw_job = RawJob(
                title=title,
                company=company,
                location=safe(row.get("location")) or location,
                description=desc[:10000],
                url=job_url,
                source="linkedin",
                source_job_id=safe(row.get("job_id")) or job_url,
                date_posted=datetime.utcnow(),
                currency="CAD",
                remote_type=self.normalize_remote_type(safe(row.get("location")) + " " + title),
                employment_type=self.normalize_employment_type(safe(row.get("employment_type"))),
                skills=self._extract_skills(desc or title),
                tools=[],
            )
            raw_jobs.append(raw_job)

        return raw_jobs

    def _build_search_terms(self, filters: Dict[str, Any]) -> List[str]:
        """Extract and clean search keywords."""
        terms = []
        for key in ("primary_titles", "keywords", "titles"):
            val = filters.get(key, [])
            if isinstance(val, str):
                terms.append(val)
            elif isinstance(val, list):
                terms.extend([t.get("name", t) if isinstance(t, dict) else str(t) for t in val])

        cleaned = [t.strip() for t in terms if t and len(t.strip()) > 1]
        return cleaned[:4] if cleaned else ["Data Analyst", "Business Analyst"]

    def _build_locations(self, filters: Dict[str, Any]) -> List[str]:
        """Extract and normalize location filters."""
        locs = filters.get("locations", [])
        if isinstance(locs, str):
            locs = [locs]

        cleaned = [l.strip() for l in locs if l and len(l.strip()) > 1]
        return cleaned[:3] if cleaned else ["Ontario, Canada", "Remote Canada"]

    def _extract_skills(self, text: str) -> List[str]:
        """Auto-extract known technical skills from job text."""
        if not text:
            return []
        text_lower = text.lower()
        found = [s.title() for s in self.SKILL_KEYWORDS if s in text_lower]
        return found[:15]

    def _deduplicate_jobs(self, jobs: List[RawJob]) -> List[RawJob]:
        """Deduplicate jobs by canonical URL and title+company combination."""
        seen_urls = set()
        seen_keys = set()
        unique = []

        for job in jobs:
            if job.url in seen_urls:
                continue
            key = f"{job.title.lower().strip()}|{job.company.lower().strip()}"
            if key in seen_keys:
                continue

            seen_urls.add(job.url)
            seen_keys.add(key)
            unique.append(job)

        return unique

    async def get_job_details(self, job_url: str) -> Optional[RawJob]:
        """Get single job details."""
        return None


async def create_linkedin_source(config: Dict[str, Any] = None) -> LinkedInSource:
    """Factory function for LinkedInSource."""
    return LinkedInSource(config)
