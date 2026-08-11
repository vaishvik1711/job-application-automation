"""
JobSpy Source - Integrates python-jobspy for LinkedIn, Indeed, ZipRecruiter scraping.
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd

from job_sources.base import JobSource, RawJob
from utils.logger import get_logger


logger = get_logger(__name__)


class JobSpySource(JobSource):
    """
    JobSpy source for scraping LinkedIn, Indeed, ZipRecruiter.

    Uses python-jobspy library to scrape job postings.
    No API keys required but subject to rate limiting.
    """

    # Supported sites in jobspy
    SUPPORTED_SITES = ["linkedin", "indeed", "zip_recruiter", "glassdoor", "google"]

    # Default site configuration per source
    SITE_CONFIG = {
        "linkedin": {
            "fetch_description": True,
            "results_per_search": 25,
        },
        "indeed": {
            "country": "Canada",
            "results_per_search": 25,
        },
        "zip_recruiter": {
            "results_per_search": 25,
        },
        "glassdoor": {
            "results_per_search": 25,
        },
        "google": {
            "results_per_search": 25,
        },
    }

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("jobspy", config)
        self.enabled_sites = config.get("sites", ["linkedin", "indeed", "zip_recruiter"]) if config else ["linkedin", "indeed", "zip_recruiter"]
        self.max_results_per_site = config.get("max_results_per_site", 25) if config else 25
        self.hours_old = config.get("hours_old", 720) if config else 720  # 30 days default
        self.linkedin_fetch_description = config.get("linkedin_fetch_description", True) if config else True
        self.country_indeed = config.get("country_indeed", "Canada") if config else "Canada"

        # Validate sites
        self.enabled_sites = [s for s in self.enabled_sites if s in self.SUPPORTED_SITES]
        if not self.enabled_sites:
            logger.warning("No valid sites configured for JobSpy, defaulting to linkedin, indeed")
            self.enabled_sites = ["linkedin", "indeed"]

    async def search(self, filters: Dict[str, Any], limit: int = 50) -> List[RawJob]:
        """
        Search for jobs using jobspy across multiple sites.

        Args:
            filters: Search filters from job_filters.yaml
            limit: Maximum total jobs to return (distributed across sites)

        Returns:
            List of RawJob objects
        """
        try:
            from jobspy import scrape_jobs
        except ImportError:
            logger.error("python-jobspy not installed. Run: pip install python-jobspy")
            return []

        # Build search terms from filters
        search_terms = self._build_search_terms(filters)
        locations = self._build_locations(filters)

        all_jobs = []
        jobs_per_site = max(1, limit // len(self.enabled_sites))

        for site in self.enabled_sites:
            try:
                logger.info(f"Searching {site} for {len(search_terms)} search terms...")

                for search_term in search_terms:
                    for location in locations:
                        try:
                            site_jobs = await self._scrape_site(
                                site=site,
                                search_term=search_term,
                                location=location,
                                limit=jobs_per_site,
                            )
                            all_jobs.extend(site_jobs)

                            if len(all_jobs) >= limit:
                                break
                        except Exception as e:
                            logger.warning(f"Error searching {site} for '{search_term}' in '{location}': {e}")
                            continue

                    if len(all_jobs) >= limit:
                        break

            except Exception as e:
                logger.error(f"Error searching site {site}: {e}")
                continue

        # Deduplicate and limit
        unique_jobs = self._deduplicate_jobs(all_jobs)
        return unique_jobs[:limit]

    async def _scrape_site(
        self,
        site: str,
        search_term: str,
        location: str,
        limit: int,
    ) -> List[RawJob]:
        """Scrape a single site with jobspy."""
        from jobspy import scrape_jobs

        # Run in thread pool since jobspy is synchronous
        loop = asyncio.get_event_loop()

        site_config = self.SITE_CONFIG.get(site, {})

        jobs_df = await loop.run_in_executor(
            None,
            lambda: scrape_jobs(
                site_name=[site],
                search_term=search_term,
                location=location,
                results_wanted=min(limit, site_config.get("results_per_search", 25)),
                hours_old=self.hours_old,
                country_indeed=self.country_indeed if site == "indeed" else None,
                linkedin_fetch_description=self.linkedin_fetch_description if site == "linkedin" else False,
            )
        )

        if jobs_df is None or jobs_df.empty:
            return []

        # Convert to RawJob objects
        raw_jobs = []
        for _, row in jobs_df.iterrows():
            try:
                raw_job = self._convert_row_to_rawjob(row, site)
                if raw_job:
                    raw_jobs.append(raw_job)
            except Exception as e:
                logger.warning(f"Error converting job row: {e}")
                continue

        logger.info(f"Found {len(raw_jobs)} jobs from {site} for '{search_term}' in '{location}'")
        return raw_jobs

    def _convert_row_to_rawjob(self, row: pd.Series, site: str) -> Optional[RawJob]:
        """Convert jobspy DataFrame row to RawJob."""
        # Extract required fields with fallbacks - handle None values safely
        def safe_str(val):
            return str(val).strip() if val is not None and pd.notna(val) else ""

        title = safe_str(row.get("title"))
        company = safe_str(row.get("company"))
        location = safe_str(row.get("location"))
        description = safe_str(row.get("description"))
        job_url = safe_str(row.get("job_url"))

        # Skip if missing critical fields
        if not title or not company or not job_url or job_url == "N/A":
            return None

        # Parse date
        date_posted = None
        date_str = row.get("date_posted")
        if pd.notna(date_str) and date_str:
            try:
                if isinstance(date_str, str):
                    date_posted = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                elif isinstance(date_str, datetime):
                    date_posted = date_str
            except Exception:
                pass

        # Parse salary
        salary_min = None
        salary_max = None
        try:
            if pd.notna(row.get("salary_min")):
                salary_min = int(row.get("salary_min", 0)) or None
            if pd.notna(row.get("salary_max")):
                salary_max = int(row.get("salary_max", 0)) or None
        except Exception:
            pass

        # Normalize remote type
        remote_type = "on_site"
        remote_str = safe_str(row.get("remote_type")).lower()
        if "remote" in remote_str:
            remote_type = "remote"
        elif "hybrid" in remote_str:
            remote_type = "hybrid"

        # Normalize employment type
        employment_type = "full_time"
        emp_str = safe_str(row.get("employment_type")).lower()
        if "contract" in emp_str:
            employment_type = "contract"
        elif "part" in emp_str:
            employment_type = "part_time"
        elif "intern" in emp_str:
            employment_type = "internship"

        # Extract skills and tools from description
        skills = self._extract_skills_from_text(description)
        tools = self._extract_tools_from_text(description)

        # Source job ID
        source_job_id = safe_str(row.get("job_id")) or job_url

        # Convert row to dict with JSON-serializable values
        raw_data = self._make_json_serializable(row.to_dict() if hasattr(row, "to_dict") else {})

        return RawJob(
            title=title,
            company=company,
            location=location,
            description=description[:10000] if description else "",  # Limit description length
            url=job_url,
            source=f"jobspy_{site}",
            source_job_id=source_job_id,
            date_posted=date_posted,
            salary_min=salary_min,
            salary_max=salary_max,
            currency="CAD",
            remote_type=remote_type,
            employment_type=employment_type,
            requirements=str(row.get("requirements", ""))[:5000] if pd.notna(row.get("requirements")) else None,
            preferred_qualifications=str(row.get("preferred_qualifications", ""))[:5000] if pd.notna(row.get("preferred_qualifications")) else None,
            skills=skills,
            tools=tools,
            raw_data=raw_data,
        )

    def _make_json_serializable(self, obj: Any) -> Any:
        """Recursively convert date/datetime objects to ISO format strings for JSON serialization."""
        from datetime import date, datetime
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(v) for v in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        elif pd.isna(obj):
            return None
        else:
            return obj

    def _build_search_terms(self, filters: Dict[str, Any]) -> List[str]:
        """Build search terms from filters."""
        terms = []

        # Primary titles (highest priority)
        primary_titles = filters.get("primary_titles", [])
        terms.extend(primary_titles[:5])  # Limit to top 5

        # Secondary titles
        secondary_titles = filters.get("secondary_titles", [])
        terms.extend(secondary_titles[:3])  # Limit to top 3

        # If no titles from filters, use defaults
        if not terms:
            terms = ["Data Analyst", "Business Analyst", "Data Scientist", "Data Engineer"]

        return terms

    def _build_locations(self, filters: Dict[str, Any]) -> List[str]:
        """Build locations from filters."""
        locations = filters.get("locations", [])

        if not locations:
            # Default Canadian locations
            locations = [
                "Toronto, ON",
                "Mississauga, ON",
                "Vancouver, BC",
                "Montreal, QC",
                "Calgary, AB",
                "Ottawa, ON",
                "Remote Canada",
            ]

        return locations[:5]  # Limit to top 5 locations

    def _extract_skills_from_text(self, text: str) -> List[str]:
        """Extract common tech skills from job description."""
        if not text:
            return []

        text_lower = text.lower()
        skill_keywords = [
            "python", "sql", "r", "java", "javascript", "typescript", "c++", "c#",
            "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "keras",
            "tableau", "power bi", "looker", "metabase", "superset",
            "aws", "azure", "gcp", "cloud", "docker", "kubernetes", "terraform",
            "git", "github", "gitlab", "ci/cd", "jenkins",
            "spark", "hadoop", "kafka", "airflow", "dbt",
            "excel", "vba", "power query",
            "statistics", "machine learning", "deep learning", "nlp",
            "data visualization", "dashboard", "reporting",
            "etl", "data pipeline", "data warehouse", "snowflake", "redshift", "bigquery",
        ]

        found = []
        for skill in skill_keywords:
            if skill in text_lower:
                found.append(skill.title())

        return found[:20]  # Limit

    def _extract_tools_from_text(self, text: str) -> List[str]:
        """Extract common tools from job description."""
        if not text:
            return []

        text_lower = text.lower()
        tool_keywords = [
            "jira", "confluence", "slack", "teams", "notion",
            "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
            "linux", "windows", "macos",
            "vscode", "pycharm", "intellij",
        ]

        found = []
        for tool in tool_keywords:
            if tool in text_lower:
                found.append(tool.title())

        return found[:10]

    def _deduplicate_jobs(self, jobs: List[RawJob]) -> List[RawJob]:
        """Deduplicate jobs by URL and title+company combination."""
        seen_urls = set()
        seen_fingerprints = set()
        unique = []

        for job in jobs:
            # URL-based deduplication
            if job.url in seen_urls:
                continue

            # Fingerprint-based (title + company + location)
            fingerprint = f"{job.title.lower().strip()}|{job.company.lower().strip()}|{job.location.lower().strip()}"
            if fingerprint in seen_fingerprints:
                continue

            seen_urls.add(job.url)
            seen_fingerprints.add(fingerprint)
            unique.append(job)

        return unique

    async def get_job_details(self, job_url: str) -> Optional[RawJob]:
        """Get detailed job info - jobspy doesn't support single URL fetch well."""
        # Jobspy is designed for search, not individual URL fetching
        # Return None to fall back to database info
        return None

    async def close(self):
        """Cleanup - nothing to close for jobspy."""
        pass


async def create_jobspy_source(config: Dict[str, Any] = None) -> JobSpySource:
    """Factory function to create a JobSpySource."""
    source = JobSpySource(config)
    return source