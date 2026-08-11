"""
ATS API Base Class - Common functionality for ATS (Applicant Tracking System) API integrations.
"""
import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse

import aiohttp

from job_sources.base import JobSource, RawJob
from utils.logger import get_logger


logger = get_logger(__name__)


class ATSSource(JobSource):
    """
    Abstract base class for ATS (Applicant Tracking System) API sources.

    Provides common functionality for:
    - Authentication handling
    - Rate limiting
    - Pagination
    - Error handling
    - Response normalization
    """

    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, config)
        self.base_url = config.get("base_url", "") if config else ""
        self.api_key = config.get("api_key", "") if config else ""
        self.auth_type = config.get("auth_type", "bearer") if config else "bearer"  # bearer, basic, custom
        self.rate_limit = config.get("rate_limit", 1.0) if config else 1.0  # requests per second
        self.max_pages = config.get("max_pages", 10) if config else 10
        self.timeout = config.get("timeout", 30) if config else 30
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_request = 0.0
        self._headers = self._build_headers()

    def _build_headers(self) -> Dict[str, str]:
        """Build HTTP headers with authentication."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if self.api_key:
            if self.auth_type == "bearer":
                headers["Authorization"] = f"Bearer {self.api_key}"
            elif self.auth_type == "basic":
                import base64
                # For basic auth, api_key should be in format "username:password"
                credentials = base64.b64encode(self.api_key.encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"
            elif self.auth_type == "api_key":
                headers["X-API-Key"] = self.api_key

        # Add any custom headers from config
        if self.config and "custom_headers" in self.config:
            headers.update(self.config["custom_headers"])

        return headers

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(headers=self._headers, timeout=timeout)
        return self._session

    async def _rate_limit(self):
        """Enforce rate limiting."""
        import time
        elapsed = time.time() - self._last_request
        if elapsed < (1.0 / self.rate_limit):
            await asyncio.sleep((1.0 / self.rate_limit) - elapsed)
        self._last_request = time.time()

    @abstractmethod
    def _build_search_url(self, filters: Dict[str, Any], page: int = 1) -> str:
        """Build the search URL for the ATS API."""
        pass

    @abstractmethod
    def _parse_jobs(self, response_data: Dict[str, Any]) -> List[RawJob]:
        """Parse job listings from API response."""
        pass

    @abstractmethod
    def _parse_job_details(self, response_data: Dict[str, Any], url: str) -> RawJob:
        """Parse detailed job information from API response."""
        pass

    @abstractmethod
    def _get_pagination_info(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract pagination info from response."""
        pass

    async def search(self, filters: Dict[str, Any], limit: int = 50) -> List[RawJob]:
        """Search for jobs using the ATS API."""
        jobs = []
        session = await self._get_session()
        page = 1

        while page <= self.max_pages and len(jobs) < limit:
            url = self._build_search_url(filters, page)

            try:
                await self._rate_limit()
                logger.debug(f"Fetching {self.name} page {page}: {url}")

                async with session.get(url) as response:
                    if response.status == 429:  # Rate limited
                        retry_after = int(response.headers.get("Retry-After", 60))
                        logger.warning(f"{self.name} rate limited, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue

                    if response.status != 200:
                        logger.warning(f"{self.name} search returned status {response.status}")
                        break

                    data = await response.json()
                    page_jobs = self._parse_jobs(data)

                    if not page_jobs:
                        logger.info(f"{self.name} page {page}: no jobs found, stopping")
                        break

                    for job in page_jobs:
                        if self._matches_filters(job, filters):
                            jobs.append(job)
                            if len(jobs) >= limit:
                                break

                    logger.info(f"{self.name} page {page}: found {len(page_jobs)} jobs, total: {len(jobs)}")

                    # Check pagination
                    pagination = self._get_pagination_info(data)
                    if not pagination.get("has_more", False):
                        break

                    page = pagination.get("next_page", page + 1)

            except asyncio.TimeoutError:
                logger.error(f"Timeout fetching {self.name} page {page}")
                break
            except aiohttp.ClientError as e:
                logger.error(f"Client error fetching {self.name} page {page}: {e}")
                break
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for {self.name} page {page}: {e}")
                break
            except Exception as e:
                logger.error(f"Error searching {self.name} page {page}: {e}")
                break

        return jobs[:limit]

    async def get_job_details(self, job_url: str) -> Optional[RawJob]:
        """Get detailed job information from ATS API."""
        if not job_url:
            return None

        session = await self._get_session()

        try:
            await self._rate_limit()
            async with session.get(job_url) as response:
                if response.status != 200:
                    logger.warning(f"{self.name} job details returned status {response.status}")
                    return None

                data = await response.json()
                return self._parse_job_details(data, job_url)

        except Exception as e:
            logger.error(f"Error getting {self.name} job details: {e}")
            return None

    def _matches_filters(self, job: RawJob, filters: Dict[str, Any]) -> bool:
        """Check if job matches filters."""
        negative_keywords = filters.get("negative_keywords", [])
        job_text = f"{job.title} {job.description} {job.company}".lower()
        for neg in negative_keywords:
            if neg.lower() in job_text:
                return False
        return True

    def _normalize_location(self, location: str) -> str:
        """Normalize location string."""
        if not location:
            return "Unknown"
        return location.strip()

    def _normalize_remote_type(self, remote_str: str) -> str:
        """Normalize remote type string."""
        if not remote_str:
            return "on_site"
        remote_lower = remote_str.lower()
        if "remote" in remote_lower:
            return "remote"
        elif "hybrid" in remote_lower:
            return "hybrid"
        return "on_site"

    def _normalize_employment_type(self, emp_type: str) -> str:
        """Normalize employment type string."""
        if not emp_type:
            return "full_time"
        emp_lower = emp_type.lower()
        if "contract" in emp_lower:
            return "contract"
        elif "part" in emp_lower:
            return "part_time"
        elif "intern" in emp_lower:
            return "internship"
        elif "temp" in emp_lower:
            return "temporary"
        return "full_time"

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string in various formats."""
        if not date_str:
            return None

        # Try common formats
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%d/%m/%Y",
            "%m/%d/%Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None

    def _extract_salary(self, salary_data: Dict[str, Any]) -> tuple:
        """Extract salary min/max from salary data."""
        if not salary_data:
            return None, None

        salary_min = salary_data.get("min") or salary_data.get("minimum") or salary_data.get("min_amount")
        salary_max = salary_data.get("max") or salary_data.get("maximum") or salary_data.get("max_amount")

        return salary_min, salary_max

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()


def create_ats_source(source_class, config: Dict[str, Any] = None):
    """Factory function to create an ATS source instance."""
    return source_class(config)