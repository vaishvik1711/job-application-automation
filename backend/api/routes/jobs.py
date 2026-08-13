"""Jobs API routes."""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from api.schemas import JobSchema, PaginatedJobResponse, MatchDetailSchema, ApiResponse, JobStatsSchema
from api.dependencies import get_db_session
from database.models import Job, JobMatch, JobStatus
from database.repositories import RepositoryFactory
from datetime import datetime, timedelta

router = APIRouter()


def _job_to_schema(job: Job) -> dict:
    """Convert Job SQLAlchemy model to dict for frontend."""
    return {
        "id": str(job.id),
        "external_id": None,
        "title": job.title,
        "company": job.company,
        "location": {
            "city": None,
            "state": None,
            "country": "Canada",
            "remote": job.remote_type.value == "remote" if job.remote_type else False,
            "timezone": None,
        },
        "description": job.description,
        "requirements": job.requirements.split("\n") if job.requirements else [],
        "responsibilities": [],
        "benefits": [],
        "job_type": job.employment_type.value if job.employment_type else "full_time",
        "experience_level": "mid",
        "salary_range": {
            "min": job.salary_min,
            "max": job.salary_max,
            "currency": job.currency or "CAD",
            "period": "yearly",
        } if job.salary_min or job.salary_max else None,
        "source": job.source,
        "source_url": job.application_url or "",
        "posted_date": job.date_posted.isoformat() if job.date_posted else "",
        "discovered_at": job.discovered_at.isoformat() if job.discovered_at else "",
        "status": job.status.value if job.status else "discovered",
    }


@router.get("/jobs", response_model=ApiResponse)
async def list_jobs(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = "discovered_at",
    sort_order: str = "desc",
    session: AsyncSession = Depends(get_db_session),
):
    """List jobs with pagination and filtering."""
    repos = RepositoryFactory(session)

    query = select(Job).order_by(
        Job.discovered_at.desc() if sort_order == "desc" else Job.discovered_at.asc()
    )

    if status:
        query = query.where(Job.status == status)

    if search:
        query = query.where(
            func.lower(Job.title).contains(func.lower(search)) |
            func.lower(Job.company).contains(func.lower(search))
        )

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    jobs = result.scalars().all()

    # Count total
    count_query = select(func.count(Job.id))
    if status:
        count_query = count_query.where(Job.status == status)
    if search:
        count_query = count_query.where(
            func.lower(Job.title).contains(func.lower(search)) |
            func.lower(Job.company).contains(func.lower(search))
        )
    total = await session.scalar(count_query)

    items = [_job_to_schema(j) for j in jobs]

    return ApiResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
    })


@router.get("/jobs/{job_id}", response_model=ApiResponse)
async def get_job(
    job_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get a single job by ID."""
    job = await (RepositoryFactory(session).jobs.get_job(int(job_id)))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return ApiResponse(data=_job_to_schema(job))


@router.post("/jobs/search", response_model=ApiResponse)
async def search_jobs(
    request: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """Search for jobs (uses DiscoveryAgent with real-time Socket.IO updates)."""
    from agents.discovery_agent import create_discovery_agent
    from api.websocket import emit_pipeline_update, emit_error

    filters = request.get("filters", {})
    max_results = request.get("max_results_per_source", 50)

    try:
        await emit_pipeline_update(
            stage="search",
            current=0,
            total=1,
            message="Initializing job search agent...",
        )

        # Map frontend filter format to the format expected by job sources.
        # The generate-filters endpoint provides:
        #   primary_titles – actual job titles from the profile (e.g., "Data Analyst")
        #   keywords – individual skills (e.g., "SQL", "Python")
        # Job sources search by title first, so primary_titles is what produces
        # relevant results; keywords/skills become supplementary search terms.
        search_filters = dict(filters)
        if not search_filters.get("primary_titles"):
            keywords = filters.get("keywords", [])
            if isinstance(keywords, str):
                keywords = [keywords]
            # Without job titles from the filter generator, use the first
            # few keywords as title-like search terms.
            search_filters["primary_titles"] = keywords[:5]
            search_filters["secondary_titles"] = []

        agent = await create_discovery_agent()
        result = await agent.discover_jobs(
            filters=search_filters,
            limit_per_source=max_results,
        )
        await agent.close()

        # Fetch jobs discovered within the last hour (the agent saves jobs in
        # its own session, so use a time window instead of a pre-search marker).
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        stmt = (
            select(Job)
            .where(Job.discovered_at >= one_hour_ago)
            .order_by(Job.discovered_at.desc())
            .limit(max_results * 5)
        )
        db_result = await session.execute(stmt)
        jobs = db_result.scalars().all()

        await emit_pipeline_update(
            stage="search",
            current=1,
            total=1,
            message=f"Found {result.jobs_found} jobs across {len(result.sources_used)} sources ({result.jobs_new} new)",
        )

        return ApiResponse(data={
            "jobs": [_job_to_schema(j) for j in jobs],
            "total_found": result.jobs_found,
            "sources_searched": result.sources_used,
            "search_duration_ms": 0,
            "duplicates_removed": result.jobs_duplicate,
        })
    except Exception as e:
        await emit_error(f"Job search failed: {str(e)}")
        raise


@router.post("/jobs/{job_id}/analyze", response_model=ApiResponse)
async def analyze_job(
    job_id: str,
    weights: Optional[dict] = None,
    session: AsyncSession = Depends(get_db_session),
):
    """Analyze a job against the candidate profile and return match details."""
    from agents.matching_agent import MatchingAgent

    agent = MatchingAgent()
    match = await agent.match_job(int(job_id), weights or {})

    return ApiResponse(data=match)


@router.post("/jobs/batch-analyze", response_model=ApiResponse)
async def batch_analyze_jobs(
    job_ids: list,
    weights: Optional[dict] = None,
    session: AsyncSession = Depends(get_db_session),
):
    """Analyze multiple jobs at once."""
    from agents.matching_agent import MatchingAgent

    agent = MatchingAgent()
    matches = await agent.match_jobs(job_ids=[int(id) for id in job_ids], weights=weights or {})

    return ApiResponse(data=[m for m in matches])


@router.get("/jobs/matches", response_model=ApiResponse)
async def get_matches(
    page: int = 1,
    page_size: int = 20,
    verdict: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    session: AsyncSession = Depends(get_db_session),
):
    """Get matches with filtering."""
    repos = RepositoryFactory(session)

    query = select(JobMatch).order_by(JobMatch.match_score.desc())

    if min_score is not None:
        query = query.where(JobMatch.match_score >= min_score)
    if max_score is not None:
        query = query.where(JobMatch.match_score <= max_score)
    if verdict:
        query = query.where(JobMatch.recommendation == verdict.upper())

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    matches = result.scalars().all()

    # Load associated jobs
    items = []
    for match in matches:
        job = await repos.jobs.get_job(match.job_id)
        if job:
            items.append({
                "job_id": str(match.job_id),
                "job": _job_to_schema(job),
                "score": {
                    "overall": match.match_score,
                    "skills": match.technical_score,
                    "experience": 0,
                    "education": 0,
                    "location": 0,
                    "keywords": 0,
                    "verdict": "QUALIFIED" if match.recommendation == "APPLY" else "UNQUALIFIED",
                },
                "skill_matches": [],
                "experience_matches": [],
                "missing_requirements": match.missing_requirements or [],
                "matched_keywords": [],
                "analysis": match.reasoning,
                "analyzed_at": match.created_at.isoformat() if match.created_at else None,
            })

    return ApiResponse(data={
        "items": items,
        "total": len(items),
        "page": page,
        "page_size": page_size,
        "total_pages": 1,
    })


@router.get("/jobs/stats", response_model=ApiResponse)
async def get_job_stats(session: AsyncSession = Depends(get_db_session)):
    """Get job statistics."""
    total = await session.scalar(select(func.count(Job.id)))

    result = await session.execute(
        select(Job.status, func.count(Job.id)).group_by(Job.status)
    )
    by_status = {row.status.value if row.status else "unknown": row[1] for row in result}

    return ApiResponse(data={
        "total_jobs": total,
        "by_status": by_status,
        "by_source": {},
    })


@router.get("/jobs/export", response_class=BytesIO if False else None)
async def export_jobs(
    job_ids: Optional[str] = None,
    format: str = "csv",
    session: AsyncSession = Depends(get_db_session),
):
    """Export jobs to CSV or Excel."""
    from excel import export_to_excel

    ids = [int(id) for id in job_ids.split(",")] if job_ids else None

    if format == "excel":
        file_path = await export_to_excel("/tmp/export.xlsx", job_ids=ids)
        with open(file_path, "rb") as f:
            return StreamingResponse(
                iter([f.read()]),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename=export.xlsx"},
            )

    # CSV export
    query = select(Job)
    if ids:
        query = query.where(Job.id.in_(ids))
    result = await session.execute(query)
    jobs = result.scalars().all()

    import csv
    from io import StringIO

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Title", "Company", "Location", "Status", "Source", "Discovered"])
    for job in jobs:
        writer.writerow([
            job.title,
            job.company,
            job.location,
            job.status.value if job.status else "",
            job.source,
            job.discovered_at.isoformat() if job.discovered_at else "",
        ])

    return StreamingResponse(
        iter([output.getvalue().encode()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=export.csv"},
    )
