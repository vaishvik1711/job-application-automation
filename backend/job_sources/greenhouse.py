"""
Greenhouse ATS API Source.
Greenhouse is a popular ATS used by many companies.
API Documentation: https://developers.greenhouse.io/
"""
from datetime import datetime
from typing import List, Dict, Any, Optional

from job_sources.ats_base import ATSSource
from job_sources.base import RawJob


class GreenhouseSource(ATSSource):
    """
    Greenhouse ATS API Source.

    Greenhouse API requires:
    - base_url: "https://api.greenhouse.io/v1"
    - api_key: API key from Greenhouse
    - board_token: Board token for specific job board (optional, for public boards)
    """

    def __init__(self, config: Dict[str, Any] = None):
        # Set default base_url if not provided
        if config and "base_url" not in config:
            config = config.copy()
            config["base_url"] = "https://api.greenhouse.io/v1"
        super().__init__("greenhouse", config)
        self.board_token = config.get("board_token", "") if config else ""

    def _build_search_url(self, filters: Dict[str, Any], page: int = 1) -> str:
        """Build Greenhouse API search URL."""
        # Greenhouse uses different endpoints depending on auth type
        if self.board_token:
            # Public board access
            return f"{self.base_url}/boards/{self.board_token}/jobs"
        else:
            # Authenticated API access
            return f"{self.base_url}/jobs"

    def _parse_jobs(self, response_data: Dict[str, Any]) -> List[RawJob]:
        """Parse Greenhouse job listings."""
        jobs = []

        # Greenhouse returns jobs in a "jobs" array
        job_list = response_data.get("jobs", [])
        if not isinstance(job_list, list):
            job_list = [response_data] if "id" in response_data else []

        for job_data in job_list:
            try:
                job = self._parse_greenhouse_job(job_data)
                if job:
                    jobs.append(job)
            except Exception as e:
                import logging
                logging.getLogger(__name__).debug(f"Error parsing Greenhouse job: {e}")
                continue

        return jobs

    def _parse_greenhouse_job(self, job_data: Dict[str, Any]) -> Optional[RawJob]:
        """Parse a single Greenhouse job."""
        # Extract basic fields
        title = job_data.get("title", "Unknown")
        company = job_data.get("company_name", job_data.get("company", {}).get("name", "Unknown"))

        # Location
        location_data = job_data.get("location", {})
        if isinstance(location_data, dict):
            location = location_data.get("name", "Unknown")
        else:
            location = str(location_data) if location_data else "Unknown"

        # URL
        url = job_data.get("absolute_url", job_data.get("url", ""))

        # Description
        description = job_data.get("content", job_data.get("description", ""))

        # Date posted
        date_posted = None
        updated_at = job_data.get("updated_at")
        if updated_at:
            date_posted = self._parse_date(updated_at)

        # Employment type
        employment_type = "full_time"
        metadata = job_data.get("metadata", [])
        for meta in metadata:
            if meta.get("name", "").lower() in ["employment type", "job type"]:
                employment_type = self._normalize_employment_type(meta.get("value", ""))

        # Remote type
        remote_type = "on_site"
        if job_data.get("telecommuting", False):
            remote_type = "remote"

        # Salary
        salary_min, salary_max = None, None
        salary_data = job_data.get("salary", {})
        if salary_data:
            salary_min, salary_max = self._extract_salary(salary_data)

        # Skills from job description and metadata
        skills = self._extract_skills_from_text(description)
        for meta in metadata:
            if meta.get("name", "").lower() in ["skills", "technologies", "requirements"]:
                skills.extend([s.strip() for s in meta.get("value", "").split(",")])

        # Department/team
        department = job_data.get("departments", [{}])[0].get("name", "") if job_data.get("departments") else ""

        return RawJob(
            title=title,
            company=company,
            location=self._normalize_location(location),
            description=description,
            url=url,
            source="greenhouse",
            source_job_id=str(job_data.get("id", "")),
            date_posted=date_posted,
            salary_min=salary_min,
            salary_max=salary_max,
            currency="USD",  # Greenhouse typically uses USD
            remote_type=remote_type,
            employment_type=employment_type,
            skills=list(set(skills)),  # Deduplicate
            tools=[],
            raw_data={
                "department": department,
                "requisition_id": job_data.get("requisition_id", ""),
                "metadata": metadata,
            }
        )

    def _parse_job_details(self, response_data: Dict[str, Any], url: str) -> RawJob:
        """Parse detailed Greenhouse job information."""
        # For Greenhouse, the detail endpoint returns the same structure
        return self._parse_greenhouse_job(response_data)

    def _get_pagination_info(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract pagination info from Greenhouse response."""
        # Greenhouse uses page and per_page parameters
        # Check if there's a next page
        pagination = response_data.get("pagination", {})
        current_page = pagination.get("page", 1)
        per_page = pagination.get("per_page", 50)
        total = pagination.get("total", 0)

        has_more = (current_page * per_page) < total

        return {
            "has_more": has_more,
            "next_page": current_page + 1 if has_more else None,
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
        ]

        found = []
        text_lower = text.lower()
        for skill in common_skills:
            if skill.lower() in text_lower:
                found.append(skill)
        return found


async def create_greenhouse_source(config: Dict[str, Any] = None) -> GreenhouseSource:
    """Factory function to create a Greenhouse source."""
    return GreenhouseSource(config)