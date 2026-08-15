"""
Resume Validator - Verifies customized resume against sources for truthfulness.
"""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from dataclasses import dataclass, field

from resume.parser import ParsedResume, parse_resume
from resume.docx_editor import DocxEditor
from llm.client import get_llm_client
from llm.prompts import get_prompt
from llm.schemas import ResumeValidationResult
from database.database import get_session
from database.repositories import RepositoryFactory
from database.models import Resume, Job
from utils.logger import get_logger

if TYPE_CHECKING:
    from agents.profile_agent import CandidateProfile


logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of resume validation."""
    success: bool
    validation_score: float = 0.0
    truthfulness_score: int = 0
    format_score: int = 0
    relevance_score: int = 0
    issues: List[Dict[str, Any]] = field(default_factory=list)
    traceability_check: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ResumeValidator:
    """
    Validates a customized resume for:
    1. Truthfulness - All claims traceable to master resume or additional experience
    2. Format preservation - Page count, sections, fonts, margins, spacing intact
    3. Relevance - Keywords from job description covered, relevant experience prioritized
    4. Quality - No grammar issues, duplicate bullets, broken formatting, keyword stuffing
    """

    def __init__(self, llm_client=None):
        self.llm = llm_client or get_llm_client()
        self.validation_prompt = get_prompt("resume_validation")

    async def validate_resume(
        self,
        resume_id: int,
        master_resume_path: str,
        additional_experience_path: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate a generated resume against sources.

        Args:
            resume_id: Database resume record ID
            master_resume_path: Path to master resume
            additional_experience_path: Path to additional experience notes

        Returns:
            ValidationResult with scores and issues
        """
        result = ValidationResult(success=False)

        try:
            # Load resume record and related data
            async with get_session() as session:
                repos = RepositoryFactory(session)
                resume_record = await repos.resumes.get_resume(resume_id)

                if not resume_record:
                    result.errors.append(f"Resume {resume_id} not found")
                    return result

                job = await repos.jobs.get_job(resume_record.job_id)
                profile = await repos.candidates.get_profile()

                if not job or not profile:
                    result.errors.append("Missing job or profile data")
                    return result

                # Load additional experience
                experience_notes = await repos.candidates.get_experience_notes(profile.id)
                additional_exp = "\n".join([e.original_text for e in experience_notes])

            # Parse both resumes
            master_parsed = parse_resume(master_resume_path)
            master_text = self._format_resume_for_llm(master_parsed)

            generated_parsed = parse_resume(resume_record.file_path)
            generated_text = self._format_resume_for_llm(generated_parsed)

            # Build candidate profile summary
            profile_summary = self._build_profile_summary(profile, additional_exp)

            # Run LLM validation
            logger.info(f"Validating resume {resume_id} for job {job.title}")
            validation = await self.llm.generate_json(
                system_prompt=self.validation_prompt,
                user_prompt=f"ORIGINAL MASTER RESUME:\n{master_text}\n\n"
                           f"CANDIDATE PROFILE:\n{profile_summary}\n\n"
                           f"ADDITIONAL EXPERIENCE:\n{additional_exp}\n\n"
                           f"GENERATED RESUME:\n{generated_text}\n\n"
                           f"JOB DESCRIPTION:\nTitle: {job.title}\nCompany: {job.company}\nDescription: {job.description}\nRequirements: {job.requirements}",
                schema=ResumeValidationResult,
            )

            # Check format preservation
            format_issues = self._check_format_preservation(
                master_resume_path, resume_record.file_path
            )

            # Combine results
            result.success = True
            result.truthfulness_score = validation.truthfulness_score
            result.format_score = validation.format_score
            result.relevance_score = validation.relevance_score
            result.validation_score = (
                validation.truthfulness_score * 0.5 +
                validation.format_score * 0.2 +
                validation.relevance_score * 0.3
            )
            result.issues = validation.issues + format_issues
            result.traceability_check = validation.traceability_check

            # Update database
            async with get_session() as session:
                repos = RepositoryFactory(session)
                await repos.resumes.update_validation(
                    resume_id,
                    validation_score=result.validation_score,
                    truthfulness_score=validation.truthfulness_score,
                    format_score=validation.format_score,
                    relevance_score=validation.relevance_score,
                    issues=result.issues,
                    traceability=result.traceability_check,
                )
                await repos.statistics.increment_stat("resumes_validated", 1)
                await session.commit()

                # Update job status if validation passes
                if validation.valid and result.validation_score >= 70:
                    await repos.jobs.update_job_status(resume_record.job_id,
                                                       job.status.__class__.READY_TO_APPLY if hasattr(job.status.__class__, 'READY_TO_APPLY') else job.status)
                    await session.commit()

            logger.info(f"Validation complete: score={result.validation_score:.1f}, valid={validation.valid}")

        except Exception as e:
            logger.error(f"Error validating resume {resume_id}: {e}")
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

    def _build_profile_summary(self, profile, additional_exp: str) -> str:
        """Build candidate profile summary for LLM."""
        parts = []

        # Skills - database model stores skills as JSON arrays
        all_skills = []
        if profile.technical_skills:
            all_skills.extend(profile.technical_skills)
        if profile.tools:
            all_skills.extend(profile.tools)
        if profile.skills:
            all_skills.extend(profile.skills)
        if profile.programming_languages:
            all_skills.extend(profile.programming_languages)
        if profile.business_skills:
            all_skills.extend(profile.business_skills)
        parts.append(f"VERIFIED SKILLS: {', '.join(all_skills)}")

        # Experience
        parts.append("EMPLOYMENT HISTORY:")
        for emp in profile.employment_history:
            parts.append(f"  {emp.get('title', '')} at {emp.get('company', '')} ({emp.get('start_date', '')}-{emp.get('end_date', '') or 'Present'})")
            if emp.get('achievements'):
                for a in emp.get('achievements', []):
                    parts.append(f"    - {a}")

        # Education
        parts.append("EDUCATION:")
        for edu in profile.education:
            parts.append(f"  {edu.get('degree', '')} from {edu.get('institution', '')} ({edu.get('graduation_year', '') or 'N/A'})")

        # Certifications
        if profile.certifications:
            cert_names = [c.get('name', '') for c in profile.certifications]
            parts.append(f"CERTIFICATIONS: {', '.join(cert_names)}")

        # Projects (not in database model, skip if not present)
        projects = getattr(profile, 'projects', None)
        if projects:
            parts.append("PROJECTS:")
            for proj in projects:
                parts.append(f"  {proj.get('name', '')}: {proj.get('description', '')}")

        # Additional experience
        if additional_exp.strip():
            parts.append(f"ADDITIONAL EXPERIENCE:\n{additional_exp}")

        return "\n".join(parts)

    def _check_format_preservation(self, master_path: str, generated_path: str) -> List[Dict[str, Any]]:
        """Check that formatting is preserved between master and generated resume."""
        issues = []

        try:
            master_doc = DocxEditor(master_path, preserve_original=True)
            generated_doc = DocxEditor(generated_path, preserve_original=True)

            # Check page count
            master_paras = len(master_doc.doc.paragraphs)
            generated_paras = len(generated_doc.doc.paragraphs)

            if abs(master_paras - generated_paras) > 5:
                issues.append({
                    "type": "format",
                    "severity": "warning",
                    "message": f"Paragraph count changed significantly: {master_paras} -> {generated_paras}",
                })

            # Check sections preserved
            master_sections = [s.name for s in master_doc.sections]
            generated_sections = [s.name for s in generated_doc.sections]

            for section in master_sections:
                if not any(section.lower() in s.lower() for s in generated_sections):
                    issues.append({
                        "type": "format",
                        "severity": "error",
                        "message": f"Section missing in generated resume: {section}",
                    })

            # Check margins
            master_margins = master_doc.format_info.get("page_margins", {})
            generated_margins = generated_doc.format_info.get("page_margins", {})
            for side in ["top", "bottom", "left", "right"]:
                if master_margins.get(side) != generated_margins.get(side):
                    issues.append({
                        "type": "format",
                        "severity": "warning",
                        "message": f"Margin changed: {side} {master_margins.get(side)} -> {generated_margins.get(side)}",
                    })

            # Check default font
            if master_doc.format_info.get("default_font") != generated_doc.format_info.get("default_font"):
                issues.append({
                    "type": "format",
                    "severity": "warning",
                    "message": f"Default font changed: {master_doc.format_info.get('default_font')} -> {generated_doc.format_info.get('default_font')}",
                })

        except Exception as e:
            issues.append({
                "type": "format",
                "severity": "error",
                "message": f"Format check failed: {str(e)}",
            })

        return issues

    async def validate_all_resumes(
        self,
        master_resume_path: str,
        additional_experience_path: Optional[str] = None,
        limit: int = 50,
    ) -> List[ValidationResult]:
        """Validate all unvalidated resumes."""
        results = []

        async with get_session() as session:
            repos = RepositoryFactory(session)
            resumes = await repos.resumes.get_unvalidated(limit=limit)

        for resume in resumes:
            result = await self.validate_resume(
                resume.id,
                master_resume_path,
                additional_experience_path,
            )
            results.append(result)

        return results


async def create_resume_validator() -> ResumeValidator:
    """Factory function to create a ResumeValidator."""
    return ResumeValidator()