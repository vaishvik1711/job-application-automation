#!/usr/bin/env python3
"""Test single job matching with debug output."""
import asyncio
from database.database import init_db, get_session
from database.repositories import RepositoryFactory
from database.models import Job
from agents.matching_agent import MatchingAgent
from llm.client import get_llm_client
from llm.prompts import get_prompt
from llm.schemas import JobMatchResult

async def test():
    await init_db()

    async with get_session() as session:
        repos = RepositoryFactory(session)
        job = await repos.jobs.get_job(89)  # Latest job

    if not job:
        print("Job not found")
        return

    print(f"Testing job: {job.title} at {job.company}")

    # Get profile
    agent = MatchingAgent()
    profile = await agent._get_candidate_profile()

    if not profile:
        print("No profile found")
        return

    # Prepare job data
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

    profile_summary = agent._build_profile_summary(profile)

    # Run LLM matching
    llm = get_llm_client()
    match_prompt = get_prompt("job_matching")

    print("\n--- Sending to LLM ---")

    match_result = await llm.generate_json(
        system_prompt=match_prompt,
        user_prompt=f"JOB:\n{job_data}\n\nCANDIDATE PROFILE:\n{profile_summary}",
        schema=JobMatchResult,
    )

    print(f"\n--- LLM Result ---")
    print(f"match_score: {match_result.match_score}")
    print(f"technical_score: {match_result.technical_score}")
    print(f"soft_skills_score: {match_result.soft_skills_score}")
    print(f"recommendation: {match_result.recommendation}")
    print(f"reasoning: {match_result.reasoning}")
    print(f"strong_matches: {match_result.strong_matches}")
    print(f"missing_requirements: {match_result.missing_requirements}")
    print(f"missing_soft_skills: {match_result.missing_soft_skills}")

asyncio.run(test())