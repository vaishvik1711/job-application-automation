#!/usr/bin/env python3
"""Generate custom resume for Lyft job with AI projects added."""
import asyncio
from pathlib import Path
from database.database import init_db, close_db, get_session
from database.repositories import RepositoryFactory
from database.models import Job, JobMatch, JobStatus, Resume
from resume import create_resume_agent, create_resume_validator
from resume.parser import parse_resume
import json


async def generate_resume_with_ai_projects():
    await init_db()

    # First check if match exists, if not create it
    async with get_session() as session:
        repos = RepositoryFactory(session)
        job = await repos.jobs.get_job(90)
        if not job:
            print("Job 90 not found")
            await close_db()
            return

        match = await repos.matches.get_by_job_id(90)
        if not match:
            print("Creating match record...")
            match = JobMatch(
                job_id=90,
                match_score=79,
                technical_score=88,
                soft_skills_score=65,
                recommendation="APPLY",
                prompt_version="1.0.0",
                strong_matches=[
                    {"skill": "SQL", "proficiency": "expert", "source": "master_resume.work_history[0], technical_skills", "verified": True},
                    {"skill": "Power BI", "proficiency": "expert", "source": "master_resume.work_history[0]", "verified": True},
                    {"skill": "Data Analysis", "proficiency": "expert", "source": "master_resume.work_history[0]", "verified": True},
                    {"skill": "Data Modelling", "proficiency": "advanced", "source": "master_resume.work_history[0]", "verified": True},
                    {"skill": "Data Cleaning", "proficiency": "advanced", "source": "master_resume.work_history[0]", "verified": True},
                    {"skill": "Dashboard Development", "proficiency": "advanced", "source": "master_resume.work_history[0]", "verified": True},
                    {"skill": "DAX", "proficiency": "advanced", "source": "master_resume.skills", "verified": True},
                    {"skill": "Python", "proficiency": "advanced", "source": "master_resume.skills, technical_skills", "verified": True},
                    {"skill": "Excel (VBA, XLOOKUP, Macros, Power Query)", "proficiency": "advanced", "source": "master_resume.projects[1], skills", "verified": True},
                    {"skill": "Anaplan", "proficiency": "intermediate", "source": "master_resume.work_history[0]", "verified": True},
                    {"skill": "Process Automation", "proficiency": "intermediate", "source": "master_resume.work_history[0]", "verified": True},
                    {"skill": "Stakeholder Reporting", "proficiency": "intermediate", "source": "master_resume.work_history[0]", "verified": True},
                    {"skill": "Cross-functional Collaboration", "proficiency": "intermediate", "source": "master_resume.work_history[0]", "verified": True},
                ],
                partial_matches=[
                    {"skill": "Forecasting", "proficiency": "intermediate", "source": "master_resume.work_history[0]", "verified": True},
                    {"skill": "Capacity Planning", "proficiency": "beginner", "source": "master_resume.work_history[0]", "verified": True},
                ],
                missing_requirements=["AI fluency with AI tools for analysis acceleration"],
                preferred_requirements_missing=["Workforce management exposure"],
                missing_soft_skills=["Stakeholder Management", "Cross-functional Team Leadership", "Ambiguity Navigation", "Executive Communication"],
                concerns=["AI fluency gap - job explicitly requires AI tooling experience", "No direct business planning & forecasting title in history"],
                reasoning="Strong technical match on core skills SQL, Python, Power BI, Data Modeling, Anaplan (88%). Soft skills match at 65% - missing stakeholder management and cross-functional leadership which can be added to resume. Missing AI tooling experience which is a hard requirement. Sales compensation modeling is highly transferable to business planning/forecasting domain.",
            )
            session.add(match)
            job.status = JobStatus.QUALIFIED
            await session.commit()
            print("Match created!")

    # Now generate the resume
    print("Generating custom resume...")
    resume_agent = await create_resume_agent()
    validator = await create_resume_validator()

    master_resume_path = "data/master_resume/IT RESUME VAISHVIK PATEL.docx"

    result = await resume_agent.generate_resume(
        job_id=90,
        master_resume_path=master_resume_path,
        output_dir="data/generated_resumes",
    )

    if result.success:
        print(f"✓ Resume generated: {result.resume_path}")
        print(f"  Resume ID: {result.resume_id}")
        print(f"  Version: {result.version}")

        # Validate the resume
        print("\nValidating resume...")
        val_result = await validator.validate_resume(result.resume_id, master_resume_path)
        print(f"  Overall Validation Score: {val_result.validation_score:.1f}/100")
        print(f"  Truthfulness: {val_result.truthfulness_score}/100")
        print(f"  Format: {val_result.format_score}/100")
        print(f"  Relevance: {val_result.relevance_score}/100")
        if val_result.issues:
            print("  Issues:")
            for issue in val_result.issues[:5]:
                print(f"    - {issue.get('message', issue)}")
    else:
        print(f"✗ Failed: {result.errors}")

    await close_db()


if __name__ == '__main__':
    asyncio.run(generate_resume_with_ai_projects())