#!/usr/bin/env python3
"""Database migration to add technical/soft skills columns."""
import asyncio
from database.database import engine
from sqlalchemy import text

async def migrate():
    async with engine.begin() as conn:
        # Add new columns to job_matches table
        try:
            await conn.execute(text('ALTER TABLE job_matches ADD COLUMN technical_score FLOAT DEFAULT 0'))
            print('Added technical_score column')
        except Exception as e:
            print(f'technical_score: {e}')

        try:
            await conn.execute(text('ALTER TABLE job_matches ADD COLUMN soft_skills_score FLOAT DEFAULT 0'))
            print('Added soft_skills_score column')
        except Exception as e:
            print(f'soft_skills_score: {e}')

        try:
            await conn.execute(text('ALTER TABLE job_matches ADD COLUMN missing_soft_skills JSON DEFAULT "[]"'))
            print('Added missing_soft_skills column')
        except Exception as e:
            print(f'missing_soft_skills: {e}')

        await conn.commit()
        print('Migration complete')

if __name__ == "__main__":
    asyncio.run(migrate())