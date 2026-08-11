"""
RemoteOK Free API Source.
RemoteOK provides a free JSON API for remote job listings.
No authentication required.
API: https://remoteok.io/api
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse urlencode

from job_sources.base import JobSource, RawJob
from utils.logger import get_logger


logger = get_logger(__name__)


class RemoteOKSource(JobSource):
    """
    RemoteOK Free API Source.

    Free JSON API - no authentication required.
    Returns remote jobs from various companies.
    """

    BASE_URL = "https://remoteok.io/api"

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("remoteok", config)
        self.rate_limit = config.get("rate_limit", 0.5) if config else 0.5  # Be respectful
        self._session = None
        self._last_request = 0.0

    async def _get_session(self):
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            import aiohttp
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
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
        """Build RemoteOK API URL."""
        # RemoteOK API doesn't support pagination in traditional sense
        # It returns all jobs in one call
        params = {}

        # Add tag filter if provided (e.g., "python", "javascript", "data")
        if filters.get("tags"):
            tags = filters["tags"]
            if isinstance(tags, list):
                params["tag"] = tags[0]  # API only supports one tag at a time
            else:
                params["tag"] = tags

        # Add location filter (remote only, but can filter by timezone)
        if filters.get("timezone"):
            params["timezone"] = filters["timezone"]

        from urllib.parse import urlencode
        if params:
            return f"{self.BASE_URL}?{urlencode(params)}"
        return self.BASE_URL

    async def search(self, filters: Dict[str, Any], limit: int = 50) -> List[RawJob]:
        """Search RemoteOK for jobs."""
        session = await self._get_session()
        jobs = []

        try:
            await self._rate_limit()
            url = self._build_search_url(filters)

            logger.info(f"Fetching RemoteOK jobs from {url}")

            async with session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"RemoteOK API returned status {response.status}")
                    return []

                data = await response.json()

                # First element is metadata, rest are jobs
                if isinstance(data, list) and len(data) > 1:
                    job_list = data[1:]  # Skip metadata
                elif isinstance(data, list):
                    job_list = data
                else:
                    job_list = []

                logger.info(f"RemoteOK returned {len(job_list)} jobs")

                for job_data in job_list:
                    if len(jobs) >= limit:
                        break

                    try:
                        job = self._parse_remoteok_job(job_data)
                        if job and self._matches_filters(job, filters):
                            jobs.append(job)
                    except Exception as e:
                        logger.debug(f"Error parsing RemoteOK job: {e}")
                        continue

        except asyncio.TimeoutError:
            logger.error("Timeout fetching RemoteOK jobs")
        except Exception as e:
            logger.error(f"Error searching RemoteOK: {e}")

        return jobs[:limit]

    def _parse_remoteok_job(self, job_data: Dict[str, Any]) -> Optional[RawJob]:
        """Parse a single RemoteOK job."""
        # RemoteOK returns a specific format
        # First item in array is often metadata, skip if it has "legal" key
        if job_data.get("legal") or job_data.get("metadata"):
            return None

        title = job_data.get("position", job_data.get("title", "Unknown"))
        company = job_data.get("company", "Unknown")

        # Location - RemoteOK is remote-first
        location = job_data.get("location", "Remote")
        if not location or location.lower() in ["worldwide", "anywhere", "global"]:
            location = "Remote"

        # URL
        url = job_data.get("url", job_data.get("apply_url", ""))

        # Description
        description = job_data.get("description", "")

        # Date posted
        date_posted = None
        for date_field in ["date", "created_at", "timestamp"]:
            if job_data.get(date_field):
                date_posted = self._parse_date(job_data[date_field])
                if date_posted:
                    break

        # Salary
        salary_min, salary_max = None, None
        salary_data = job_data.get("salary", {})
        if isinstance(salary_data, dict):
            salary_min = salary_data.get("min")
            salary_max = salary_data.get("max")
        elif isinstance(job_data.get("salary"), (int, float)):
            salary_min = salary_max = job_data.get("salary")

        # Currency
        currency = job_data.get("currency", "USD")

        # Tags/skills
        skills = []
        tags = job_data.get("tags", [])
        if isinstance(tags, list):
            skills.extend([str(t) for t in tags])

        # Also extract from description
        skills.extend(self._extract_skills_from_text(description))

        # Remote type - RemoteOK is primarily remote
        remote_type = "remote"

        # Employment type
        employment_type = "full_time"

        return RawJob(
            title=title,
            company=company,
            location=self._normalize_location(location),
            description=description,
            url=url,
            source="remoteok",
            source_job_id=str(job_data.get("id", "")),
            date_posted=date_posted,
            salary_min=salary_min,
            salary_max=salary_max,
            currency=currency,
            remote_type=remote_type,
            employment_type=employment_type,
            skills=list(set(skills)),
            tools=[],
            raw_data={
                "tags": tags,
                "company_logo": job_data.get("company_logo", ""),
                "company_url": job_data.get("company_url", ""),
            }
        )

    def _parse_date(self, date_str: Any) -> Optional[datetime]:
        """Parse date from various formats."""
        if not date_str:
            return None

        if isinstance(date_str, (int, float)):
            # Unix timestamp
            try:
                return datetime.fromtimestamp(date_str)
            except (ValueError, OSError):
                pass

        if isinstance(date_str, str):
            formats = [
                "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
                "%d %b %Y",
                "%b %d, %Y",
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

        return None

    def _parse_job_details(self, response_data: Dict[str, Any], url: str) -> RawJob:
        """Parse detailed job - RemoteOK returns full data in search."""
        return self._parse_remoteok_job(response_data)

    def _get_pagination_info(self, response_data: Any) -> Dict[str, Any]:
        """RemoteOK doesn't paginate - returns all at once."""
        return {
            "has_more": False,
            "next_page": None,
            "total": len(response_data) if isinstance(response_data, list) else 0,
        }

    def _extract_skills_from_text(self, text: str) -> List[str]:
        """Extract common technical skills from text."""
        if not text:
            return []

        common_skills = [
            "Python", "JavaScript", "TypeScript", "React", "Node.js", "FastAPI",
            "Django", "PostgreSQL", "MongoDB", "Redis", "AWS", "Docker",
            "Kubernetes", "Git", "CI/CD", "SQL", "NoSQL", "REST APIs",
            "GraphQL", "Microservices", "Terraform", "GitHub Actions", "GitLab CI",
            "Prometheus", "Grafana", "Datadog", "Elasticsearch", "Kafka",
            "Airflow", "Spark", "Pandas", "NumPy", "Machine Learning",
            "Power BI", "Data Analysis", "Data Modeling", "DAX",
            "Anaplan", "Excel", "Tableau", "Looker", "Snowflake",
            "Java", "C++", "Go", "Rust", "Ruby", "PHP",
            "Vue.js", "Angular", "Next.js", "Svelte",
            "GCP", "Azure", "Cloudflare", "Vercel",
        ]

        found = []
        text_lower = text.lower()
        for skill in common_skills:
            if skill.lower() in text_lower:
                found.append(skill)
        return found

    def _matches_filters(self, job: RawJob, filters: Dict[str, Any]) -> bool:
        """Check if job matches filters."""
        negative_keywords = filters.get("negative_keywords", [])
        job_text = f"{job.title} {job.description} {job.company}".lower()
        for neg in negative_keywords:
            if neg.lower() in job_text:
                return False

        # Filter by tags if specified
        if filters.get("tags"):
            required_tags = filters["tags"]
            if isinstance(required_tags, str):
                required_tags = [required_tags]
            job_tags = [s.lower() for s in job.skills]
            if not any(tag.lower() in job_tags for tag in required_tags):
                return False

        return True

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()


async def create_remoteok_source(config: Dict[str, Any] = None) -> RemoteOKSource:
    """Factory function to create a RemoteOK source."""
    return RemoteOKSource(config)