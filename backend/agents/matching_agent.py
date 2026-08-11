"""
Matching Agent - Scores jobs against candidate profile using LLM.
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from database.database import get_session
from database.repositories import RepositoryFactory
from database.models import Job, JobMatch, JobStatus, CandidateProfile
from agents.profile_agent import CandidateProfile as PydanticCandidateProfile
from llm.client import get_llm_client
from llm.schemas import JobMatchResult
from llm.prompts import get_prompt
from utils.logger import get_logger
from config import load_settings


logger = get_logger(__name__)


@dataclass
class MatchResult:
    """Result of a matching run."""
    jobs_processed: int = 0
    jobs_matched: int = 0
    jobs_qualified: int = 0
    jobs_rejected: int = 0
    jobs_failed: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class MatchingAgent:
    """Agent responsible for matching jobs against candidate profile."""

    def __init__(self, config: Dict[str, Any] = None, llm_client=None):
        self.config = config or load_settings()
        self.llm = llm_client or get_llm_client()
        self.match_prompt = get_prompt("job_matching")
        self.min_match_score = self.config.get("min_match_score", 70)
        self.min_technical_score = self.config.get("min_technical_score", 70)
        self.min_soft_skills_score = self.config.get("min_soft_skills_score", 50)
        # Parallel processing config
        self.max_concurrent_matches = self.config.get("max_concurrent_matches", 3)

    async def match_jobs(
        self,
        job_ids: List[int] = None,
        limit: int = 50,
        force_rematch: bool = False,
    ) -> MatchResult:
        """
        Match jobs against candidate profile.

        Args:
            job_ids: Specific job IDs to match (None = all unmatched)
            limit: Maximum jobs to process
            force_rematch: Re-match already matched jobs

        Returns:
            MatchResult with statistics
        """
        result = MatchResult()

        # Get candidate profile
        profile = await self._get_candidate_profile()
        if not profile:
            result.errors.append("No candidate profile found")
            return result

        # Get jobs to match
        jobs = await self._get_jobs_to_match(job_ids, limit, force_rematch)
        logger.info(f"Matching {len(jobs)} jobs against profile (max {self.max_concurrent_matches} concurrent)")

        if not jobs:
            return result

        # Process jobs in parallel with semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent_matches)

        async def match_with_semaphore(job: Job) -> tuple[Job, Optional[JobMatchResult], Optional[str]]:
            """Match a single job with semaphore."""
            async with semaphore:
                try:
                    match_result = await self._match_single_job(job, profile)
                    return job, match_result, None
                except Exception as e:
                    error_msg = f"Error matching job {job.id}: {e}"
                    logger.error(error_msg)
                    return job, None, error_msg

        # Run all matches concurrently
        tasks = [match_with_semaphore(job) for job in jobs]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        # Process results
        for job, match_result, error_msg in results:
            if error_msg:
                result.errors.append(error_msg)
                result.jobs_failed += 1
                result.jobs_processed += 1
                continue

            if match_result:
                await self._save_match(job.id, match_result)
                result.jobs_matched += 1

                # Update job status based on recommendation
                await self._update_job_status(job.id, match_result.recommendation)
                if match_result.recommendation == "APPLY":
                    result.jobs_qualified += 1
                    # Update daily statistics
                    async with get_session() as session:
                        repos = RepositoryFactory(session)
                        await repos.statistics.increment_stat("jobs_qualified", 1)
                elif match_result.recommendation == "REJECT":
                    result.jobs_rejected += 1

            result.jobs_processed += 1

        # Update average match score
        async with get_session() as session:
            repos = RepositoryFactory(session)
            await repos.statistics.update_average_match_score()

        return result

    async def _get_candidate_profile(self) -> Optional[PydanticCandidateProfile]:
        """Load candidate profile from database."""
        async with get_session() as session:
            repos = RepositoryFactory(session)
            db_profile = await repos.candidates.get_profile()

            if not db_profile:
                return None

            # Convert to Pydantic model
            return self._db_to_pydantic_profile(db_profile)

    def _db_to_pydantic_profile(self, db_profile: CandidateProfile) -> PydanticCandidateProfile:
        """Convert database profile to Pydantic model."""
        from agents.profile_agent import (
            SkillEntry, EducationEntry, EmploymentEntry,
            CertificationEntry, ProjectEntry, AdditionalExperienceEntry,
            ProficiencyLevel, VerificationStatus
        )

        # Parse skills
        def parse_skills(skill_list: List[str], category: str) -> List[SkillEntry]:
            return [SkillEntry(name=s, category=category) for s in skill_list]

        # Handle experience notes
        experience_notes = []
        if hasattr(db_profile, 'experience_notes') and db_profile.experience_notes:
            for e in db_profile.experience_notes:
                if hasattr(e, 'original_text'):
                    experience_notes.append(AdditionalExperienceEntry(
                        id=str(e.id),
                        original_text=e.original_text,
                        category=e.category,
                        verified=e.verified,
                        source=e.source,
                    ))
                elif isinstance(e, dict):
                    experience_notes.append(AdditionalExperienceEntry(**e))

        profile = PydanticCandidateProfile(
            id=db_profile.id,
            name=db_profile.name,
            email=db_profile.email,
            phone=db_profile.phone,
            address=db_profile.address,
            city=db_profile.city,
            province=db_profile.province,
            postal_code=db_profile.postal_code,
            country=db_profile.country,
            work_authorization=db_profile.work_authorization,
            linkedin_url=db_profile.linkedin_url,
            portfolio_url=db_profile.portfolio_url,
            github_url=db_profile.github_url,
            notice_period_weeks=db_profile.notice_period_weeks,
            salary_expectation_min=db_profile.salary_expectation_min,
            salary_expectation_max=db_profile.salary_expectation_max,
            salary_currency=db_profile.salary_currency,
            education=[EducationEntry(**e) for e in db_profile.education] if db_profile.education else [],
            certifications=[CertificationEntry(**c) for c in db_profile.certifications] if db_profile.certifications else [],
            employment_history=[EmploymentEntry(**e) for e in db_profile.employment_history] if db_profile.employment_history else [],
            projects=[],  # SQLAlchemy model doesn't have projects field
            skills=parse_skills(db_profile.skills or [], "general"),
            technical_skills=parse_skills(db_profile.technical_skills or [], "technical"),
            business_skills=parse_skills(db_profile.business_skills or [], "business"),
            tools=parse_skills(db_profile.tools or [], "tool"),
            programming_languages=parse_skills(db_profile.programming_languages or [], "programming"),
            industries=db_profile.industries or [],
            job_titles=db_profile.job_titles or [],
            preferred_job_titles=db_profile.preferred_job_titles or [],
            preferred_locations=db_profile.preferred_locations or [],
            remote_preferences=db_profile.remote_preferences or [],
            employment_preferences=db_profile.employment_preferences or [],
            excluded_titles=db_profile.excluded_titles or [],
            excluded_industries=db_profile.excluded_industries or [],
            excluded_requirements=db_profile.excluded_requirements or [],
            additional_experience=experience_notes,
            created_at=db_profile.created_at.isoformat() if db_profile.created_at else "",
            updated_at=db_profile.updated_at.isoformat() if db_profile.updated_at else "",
        )

        return profile

    async def _get_jobs_to_match(
        self,
        job_ids: List[int] = None,
        limit: int = 50,
        force_rematch: bool = False,
    ) -> List[Job]:
        """Get jobs that need matching."""
        async with get_session() as session:
            repos = RepositoryFactory(session)

            if job_ids:
                jobs = []
                for jid in job_ids:
                    job = await repos.jobs.get_job(jid)
                    if job:
                        jobs.append(job)
                return jobs[:limit]

            # Get jobs without matches or with force_rematch
            if force_rematch:
                return await repos.jobs.get_all(limit=limit)
            else:
                return await repos.jobs.get_unmatched(limit=limit)

    async def _match_single_job(self, job: Job, profile: PydanticCandidateProfile) -> Optional[JobMatchResult]:
        """Match a single job against the profile using LLM."""
        # Prepare job data for LLM
        job_data = {
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "remote_type": job.remote_type.value if job.remote_type else "on_site",
            "employment_type": job.employment_type.value if job.employment_type else "full_time",
            "description": job.description,
            "requirements": job.requirements or "",
            "preferred_qualifications": job.preferred_qualifications or "",
            "skills": job.skills or [],
            "tools": job.tools or [],
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "currency": job.currency,
        }

        # Prepare profile summary for LLM
        profile_summary = self._build_profile_summary(profile)

        # Run LLM matching
        match_result = await self.llm.generate_json(
            system_prompt=self.match_prompt,
            user_prompt=f"JOB:\n{job_data}\n\nCANDIDATE PROFILE:\n{profile_summary}",
            schema=JobMatchResult,
        )

        return match_result

    def _build_profile_summary(self, profile: PydanticCandidateProfile) -> str:
        """Build a concise profile summary for LLM."""
        parts = []

        # Skills
        all_skills = profile.get_verified_skills()
        skill_names = [s.name for s in all_skills]
        parts.append(f"SKILLS: {', '.join(skill_names[:30])}")

        # Experience
        exp_years = sum(
            (int(e.end_date) if e.end_date and e.end_date.lower() not in ("present", "current") else datetime.now().year)
            - int(e.start_date)
            for e in profile.employment_history
            if e.start_date and e.start_date.isdigit()
        )
        parts.append(f"TOTAL EXPERIENCE: ~{exp_years} years")

        # Recent roles
        if profile.employment_history:
            parts.append("RECENT ROLES:")
            for emp in profile.employment_history[:3]:
                parts.append(f"  {emp.title} at {emp.company} ({emp.start_date}-{emp.end_date or 'Present'})")

        # Education
        if profile.education:
            parts.append("EDUCATION:")
            for edu in profile.education:
                parts.append(f"  {edu.degree} from {edu.institution} ({edu.graduation_year or 'N/A'})")

        # Certifications
        if profile.certifications:
            cert_names = [c.name for c in profile.certifications]
            parts.append(f"CERTIFICATIONS: {', '.join(cert_names)}")

        # Preferences
        parts.append(f"PREFERRED TITLES: {', '.join(profile.preferred_job_titles)}")
        parts.append(f"PREFERRED LOCATIONS: {', '.join(profile.preferred_locations or ['Remote Canada'])}")
        parts.append(f"REMOTE PREFERENCES: {', '.join(profile.remote_preferences or ['Remote', 'Hybrid'])}")

        # Exclusions
        if profile.excluded_titles:
            parts.append(f"EXCLUDED TITLES: {', '.join(profile.excluded_titles)}")
        if profile.excluded_requirements:
            parts.append(f"EXCLUDED REQUIREMENTS: {', '.join(profile.excluded_requirements)}")

        return "\n".join(parts)

    async def _save_match(self, job_id: int, match_result: JobMatchResult):
        """Save match result to database."""
        async with get_session() as session:
            repos = RepositoryFactory(session)

            # Check if match exists
            existing = await repos.matches.get_by_job_id(job_id)

            match_data = {
                "match_score": match_result.match_score,
                "technical_score": match_result.technical_score,
                "soft_skills_score": match_result.soft_skills_score,
                "recommendation": match_result.recommendation,
                "strong_matches": [m.model_dump() for m in match_result.strong_matches],
                "partial_matches": [m.model_dump() for m in match_result.partial_matches],
                "missing_requirements": match_result.missing_requirements,
                "preferred_requirements_missing": match_result.preferred_requirements_missing,
                "missing_soft_skills": match_result.missing_soft_skills,
                "concerns": match_result.concerns,
                "reasoning": match_result.reasoning,
                "prompt_version": "1.0.0",
            }

            if existing:
                await repos.matches.update_match(existing.id, **match_data)
            else:
                match_data["job_id"] = job_id
                await repos.matches.create_match(**match_data)

            await session.commit()

    async def _update_job_status(self, job_id: int, recommendation: str):
        """Update job status based on match recommendation."""
        async with get_session() as session:
            repos = RepositoryFactory(session)

            status_map = {
                "APPLY": JobStatus.QUALIFIED,
                "REVIEW": JobStatus.MATCHED,
                "REJECT": JobStatus.REJECTED,
            }

            new_status = status_map.get(recommendation, JobStatus.MATCHED)
            await repos.jobs.update_status(job_id, new_status)
            await session.commit()


async def create_matching_agent(config: Dict[str, Any] = None) -> MatchingAgent:
    """Factory function to create a MatchingAgent."""
    return MatchingAgent(config)