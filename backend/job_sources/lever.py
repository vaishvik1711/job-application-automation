"""
Lever ATS API Source.
Lever is a popular ATS used by many companies.
API Documentation: https://developer.lever.co/
"""
from datetime import datetime
from typing import List, Dict, Any, Optional

from job_sources.ats_base import ATSSource
from job_sources.base import RawJob


class LeverSource(ATSSource):
    """
    Lever ATS API Source.

    Lever API requires:
    - base_url: "https://api.lever.co/v1"
    - api_key: API key from Lever
    """

    def __init__(self, config: Dict[str, Any] = None):
        # Set default base_url if not provided
        if config and "base_url" not in config:
            config = config.copy()
            config["base_url"] = "https://api.lever.co/v1"
        super().__init__("lever", config)

    def _build_search_url(self, filters: Dict[str, Any], page: int = 1) -> str:
        """Build Lever API search URL."""
        # Lever uses /postings endpoint
        # Use limit and offset for pagination
        limit = filters.get("limit", 50)
        offset = (page - 1) * limit

        params = [
            f"limit={limit}",
            f"offset={offset}",
            "mode=json",
        ]

        # Add query if provided
        if filters.get("query"):
            params.append(f"query={filters['query']}")

        return f"{self.base_url}/postings?{'&'.join(params)}"

    def _parse_jobs(self, response_data: List[Dict[str, Any]]) -> List[RawJob]:
        """Parse Lever job listings."""
        jobs = []

        # Lever returns a list directly
        job_list = response_data if isinstance(response_data, list) else []

        for job_data in job_list:
            try:
                job = self._parse_lever_job(job_data)
                if job:
                    jobs.append(job)
            except Exception as e:
                import logging
                logging.getLogger(__name__).debug(f"Error parsing Lever job: {e}")
                continue

        return jobs

    def _parse_lever_job(self, job_data: Dict[str, Any]) -> Optional[RawJob]:
        """Parse a single Lever job."""
        # Extract basic fields
        title = job_data.get("text", job_data.get("title", "Unknown"))
        company = job_data.get("company", "Unknown")

        # Location
        location_data = job_data.get("categories", {}).get("location", "Unknown")
        location = location_data if isinstance(location_data, str) else "Unknown"

        # URL
        url = job_data.get("hostedUrl", job_data.get("applyUrl", job_data.get("url", "")))

        # Description
        description = job_data.get("descriptionPlain", job_data.get("description", ""))

        # Date posted
        date_posted = None
        created_at = job_data.get("createdAt")
        if created_at:
            date_posted = self._parse_date(str(created_at))

        # Employment type
        employment_type = "full_time"
        commitment = job_data.get("categories", {}).get("commitment", "")
        if commitment:
            employment_type = self._normalize_employment_type(commitment)

        # Remote type
        remote_type = "on_site"
        workplace_type = job_data.get("workplaceType", "").lower()
        if workplace_type == "remote":
            remote_type = "remote"
        elif workplace_type == "hybrid":
            remote_type = "hybrid"

        # Salary - Lever doesn't typically include salary in API
        salary_min, salary_max = None, None

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

        # Department/team
        team = job_data.get("categories", {}).get("team", "")
        department = job_data.get("categories", {}).get("department", "")

        return RawJob(
            title=title,
            company=company,
            location=self._normalize_location(location),
            description=description,
            url=url,
            source="lever",
            source_job_id=str(job_data.get("id", "")),
            date_posted=date_posted,
            salary_min=salary_min,
            salary_max=salary_max,
            currency="USD",
            remote_type=remote_type,
            employment_type=employment_type,
            skills=list(set(skills)),  # Deduplicate
            tools=[],
            raw_data={
                "team": team,
                "department": department,
                "workplace_type": workplace_type,
                "commitment": commitment,
                "requisition_id": job_data.get("requisitionId", ""),
            }
        )

    def _parse_job_details(self, response_data: Dict[str, Any], url: str) -> RawJob:
        """Parse detailed Lever job information."""
        return self._parse_lever_job(response_data)

    def _get_pagination_info(self, response_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract pagination info from Lever response."""
        # Lever returns a list, we need to check if there are more results
        # Typically if the list length equals the limit, there might be more
        limit = 50  # default
        has_more = len(response_data) >= limit

        return {
            "has_more": has_more,
            "next_page": None,  # We calculate next page in search method
            "total": len(response_data),
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


async def create_lever_source(config: Dict[str, Any] = None) -> LeverSource:
    """Factory function to create a Lever source."""
    return LeverSource(config)