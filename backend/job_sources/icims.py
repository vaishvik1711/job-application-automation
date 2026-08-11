"""
iCIMS ATS API Source.
iCIMS is a popular enterprise ATS used by many large companies.
API Documentation: https://developer.icims.com/
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

from job_sources.ats_base import ATSSource
from job_sources.base import RawJob


class ICIMSSource(ATSSource):
    """
    iCIMS ATS API Source.

    iCIMS API requires:
    - base_url: Company-specific iCIMS URL (e.g., "https://api.icims.com/customers/12345")
    - api_key: API key (client_id:client_secret for OAuth)
    - customer_id: iCIMS customer ID
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("icims", config)
        self.customer_id = config.get("customer_id", "") if config else ""
        # iCIMS uses OAuth 2.0
        self.auth_type = config.get("auth_type", "oauth") if config else "oauth"
        self._access_token = None
        self._token_expires = 0

    def _build_headers(self) -> Dict[str, str]:
        """Build HTTP headers with iCIMS authentication."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # iCIMS uses Authorization: Bearer <access_token>
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        elif self.api_key:
            # Fallback to basic auth if no OAuth token
            import base64
            credentials = base64.b64encode(self.api_key.encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"

        if self.config and "custom_headers" in self.config:
            headers.update(self.config["custom_headers"])

        return headers

    async def _get_access_token(self) -> Optional[str]:
        """Get OAuth access token for iCIMS API."""
        import time

        # Return cached token if still valid
        if self._access_token and time.time() < self._token_expires - 60:
            return self._access_token

        # iCIMS OAuth token endpoint
        token_url = f"{self.base_url.rstrip('/')}/oauth/token"

        # Parse client_id and client_secret from api_key (format: "client_id:client_secret")
        if ":" in self.api_key:
            client_id, client_secret = self.api_key.split(":", 1)
        else:
            client_id = self.config.get("client_id", "") if self.config else ""
            client_secret = self.config.get("client_secret", "") if self.config else ""

        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }

        session = await self._get_session()

        try:
            async with session.post(token_url, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self._access_token = token_data.get("access_token")
                    expires_in = token_data.get("expires_in", 3600)
                    import time
                    self._token_expires = time.time() + expires_in
                    # Update session headers with new token
                    self._headers = self._build_headers()
                    return self._access_token
                else:
                    import logging
                    logging.getLogger(__name__).error(f"iCIMS token request failed: {response.status}")
                    return None
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error getting iCIMS access token: {e}")
            return None

    def _build_search_url(self, filters: Dict[str, Any], page: int = 1) -> str:
        """Build iCIMS API search URL."""
        # Ensure we have a valid token
        # Note: token refresh happens in _get_session via _build_headers

        limit = filters.get("limit", 50)
        offset = (page - 1) * limit

        # iCIMS jobs endpoint
        base = self.base_url.rstrip("/")

        # If base_url already includes customer path, use it; otherwise construct
        if f"/customers/{self.customer_id}" in base:
            jobs_endpoint = f"{base}/jobs"
        else:
            jobs_endpoint = f"{base}/customers/{self.customer_id}/jobs"

        params = {
            "limit": limit,
            "offset": offset,
            "fields": "id,title,company,location,description,createdDate,employmentType,workLocationType,salary,requisitionId,category,tags",
        }

        # Add search query if provided
        if filters.get("query"):
            params["search"] = filters["query"]

        from urllib.parse import urlencode
        return f"{jobs_endpoint}?{urlencode(params)}"

    async def search(self, filters: Dict[str, Any], limit: int = 50) -> List[RawJob]:
        """Search for jobs using iCIMS API."""
        # Refresh token before search
        await self._get_access_token()
        return await super().search(filters, limit)

    def _parse_jobs(self, response_data: Dict[str, Any]) -> List[RawJob]:
        """Parse iCIMS job listings."""
        jobs = []

        # iCIMS returns jobs in a "jobs" array or "searchResults"
        job_list = response_data.get("jobs", response_data.get("searchResults", []))

        if not isinstance(job_list, list):
            job_list = []

        for job_data in job_list:
            try:
                job = self._parse_icims_job(job_data)
                if job:
                    jobs.append(job)
            except Exception as e:
                import logging
                logging.getLogger(__name__).debug(f"Error parsing iCIMS job: {e}")
                continue

        return jobs

    def _parse_icims_job(self, job_data: Dict[str, Any]) -> Optional[RawJob]:
        """Parse a single iCIMS job."""
        # Extract basic fields
        title = job_data.get("title", "Unknown")

        # Company
        company = job_data.get("company", {}).get("name", "Unknown")

        # Location
        location_data = job_data.get("location", {})
        if isinstance(location_data, dict):
            location = location_data.get("name", "Unknown")
        elif isinstance(location_data, list) and location_data:
            location = location_data[0].get("name", "Unknown")
        else:
            location = str(location_data) if location_data else "Unknown"

        # URL
        url = job_data.get("applyUrl", job_data.get("jobUrl", job_data.get("url", "")))

        # Description
        description = job_data.get("description", "")

        # Date posted
        date_posted = None
        created_date = job_data.get("createdDate", job_data.get("postedDate"))
        if created_date:
            date_posted = self._parse_date(created_date)

        # Employment type
        employment_type = "full_time"
        emp_type = job_data.get("employmentType", {})
        if isinstance(emp_type, dict):
            employment_type = self._normalize_employment_type(emp_type.get("name", ""))
        else:
            employment_type = self._normalize_employment_type(str(emp_type))

        # Remote type
        remote_type = "on_site"
        work_location = job_data.get("workLocationType", {})
        if isinstance(work_location, dict):
            remote_type = self._normalize_remote_type(work_location.get("name", ""))
        else:
            remote_type = self._normalize_remote_type(str(work_location))

        # Salary
        salary_min, salary_max = None, None
        salary_data = job_data.get("salary", {})
        if salary_data:
            salary_min, salary_max = self._extract_salary(salary_data)

        # Skills from tags
        skills = []
        tags = job_data.get("tags", [])
        for tag in tags:
            if isinstance(tag, dict):
                skills.append(tag.get("name", ""))
            else:
                skills.append(str(tag))

        # Also extract from description
        skills.extend(self._extract_skills_from_text(description))

        # Category/department
        category = job_data.get("category", {}).get("name", "") if isinstance(job_data.get("category"), dict) else str(job_data.get("category", ""))

        return RawJob(
            title=title,
            company=company,
            location=self._normalize_location(location),
            description=description,
            url=url,
            source="icims",
            source_job_id=str(job_data.get("id", "")),
            date_posted=date_posted,
            salary_min=salary_min,
            salary_max=salary_max,
            currency="USD",
            remote_type=remote_type,
            employment_type=employment_type,
            skills=list(set(skills)),
            tools=[],
            raw_data={
                "category": category,
                "requisition_id": job_data.get("requisitionId", ""),
                "employment_type_detail": emp_type,
                "work_location_detail": work_location,
            }
        )

    def _parse_job_details(self, response_data: Dict[str, Any], url: str) -> RawJob:
        """Parse detailed iCIMS job information."""
        return self._parse_icims_job(response_data)

    def _get_pagination_info(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract pagination info from iCIMS response."""
        total = response_data.get("totalResults", response_data.get("total", 0))
        limit = response_data.get("limit", 50)
        offset = response_data.get("offset", 0)

        has_more = (offset + limit) < total

        return {
            "has_more": has_more,
            "next_page": (offset // limit) + 2 if has_more else None,
            "total": total,
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
            "iCIMS", "Workday", "SAP", "Oracle", "Salesforce", "ServiceNow",
        ]

        found = []
        text_lower = text.lower()
        for skill in common_skills:
            if skill.lower() in text_lower:
                found.append(skill)
        return found


async def create_icims_source(config: Dict[str, Any] = None) -> ICIMSSource:
    """Factory function to create an iCIMS source."""
    return ICIMSSource(config)