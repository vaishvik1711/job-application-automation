"""
Repository layer for database operations.
"""
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    CandidateProfile, CandidateExperience, Job, JobSource, JobMatch,
    Resume, Application, ScreeningQuestion, ApplicationEvent, ApplicationError,
    DailyStatistics, JobStatus, ApplicationStatus
)


class CandidateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_profile(self) -> Optional[CandidateProfile]:
        result = await self.session.execute(
            select(CandidateProfile).options(selectinload(CandidateProfile.experience_notes))
        )
        return result.scalars().first()

    async def create_profile(self, **kwargs) -> CandidateProfile:
        profile = CandidateProfile(**kwargs)
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def update_profile(self, profile: CandidateProfile, **kwargs) -> CandidateProfile:
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        profile.updated_at = datetime.utcnow()
        await self.session.flush()
        return profile

    async def add_experience_note(self, profile_id: int, **kwargs) -> CandidateExperience:
        note = CandidateExperience(profile_id=profile_id, **kwargs)
        self.session.add(note)
        await self.session.flush()
        return note

    async def get_experience_notes(self, profile_id: int) -> List[CandidateExperience]:
        result = await self.session.execute(
            select(CandidateExperience).where(CandidateExperience.profile_id == profile_id)
        )
        return list(result.scalars().all())


class JobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_job(self, **kwargs) -> Job:
        job = Job(**kwargs)
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_job(self, job_id: int) -> Optional[Job]:
        result = await self.session.execute(
            select(Job).options(selectinload(Job.sources_rel)).where(Job.id == job_id)
        )
        return result.scalars().first()

    async def get_job_by_canonical_url(self, url: str) -> Optional[Job]:
        result = await self.session.execute(
            select(Job).where(Job.canonical_url == url)
        )
        return result.scalars().first()

    async def get_job_by_content_hash(self, hash: str) -> Optional[Job]:
        result = await self.session.execute(
            select(Job).where(Job.content_hash == hash)
        )
        return result.scalars().first()

    async def get_potential_duplicates(self, company: str, title: str, location: str) -> List[Job]:
        result = await self.session.execute(
            select(Job).where(
                and_(
                    Job.company.ilike(f"%{company}%"),
                    Job.title.ilike(f"%{title}%"),
                    Job.location.ilike(f"%{location}%"),
                )
            )
        )
        return list(result.scalars().all())

    async def get_jobs_by_status(self, status: JobStatus, limit: int = 100) -> List[Job]:
        result = await self.session.execute(
            select(Job)
            .where(Job.status == status)
            .order_by(desc(Job.discovered_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_jobs_for_matching(self, limit: int = 100) -> List[Job]:
        result = await self.session.execute(
            select(Job)
            .where(Job.status.in_([JobStatus.DEDUPLICATED, JobStatus.DISCOVERED]))
            .order_by(desc(Job.discovered_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_unmatched(self, limit: int = 100) -> List[Job]:
        """Get jobs that don't have a match yet."""
        result = await self.session.execute(
            select(Job)
            .outerjoin(JobMatch, Job.id == JobMatch.job_id)
            .where(JobMatch.id.is_(None))
            .where(Job.status.in_([JobStatus.DISCOVERED, JobStatus.DEDUPLICATED]))
            .order_by(desc(Job.discovered_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_url(self, url: str) -> Optional[Job]:
        """Get job by canonical URL (alias for get_job_by_canonical_url)."""
        return await self.get_job_by_canonical_url(url)

    async def get_all(self, limit: int = 100, status: JobStatus = None) -> List[Job]:
        """Get all jobs with optional status filter."""
        query = select(Job).order_by(desc(Job.discovered_at)).limit(limit)
        if status:
            query = query.where(Job.status == status)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_status(self, job_id: int, status: JobStatus) -> Optional[Job]:
        """Update job status (alias for update_job_status)."""
        return await self.update_job_status(job_id, status)

    async def get_qualified_jobs(self, limit: int = 100) -> List[Job]:
        result = await self.session.execute(
            select(Job)
            .where(Job.status == JobStatus.QUALIFIED)
            .order_by(desc(Job.discovered_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_job_status(self, job_id: int, status: JobStatus) -> Optional[Job]:
        job = await self.get_job(job_id)
        if job:
            job.status = status
            await self.session.flush()
        return job

    async def add_source_to_job(self, job_id: int, **kwargs) -> JobSource:
        source = JobSource(job_id=job_id, **kwargs)
        self.session.add(source)
        await self.session.flush()
        return source


class JobMatchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_match(self, job_id: int, **kwargs) -> JobMatch:
        match = JobMatch(job_id=job_id, **kwargs)
        self.session.add(match)
        await self.session.flush()
        return match

    async def get_match(self, job_id: int) -> Optional[JobMatch]:
        result = await self.session.execute(
            select(JobMatch).where(JobMatch.job_id == job_id)
        )
        return result.scalars().first()

    async def get_by_job_id(self, job_id: int) -> Optional[JobMatch]:
        """Alias for get_match."""
        return await self.get_match(job_id)

    async def update_match(self, match_id: int, **kwargs) -> Optional[JobMatch]:
        result = await self.session.execute(
            select(JobMatch).where(JobMatch.id == match_id)
        )
        match = result.scalars().first()
        if match:
            for key, value in kwargs.items():
                if hasattr(match, key):
                    setattr(match, key, value)
            await self.session.flush()
        return match

    async def get_matches_above_score(self, min_score: float, limit: int = 100) -> List[JobMatch]:
        result = await self.session.execute(
            select(JobMatch)
            .where(JobMatch.match_score >= min_score)
            .order_by(desc(JobMatch.match_score))
            .limit(limit)
        )
        return list(result.scalars().all())


class ResumeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_resume(self, **kwargs) -> Resume:
        resume = Resume(**kwargs)
        self.session.add(resume)
        await self.session.flush()
        return resume

    async def get_resume(self, resume_id: int) -> Optional[Resume]:
        result = await self.session.execute(
            select(Resume).where(Resume.id == resume_id)
        )
        return result.scalars().first()

    async def get_resume_by_job(self, job_id: int) -> Optional[Resume]:
        result = await self.session.execute(
            select(Resume).where(Resume.job_id == job_id)
        )
        return result.scalars().first()

    async def get_latest_resume_version(self, candidate_id: int, job_id: int) -> int:
        result = await self.session.execute(
            select(func.max(Resume.version))
            .where(and_(Resume.candidate_id == candidate_id, Resume.job_id == job_id))
        )
        return result.scalar() or 0

    async def get_unvalidated(self, limit: int = 50) -> List[Resume]:
        result = await self.session.execute(
            select(Resume)
            .where(Resume.validation_score.is_(None))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_validation(
        self,
        resume_id: int,
        validation_score: float = None,
        truthfulness_score: float = None,
        format_score: float = None,
        relevance_score: float = None,
        issues: List[dict] = None,
        traceability: List[dict] = None,
    ) -> Optional[Resume]:
        resume = await self.get_resume(resume_id)
        if resume:
            if validation_score is not None:
                resume.validation_score = validation_score
            if truthfulness_score is not None:
                resume.truthfulness_score = truthfulness_score
            if format_score is not None:
                resume.format_score = format_score
            if relevance_score is not None:
                resume.relevance_score = relevance_score
            if issues is not None:
                resume.validation_issues = issues
            if traceability is not None:
                resume.traceability = traceability
            await self.session.flush()
        return resume


class ApplicationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_application(self, **kwargs) -> Application:
        app = Application(**kwargs)
        self.session.add(app)
        await self.session.flush()
        return app

    async def get_application(self, app_id: int) -> Optional[Application]:
        result = await self.session.execute(
            select(Application)
            .options(
                selectinload(Application.screening_questions),
                selectinload(Application.events),
                selectinload(Application.errors),
            )
            .where(Application.id == app_id)
        )
        return result.scalars().first()

    async def get_application_by_job(self, job_id: int) -> Optional[Application]:
        result = await self.session.execute(
            select(Application).where(Application.job_id == job_id)
        )
        return result.scalars().first()

    async def update_application_status(self, app_id: int, status: ApplicationStatus) -> Optional[Application]:
        app = await self.get_application(app_id)
        if app:
            app.status = status
            await self.session.flush()
        return app

    async def add_screening_question(self, application_id: int, **kwargs) -> ScreeningQuestion:
        question = ScreeningQuestion(application_id=application_id, **kwargs)
        self.session.add(question)
        await self.session.flush()
        return question

    async def add_event(self, application_id: int, **kwargs) -> ApplicationEvent:
        event = ApplicationEvent(application_id=application_id, **kwargs)
        self.session.add(event)
        await self.session.flush()
        return event

    async def add_error(self, application_id: int, **kwargs) -> ApplicationError:
        error = ApplicationError(application_id=application_id, **kwargs)
        self.session.add(error)
        await self.session.flush()
        return error

    async def get_applications_today(self) -> List[Application]:
        today = date.today()
        result = await self.session.execute(
            select(Application)
            .where(func.date(Application.applied_at) == today)
            .order_by(desc(Application.applied_at))
        )
        return list(result.scalars().all())


class StatisticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_today(self) -> DailyStatistics:
        today = date.today()
        result = await self.session.execute(
            select(DailyStatistics).where(DailyStatistics.date == today)
        )
        stats = result.scalars().first()
        if not stats:
            stats = DailyStatistics(date=today)
            self.session.add(stats)
            await self.session.flush()
        return stats

    async def increment_stat(self, field: str, value: int = 1) -> None:
        stats = await self.get_or_create_today()
        current = getattr(stats, field, 0)
        setattr(stats, field, current + value)
        stats.updated_at = datetime.utcnow()
        await self.session.flush()

    async def update_average_match_score(self) -> None:
        stats = await self.get_or_create_today()
        result = await self.session.execute(
            select(func.avg(JobMatch.match_score)).where(JobMatch.match_score.isnot(None))
        )
        avg = result.scalar()
        if avg:
            stats.average_match_score = round(float(avg), 1)
            await self.session.flush()


class RepositoryFactory:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.candidates = CandidateRepository(session)
        self.jobs = JobRepository(session)
        self.matches = JobMatchRepository(session)
        self.resumes = ResumeRepository(session)
        self.applications = ApplicationRepository(session)
        self.statistics = StatisticsRepository(session)

    async def get_resume_generation_data(self, job_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch all data needed for resume generation.
        Returns dict with: job, match, profile, experience_notes
        """
        from sqlalchemy import select
        from database.models import Job, JobMatch, CandidateProfile, CandidateExperience

        # JobMatch has no FK/relationship to CandidateProfile, so its join
        # cannot be inferred — fetch job+match via outerjoin so jobs without prior match succeed,
        # then get the singleton candidate profile separately (single-candidate system).
        result = await self.session.execute(
            select(Job, JobMatch)
            .outerjoin(JobMatch, Job.id == JobMatch.job_id)
            .where(Job.id == job_id)
        )
        row = result.first()
        if not row:
            return None

        job, match = row

        profile = await self.candidates.get_profile()
        if not profile:
            return None

        # Load experience notes for the profile
        exp_result = await self.session.execute(
            select(CandidateExperience).where(CandidateExperience.profile_id == profile.id)
        )
        experience_notes = list(exp_result.scalars().all())

        return {
            "job": job,
            "match": match,
            "profile": profile,
            "experience_notes": experience_notes,
        }