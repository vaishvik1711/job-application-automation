"""Applications API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from api.schemas import ApplicationSchema, ApiResponse
from api.dependencies import get_db_session
from database.models import Application, ApplicationStatus as AppStatusEnum
from database.repositories import RepositoryFactory
from api.routes.jobs import _job_to_schema

router = APIRouter()

# ---------------------------------------------------------------------------
# Status vocabulary mapping.
#
# The frontend kanban uses 8 display statuses (READY_TO_APPLY ... WITHDRAWN)
# while the DB enum stores pipeline statuses (discovered/qualified/applied/...).
# SQLAlchemy Enum columns persist member *names* (e.g. "READY"), so the
# mapping below targets names and every API response speaks the frontend
# vocabulary. Unknown backend values fall back to READY_TO_APPLY so cards
# always land in a column.
# ---------------------------------------------------------------------------
FRONTEND_TO_BACKEND = {
    "READY_TO_APPLY": AppStatusEnum.READY,
    "APPLYING": AppStatusEnum.APPLYING,
    "SUBMITTED": AppStatusEnum.APPLIED,
    "INTERVIEW_SCHEDULED": AppStatusEnum.INTERVIEW,
    "INTERVIEWED": AppStatusEnum.INTERVIEWED,
    "OFFER": AppStatusEnum.OFFER,
    "REJECTED": AppStatusEnum.REJECTED,
    "WITHDRAWN": AppStatusEnum.WITHDRAWN,
}
BACKEND_TO_FRONTEND = {
    AppStatusEnum.DISCOVERED: "READY_TO_APPLY",
    AppStatusEnum.REJECTED: "REJECTED",
    AppStatusEnum.QUALIFIED: "READY_TO_APPLY",
    AppStatusEnum.RESUME_CREATED: "READY_TO_APPLY",
    AppStatusEnum.READY: "READY_TO_APPLY",
    AppStatusEnum.APPLYING: "APPLYING",
    AppStatusEnum.APPLIED: "SUBMITTED",
    AppStatusEnum.FAILED: "REJECTED",
    AppStatusEnum.NEEDS_HUMAN_INPUT: "READY_TO_APPLY",
    AppStatusEnum.INTERVIEW: "INTERVIEW_SCHEDULED",
    AppStatusEnum.INTERVIEWED: "INTERVIEWED",
    AppStatusEnum.REJECTED_BY_COMPANY: "REJECTED",
    AppStatusEnum.OFFER: "OFFER",
    AppStatusEnum.WITHDRAWN: "WITHDRAWN",
}


def _frontend_status(value) -> str:
    """Convert a stored ApplicationStatus (or raw value/name) to a frontend column name."""
    if value is None:
        return "READY_TO_APPLY"
    if isinstance(value, AppStatusEnum):
        return BACKEND_TO_FRONTEND.get(value, "READY_TO_APPLY")
    # raw name or value string from the DB driver
    for member in AppStatusEnum:
        if value in (member.name, member.value):
            return BACKEND_TO_FRONTEND.get(member, "READY_TO_APPLY")
    return "READY_TO_APPLY"


def _parse_app_id(app_id: str) -> int:
    try:
        return int(app_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"Invalid application id: {app_id!r}")


def _map_status(status_str) -> AppStatusEnum:
    """Accept a frontend column name (or legacy backend value/name)."""
    if not isinstance(status_str, str):
        raise HTTPException(status_code=400, detail="status must be a string")
    key = status_str.strip()
    member = FRONTEND_TO_BACKEND.get(key.upper())
    if member:
        return member
    # legacy/verbose clients may send backend values directly
    for m in AppStatusEnum:
        if key.lower() in (m.value, m.name.lower()):
            return m
    valid = ", ".join(FRONTEND_TO_BACKEND.keys())
    raise HTTPException(status_code=400, detail=f"Invalid status {status_str!r}. Valid: {valid}")


async def _serialize_application(repos, session: AsyncSession, app_record: Application, include_relations=True):
    job = await repos.jobs.get_job(app_record.job_id) if include_relations else None
    resume = await repos.resumes.get_resume(app_record.resume_id) if include_relations else None

    # Reuse the full job schema — a hand-rolled subset here previously dropped
    # the real location/description and broke detail views.
    job_dict = _job_to_schema(job) if job else None

    # The frontend reads format/file_url/job_title/company off the nested
    # resume (kanban card renders `resume.format.toUpperCase()`), so mirror
    # the /resumes serializer instead of exposing raw model columns.
    resume_job = await repos.jobs.get_job(resume.job_id) if resume else None
    resume_dict = {
        "id": str(resume.id),
        "job_id": str(resume.job_id),
        "job_title": resume_job.title if resume_job else "",
        "company": resume_job.company if resume_job else "",
        "template_id": "",
        "file_path": resume.file_path,
        "file_url": resume.filename,
        "format": "docx",
        "customization_options": {},
        "created_at": resume.created_at.isoformat() if resume.created_at else None,
    } if resume else None

    return {
        "id": str(app_record.id),
        "job_id": str(app_record.job_id),
        "job": job_dict,
        "resume_id": str(app_record.resume_id),
        "resume": resume_dict,
        "cover_letter": None,
        "status": _frontend_status(app_record.status),
        "applied_at": app_record.applied_at.isoformat() if app_record.applied_at else None,
        "submitted_at": app_record.submitted_at.isoformat() if app_record.submitted_at else None,
        "interview_date": None,
        # notes live in error_message — surfaced here so PATCHed notes round-trip
        "notes": app_record.error_message,
        "follow_up_date": None,
        "external_application_id": app_record.confirmation,
        "created_at": app_record.created_at.isoformat() if app_record.created_at else None,
        "updated_at": app_record.updated_at.isoformat() if app_record.updated_at else None,
    }


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
    page = max(1, page)
    page_size = min(max(1, page_size), 200)

    query = select(Application).order_by(
        Application.created_at.desc() if sort_order == "desc" else Application.created_at.asc()
    )

    if status:
        query = query.where(Application.status == _map_status(status))

    count_query = select(func.count(Application.id))
    if status:
        count_query = count_query.where(Application.status == _map_status(status))

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    applications = result.scalars().all()

    total = await session.scalar(count_query)

    items = []
    for app in applications:
        items.append(await _serialize_application(repos, session, app))

    return ApiResponse(data={
        "items": items,
        "total": total or 0,
        "page": page,
        "page_size": page_size,
        "total_pages": ((total or 0) + page_size - 1) // page_size if total else 0,
    })


# NOTE: declared before /applications/{app_id} so "bulk-status" is not
# captured as a path parameter.
@router.patch("/applications/bulk-status", response_model=ApiResponse)
async def bulk_update_status(
    data: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """Bulk update application statuses."""
    ids = data.get("ids", [])
    status_member = _map_status(data.get("status", "SUBMITTED"))

    if not ids:
        return ApiResponse(data={"updated": 0})

    try:
        numeric_ids = [int(i) for i in ids]
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="ids must be a list of integers")

    stmt = select(Application).where(Application.id.in_(numeric_ids))
    result = await session.execute(stmt)
    apps = result.scalars().all()

    for app_record in apps:
        app_record.status = status_member

    await session.flush()

    return ApiResponse(data={"updated": len(apps)})


@router.get("/applications/{app_id}", response_model=ApiResponse)
async def get_application(
    app_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get a single application."""
    repos = RepositoryFactory(session)
    app_record = await repos.applications.get_application(_parse_app_id(app_id))

    if not app_record:
        raise HTTPException(status_code=404, detail="Application not found")

    return ApiResponse(data=await _serialize_application(repos, session, app_record))


@router.post("/applications", response_model=ApiResponse)
async def create_application(
    data: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """Create a new application."""
    data = data or {}
    if "job_id" not in data or "resume_id" not in data:
        raise HTTPException(status_code=400, detail="Both job_id and resume_id are required")
    try:
        job_id, resume_id = int(data["job_id"]), int(data["resume_id"])
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="job_id and resume_id must be integers")

    repos = RepositoryFactory(session)

    profile = await repos.candidates.get_profile()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Save your profile first.")

    job = await repos.jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    resume = await repos.resumes.get_resume(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail=f"Resume {resume_id} not found")

    new_app = Application(
        candidate_id=profile.id,
        job_id=job_id,
        resume_id=resume_id,
        application_url=data.get("application_url") or job.application_url or "https://example.com/apply",
        status=_map_status(data.get("status", "READY_TO_APPLY")),
    )
    new_app.error_message = data.get("notes")
    session.add(new_app)
    try:
        await session.flush()
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail=f"An application for job {job_id} already exists",
        )

    return ApiResponse(data=await _serialize_application(repos, session, new_app))


@router.patch("/applications/{app_id}", response_model=ApiResponse)
async def update_application(
    app_id: str,
    data: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """Update an application."""
    result = await session.execute(select(Application).where(Application.id == _parse_app_id(app_id)))
    app_record = result.scalars().first()

    if not app_record:
        raise HTTPException(status_code=404, detail="Application not found")

    if "status" in data and data["status"] is not None:
        app_record.status = _map_status(data["status"])
    if "notes" in data:
        app_record.error_message = data["notes"]

    try:
        await session.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Update conflicts with existing data")

    return ApiResponse(data={
        "id": str(app_record.id),
        "status": _frontend_status(app_record.status),
        "notes": app_record.error_message,
    })


@router.delete("/applications/{app_id}", response_model=ApiResponse)
async def delete_application(
    app_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Delete an application."""
    result = await session.execute(select(Application).where(Application.id == _parse_app_id(app_id)))
    app_record = result.scalars().first()

    if not app_record:
        raise HTTPException(status_code=404, detail="Application not found")

    await session.delete(app_record)
    await session.flush()

    return ApiResponse(data={"success": True})
