"""
Resume Customization Agent.
Uses LLM to create tailored resumes for specific jobs.
"""
import asyncio
import json
import hashlib
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

# Cache for parsed resumes: key = (file_path, mtime), value = ParsedResume
_parsed_resume_cache: Dict[tuple, "ParsedResume"] = {}

# Cache for LLM customization plans: key = hash of inputs, value = ResumeCustomizationPlan
_customization_plan_cache: Dict[str, "ResumeCustomizationPlan"] = {}
# Max cache size to prevent memory issues
_MAX_PLAN_CACHE_SIZE = 100


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
            # Load all data in a single batched query
            async with get_session() as session:
                repos = RepositoryFactory(session)
                data = await repos.get_resume_generation_data(job_id)

                if not data:
                    result.errors.append(f"Job {job_id} not found or no match")
                    return result

                job = data["job"]
                match = data["match"]
                profile = data["profile"]
                experience_notes = data["experience_notes"]

                if not match or match.recommendation != "APPLY":
                    result.errors.append(f"Job {job_id} not qualified for application")
                    return result

                if not profile:
                    result.errors.append("No candidate profile found")
                    return result

                additional_exp = "\n".join([e.original_text or "" for e in (experience_notes or [])])
                logger.info(f"Additional exp loaded: {len(additional_exp)} chars")

            # Parse master resume (with caching)
            import os
            mtime = os.path.getmtime(master_resume_path)
            cache_key = (master_resume_path, mtime)
            if cache_key in _parsed_resume_cache:
                parsed_resume = _parsed_resume_cache[cache_key]
                logger.debug(f"Using cached parsed resume for {master_resume_path}")
            else:
                parsed_resume = parse_resume(master_resume_path)
                _parsed_resume_cache[cache_key] = parsed_resume
                logger.debug(f"Parsed and cached resume: {master_resume_path}")
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

            # Persist to Supabase Storage so the download survives Railway's
            # ephemeral-disk redeploys. Best-effort — never fail the generation.
            try:
                from storage import persist_resume_file
                await persist_resume_file(resume_record.id, Path(output_path).name, output_path)
            except Exception as upload_err:
                logger.warning("Storage persist skipped for resume %s: %s", resume_record.id, upload_err)

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
        """Format parsed resume for LLM consumption - only include sections relevant for customization."""
        parts = []

        # Only include sections that are directly customized
        if parsed.summary:
            parts.append(f"SUMMARY:\n{parsed.summary}")

        if parsed.work_history:
            parts.append("WORK HISTORY:")
            for i, job in enumerate(parsed.work_history):
                parts.append(f"\n  Job {i+1}:")
                # Only include title, company, dates, and bullets - skip raw
                for k, v in job.items():
                    if k in ("title", "company", "location", "start_date", "end_date", "bullets") and v:
                        parts.append(f"    {k}: {v}")

        # Combine all skills into one section for customization relevance
        all_skills = []
        if parsed.technical_skills:
            all_skills.extend(parsed.technical_skills)
        if parsed.tools:
            all_skills.extend(parsed.tools)
        if parsed.skills:
            all_skills.extend(parsed.skills)
        if all_skills:
            parts.append(f"SKILLS: {', '.join(all_skills)}")

        # Skip: contact_info, education, certifications, projects - not customized
        return "\n".join(parts)

    def _build_job_analysis(self, match: JobMatch) -> Dict[str, Any]:
        """Build job analysis dict from match record."""
        analysis = {
            "match_score": match.match_score,
            "recommendation": match.recommendation,
            "strong_matches": match.strong_matches,
            "partial_matches": match.partial_matches,
            "missing_requirements": match.missing_requirements,
            "preferred_requirements_missing": match.preferred_requirements_missing,
            "concerns": match.concerns,
            "reasoning": match.reasoning,
        }
        # Include pre-computed job analysis from matching phase if available
        if match.job_analysis:
            analysis["job_analysis"] = match.job_analysis
        return analysis

    async def _get_customization_plan(
        self,
        master_resume_text: str,
        additional_exp: str,
        job: Job,
        job_analysis: Dict[str, Any],
    ) -> ResumeCustomizationPlan:
        """Get customization plan from LLM with caching."""
        # Check if we have pre-computed job analysis from matching phase
        precomputed_analysis = job_analysis.get("job_analysis")

        if precomputed_analysis:
            # Use pre-computed analysis - skip sending full job description
            job_data = {
                "title": job.title,
                "company": job.company,
                # Only send truncated description for context
                "description": job.description[:500] if job.description else "",
            }
            # Use pre-computed structured analysis directly
            condensed_analysis = {
                "match_score": job_analysis.get("match_score"),
                "strong_matches": [m.get("skill") if isinstance(m, dict) else str(m) for m in job_analysis.get("strong_matches", [])],
                "partial_matches": [m.get("skill") if isinstance(m, dict) else str(m) for m in job_analysis.get("partial_matches", [])],
                "missing_requirements": job_analysis.get("missing_requirements", [])[:10],
                "concerns": job_analysis.get("concerns", [])[:5],
                # Pre-computed structured analysis from matching phase
                "required_skills": precomputed_analysis.get("required_skills", []),
                "preferred_skills": precomputed_analysis.get("preferred_skills", []),
                "required_tools": precomputed_analysis.get("required_tools", []),
                "preferred_tools": precomputed_analysis.get("preferred_tools", []),
                "required_experience_years": precomputed_analysis.get("required_experience_years"),
                "seniority_level": precomputed_analysis.get("seniority_level"),
                "responsibilities": precomputed_analysis.get("responsibilities", [])[:5],
            }
            logger.debug("Using pre-computed job analysis from matching phase")
        else:
            # Fallback: send essential job fields (original behavior)
            job_data = {
                "title": job.title,
                "company": job.company,
                "description": job.description[:2000] if job.description else "",
                "requirements": job.requirements[:1500] if job.requirements else "",
                "skills": job.skills[:20] if job.skills else [],
                "tools": job.tools[:15] if job.tools else [],
            }
            condensed_analysis = {
                "match_score": job_analysis.get("match_score"),
                "strong_matches": [m.get("skill") if isinstance(m, dict) else str(m) for m in job_analysis.get("strong_matches", [])],
                "partial_matches": [m.get("skill") if isinstance(m, dict) else str(m) for m in job_analysis.get("partial_matches", [])],
                "missing_requirements": job_analysis.get("missing_requirements", [])[:10],
                "concerns": job_analysis.get("concerns", [])[:5],
            }

        # Build cache key from all inputs that affect the plan
        cache_input = f"{master_resume_text}|{additional_exp[:2000] if additional_exp else ''}|{json.dumps(job_data, sort_keys=True)}|{json.dumps(condensed_analysis, sort_keys=True)}"
        cache_key = hashlib.sha256(cache_input.encode()).hexdigest()[:32]

        # Check cache
        if cache_key in _customization_plan_cache:
            logger.debug(f"Using cached customization plan (key: {cache_key[:8]})")
            return _customization_plan_cache[cache_key]

        plan = await self.llm.generate_json(
            system_prompt=self.customization_prompt,
            user_prompt=f"MASTER RESUME:\n{master_resume_text}\n\n"
                       f"ADDITIONAL EXPERIENCE:\n{additional_exp[:2000] if additional_exp else ''}\n\n"
                       f"JOB:\n{json.dumps(job_data, indent=2)}\n\n"
                       f"JOB MATCH ANALYSIS:\n{json.dumps(condensed_analysis, indent=2)}",
            schema=ResumeCustomizationPlan,
        )

        # Store in cache with size limit
        if len(_customization_plan_cache) >= _MAX_PLAN_CACHE_SIZE:
            # Remove oldest entry (first key)
            oldest_key = next(iter(_customization_plan_cache))
            del _customization_plan_cache[oldest_key]
        _customization_plan_cache[cache_key] = plan
        logger.debug(f"Cached new customization plan (key: {cache_key[:8]}, cache size: {len(_customization_plan_cache)})")

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
        max_concurrent: int = 3,
    ) -> List[ResumeGenerationResult]:
        """Generate resumes for all qualified jobs in parallel."""
        async with get_session() as session:
            repos = RepositoryFactory(session)
            qualified_jobs = await repos.jobs.get_jobs_by_status(JobStatus.QUALIFIED, limit=limit)

        if not qualified_jobs:
            return []

        # Limit concurrent LLM calls to avoid rate limits
        semaphore = asyncio.Semaphore(max_concurrent)

        async def gen_one(job):
            async with semaphore:
                return await self.generate_resume(job.id, master_resume_path, output_dir)

        results = await asyncio.gather(*[gen_one(job) for job in qualified_jobs], return_exceptions=True)

        # Handle any exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error generating resume for job {qualified_jobs[i].id}: {result}")
                final_results.append(ResumeGenerationResult(success=False, errors=[str(result)]))
            else:
                final_results.append(result)

        return final_results


async def create_resume_agent() -> ResumeAgent:
    """Factory function to create a ResumeAgent."""
    return ResumeAgent()