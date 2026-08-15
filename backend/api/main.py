"""
FastAPI application for Job Automation System.
This provides the REST API backend for the frontend dashboard.
"""
# Load environment variables FIRST, before any other imports that read env vars
from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager

import logging
import socketio
from sqlalchemy import text
from api.websocket import sio

from api.routes.health import router as health_router
from api.routes.profile import router as profile_router
from api.routes.jobs import router as jobs_router
from api.routes.matching import router as matching_router
from api.routes.resumes import router as resumes_router
from api.routes.applications import router as applications_router
from api.routes.analytics import router as analytics_router
from api.routes.settings import router as settings_router
from api.dependencies import engine, async_session
from database import models as db_models
from sqlalchemy import select

# Setup logging
from utils.logger import setup_logging
setup_logging()

logger = logging.getLogger(__name__)


# Create / migrate tables on startup.
# SQLAlchemy's create_all only creates missing tables — it does NOT add
# columns to existing tables, so we must run ALTER TABLE for any new
# columns added after the initial deployment.
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(db_models.Base.metadata.create_all)
            # ------------------------------------------------------------------
            # Schema migrations for columns added after initial deployment.
            # ------------------------------------------------------------------
            # Detect dialect to use correct ALTER TABLE syntax
            dialect = engine.dialect.name
            if dialect == "postgresql":
                # PostgreSQL supports IF NOT EXISTS
                await conn.execute(
                    text(
                        "ALTER TABLE candidate_profiles "
                        "ADD COLUMN IF NOT EXISTS additional_experience JSON"
                    )
                )
                await conn.execute(
                    text(
                        "ALTER TABLE candidate_profiles "
                        "ADD COLUMN IF NOT EXISTS title_keywords JSON"
                    )
                )
                await conn.execute(
                    text(
                        "ALTER TABLE job_matches "
                        "ADD COLUMN IF NOT EXISTS job_analysis JSON"
                    )
                )
            elif dialect == "sqlite":
                # SQLite doesn't support IF NOT EXISTS in ALTER TABLE
                # Check if columns exist first
                for col_name in ["additional_experience", "title_keywords"]:
                    result = await conn.execute(
                        text(f"PRAGMA table_info(candidate_profiles)")
                    )
                    columns = [row[1] for row in result.fetchall()]
                    if col_name not in columns:
                        await conn.execute(
                            text(f"ALTER TABLE candidate_profiles ADD COLUMN {col_name} JSON")
                        )
                # Check for job_analysis column in job_matches
                result = await conn.execute(
                    text("PRAGMA table_info(job_matches)")
                )
                columns = [row[1] for row in result.fetchall()]
                if "job_analysis" not in columns:
                    await conn.execute(
                        text("ALTER TABLE job_matches ADD COLUMN job_analysis JSON")
                    )
    except Exception as e:
        logger.warning("Database connection failed during startup: %s", e)
        logger.warning("Tables will not be created until the database is reachable.")

    # Seed default matching config
    try:
        async with async_session() as session:
            result = await session.execute(select(db_models.MatchingConfig))
            config = result.scalars().first()
            if not config:
                config = db_models.MatchingConfig(
                    default_weights={"skills": 30, "experience": 25, "education": 10, "location": 15, "keywords": 20},
                    auto_qualify_threshold=75.0,
                    min_skill_match=0.5,
                )
                session.add(config)
                await session.flush()
    except Exception as e:
        logger.warning("Failed to seed matching config: %s", e)

    yield


app = FastAPI(
    title="Job Automation API",
    description="API for the AI Job Application Automation System",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers — routes mount directly (no /api prefix) so the
# frontend's VITE_API_URL + relative paths resolve correctly in production.
# In dev, Vite's proxy on '/api' still works because '/api' is a standalone
# info endpoint (see above), not a prefix.
app.include_router(health_router)
app.include_router(profile_router)
app.include_router(jobs_router)
app.include_router(matching_router)
app.include_router(resumes_router)
app.include_router(applications_router)
app.include_router(analytics_router)
app.include_router(settings_router)


@app.get("/")
async def root():
    return RedirectResponse(url="/health")


@app.get("/api")
async def api_root():
    return {"message": "Job Automation API", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Wrap the FastAPI app with the Socket.IO ASGI middleware so that a single
# uvicorn process serves both REST routes and real-time WebSocket events.
#
# The Socket.IO wrapper passes non-Socket.IO requests (including OPTIONS
# preflight) through to the FastAPI app, which already has CORS middleware
# configured. No additional CORS configuration is needed here.
# ---------------------------------------------------------------------------
app = socketio.ASGIApp(sio, other_asgi_app=app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)