"""
Workday ATS API Source.
Workday is a popular ATS/HRIS used by many large enterprises.
Note: Workday API requires specific credentials and is often company-specific.
This is a generic implementation that can be customized per company.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
import re

from job_sources.ats_base import ATSSource
from job_sources.base import RawJob


class WorkdaySource(ATSSource):
    """
    Workday ATS API Source.

    Workday API requires:
    - base_url: Company-specific Workday URL (e.g., "https://company.wd1.myworkdayjobs.com")
    - api_key: May require username/password or OAuth token
    - company_name: Company identifier in Workday
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("workday", config)
        self.company_name = config.get("company_name", "") if config else ""
        # Workday often uses basic auth or OAuth
        self.auth_type = config.get("auth_type", "basic") if config else "basic"

    def _build_search_url(self, filters: Dict[str, Any], page: int = 1) -> str:
        """Build Workday API search URL."""
        # Workday typically uses a search endpoint with specific query parameters
        # The exact endpoint varies by company configuration
        limit = filters.get("limit", 20)
        offset = (page - 1) * limit

        # Base job search endpoint
        base = self.base_url.rstrip("/")

        # Common Workday job search endpoints
        if "myworkdayjobs.com" in base:
            # Public career site
            search_path = f"/wday/cxs/{self.company_name}/jobs"
            params = {
                "limit": limit,
                "offset": offset,
                "searchText": filters.get("query", ""),
            }
            from urllib.parse import urlencode
            return f"{base}{search_path}?{urlencode(params)}"
        else:
            # Internal API endpoint (varies by company)
            search_path = config.get("search_path", "/api/jobs") if (config := self.config) else "/api/jobs"
            return f"{base}{search_path}?limit={limit}&offset={offset}"

    def _parse_jobs(self, response_data: Dict[str, Any]) -> List[RawJob]:
        """Parse Workday job listings."""
        jobs = []

        # Workday returns jobs in different formats depending on endpoint
        # Common format: { "jobPostings": [...] }
        job_list = response_data.get("jobPostings", response_data.get("jobs", []))

        if not isinstance(job_list, list):
            job_list = []

        for job_data in job_list:
            try:
                job = self._parse_workday_job(job_data)
                if job:
                    jobs.append(job)
            except Exception as e:
                import logging
                logging.getLogger(__name__).debug(f"Error parsing Workday job: {e}")
                continue

        return jobs

    def _parse_workday_job(self, job_data: Dict[str, Any]) -> Optional[RawJob]:
        """Parse a single Workday job."""
        # Extract basic fields
        title = job_data.get("title", job_data.get("jobTitle", "Unknown"))

        # Company - might be in different fields
        company = (
            job_data.get("company", {}).get("name")
            or job_data.get("companyName")
            or job_data.get("organization", {}).get("name")
            or self.company_name
            or "Unknown"
        )

        # Location
        location_data = job_data.get("location", job_data.get("locations", {}))
        if isinstance(location_data, list):
            location = location_data[0].get("name", "Unknown") if location_data else "Unknown"
        elif isinstance(location_data, dict):
            location = location_data.get("name", location_data.get("address", "Unknown"))
        else:
            location = str(location_data) if location_data else "Unknown"

        # URL
        url = (
            job_data.get("externalPath")
            or job_data.get("applyUrl")
            or job_data.get("jobUrl")
            or job_data.get("url")
            or ""
        )
        # Make URL absolute if relative
        if url and not url.startswith("http"):
            url = urljoin(self.base_url, url)

        # Description
        description = (
            job_data.get("jobDescription")
            or job_data.get("description")
            or job_data.get("descriptionTeaser")
            or ""
        )

        # Date posted
        date_posted = None
        for date_field in ["postedOn", "postedDate", "startDate", "creationDate"]:
            if job_data.get(date_field):
                date_posted = self._parse_date(job_data[date_field])
                if date_posted:
                    break

        # Employment type
        employment_type = "full_time"
        for field in ["workerType", "employmentType", "jobType", "timeType"]:
            if job_data.get(field):
                employment_type = self._normalize_employment_type(str(job_data[field]))
                break

        # Remote type
        remote_type = "on_site"
        # Check various fields for remote indication
        for field in ["remoteType", "workLocationType", "locationType"]:
            if job_data.get(field):
                remote_type = self._normalize_remote_type(str(job_data[field]))
                break

        # Also check location text for remote
        if remote_type == "on_site" and "remote" in location.lower():
            remote_type = "remote"

        # Salary
        salary_min, salary_max = None, None
        salary_data = job_data.get("salary", job_data.get("compensation", {}))
        if salary_data:
            salary_min, salary_max = self._extract_salary(salary_data)

        # Skills from description and job profile
        skills = self._extract_skills_from_text(description)

        # Add skills from job profile/qualifications if available
        for field in ["qualifications", "requirements", "skills", "profile"]:
            if job_data.get(field):
                skills.extend(self._extract_skills_from_text(str(job_data[field])))

        # Job category/department
        category = (
            job_data.get("jobCategory", {}).get("name")
            or job_data.get("jobFunction", {}).get("name")
            or job_data.get("department", "")
        )

        return RawJob(
            title=title,
            company=company,
            location=self._normalize_location(location),
            description=description,
            url=url,
            source="workday",
            source_job_id=str(job_data.get("id", job_data.get("jobId", ""))),
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
                "requisition_id": job_data.get("requisitionId", job_data.get("reqId", "")),
                "is_remote": remote_type == "remote",
            }
        )

    def _parse_job_details(self, response_data: Dict[str, Any], url: str) -> RawJob:
        """Parse detailed Workday job information."""
        return self._parse_workday_job(response_data)

    def _get_pagination_info(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract pagination info from Workday response."""
        total = response_data.get("total", response_data.get("totalResults", 0))
        limit = response_data.get("limit", 20)
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
            "Workday", "SAP", "Oracle", "Salesforce", "ServiceNow",
        ]

        found = []
        text_lower = text.lower()
        for skill in common_skills:
            if skill.lower() in text_lower:
                found.append(skill)
        return found


async def create_workday_source(config: Dict[str, Any] = None) -> WorkdaySource:
    """Factory function to create a Workday source."""
    return WorkdaySource(config)