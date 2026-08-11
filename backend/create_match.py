#!/usr/bin/env python3
"""Create match record for Lyft job and generate custom resume with AI projects."""
import asyncio
import json
from database.database import init_db, close_db, get_session
from database.repositories import RepositoryFactory
from database.models import Job, JobMatch, JobStatus
from datetime import datetime


async def create_match_and_resume():
    await init_db()
    async with get_session() as session:
        repos = RepositoryFactory(session)

        # Get the job
        job = await repos.jobs.get_job(90)
        if not job:
            print("Job 90 not found")
            return

        print(f"Job: {job.title} at {job.company}")

        # Create match record with the analysis
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

        # Update job status to QUALIFIED (since recommendation is APPLY)
        job.status = JobStatus.QUALIFIED

        await session.commit()
        print("Match created successfully!")
        print(f"Match Score: {match.match_score}")
        print(f"Technical Score: {match.technical_score}")
        print(f"Soft Skills Score: {match.soft_skills_score}")
        print(f"Recommendation: {match.recommendation}")

    await close_db()


if __name__ == '__main__':
    asyncio.run(create_match_and_resume())