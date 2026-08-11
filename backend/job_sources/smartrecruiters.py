"""
SmartRecruiters ATS API Source.
SmartRecruiters is a popular ATS used by many companies.
API Documentation: https://developers.smartrecruiters.com/
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode

from job_sources.ats_base import ATSSource
from job_sources.base import RawJob


class SmartRecruitersSource(ATSSource):
    """
    SmartRecruiters ATS API Source.

    SmartRecruiters API requires:
    - base_url: "https://api.smartrecruiters.com"
    - api_key: API access token
    - company_id: Company identifier (optional, can be derived from token)
    """

    def __init__(self, config: Dict[str, Any] = None):
        # Set default base_url if not provided
        if config and "base_url" not in config:
            config = config.copy()
            config["base_url"] = "https://api.smartrecruiters.com"
        super().__init__("smartrecruiters", config)
        self.company_id = config.get("company_id", "") if config else ""

    def _build_search_url(self, filters: Dict[str, Any], page: int = 1) -> str:
        """Build SmartRecruiters API search URL."""
        limit = filters.get("limit", 50)
        offset = (page - 1) * limit

        # SmartRecruiters jobs endpoint
        base = self.base_url.rstrip("/")
        jobs_endpoint = f"{base}/postings"

        params = {
            "limit": limit,
            "offset": offset,
            "status": "active",  # Only active postings
        }

        # Add search query if provided
        if filters.get("query"):
            params["q"] = filters["query"]

        # Add location filter if provided
        if filters.get("locations"):
            params["location"] = filters["locations"][0]

        return f"{jobs_endpoint}?{urlencode(params)}"

    def _parse_jobs(self, response_data: Dict[str, Any]) -> List[RawJob]:
        """Parse SmartRecruiters job listings."""
        jobs = []

        # SmartRecruiters returns jobs in "content" array
        job_list = response_data.get("content", [])

        if not isinstance(job_list, list):
            job_list = []

        for job_data in job_list:
            try:
                job = self._parse_smartrecruiters_job(job_data)
                if job:
                    jobs.append(job)
            except Exception as e:
                import logging
                logging.getLogger(__name__).debug(f"Error parsing SmartRecruiters job: {e}")
                continue

        return jobs

    def _parse_smartrecruiters_job(self, job_data: Dict[str, Any]) -> Optional[RawJob]:
        """Parse a single SmartRecruiters job."""
        # Extract basic fields
        title = job_data.get("name", job_data.get("title", "Unknown"))

        # Company
        company = job_data.get("company", {}).get("name", "Unknown")

        # Location
        location_data = job_data.get("location", {})
        if isinstance(location_data, dict):
            # SmartRecruiters location has city, region, country
            parts = []
            for field in ["city", "region", "country"]:
                if location_data.get(field):
                    parts.append(location_data[field])
            location = ", ".join(parts) if parts else "Unknown"
        else:
            location = str(location_data) if location_data else "Unknown"

        # URL
        url = job_data.get("applyUrl", job_data.get("url", job_data.get("ref", "")))

        # Description
        description = job_data.get("jobAd", {}).get("sections", {}).get("jobDescription", {}).get("text", "")
        if not description:
            description = job_data.get("description", "")

        # Date posted
        date_posted = None
        for date_field in ["releasedDate", "createdOn", "postedDate"]:
            if job_data.get(date_field):
                date_posted = self._parse_date(job_data[date_field])
                if date_posted:
                    break

        # Employment type
        employment_type = "full_time"
        employment_type_data = job_data.get("employmentType", {})
        if isinstance(employment_type_data, dict):
            employment_type = self._normalize_employment_type(employment_type_data.get("label", ""))
        else:
            employment_type = self._normalize_employment_type(str(employment_type_data))

        # Remote type
        remote_type = "on_site"
        # Check job location type or custom fields
        location_type = job_data.get("locationType", "")
        if location_type:
            remote_type = self._normalize_remote_type(location_type)
        # Also check custom fields
        custom_fields = job_data.get("customFields", [])
        for field in custom_fields:
            if field.get("fieldId", "").lower() in ["remote", "worktype", "work_type"]:
                remote_type = self._normalize_remote_type(field.get("value", ""))

        # Salary - SmartRecruiters doesn't typically expose salary via API
        salary_min, salary_max = None, None

        # Skills from tags and description
        skills = []
        tags = job_data.get("tags", [])
        for tag in tags:
            if isinstance(tag, dict):
                skills.append(tag.get("label", tag.get("name", "")))
            else:
                skills.append(str(tag))

        # Also extract from description
        skills.extend(self._extract_skills_from_text(description))

        # Department/function
        department = job_data.get("department", {}).get("label", "") if isinstance(job_data.get("department"), dict) else ""
        function = job_data.get("function", {}).get("label", "") if isinstance(job_data.get("function"), dict) else ""

        return RawJob(
            title=title,
            company=company,
            location=self._normalize_location(location),
            description=description,
            url=url,
            source="smartrecruiters",
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
                "department": department,
                "function": function,
                "requisition_id": job_data.get("ref", ""),
                "job_ad_sections": job_data.get("jobAd", {}).get("sections", {}),
            }
        )

    def _parse_job_details(self, response_data: Dict[str, Any], url: str) -> RawJob:
        """Parse detailed SmartRecruiters job information."""
        return self._parse_smartrecruiters_job(response_data)

    def _get_pagination_info(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract pagination info from SmartRecruiters response."""
        total = response_data.get("totalFound", response_data.get("total", 0))
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
            "SmartRecruiters", "Workday", "SAP", "Oracle", "Salesforce", "ServiceNow",
        ]

        found = []
        text_lower = text.lower()
        for skill in common_skills:
            if skill.lower() in text_lower:
                found.append(skill)
        return found


async def create_smartrecruiters_source(config: Dict[str, Any] = None) -> SmartRecruitersSource:
    """Factory function to create a SmartRecruiters source."""
    return SmartRecruitersSource(config)