"""
Discovery Agent - Orchestrates job search across multiple sources.
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from pathlib import Path

from job_sources import JobSource, RawJob, list_sources, get_source_factory
from database.database import get_session
from database.repositories import RepositoryFactory
from database.models import Job, JobSource as JobSourceModel, JobStatus, RemoteType, EmploymentType
from utils.hashing import job_fingerprint, content_hash
from utils.logger import get_logger
from config import load_settings


logger = get_logger(__name__)


@dataclass
class DiscoveryResult:
    """Result of a discovery run."""
    jobs_found: int = 0
    jobs_new: int = 0
    jobs_duplicate: int = 0
    jobs_failed: int = 0
    sources_used: List[str] = None
    errors: List[str] = None

    def __post_init__(self):
        if self.sources_used is None:
            self.sources_used = []
        if self.errors is None:
            self.errors = []


class DiscoveryAgent:
    """Agent responsible for discovering jobs from multiple sources."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or load_settings()
        self.sources: List[JobSource] = []
        self._initialized = False

    async def initialize(self):
        """Async initialization - load job sources."""
        if self._initialized:
            return
        await self._load_sources()
        self._initialized = True

    async def _load_sources(self):
        """Load configured job sources from settings."""
        job_sources_config = self.config.get("job_sources", {})

        for source_name, source_config in job_sources_config.items():
            if not source_config.get("enabled", True):
                logger.info(f"Source {source_name} is disabled, skipping")
                continue

            try:
                factory = get_source_factory(source_name)
                source = await factory(source_config)
                self.sources.append(source)
                logger.info(f"Loaded job source: {source_name}")
            except Exception as e:
                logger.error(f"Failed to load job source {source_name}: {e}")

        # No fallback - if no sources loaded, log warning
        if not self.sources:
            logger.warning("No job sources loaded! Please configure at least one job source in config/settings.yaml")

        logger.info(f"Loaded job sources: {[s.name for s in self.sources]}")

    def add_source(self, source: JobSource):
        """Add a job source."""
        self.sources.append(source)

    async def close(self):
        """Close all sources and cleanup."""
        for source in self.sources:
            if hasattr(source, 'close'):
                try:
                    await source.close()
                except Exception as e:
                    logger.error(f"Error closing source {source.name}: {e}")

    async def discover_jobs(
        self,
        filters: Dict[str, Any] = None,
        limit_per_source: int = 50,
        dry_run: bool = False,
    ) -> DiscoveryResult:
        """
        Discover jobs from all configured sources.

        Args:
            filters: Search filters (from job_filters.yaml)
            limit_per_source: Max jobs per source
            dry_run: If True, don't save to database

        Returns:
            DiscoveryResult with statistics
        """
        if filters is None:
            filters = self._load_job_filters()

        result = DiscoveryResult()
        all_jobs: List[RawJob] = []

        # Search each source
        for source in self.sources:
            try:
                logger.info(f"Searching jobs from {source.name}")
                result.sources_used.append(source.name)

                jobs = await source.search(filters, limit_per_source)
                logger.info(f"Found {len(jobs)} jobs from {source.name}")
                result.jobs_found += len(jobs)
                all_jobs.extend(jobs)

            except Exception as e:
                error_msg = f"Error searching {source.name}: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)
                result.jobs_failed += 1

        # Deduplicate jobs
        unique_jobs = self._deduplicate_jobs(all_jobs)
        duplicates_removed = len(all_jobs) - len(unique_jobs)
        result.jobs_duplicate = duplicates_removed
        logger.info(f"Removed {duplicates_removed} duplicates, {len(unique_jobs)} unique jobs")

        # Update daily statistics for duplicates
        if duplicates_removed > 0:
            async with get_session() as session:
                repos = RepositoryFactory(session)
                await repos.statistics.increment_stat("duplicates_removed", duplicates_removed)

        # Save to database (unless dry run)
        if not dry_run and unique_jobs:
            saved = await self._save_jobs(unique_jobs)
            result.jobs_new = saved
            logger.info(f"Saved {saved} new jobs to database")

        return result

    def _load_job_filters(self) -> Dict[str, Any]:
        """Load job filters from config file."""
        import yaml
        filter_path = Path("config/job_filters.yaml")
        if filter_path.exists():
            with open(filter_path, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _deduplicate_jobs(self, jobs: List[RawJob]) -> List[RawJob]:
        """
        Deduplicate jobs using content hash and fingerprint.
        Keeps the first occurrence of each unique job.
        """
        seen_fingerprints: Set[str] = set()
        seen_hashes: Set[str] = set()
        unique_jobs = []

        for job in jobs:
            # Generate fingerprint (title + company + location)
            fingerprint = job_fingerprint(job.title, job.company, job.location)

            # Generate content hash (description + requirements)
            content = f"{job.description}{job.requirements or ''}"
            content_h = content_hash(content)

            # Check if we've seen this job
            is_duplicate = False

            if fingerprint in seen_fingerprints:
                is_duplicate = True
                logger.debug(f"Duplicate by fingerprint: {job.title} at {job.company}")
            elif content_h in seen_hashes:
                is_duplicate = True
                logger.debug(f"Duplicate by content hash: {job.title} at {job.company}")

            if not is_duplicate:
                seen_fingerprints.add(fingerprint)
                seen_hashes.add(content_h)
                unique_jobs.append(job)

        return unique_jobs

    async def _save_jobs(self, jobs: List[RawJob]) -> int:
        """Save jobs to database."""
        saved_count = 0

        async with get_session() as session:
            repos = RepositoryFactory(session)

            for job in jobs:
                try:
                    # Check if job already exists (by canonical_url)
                    existing = await repos.jobs.get_by_url(job.url)
                    if existing:
                        # Add source reference
                        await self._add_job_source(session, existing.id, job)
                        continue

                    # Create new job
                    job_model = Job(
                        canonical_url=job.url,
                        source_urls=[job.url],
                        source=job.source,
                        title=job.title,
                        company=job.company,
                        location=job.location,
                        remote_type=RemoteType(job.remote_type) if job.remote_type else RemoteType.ON_SITE,
                        employment_type=EmploymentType(job.employment_type) if job.employment_type else EmploymentType.FULL_TIME,
                        date_posted=job.date_posted,
                        salary_min=job.salary_min,
                        salary_max=job.salary_max,
                        currency=job.currency or "CAD",
                        description=job.description,
                        requirements=job.requirements,
                        preferred_qualifications=job.preferred_qualifications,
                        skills=job.skills or [],
                        tools=job.tools or [],
                        content_hash=content_hash(f"{job.description}{job.requirements or ''}"),
                        status=JobStatus.DISCOVERED,
                    )

                    session.add(job_model)
                    await session.flush()  # Get the ID

                    # Add source reference
                    await self._add_job_source(session, job_model.id, job)

                    saved_count += 1

                except Exception as e:
                    logger.error(f"Error saving job {job.title}: {e}")
                    await session.rollback()

            await session.commit()

        # Update daily statistics
        if saved_count > 0:
            async with get_session() as session:
                repos = RepositoryFactory(session)
                await repos.statistics.increment_stat("jobs_found", saved_count)

        return saved_count

    async def _add_job_source(self, session, job_id: int, raw_job: RawJob):
        """Add a job source reference."""
        source_ref = JobSourceModel(
            job_id=job_id,
            source=raw_job.source,
            source_url=raw_job.url,
            source_job_id=raw_job.source_job_id,
            raw_data=raw_job.raw_data or {},
        )
        session.add(source_ref)

    async def get_job_details(self, job_id: int) -> Optional[RawJob]:
        """Get detailed job information for a specific job ID."""
        async with get_session() as session:
            repos = RepositoryFactory(session)
            job = await repos.jobs.get_by_id(job_id)

            if not job:
                return None

            # Try to get details from the source
            for source in self.sources:
                if source.name == job.source:
                    try:
                        details = await source.get_job_details(job.canonical_url)
                        if details:
                            return details
                    except Exception as e:
                        logger.error(f"Error getting job details from {source.name}: {e}")

            # Return basic info from database
            return RawJob(
                title=job.title,
                company=job.company,
                location=job.location,
                description=job.description,
                url=job.canonical_url,
                source=job.source,
                source_job_id=None,
                date_posted=job.date_posted,
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                currency=job.currency,
                remote_type=job.remote_type.value if job.remote_type else "on_site",
                employment_type=job.employment_type.value if job.employment_type else "full_time",
                requirements=job.requirements,
                preferred_qualifications=job.preferred_qualifications,
                skills=job.skills,
                tools=job.tools,
                raw_data={},
            )


async def create_discovery_agent(config: Dict[str, Any] = None) -> DiscoveryAgent:
    """Factory function to create a DiscoveryAgent."""
    agent = DiscoveryAgent(config)
    await agent.initialize()
    return agent