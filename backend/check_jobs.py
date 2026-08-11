#!/usr/bin/env python3
"""Check current jobs and matches in database."""
import asyncio
from database.database import get_session
from database.repositories import RepositoryFactory
from database.models import Job, JobMatch, JobStatus

async def check():
    async with get_session() as session:
        repos = RepositoryFactory(session)
        # Get all jobs
        jobs = await repos.jobs.get_all(limit=100)
        print(f"Total jobs: {len(jobs)}")
        for j in jobs[:5]:
            print(f"  Job {j.id}: {j.title[:60]} at {j.company[:30]} - Status: {j.status.value}")

        # Get matches for specific jobs
        from sqlalchemy import select
        for job_id in [89, 88, 87, 86, 85]:
            result = await session.execute(select(JobMatch).where(JobMatch.job_id == job_id))
            match = result.scalars().first()
            if match:
                print(f"\n  Job {job_id} -> Match {match.id}: score={match.match_score}, tech={match.technical_score}, soft={match.soft_skills_score}, rec={match.recommendation}")
                if match.missing_soft_skills:
                    print(f"    missing_soft_skills: {match.missing_soft_skills}")
            else:
                print(f"\n  Job {job_id} -> No match found")

asyncio.run(check())