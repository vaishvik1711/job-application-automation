"""
FastAPI dependencies for database sessions and authentication.
"""
import os
from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from supabase import create_client, Client as SupabaseClient
from pydantic import BaseModel

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./jobs.db")
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
supabase_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    global supabase_client
    if supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase not configured",
            )
        supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return supabase_client


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Simple auth (can be extended later)
class TokenData(BaseModel):
    user_id: Optional[str] = None


def get_current_user_token(
    authorization: Optional[str] = Header(None),
) -> Optional[str]:
    """Extract bearer token from request."""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


async def get_db_session(
    session: AsyncSession = Depends(get_session),
) -> AsyncSession:
    return session