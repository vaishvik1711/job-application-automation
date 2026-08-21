"""Settings API routes."""
import os
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.schemas import AppSettingsSchema, ApiResponse
from api.dependencies import get_db_session
from database.models import AppSettings
from typing import Optional

router = APIRouter()

_DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL")

DEFAULT_SETTINGS = {
    "llm": {
        "provider": "nvidia",
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "api_key": None,
        "base_url": None,
        "temperature": 0.7,
        "max_tokens": 4000,
    },
    "job_sources": {},
    "matching": {
        "default_weights": {
            "skills": 30,
            "experience": 25,
            "education": 10,
            "location": 15,
            "keywords": 20,
        },
        "auto_qualify_threshold": 75.0,
        "min_skill_match": 0.5,
    },
    "notifications": {
        "email_enabled": False,
        "email_address": None,
        "browser_enabled": True,
        "webhook_url": None,
        "events": {
            "job_found": True,
            "match_complete": True,
            "resume_generated": True,
            "application_submitted": True,
            "interview_scheduled": True,
        },
    },
    "resume_templates": [],
}


async def _get_setting(session: AsyncSession, key: str, default: any = None) -> any:
    """Get a setting value from the database."""
    result = await session.execute(
        select(AppSettings.value).where(AppSettings.key == key)
    )
    row = result.first()
    if row and row[0]:
        return row[0]
    return default


async def _set_setting(session: AsyncSession, key: str, value: any):
    """Set a setting value in the database."""
    stmt = select(AppSettings).where(AppSettings.key == key)
    result = await session.execute(stmt)
    setting = result.scalars().first()

    if setting:
        setting.value = value
    else:
        new_setting = AppSettings(key=key, value=value)
        session.add(new_setting)


@router.get("/settings", response_model=ApiResponse)
async def get_settings(session: AsyncSession = Depends(get_db_session)):
    """Get all application settings."""
    from api.routes.resumes import RESUME_TEMPLATES

    llm = await _get_setting(session, "llm", DEFAULT_SETTINGS["llm"])
    job_sources = await _get_setting(session, "job_sources", {})
    matching = await _get_setting(session, "matching", DEFAULT_SETTINGS["matching"])
    notifications = await _get_setting(session, "notifications", DEFAULT_SETTINGS["notifications"])

    return ApiResponse(data={
        "llm": llm,
        "job_sources": job_sources,
        "matching": matching,
        "notifications": notifications,
        "resume_templates": RESUME_TEMPLATES,
    })


@router.patch("/settings", response_model=ApiResponse)
async def update_settings(
    data: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """Update application settings."""
    from api.routes.resumes import RESUME_TEMPLATES

    if "llm" in data:
        await _set_setting(session, "llm", data["llm"])
    if "job_sources" in data:
        await _set_setting(session, "job_sources", data["job_sources"])
    if "matching" in data:
        await _set_setting(session, "matching", data["matching"])
    if "notifications" in data:
        await _set_setting(session, "notifications", data["notifications"])

    await session.flush()

    # Return updated settings
    llm = await _get_setting(session, "llm", DEFAULT_SETTINGS["llm"])
    job_sources = await _get_setting(session, "job_sources", {})
    matching = await _get_setting(session, "matching", DEFAULT_SETTINGS["matching"])
    notifications = await _get_setting(session, "notifications", DEFAULT_SETTINGS["notifications"])

    return ApiResponse(data={
        "llm": llm,
        "job_sources": job_sources,
        "matching": matching,
        "notifications": notifications,
        # match GET /settings so clients replacing state from the PATCH
        # response don't blank their template list
        "resume_templates": RESUME_TEMPLATES,
    })


@router.post("/settings/test-llm", response_model=ApiResponse)
async def test_llm(
    config: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """Test LLM configuration."""
    from llm.client import LLMClient

    start = time.time()

    try:
        client = LLMClient(
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            model=config.get("model"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 4000),
        )

        # Simple test call
        response = await client.generate_text(
            system_prompt="You are a helpful assistant.",
            user_prompt="Hello, this is a test.",
        )

        latency = int((time.time() - start) * 1000)

        return ApiResponse(data={
            "success": True,
            "latency_ms": latency,
        })
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return ApiResponse(data={
            "success": False,
            "latency_ms": latency,
            "error": str(e),
        })


@router.post("/settings/test-source", response_model=ApiResponse)
async def test_job_source(
    body: Optional[dict] = None,
    source: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session),
):
    """Test a job source configuration.

    Accepts the source/config either in the JSON body ({"source": ..., "config": ...})
    — what the frontend sends — or as a ?source= query parameter.
    """
    import re
    from fastapi.responses import JSONResponse

    body = body or {}
    src = body.get("source") or source
    config = body.get("config") or {}

    if not src:
        raise HTTPException(status_code=400, detail="source is required (in body or query)")

    # Only allow simple module-name characters — src is interpolated into an
    # import below, so never accept paths or arbitrary identifiers.
    if not re.fullmatch(r"[a-z_]+", str(src).lower()):
        return ApiResponse(data={
            "success": False,
            "jobs_found": 0,
            "error": f"Invalid job source name: {src}",
        })

    try:
        # Try to import the source module
        source_module = __import__(f"job_sources.{str(src).lower()}_source", fromlist=[src])

        if hasattr(source_module, "test_connection"):
            success, jobs_found = await source_module.test_connection(config)
        else:
            # Try a mock search
            jobs_found = 0
            success = True

        return ApiResponse(data={
            "success": success,
            "jobs_found": jobs_found,
        })
    except ImportError:
        return ApiResponse(data={
            "success": False,
            "jobs_found": 0,
            "error": f"Unknown job source: {src}",
        })