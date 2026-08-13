"""Jobs API routes."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from api.schemas import JobSchema, PaginatedJobResponse, MatchDetailSchema, ApiResponse, JobStatsSchema
from api.dependencies import get_db_session
from database.models import Job, JobMatch, JobStatus
from database.repositories import RepositoryFactory
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

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
        # Match score placeholders populated by the search endpoint
        "match_score": None,
        "match_verdict": None,
        "skill_match_pct": None,
    }


def _enrich_with_match(job_dict: dict, match: Optional[JobMatch]) -> dict:
    """Inject match data into a job dict (mutates and returns it)."""
    if match is not None:
        job_dict["match_score"] = match.match_score
        job_dict["match_verdict"] = match.recommendation
        job_dict["skill_match_pct"] = match.technical_score
    return job_dict


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
    """Search for jobs and auto-analyze against the candidate profile."""
    from agents.discovery_agent import create_discovery_agent
    from agents.matching_agent import MatchingAgent
    from api.websocket import emit_pipeline_update, emit_error

    filters = request.get("filters", {})
    max_results = request.get("max_results_per_source", 50)

    try:
        await emit_pipeline_update(
            stage="search",
            current=0,
            total=3,
            message="Initializing job search agent...",
        )

        # Map frontend filter format to the format expected by job sources.
        search_filters = dict(filters)
        if not search_filters.get("primary_titles"):
            keywords = filters.get("keywords", [])
            if isinstance(keywords, str):
                keywords = [keywords]
            search_filters["primary_titles"] = keywords[:5]
            search_filters["secondary_titles"] = []

        # Map frontend source names to backend source names.
        frontend_sources = filters.get("sources", [])
        backend_source_map = {
            "indeed": "indeed",
            "linkedin": "jobspy",
            "jobbank": "jobbank",
        }
        backend_sources = None
        if frontend_sources:
            mapped = set()
            for fs in frontend_sources:
                bs = backend_source_map.get(fs)
                if bs:
                    mapped.add(bs)
            backend_sources = list(mapped) if mapped else None

        # --- Phase 1: Discover jobs ---
        # Split sources: only scrape JobBank from Railway (Indeed/LinkedIn blocked).
        # Indeed jobs must be pre-imported via run_indeed_scraper.py or DB.
        scrapable_sources = (
            [s for s in backend_sources if s != "indeed"]
            if backend_sources else None
        )
        agent = await create_discovery_agent()
        result = await agent.discover_jobs(
            filters=search_filters,
            limit_per_source=max_results,
            sources=scrapable_sources,
        )
        await agent.close()

        await emit_pipeline_update(
            stage="search",
            current=1,
            total=3,
            message=f"Found {result.jobs_found} jobs across {len(result.sources_used)} sources ({result.jobs_new} new)",
        )

        # Fetch jobs from DB — filter by source if user selected specific sources.
        # Use a wider lookback for pre-imported sources (Indeed) since they aren't scraped live.
        one_hour_ago = datetime.utcnow() - timedelta(hours=7 * 24)  # 7 days
        db_filters = [Job.discovered_at >= one_hour_ago]
        if backend_sources:
            db_source_filters = [
                Job.source.like(f"{bs}%") for bs in backend_sources
            ]
            db_filters.append(or_(*db_source_filters))
        stmt = (
            select(Job)
            .where(*db_filters)
            .order_by(Job.discovered_at.desc())
            .limit(max_results * 5)
        )
        db_result = await session.execute(stmt)
        jobs = db_result.scalars().all()

        # --- Phase 2: Auto-match against profile ---
        job_ids = [j.id for j in jobs if j.id]
        matching_result_text = ""
        if job_ids:
            await emit_pipeline_update(
                stage="matching",
                current=2,
                total=3,
                message=f"Analyzing {len(job_ids)} jobs against your profile...",
            )
            try:
                m_agent = MatchingAgent()
                m_result = await m_agent.match_jobs(job_ids=job_ids)
                matching_result_text = (
                    f" | {m_result.jobs_matched} matched"
                    f" ({m_result.jobs_qualified} qualified)"
                )
            except Exception as match_err:
                logger.warning("Auto-matching failed (search continues): %s", match_err)
                matching_result_text = " | matching skipped"

        # --- Phase 3: Enrich jobs with match data ---
        enriched_jobs = []
        for j in jobs:
            job_dict = _job_to_schema(j)
            # Load match from DB
            match_stmt = select(JobMatch).where(JobMatch.job_id == j.id).limit(1)
            match_result = await session.execute(match_stmt)
            match = match_result.scalars().first()
            enriched_jobs.append(_enrich_with_match(job_dict, match))

        await emit_pipeline_update(
            stage="complete",
            current=3,
            total=3,
            message=f"Search complete — {result.jobs_found} jobs found{matching_result_text}",
        )

        return ApiResponse(data={
            "jobs": enriched_jobs,
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


@router.post("/jobs/bulk-import", response_model=ApiResponse)
async def bulk_import_jobs(
    request: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Bulk import pre-scraped jobs (e.g., from local Indeed scraper).
    Accepts a list of job objects with fields matching RawJob format.
    """
    from utils.hashing import content_hash, job_fingerprint
    from database.models import RemoteType, EmploymentType, JobStatus, JobSource

    items = request.get("jobs", [])
    source_name = request.get("source", "indeed")
    if not items:
        return ApiResponse(data={"imported": 0, "total": 0, "errors": []})

    imported = 0
    errors = []

    for raw in items:
        try:
            title = (raw.get("title") or "").strip()
            company = (raw.get("company") or "").strip()
            if not title or not company:
                continue

            url = raw.get("url") or raw.get("source_url") or ""
            # Check for existing job by URL
            if url:
                existing = await session.execute(
                    select(Job).where(Job.canonical_url == url).limit(1)
                )
                if existing.scalars().first():
                    continue

            # Build content hash for dedup
            desc = (raw.get("description") or "")[:10000]
            reqs = (raw.get("requirements") or "")
            ch = content_hash(f"{desc}{reqs}")
            location = raw.get("location") or ""
            fingerprint = job_fingerprint(company, title, location)

            # Normalize remote / employment types
            remote_raw = (raw.get("remote_type") or "on_site").lower()
            remote_type = RemoteType.REMOTE if "remote" in remote_raw else RemoteType.HYBRID if "hybrid" in remote_raw else RemoteType.ON_SITE
            emp_raw = (raw.get("employment_type") or "full_time").lower()
            if "contract" in emp_raw:
                emp_type = EmploymentType.CONTRACT
            elif "part" in emp_raw:
                emp_type = EmploymentType.PART_TIME
            elif "intern" in emp_raw:
                emp_type = EmploymentType.INTERNSHIP
            else:
                emp_type = EmploymentType.FULL_TIME

            job = Job(
                canonical_url=url or f"{source_name}:{raw.get('source_job_id', '')}:{ch[:16]}",
                source=f"indeed",
                title=title,
                company=company,
                location=location,
                remote_type=remote_type,
                employment_type=emp_type,
                date_posted=datetime.utcnow(),
                salary_min=raw.get("salary_min"),
                salary_max=raw.get("salary_max"),
                currency=raw.get("currency", "CAD"),
                description=desc,
                requirements=reqs[:5000] or None,
                skills=raw.get("skills") or [],
                tools=raw.get("tools") or [],
                application_url=url,
                content_hash=ch,
                status=JobStatus.DISCOVERED,
            )
            session.add(job)
            await session.flush()

            # Add source reference
            source_ref = JobSource(
                job_id=job.id,
                source="indeed",
                source_url=url,
                source_job_id=str(raw.get("source_job_id", "")),
            )
            session.add(source_ref)
            imported += 1

        except Exception as e:
            errors.append(str(e))
            continue

    await session.commit()
    logger.info(f"Bulk imported {imported}/{len(items)} Indeed jobs")

    return ApiResponse(data={
        "imported": imported,
        "total": len(items),
        "errors": errors[:10],
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
