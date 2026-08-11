#!/usr/bin/env python3
"""Add Lyft job to database."""
import asyncio
import hashlib
from database.database import init_db, close_db, get_session
from database.repositories import RepositoryFactory
from database.models import Job, JobStatus, RemoteType, EmploymentType, JobSource
from datetime import datetime


async def add_job():
    await init_db()
    async with get_session() as session:
        repos = RepositoryFactory(session)

        # Create content hash for deduplication
        content = 'Analyst, Business Planning & Forecasting|Lyft|Toronto, Ontario, Canada'
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:64]
        canonical_url = 'https://app.careerpuck.com/job-board/lyft/job/8643088002?gh_jid=8643088002'

        job = Job(
            canonical_url=canonical_url,
            source_urls=[canonical_url],
            source='greenhouse',
            title='Analyst, Business Planning & Forecasting',
            company='Lyft',
            location='Toronto, Ontario, Canada',
            description='''Support models/frameworks connecting business drivers to staffing decisions
Translate complex data into actionable insights for leadership
Own planning execution: dashboards, reporting, business reviews
Leverage AI tools to build and maintain dashboards, reports, and analyses
Identify process improvement opportunities
Move quickly on ambiguous, time-sensitive requests''',
            requirements='''2+ years in planning, forecasting, capacity/resource management (consulting, IB, FP&A, ops strategy backgrounds fit)
Sharp analytical mindset with hands-on SQL and Python skills
AI fluency, comfortable using AI tools to accelerate analysis
Strong business acumen; fast learner; bias toward action
Self-directed; turns data into decisions; strong communicator
Workforce management exposure a plus
Bachelor's in Business, Engineering, Data Science, or quantitative field (advanced degree a plus)''',
            preferred_qualifications='Workforce management exposure a plus',
            skills=['SQL', 'Python', 'Data Analysis', 'Data Modeling', 'Forecasting', 'Dashboard Development', 'Business Intelligence', 'AI Tools'],
            tools=['SQL', 'Python', 'Power BI', 'Tableau', 'Excel', 'Anaplan'],
            salary_min=79600,
            salary_max=99500,
            currency='CAD',
            remote_type=RemoteType.HYBRID,
            employment_type=EmploymentType.FULL_TIME,
            status=JobStatus.DISCOVERED,
            date_posted=datetime(2026, 7, 22),
            content_hash=content_hash,
        )

        session.add(job)
        await session.flush()  # Get the ID

        # Add job source
        job_source = JobSource(
            job_id=job.id,
            source='greenhouse',
            source_url=canonical_url,
            source_job_id='8643088002',
            raw_data={'requisition_id': '111005', 'department': 'Core Support Ops', 'category': 'Data Analytics & Business Intelligence'}
        )
        session.add(job_source)

        await session.commit()
        print(f'Job created with ID: {job.id}')

    await close_db()


if __name__ == '__main__':
    asyncio.run(add_job())