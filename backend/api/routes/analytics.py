"""Analytics API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from api.schemas import (
    AnalyticsOverviewSchema,
    PipelineStatsSchema,
    SourceEffectivenessSchema,
    SkillGapSchema,
    TimeSeriesDataSchema,
    ScoreDistributionSchema,
    ResponseRateSchema,
    ApiResponse,
)
from api.dependencies import get_db_session
from database.models import Job, JobMatch, Application, DailyStatistics, JobStatus

router = APIRouter()


@router.get("/analytics/overview", response_model=ApiResponse)
async def get_overview(session: AsyncSession = Depends(get_db_session)):
    """Get analytics overview."""
    from database.repositories import RepositoryFactory

    repos = RepositoryFactory(session)

    # Pipeline stats - count jobs by status
    status_counts = {}
    result = await session.execute(
        select(Job.status, func.count(Job.id)).group_by(Job.status)
    )
    for row in result:
        key = row[0].value if row[0] else "unknown"
        status_counts[key] = row[1]

    pipeline = {
        "discovered": status_counts.get("discovered", 0),
        "deduplicated": status_counts.get("deduplicated", 0),
        "matched": status_counts.get("matched", 0),
        "qualified": status_counts.get("qualified", 0),
        "resume_created": status_counts.get("resume_created", 0),
        "ready_to_apply": status_counts.get("ready_to_apply", 0),
        "applied": status_counts.get("applied", 0),
        "interviewed": status_counts.get("applied", 0),  # Approximation
        "offers": 0,
        "rejected": status_counts.get("rejected", 0),
    }

    # Source effectiveness
    result = await session.execute(
        select(Job.source, func.count(Job.id)).group_by(Job.source)
    )
    source_effectiveness = []
    for row in result:
        source_effectiveness.append({
            "source": row[0] if row[0] else "unknown",
            "jobs_found": row[1],
            "jobs_qualified": 0,
            "applications_submitted": 0,
            "interviews": 0,
            "offers": 0,
            "conversion_rate": 0.0,
        })

    # Skill gaps (placeholder - would need actual analysis)
    skill_gaps = [
        {
            "skill": "Python",
            "gap": "Missing advanced async patterns",
            "severity": "medium",
            "required_count": 3,
            "candidate_level": "Intermediate",
        }
    ]

    # Applications over time
    result = await session.execute(
        select(
            func.date_trunc('day', Application.created_at).label('date'),
            func.count(Application.id).label('count')
        ).group_by('date').order_by('date').limit(30)
    )
    applications_over_time = [
        {
            "date": row.date.strftime("%Y-%m-%d") if row.date else "",
            "applications": row.count,
            "interviews": 0,
            "offers": 0,
        }
        for row in result
    ]

    # Match score distribution
    result = await session.execute(
        select(
            func.round(JobMatch.match_score / 10) * 10,
            func.count(JobMatch.id)
        ).group_by(1).order_by(1)
    )
    match_score_distribution = [
        {
            "range": f"{int(row[0])}-{int(row[0]) + 9}%",
            "count": row[1],
        }
        for row in result
    ]

    # Response rates (placeholder)
    response_rates = [
        {"category": "Interview", "rate": 0.25, "total": 40},
        {"category": "Offer", "rate": 0.05, "total": 40},
    ]

    return ApiResponse(data={
        "pipeline": pipeline,
        "source_effectiveness": source_effectiveness,
        "skill_gaps": skill_gaps,
        "applications_over_time": applications_over_time,
        "match_score_distribution": match_score_distribution,
        "response_rates": response_rates,
    })


@router.get("/analytics/pipeline", response_model=ApiResponse)
async def get_pipeline(session: AsyncSession = Depends(get_db_session)):
    """Get pipeline statistics."""
    status_counts = {}
    result = await session.execute(
        select(Job.status, func.count(Job.id)).group_by(Job.status)
    )
    for row in result:
        key = row[0].value if row[0] else "unknown"
        status_counts[key] = row[1]

    return ApiResponse(data={
        "discovered": status_counts.get("discovered", 0),
        "deduplicated": status_counts.get("deduplicated", 0),
        "matched": status_counts.get("matched", 0),
        "qualified": status_counts.get("qualified", 0),
        "resume_created": status_counts.get("resume_created", 0),
        "ready_to_apply": status_counts.get("ready_to_apply", 0),
        "applied": status_counts.get("applied", 0),
        "interviewed": status_counts.get("applied", 0),
        "offers": 0,
        "rejected": status_counts.get("rejected", 0),
    })


@router.get("/analytics/sources", response_model=ApiResponse)
async def get_source_effectiveness(session: AsyncSession = Depends(get_db_session)):
    """Get source effectiveness analytics."""
    result = await session.execute(
        select(Job.source, func.count(Job.id)).group_by(Job.source)
    )

    sources = []
    for row in result:
        sources.append({
            "source": row[0] if row[0] else "unknown",
            "jobs_found": row[1],
        })

    return ApiResponse(data=sources)


@router.get("/analytics/skill-gaps", response_model=ApiResponse)
async def get_skill_gaps(session: AsyncSession = Depends(get_db_session)):
    """Get skill gap analysis."""
    # Placeholder - would need actual skill gap analysis from LLM
    return ApiResponse(data=[
        {
            "skill": "Python",
            "gap": "Missing advanced async patterns",
            "severity": "medium",
        }
    ])


@router.get("/analytics/timeseries", response_model=ApiResponse)
async def get_timeseries(
    days: int = 30,
    session: AsyncSession = Depends(get_db_session),
):
    """Get time series data for applications."""
    result = await session.execute(
        select(
            func.date_trunc('day', Application.created_at).label('date'),
            func.count(Application.id).label('count')
        ).group_by('date').order_by('date').limit(days)
    )

    return ApiResponse(data=[
        {
            "date": row.date.strftime("%Y-%m-%d") if row.date else "",
            "applications": row.count,
            "interviews": 0,
            "offers": 0,
        }
        for row in result
    ])


@router.get("/analytics/export")
async def export_report(
    format: str = "pdf",
    session: AsyncSession = Depends(get_db_session),
):
    """Export analytics report as PDF or Excel."""
    from fastapi.responses import JSONResponse

    # For now, return a simple JSON report
    return JSONResponse(content={"message": "Export functionality not fully implemented yet"})