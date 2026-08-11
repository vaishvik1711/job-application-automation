"""
JobBank (Canada Government Job Bank) source.
This is a public API source - no authentication required for basic search.
"""
import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode, quote_plus

from job_sources.base import JobSource, RawJob
from utils.logger import get_logger


logger = get_logger(__name__)


class JobBankSource(JobSource):
    """
    JobBank (Canada Government Job Bank) source.

    Uses the public Job Bank API / search interface.
    No authentication required for basic search.
    """

    BASE_URL = "https://www.jobbank.gc.ca"
    SEARCH_PATH = "/jobsearch/jobsearch"

    # NOC codes for common tech roles
    NOC_CODES = {
        "software engineer": "21230",
        "software developer": "21230",
        "web developer": "21232",
        "data analyst": "21223",
        "data scientist": "21211",
        "devops engineer": "21230",
        "backend developer": "21230",
        "frontend developer": "21232",
        "full stack developer": "21230",
        "machine learning engineer": "21211",
        "mobile developer": "21230",
        "cloud engineer": "21230",
        "site reliability engineer": "21230",
        "api developer": "21230",
        "systems engineer": "21230",
        "database administrator": "21223",
        "network engineer": "21230",
        "security analyst": "21220",
        "qa engineer": "21230",
        "test engineer": "21230",
    }

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("jobbank", config)
        self.rate_limit = config.get("rate_limit", 1.0) if config else 1.0
        self.max_pages = config.get("max_pages", 10) if config else 10
        self._last_request = 0.0
        self._session = None

    async def _get_session(self):
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            import aiohttp
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-CA,en;q=0.9",
            }
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self._session

    async def _rate_limit(self):
        """Enforce rate limiting."""
        import time
        elapsed = time.time() - self._last_request
        if elapsed < (1.0 / self.rate_limit):
            await asyncio.sleep((1.0 / self.rate_limit) - elapsed)
        self._last_request = time.time()

    def _build_search_url(self, filters: Dict[str, Any], page: int = 1) -> str:
        """Build JobBank search URL."""
        params = {}

        # Build keyword from titles and skills
        keywords = []
        if filters.get("primary_titles"):
            keywords.extend(filters["primary_titles"][:2])
        if filters.get("strong_skills"):
            keywords.extend(filters["strong_skills"][:3])

        if keywords:
            params["searchstring"] = " ".join(keywords)

        # Location
        if filters.get("locations"):
            params["locationstring"] = filters["locations"][0]

        # NOC codes from titles
        noc_codes = set()
        for title in (filters.get("primary_titles", []) + filters.get("secondary_titles", [])):
            noc = self._get_noc_code(title)
            if noc:
                noc_codes.add(noc)
        if noc_codes:
            params["noc"] = ",".join(noc_codes)

        # Job type
        if "Full-time" in filters.get("employment_types", []):
            params["jobtype"] = "fulltime"

        # Date posted - last 30 days
        params["sort"] = "D"  # Date

        # Pagination
        params["page"] = str(page)

        return f"{self.BASE_URL}{self.SEARCH_PATH}?{urlencode(params)}"

    def _get_noc_code(self, title: str) -> Optional[str]:
        """Get NOC code for a job title."""
        title_lower = title.lower()
        for key, noc in self.NOC_CODES.items():
            if key in title_lower:
                return noc
        return None

    async def search(self, filters: Dict[str, Any], limit: int = 50) -> List[RawJob]:
        """Search JobBank for jobs."""
        jobs = []
        session = await self._get_session()

        for page in range(1, self.max_pages + 1):
            if len(jobs) >= limit:
                break

            url = self._build_search_url(filters, page)

            try:
                await self._rate_limit()

                async with session.get(url) as response:
                    if response.status != 200:
                        logger.warning(f"JobBank search returned status {response.status}")
                        break

                    html = await response.text()
                    page_jobs = self._parse_search_results(html)

                    if not page_jobs:
                        break

                    for job in page_jobs:
                        if self._matches_filters(job, filters):
                            jobs.append(job)
                            if len(jobs) >= limit:
                                break

                    logger.info(f"JobBank page {page}: found {len(page_jobs)} jobs, total: {len(jobs)}")

            except Exception as e:
                logger.error(f"Error scraping JobBank page {page}: {e}")
                break

        return jobs[:limit]

    def _parse_search_results(self, html: str) -> List[RawJob]:
        """Parse job listings from JobBank search results."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        # JobBank uses action-buttons class for job cards
        job_cards = soup.find_all("article", class_="action-buttons")

        for card in job_cards:
            try:
                # Title and link
                title_elem = card.find("span", class_="noctitle")
                link_elem = card.find("a", class_="resultJobItem")

                title = title_elem.get_text(strip=True) if title_elem else "Unknown"
                job_url = self.BASE_URL + link_elem["href"] if link_elem and link_elem.get("href") else ""

                # Company, location, date, salary from ul li elements
                ul = card.find("ul")
                company = "Unknown"
                location = "Unknown"
                date_posted = None
                salary_text = ""
                source_text = ""

                if ul:
                    for li in ul.find_all("li"):
                        classes = li.get("class", [])
                        text = li.get_text(strip=True)
                        if not classes:
                            continue
                        class_name = classes[0]
                        if class_name == "business":
                            company = text
                        elif class_name == "location":
                            # Clean up "LocationSherbrooke (QC)" -> "Sherbrooke, QC"
                            location = text.replace("Location", "").strip()
                        elif class_name == "date":
                            date_posted = self._parse_date(text)
                        elif class_name == "salary":
                            salary_text = text
                        elif class_name == "source":
                            source_text = text

                salary_min, salary_max = self._parse_salary(salary_text)

                # Description snippet - try to get from the card
                desc_elem = card.find("div", class_="description")
                description = desc_elem.get_text(strip=True) if desc_elem else ""

                if title != "Unknown" and company != "Unknown":
                    jobs.append(RawJob(
                        title=title,
                        company=company,
                        location=location,
                        description=description,
                        url=job_url,
                        source="jobbank",
                        source_job_id=job_url.split("/")[-1].split(";")[0].split("?")[0] if job_url else "",
                        date_posted=date_posted,
                        salary_min=salary_min,
                        salary_max=salary_max,
                        currency="CAD",
                        remote_type=self._detect_remote_type(description, location),
                        employment_type="full_time",
                        skills=[],
                        tools=[],
                        raw_data={"source_site": source_text},
                    ))
            except Exception as e:
                logger.debug(f"Error parsing JobBank job card: {e}")
                continue

        return jobs

    def _parse_salary(self, salary_text: str) -> tuple:
        """Parse salary from text."""
        if not salary_text:
            return None, None

        # JobBank uses formats like "$50,000 - $80,000 per year" or "$30 - $50 per hour"
        salary_text = salary_text.lower().replace(",", "")
        numbers = re.findall(r"[\d.]+", salary_text)

        if not numbers:
            return None, None

        nums = [float(n) for n in numbers]
        if len(nums) >= 2:
            if "hour" in salary_text:
                # Convert hourly to annual (assuming 2080 hours/year)
                return int(nums[0] * 2080), int(nums[1] * 2080)
            return int(nums[0]), int(nums[1])
        elif len(nums) == 1:
            val = int(nums[0])
            if "hour" in salary_text:
                return val * 2080, val * 2080
            return val, val
        return None, None

    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """Parse JobBank date format."""
        if not date_text:
            return None

        date_text = date_text.lower().strip()
        now = datetime.now()

        # Formats: "Posted 2 days ago", "Posted on 2024-01-15", "Today"
        if "today" in date_text:
            return now
        elif "yesterday" in date_text:
            return now - timedelta(days=1)
        elif "day" in date_text:
            match = re.search(r"(\d+)\s*day", date_text)
            if match:
                return now - timedelta(days=int(match.group(1)))
        elif "week" in date_text:
            match = re.search(r"(\d+)\s*week", date_text)
            if match:
                return now - timedelta(weeks=int(match.group(1)))
        elif "posted on" in date_text:
            # Try to parse date
            match = re.search(r"(\d{4}-\d{2}-\d{2})", date_text)
            if match:
                try:
                    return datetime.strptime(match.group(1), "%Y-%m-%d")
                except ValueError:
                    pass

        return now

    def _detect_remote_type(self, description: str, location: str) -> str:
        """Detect remote type."""
        text = f"{description} {location}".lower()
        if "remote" in text or "work from home" in text or "telework" in text:
            return "remote"
        elif "hybrid" in text:
            return "hybrid"
        return "on_site"

    def _matches_filters(self, job: RawJob, filters: Dict[str, Any]) -> bool:
        """Check if job matches filters."""
        negative_keywords = filters.get("negative_keywords", [])
        job_text = f"{job.title} {job.description} {job.company}".lower()
        for neg in negative_keywords:
            if neg.lower() in job_text:
                return False
        return True

    async def get_job_details(self, job_url: str) -> Optional[RawJob]:
        """Get detailed job information from JobBank."""
        if not job_url:
            return None

        session = await self._get_session()

        try:
            await self._rate_limit()
            async with session.get(job_url) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                return self._parse_job_details(html, job_url)
        except Exception as e:
            logger.error(f"Error getting JobBank job details: {e}")
            return None

    def _parse_job_details(self, html: str, url: str) -> RawJob:
        """Parse full job details from JobBank job page."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        # Title
        title_elem = soup.find("h1", class_="job-title")
        if not title_elem:
            title_elem = soup.find("h1", id="jobTitle")
        title = title_elem.get_text(strip=True) if title_elem else "Unknown"

        # Company
        company_elem = soup.find("span", class_="business-name")
        if not company_elem:
            company_elem = soup.find("div", class_="employer-name")
        company = company_elem.get_text(strip=True) if company_elem else "Unknown"

        # Location
        location_elem = soup.find("span", class_="job-location")
        if not location_elem:
            location_elem = soup.find("div", class_="location")
        location = location_elem.get_text(strip=True) if location_elem else "Unknown"

        # Description
        desc_elem = soup.find("div", class_="job-description")
        if not desc_elem:
            desc_elem = soup.find("div", id="jobDescription")
        description = desc_elem.get_text(strip=True) if desc_elem else ""

        # Salary
        salary_elem = soup.find("span", class_="salary")
        if not salary_elem:
            salary_elem = soup.find("div", class_="salary-range")
        salary_text = salary_elem.get_text(strip=True) if salary_elem else ""
        salary_min, salary_max = self._parse_salary(salary_text)

        # Skills from description
        skills = self._extract_skills(description)

        return RawJob(
            title=title,
            company=company,
            location=location,
            description=description,
            url=url,
            source="jobbank",
            source_job_id=url.split("/")[-1].split("?")[0],
            salary_min=salary_min,
            salary_max=salary_max,
            currency="CAD",
            remote_type=self._detect_remote_type(description, location),
            employment_type="full_time",
            skills=skills,
            tools=[],
            raw_data={},
        )

    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from job description."""
        common_skills = [
            "Python", "JavaScript", "TypeScript", "React", "Node.js", "FastAPI",
            "Django", "PostgreSQL", "MongoDB", "Redis", "AWS", "Docker",
            "Kubernetes", "Git", "CI/CD", "SQL", "NoSQL", "REST APIs",
            "GraphQL", "Microservices", "Terraform", "GitHub Actions", "GitLab CI",
            "Prometheus", "Grafana", "Datadog", "Elasticsearch", "Kafka",
            "Airflow", "Spark", "Pandas", "NumPy", "Machine Learning",
            "SQL", "Power BI", "Data Analysis", "Data Modeling", "DAX",
            "Anaplan", "Excel", "Tableau", "Looker", "Snowflake",
        ]

        found = []
        text_lower = text.lower()
        for skill in common_skills:
            if skill.lower() in text_lower:
                found.append(skill)
        return found

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


async def create_jobbank_source(config: Dict[str, Any] = None) -> JobBankSource:
    return JobBankSource(config)