"""
Resume Customization Agent.
Uses LLM to create tailored resumes for specific jobs.
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from dataclasses import dataclass, field

from resume.parser import ParsedResume, parse_resume
from resume.docx_editor import DocxEditor, customize_resume_from_plan
from llm.client import get_llm_client
from llm.prompts import get_prompt
from llm.schemas import ResumeCustomizationPlan, ProfileAnalysis
from database.database import get_session
from database.repositories import RepositoryFactory
from database.models import Resume, Job, JobMatch, JobStatus
from utils.logger import get_logger
from utils.hashing import content_hash

if TYPE_CHECKING:
    from agents.profile_agent import CandidateProfile, AdditionalExperienceEntry

logger = get_logger(__name__)


@dataclass
class ResumeGenerationResult:
    """Result of resume generation."""
    success: bool
    resume_path: Optional[str] = None
    resume_id: Optional[int] = None
    version: int = 1
    validation_score: Optional[float] = None
    traceability: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None


class ResumeAgent:
    """Agent responsible for generating customized resumes for specific jobs."""

    def __init__(self, llm_client=None):
        self.llm = llm_client or get_llm_client()
        self.customization_prompt = get_prompt("resume_customization")

    async def generate_resume(
        self,
        job_id: int,
        master_resume_path: str,
        output_dir: str = "data/generated_resumes",
    ) -> ResumeGenerationResult:
        """
        Generate a customized resume for a specific job.
        
        Args:
            job_id: Database job ID
            master_resume_path: Path to master resume DOCX
            output_dir: Directory to save generated resume
            
        Returns:
            ResumeGenerationResult with path and metadata
        """
        result = ResumeGenerationResult(success=False)

        try:
            # Load job and match data
            async with get_session() as session:
                repos = RepositoryFactory(session)
                job = await repos.jobs.get_job(job_id)
                match = await repos.matches.get_match(job_id)

                if not job:
                    result.errors.append(f"Job {job_id} not found")
                    return result

                if not match or match.recommendation != "APPLY":
                    result.errors.append(f"Job {job_id} not qualified for application")
                    return result

                # Load candidate profile
                profile = await repos.candidates.get_profile()
                if not profile:
                    result.errors.append("No candidate profile found")
                    return result

                # Load additional experience
                experience_notes = await repos.candidates.get_experience_notes(profile.id)
                additional_exp = "\n".join([e.original_text or "" for e in (experience_notes or [])])
                logger.info(f"Additional exp loaded: {len(additional_exp)} chars")

            # Parse master resume
            parsed_resume = parse_resume(master_resume_path)
            master_resume_text = self._format_resume_for_llm(parsed_resume)

            # Build job analysis from match
            job_analysis = self._build_job_analysis(match)

            # Get customization plan from LLM
            logger.info(f"Generating customization plan for job {job_id}: {job.title}")
            plan = await self._get_customization_plan(
                master_resume_text,
                additional_exp,
                job,
                job_analysis,
            )

            # Generate output filename with versioning
            output_path = self._generate_output_path(job, output_dir)

            # Apply customization to DOCX
            customize_resume_from_plan(
                master_resume_path=master_resume_path,
                output_path=output_path,
                customization_plan=plan.model_dump(),
            )

            # Save to database
            async with get_session() as session:
                repos = RepositoryFactory(session)
                
                # Get next version number
                version = await repos.resumes.get_latest_resume_version(profile.id, job_id) + 1
                
                resume_record = await repos.resumes.create_resume(
                    candidate_id=profile.id,
                    job_id=job_id,
                    version=version,
                    file_path=output_path,
                    filename=Path(output_path).name,
                    traceability=self._build_traceability(plan, parsed_resume, additional_exp),
                )
                await session.commit()
                result.resume_id = resume_record.id
                result.version = version

            # Update job status
            async with get_session() as session:
                repos = RepositoryFactory(session)
                await repos.jobs.update_job_status(job_id, JobStatus.RESUME_CREATED)
                await repos.statistics.increment_stat("resumes_created", 1)
                await session.commit()

            result.success = True
            result.resume_path = output_path
            result.traceability = self._build_traceability(plan, parsed_resume, additional_exp)
            result.created_at = datetime.utcnow()
            logger.info(f"Generated resume v{version} for job {job_id}: {output_path}")

        except Exception as e:
            logger.error(f"Error generating resume for job {job_id}: {e}")
            result.errors.append(str(e))

        return result

    def _format_resume_for_llm(self, parsed: ParsedResume) -> str:
        """Format parsed resume for LLM consumption."""
        parts = []

        if parsed.contact_info:
            parts.append("CONTACT INFO:")
            for k, v in parsed.contact_info.items():
                parts.append(f"  {k}: {v}")

        if parsed.summary:
            parts.append(f"\nSUMMARY:\n{parsed.summary}")

        if parsed.work_history:
            parts.append("\nWORK HISTORY:")
            for i, job in enumerate(parsed.work_history):
                parts.append(f"\n  Job {i+1}:")
                for k, v in job.items():
                    if k != "raw" and v:
                        parts.append(f"    {k}: {v}")

        if parsed.education:
            parts.append("\nEDUCATION:")
            for edu in parsed.education:
                parts.append(f"  {edu.get('degree', '')} - {edu.get('school', '')} ({edu.get('year', '')})")

        if parsed.skills:
            parts.append(f"\nSKILLS: {', '.join(parsed.skills)}")

        if parsed.technical_skills:
            parts.append(f"\nTECHNICAL SKILLS: {', '.join(parsed.technical_skills)}")

        if parsed.tools:
            parts.append(f"\nTOOLS: {', '.join(parsed.tools)}")

        if parsed.certifications:
            parts.append("\nCERTIFICATIONS:")
            for cert in parsed.certifications:
                parts.append(f"  {cert.get('name', '')}")

        if parsed.projects:
            parts.append("\nPROJECTS:")
            for proj in parsed.projects:
                parts.append(f"  {proj.get('name', '')}: {proj.get('description', '')}")

        return "\n".join(parts)

    def _build_job_analysis(self, match: JobMatch) -> Dict[str, Any]:
        """Build job analysis dict from match record."""
        return {
            "match_score": match.match_score,
            "recommendation": match.recommendation,
            "strong_matches": match.strong_matches,
            "partial_matches": match.partial_matches,
            "missing_requirements": match.missing_requirements,
            "preferred_requirements_missing": match.preferred_requirements_missing,
            "concerns": match.concerns,
            "reasoning": match.reasoning,
        }

    async def _get_customization_plan(
        self,
        master_resume_text: str,
        additional_exp: str,
        job: Job,
        job_analysis: Dict[str, Any],
    ) -> ResumeCustomizationPlan:
        """Get customization plan from LLM."""
        job_data = {
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "description": job.description,
            "requirements": job.requirements,
            "skills": job.skills,
            "tools": job.tools,
        }

        plan = await self.llm.generate_json(
            system_prompt=self.customization_prompt,
            user_prompt=f"MASTER RESUME:\n{master_resume_text}\n\n"
                       f"ADDITIONAL EXPERIENCE:\n{additional_exp}\n\n"
                       f"JOB:\n{json.dumps(job_data, indent=2)}\n\n"
                       f"JOB MATCH ANALYSIS:\n{json.dumps(job_analysis, indent=2)}",
            schema=ResumeCustomizationPlan,
        )

        return plan

    def _generate_output_path(self, job: Job, output_dir: str) -> str:
        """Generate unique output filename."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        company_clean = "".join(c if c.isalnum() else "_" for c in job.company)
        title_clean = "".join(c if c.isalnum() else "_" for c in job.title)
        
        # Truncate to reasonable length
        company_clean = company_clean[:30]
        title_clean = title_clean[:40]
        
        filename = f"{date_str}_{company_clean}_{title_clean}_v01.docx"
        return str(Path(output_dir) / filename)

    def _build_traceability(
        self,
        plan: ResumeCustomizationPlan,
        parsed: ParsedResume,
        additional_exp: str,
    ) -> List[Dict[str, Any]]:
        """Build traceability mapping for validation."""
        traceability = []

        # Ensure additional_exp is a string
        additional_exp = additional_exp or ""

        # Summary traceability
        if plan.summary_rewrite:
            exp_lines = additional_exp.split('\n') if additional_exp else []
            traceability.append({
                "generated_content": plan.summary_rewrite,
                "type": "summary",
                "sources": ["master_resume.summary"] + [f"additional_experience[{i}]" for i in range(len(exp_lines)) if exp_lines[i].strip()],
            })

        # Bullet changes traceability
        for change in plan.bullet_changes:
            # change can be a BulletChange (Pydantic) or dict
            if hasattr(change, 'new_text'):
                new_text = change.new_text
                section = getattr(change, 'section', '')
                idx = getattr(change, 'index', 0)
                src = getattr(change, 'source', 'master_resume.work_history')
            else:
                new_text = change.get("new_text", "")
                section = change.get("section", "")
                idx = change.get("index", 0)
                src = change.get("source", "master_resume.work_history")
            traceability.append({
                "generated_content": new_text,
                "type": "bullet",
                "section": section,
                "index": idx,
                "sources": [src],
            })

        # Skills emphasis traceability
        for skill in plan.skills_to_emphasize:
            traceability.append({
                "generated_content": skill,
                "type": "skill_emphasis",
                "sources": ["master_resume.technical_skills", "additional_experience"],
            })

        return traceability

    async def generate_resumes_for_all_qualified(
        self,
        master_resume_path: str,
        limit: int = 50,
        output_dir: str = "data/generated_resumes",
    ) -> List[ResumeGenerationResult]:
        """Generate resumes for all qualified jobs."""
        results = []

        async with get_session() as session:
            repos = RepositoryFactory(session)
            qualified_jobs = await repos.jobs.get_jobs_by_status(JobStatus.QUALIFIED, limit=limit)

        for job in qualified_jobs:
            result = await self.generate_resume(job.id, master_resume_path, output_dir)
            results.append(result)

        return results


async def create_resume_agent() -> ResumeAgent:
    """Factory function to create a ResumeAgent."""
    return ResumeAgent()