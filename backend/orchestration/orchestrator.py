"""
Main Orchestrator for Phase 8.
Coordinates all phases of the job application automation pipeline.
"""
import asyncio
import signal
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from pathlib import Path

from config import load_settings
from database.database import init_db, close_db, get_session
from database.repositories import RepositoryFactory
from database.models import Job, JobStatus, Application, ApplicationStatus
from agents.profile_agent import ProfileAgent
from agents.discovery_agent import DiscoveryAgent, create_discovery_agent
from agents.matching_agent import MatchingAgent
from resume import (
    ResumeAgent,
    ResumeValidator,
    create_resume_agent,
    create_resume_validator,
)
from browser.automation import BrowserAutomation, BrowserConfig
from application.submission import ApplicationSubmission, SubmissionMode, ApplicationContext
from application.tracker import ApplicationTracker, ApplicationQueue, RetryStrategy
from application.recovery import CrashRecovery, with_crash_recovery, RecoveryPlan, RecoveryState
from orchestration.scheduler import JobScheduler, ScheduleConfig
from orchestration.queue_manager import QueueManager
from orchestration.monitor import SystemMonitor
from utils.logger import get_logger

logger = get_logger(__name__)


class PipelineMode(Enum):
    """Pipeline execution modes."""
    DRY_RUN = "dry_run"      # Full pipeline, no submissions
    MANUAL = "manual"        # Fill forms, stop before submit
    AUTO = "auto"            # Full automation with submissions


class PipelinePhase(Enum):
    """Pipeline phases."""
    SETUP = "setup"
    SEARCH = "search"
    ANALYZE = "analyze"
    RESUMES = "resumes"
    APPLY = "apply"
    EXPORT = "export"


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution."""
    mode: PipelineMode = PipelineMode.DRY_RUN
    search_limit: int = 50
    analyze_limit: int = 50
    resume_limit: int = 20
    apply_limit: int = 10
    enable_browser: bool = True
    headless: bool = True
    dry_run_search: bool = False
    force_rematch: bool = False
    validate_resumes: bool = True
    export_path: str = "output/job_applications.xlsx"


@dataclass
class PipelineStats:
    """Pipeline execution statistics."""
    start_time: datetime
    end_time: Optional[datetime] = None
    jobs_found: int = 0
    jobs_new: int = 0
    jobs_analyzed: int = 0
    jobs_qualified: int = 0
    resumes_generated: int = 0
    resumes_validated: int = 0
    applications_submitted: int = 0
    applications_failed: int = 0
    human_interventions: int = 0
    errors: List[str] = field(default_factory=list)
    phase_durations: Dict[str, float] = field(default_factory=dict)


class Orchestrator:
    """
    Main orchestrator coordinating all phases of the job application pipeline.
    Handles the complete flow from job discovery to application submission.
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.settings = load_settings()
        self.stats = PipelineStats(start_time=datetime.utcnow())
        self.profile: Optional[Dict[str, Any]] = None
        self.browser: Optional[BrowserAutomation] = None
        self.tracker = ApplicationTracker()
        self.queue_manager = QueueManager()
        self.scheduler: Optional[JobScheduler] = None
        self.monitor = SystemMonitor()
        self.recovery: Optional[CrashRecovery] = None
        self._running = False
        self._shutdown_requested = False

    async def __aenter__(self) -> "Orchestrator":
        await init_db()
        await self._load_profile()

        # Initialize browser if needed
        if self.config.enable_browser:
            browser_config = BrowserConfig(headless=self.config.headless)
            self.browser = BrowserAutomation(browser_config)
            await self.browser.start()

        # Initialize crash recovery
        self.recovery = CrashRecovery()
        self.recovery.install_signal_handlers()

        # Initialize scheduler
        schedule_config = ScheduleConfig(
            search_interval_hours=self.settings.get("scheduler", {}).get("search_interval_hours", 6),
            analyze_interval_hours=self.settings.get("scheduler", {}).get("analyze_interval_hours", 2),
            apply_interval_hours=self.settings.get("scheduler", {}).get("apply_interval_hours", 4),
            export_interval_hours=self.settings.get("scheduler", {}).get("export_interval_hours", 24),
        )
        self.scheduler = JobScheduler(schedule_config)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._running = False

        if self.browser:
            await self.browser.close()

        if self.scheduler:
            await self.scheduler.stop()

        await self.monitor.stop()
        await close_db()

    async def _load_profile(self):
        """Load candidate profile from database."""
        async with get_session() as session:
            repos = RepositoryFactory(session)
            profile = await repos.candidates.get_profile()
            if profile:
                # Load experience notes separately
                exp_notes = profile.experience_notes if hasattr(profile, 'experience_notes') else []
                self.profile = {
                    "name": profile.name,
                    "email": profile.email,
                    "phone": profile.phone,
                    "address": profile.address,
                    "city": profile.city,
                    "province": profile.province,
                    "postal_code": profile.postal_code,
                    "country": profile.country,
                    "work_authorization": profile.work_authorization,
                    "linkedin_url": profile.linkedin_url,
                    "portfolio_url": profile.portfolio_url,
                    "github_url": profile.github_url,
                    "notice_period_weeks": profile.notice_period_weeks,
                    "salary_expectation_min": profile.salary_expectation_min,
                    "salary_expectation_max": profile.salary_expectation_max,
                    "salary_currency": profile.salary_currency,
                    "education": profile.education,
                    "certifications": profile.certifications,
                    "employment_history": profile.employment_history,
                    "skills": profile.skills,
                    "technical_skills": profile.technical_skills,
                    "business_skills": profile.business_skills,
                    "tools": profile.tools,
                    "programming_languages": profile.programming_languages,
                    "industries": profile.industries,
                    "job_titles": profile.job_titles,
                    "preferred_job_titles": profile.preferred_job_titles,
                    "preferred_locations": profile.preferred_locations,
                    "remote_preferences": profile.remote_preferences,
                    "employment_preferences": profile.employment_preferences,
                    "excluded_titles": profile.excluded_titles,
                    "excluded_industries": profile.excluded_industries,
                    "excluded_requirements": profile.excluded_requirements,
                    "additional_experience": [
                        {
                            "id": str(e.id),
                            "original_text": e.original_text,
                            "category": e.category,
                            "verified": e.verified,
                            "source": e.source,
                        }
                        for e in exp_notes
                    ],
                }
                logger.info(f"Loaded profile for {profile.name}")

    async def run_pipeline(self) -> PipelineStats:
        """
        Run the complete automation pipeline.
        """
        self._running = True
        logger.info(f"Starting pipeline in {self.config.mode.value} mode")

        try:
            # Phase 1: Search for jobs
            if self._running:
                await self._run_phase(PipelinePhase.SEARCH, self._phase_search)

            # Phase 2: Analyze jobs
            if self._running:
                await self._run_phase(PipelinePhase.ANALYZE, self._phase_analyze)

            # Phase 3: Generate resumes
            if self._running:
                await self._run_phase(PipelinePhase.RESUMES, self._phase_resumes)

            # Phase 4: Apply to jobs
            if self._running:
                await self._run_phase(PipelinePhase.APPLY, self._phase_apply)

            # Phase 5: Export results
            if self._running:
                await self._run_phase(PipelinePhase.EXPORT, self._phase_export)

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            self.stats.errors.append(str(e))
            raise
        finally:
            self.stats.end_time = datetime.utcnow()
            self._running = False

        return self.stats

    async def _run_phase(self, phase: PipelinePhase, phase_func: Callable):
        """Run a single pipeline phase with timing."""
        start = datetime.utcnow()
        logger.info(f"Starting phase: {phase.value}")

        try:
            await phase_func()
        except Exception as e:
            logger.error(f"Phase {phase.value} failed: {e}")
            self.stats.errors.append(f"{phase.value}: {str(e)}")
            raise
        finally:
            duration = (datetime.utcnow() - start).total_seconds()
            self.stats.phase_durations[phase.value] = duration
            logger.info(f"Phase {phase.value} completed in {duration:.1f}s")

    async def _phase_search(self):
        """Phase 1: Search for jobs."""
        logger.info("Phase 1: Job Discovery")

        agent = await create_discovery_agent()
        result = await agent.discover_jobs(
            limit_per_source=self.config.search_limit,
            dry_run=self.config.dry_run_search,
        )
        await agent.close()

        self.stats.jobs_found = result.jobs_found
        self.stats.jobs_new = result.jobs_new

        logger.info(f"Found {result.jobs_found} jobs, {result.jobs_new} new")

    async def _phase_analyze(self):
        """Phase 2: Analyze and score jobs."""
        logger.info("Phase 2: Job Analysis")

        agent = MatchingAgent()
        result = await agent.match_jobs(
            limit=self.config.analyze_limit,
            force_rematch=self.config.force_rematch,
        )

        self.stats.jobs_analyzed = result.jobs_processed
        self.stats.jobs_qualified = result.jobs_qualified

        logger.info(f"Analyzed {result.jobs_processed} jobs, {result.jobs_qualified} qualified")

    async def _phase_resumes(self):
        """Phase 3: Generate and validate resumes."""
        logger.info("Phase 3: Resume Generation")

        resume_agent = await create_resume_agent()
        validator = await create_resume_validator()

        # Get qualified jobs
        async with get_session() as session:
            repos = RepositoryFactory(session)
            qualified_jobs = await repos.jobs.get_jobs_by_status(
                JobStatus.QUALIFIED,
                limit=self.config.resume_limit
            )

        for job in qualified_jobs:
            if not self._running:
                break

            try:
                result = await resume_agent.generate_resume(job.id)

                if result.success:
                    self.stats.resumes_generated += 1

                    if self.config.validate_resumes:
                        val_result = await validator.validate_resume(result.resume_id)
                        if val_result.success:
                            self.stats.resumes_validated += 1

            except Exception as e:
                logger.error(f"Resume generation failed for job {job.id}: {e}")
                self.stats.errors.append(f"Resume job {job.id}: {str(e)}")

        logger.info(f"Generated {self.stats.resumes_generated} resumes, validated {self.stats.resumes_validated}")

    async def _phase_apply(self):
        """Phase 4: Apply to jobs."""
        logger.info(f"Phase 4: Application Submission ({self.config.mode.value})")

        # Determine submission mode
        if self.config.mode == PipelineMode.DRY_RUN:
            submission_mode = SubmissionMode.DRY_RUN
        elif self.config.mode == PipelineMode.MANUAL:
            submission_mode = SubmissionMode.MANUAL
        else:
            submission_mode = SubmissionMode.AUTO

        # Get jobs ready to apply
        async with get_session() as session:
            repos = RepositoryFactory(session)
            ready_jobs = await repos.jobs.get_jobs_by_status(
                JobStatus.RESUME_CREATED,
                limit=self.config.apply_limit
            )

        if not ready_jobs:
            logger.info("No jobs ready for application")
            return

        # Process applications
        for job in ready_jobs:
            if not self._running:
                break

            if not job.application_url:
                logger.warning(f"Job {job.id} has no apply URL, skipping")
                continue

            # Get resume for this job
            async with get_session() as session:
                repos = RepositoryFactory(session)
                resume = await repos.resumes.get_resume_by_job(job.id)
                resume_path = resume.file_path if resume else None

            if not resume_path:
                logger.warning(f"Job {job.id} has no resume, skipping")
                continue

            # Check if already applied
            async with get_session() as session:
                repos = RepositoryFactory(session)
                existing = await repos.applications.get_application_by_job(job.id)
                if existing and existing.status == ApplicationStatus.APPLIED:
                    logger.info(f"Job {job.id} already applied, skipping")
                    continue

            # Submit application with crash recovery
            try:
                context = ApplicationContext(
                    job_id=job.id,
                    apply_url=job.application_url,
                    profile=self.profile,
                    resume_path=resume_path,
                    mode=submission_mode,
                    company_name=job.company,
                    job_title=job.title,
                )

                # Use crash recovery wrapper
                async def submit_with_recovery(**kwargs):
                    async with ApplicationSubmission(automation=self.browser) as submission:
                        return await submission.submit_application(context)

                result = await with_crash_recovery(
                    job_id=job.id,
                    application_id=None,
                    submit_func=submit_with_recovery,
                    recovery=self.recovery,
                )

                if result.success:
                    self.stats.applications_submitted += 1
                    logger.info(f"Applied to job {job.id} ({job.company} - {job.title})")

                    if result.requires_human:
                        self.stats.human_interventions += 1
                else:
                    self.stats.applications_failed += 1
                    logger.error(f"Application failed for job {job.id}: {result.errors}")

            except Exception as e:
                self.stats.applications_failed += 1
                logger.error(f"Application error for job {job.id}: {e}")
                self.stats.errors.append(f"Apply job {job.id}: {str(e)}")

            # Small delay between applications
            await asyncio.sleep(2)

        logger.info(f"Submitted {self.stats.applications_submitted}, failed {self.stats.applications_failed}")

    async def _phase_export(self):
        """Phase 5: Export to Excel."""
        logger.info("Phase 5: Export")

        try:
            from excel import export_to_excel
            file_path = await export_to_excel(self.config.export_path)
            logger.info(f"Exported to {file_path}")
        except Exception as e:
            logger.error(f"Export failed: {e}")
            self.stats.errors.append(f"Export: {str(e)}")

    async def run_single_job(self, job_id: int, mode: PipelineMode = PipelineMode.MANUAL) -> bool:
        """Run the application process for a single job."""
        logger.info(f"Running single job application for job {job_id}")

        # Get job details
        async with get_session() as session:
            repos = RepositoryFactory(session)
            job = await repos.jobs.get_job(job_id)

        if not job:
            logger.error(f"Job {job_id} not found")
            return False

        if not job.application_url:
            logger.error(f"Job {job_id} has no apply URL")
            return False

        # Get resume
        async with get_session() as session:
            repos = RepositoryFactory(session)
            resume = await repos.resumes.get_resume_by_job(job_id)
            resume_path = resume.file_path if resume else None

        if not resume_path:
            logger.error(f"Job {job_id} has no resume")
            return False

        # Determine submission mode
        if mode == PipelineMode.DRY_RUN:
            submission_mode = SubmissionMode.DRY_RUN
        elif mode == PipelineMode.MANUAL:
            submission_mode = SubmissionMode.MANUAL
        else:
            submission_mode = SubmissionMode.AUTO

        # Submit
        context = ApplicationContext(
            job_id=job.id,
            apply_url=job.application_url,
            profile=self.profile,
            resume_path=resume_path,
            mode=submission_mode,
            company_name=job.company,
            job_title=job.title,
        )

        async with ApplicationSubmission(automation=self.browser) as submission:
            result = await submission.submit_application(context)

        return result.success

    def request_shutdown(self):
        """Request graceful shutdown."""
        self._shutdown_requested = True
        self._running = False

    def get_stats(self) -> PipelineStats:
        """Get current pipeline statistics."""
        return self.stats


async def run_orchestrator(
    mode: PipelineMode = PipelineMode.DRY_RUN,
    search_limit: int = 50,
    analyze_limit: int = 50,
    resume_limit: int = 20,
    apply_limit: int = 10,
    headless: bool = True,
    validate: bool = True,
) -> PipelineStats:
    """Convenience function to run the orchestrator."""
    config = PipelineConfig(
        mode=mode,
        search_limit=search_limit,
        analyze_limit=analyze_limit,
        resume_limit=resume_limit,
        apply_limit=apply_limit,
        headless=headless,
        validate_resumes=validate,
    )

    async with Orchestrator(config) as orchestrator:
        return await orchestrator.run_pipeline()