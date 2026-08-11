"""Applications API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from api.schemas import ApplicationSchema, ApiResponse
from api.dependencies import get_db_session
from database.models import Application, ApplicationStatus as AppStatusEnum
from database.repositories import RepositoryFactory

router = APIRouter()


@router.get("/applications", response_model=ApiResponse)
async def list_applications(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    session: AsyncSession = Depends(get_db_session),
):
    """List applications with pagination and filtering."""
    repos = RepositoryFactory(session)

    query = select(Application).order_by(
        Application.created_at.desc() if sort_order == "desc" else Application.created_at.asc()
    )

    if status:
        query = query.where(Application.status == status)

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    applications = result.scalars().all()

    total = await session.scalar(
        select(func.count(Application.id)).where(
            Application.status == status if status else True
        )
    )

    items = []
    for app in applications:
        job = await repos.jobs.get_job(app.job_id)
        resume = await repos.resumes.get_resume(app.resume_id)

        items.append({
            "id": str(app.id),
            "job_id": str(app.job_id),
            "job": {
                "id": str(job.id),
                "title": job.title,
                "company": job.company,
                "location": {"country": "Canada", "remote": False},
                "description": "",
                "requirements": [],
                "job_type": job.employment_type.value if job.employment_type else "full_time",
                "experience_level": "mid",
                "source": job.source,
                "source_url": job.application_url or "",
                "posted_date": "",
                "discovered_at": job.discovered_at.isoformat() if job.discovered_at else "",
                "status": job.status.value if job.status else "discovered",
            } if job else None,
            "resume_id": str(app.resume_id),
            "resume": {
                "id": str(resume.id),
                "job_id": str(resume.job_id),
                "file_path": resume.file_path,
                "created_at": resume.created_at.isoformat() if resume.created_at else "",
            } if resume else None,
            "cover_letter": None,
            "status": app.status.value if app.status else "discovered",
            "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
            "interview_date": app.interview_date,
            "notes": None,
            "follow_up_date": None,
            "external_application_id": app.confirmation,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "updated_at": app.updated_at.isoformat() if app.updated_at else None,
        })

    return ApiResponse(data={
        "items": items,
        "total": total or 0,
        "page": page,
        "page_size": page_size,
        "total_pages": ((total or 0) + page_size - 1) // page_size if total else 0,
    })


@router.get("/applications/{app_id}", response_model=ApiResponse)
async def get_application(
    app_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get a single application."""
    repos = RepositoryFactory(session)
    app_record = await repos.applications.get_application(int(app_id))

    if not app_record:
        raise HTTPException(status_code=404, detail="Application not found")

    job = await repos.jobs.get_job(app_record.job_id)
    resume = await repos.resumes.get_resume(app_record.resume_id)

    return ApiResponse(data={
        "id": str(app_record.id),
        "job_id": str(app_record.job_id),
        "job": None,
        "resume_id": str(app_record.resume_id),
        "resume": None,
        "cover_letter": None,
        "status": app_record.status.value if app_record.status else "discovered",
        "applied_at": app_record.applied_at.isoformat() if app_record.applied_at else None,
        "submitted_at": app_record.submitted_at.isoformat() if app_record.submitted_at else None,
        "interview_date": app_record.interview_date,
        "notes": None,
        "follow_up_date": None,
        "external_application_id": app_record.confirmation,
        "created_at": app_record.created_at.isoformat() if app_record.created_at else None,
        "updated_at": app_record.updated_at.isoformat() if app_record.updated_at else None,
    })


@router.post("/applications", response_model=ApiResponse)
async def create_application(
    data: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """Create a new application."""
    from database.models import Application

    new_app = Application(
        candidate_id=1,  # Default candidate
        job_id=int(data["job_id"]),
        resume_id=int(data["resume_id"]),
        application_url="https://example.com/apply",
        status=AppStatusEnum.READY,
    )
    session.add(new_app)
    await session.flush()

    return ApiResponse(data={
        "id": str(new_app.id),
        "job_id": str(new_app.job_id),
        "resume_id": str(new_app.resume_id),
        "status": "ready",
        "created_at": new_app.created_at.isoformat(),
        "updated_at": new_app.updated_at.isoformat(),
    })


@router.patch("/applications/{app_id}", response_model=ApiResponse)
async def update_application(
    app_id: str,
    data: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """Update an application."""
    from database.models import Application

    result = await session.execute(select(Application).where(Application.id == int(app_id)))
    app_record = result.scalars().first()

    if not app_record:
        raise HTTPException(status_code=404, detail="Application not found")

    if "status" in data:
        app_record.status = AppStatusEnum(data["status"].lower())
    if "notes" in data:
        app_record.error_message = data["notes"]

    await session.flush()

    return ApiResponse(data={
        "id": str(app_record.id),
        "status": app_record.status.value if app_record.status else "discovered",
    })


@router.patch("/applications/bulk-status", response_model=ApiResponse)
async def bulk_update_status(
    data: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """Bulk update application statuses."""
    ids = data.get("ids", [])
    status_val = data.get("status", "applied")

    if not ids:
        return ApiResponse(data={"updated": 0})

    stmt = (
        select(Application)
        .where(Application.id.in_([int(id) for id in ids]))
    )
    result = await session.execute(stmt)
    apps = result.scalars().all()

    for app_record in apps:
        app_record.status = AppStatusEnum(status_val.lower())

    await session.flush()

    return ApiResponse(data={"updated": len(apps)})


@router.delete("/applications/{app_id}", response_model=ApiResponse)
async def delete_application(
    app_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Delete an application."""
    from database.models import Application

    result = await session.execute(select(Application).where(Application.id == int(app_id)))
    app_record = result.scalars().first()

    if not app_record:
        raise HTTPException(status_code=404, detail="Application not found")

    await session.delete(app_record)
    await session.flush()

    return ApiResponse(data={"success": True})