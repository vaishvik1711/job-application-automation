#!/usr/bin/env python3
"""Test single job matching through agent with save."""
import asyncio
from database.database import init_db
from agents.matching_agent import MatchingAgent

async def test():
    await init_db()

    agent = MatchingAgent()

    # Match just job 89 with force_rematch
    result = await agent.match_jobs(job_ids=[89], limit=1, force_rematch=True)

    print(f"Result: {result}")
    print(f"Jobs processed: {result.jobs_processed}")
    print(f"Jobs matched: {result.jobs_matched}")
    print(f"Jobs qualified: {result.jobs_qualified}")
    print(f"Jobs rejected: {result.jobs_rejected}")

asyncio.run(test())