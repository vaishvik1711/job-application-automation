"""Resumes API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from api.schemas import (
    GeneratedResumeSchema,
    ValidationResultSchema,
    ResumeTemplateSchema,
    ResumeCustomizationOptionsSchema,
    ApiResponse,
)
from api.dependencies import get_db_session
from database.models import Resume, CandidateProfile, Job

router = APIRouter()

# Predefined resume templates (can be extended)
RESUME_TEMPLATES = [
    {
        "id": "professional",
        "name": "Professional",
        "description": "Clean, traditional format with clear section headings",
        "preview_url": "/templates/professional.png",
        "is_default": True,
    },
    {
        "id": "modern",
        "name": "Modern",
        "description": "Contemporary design with side columns and visual elements",
        "preview_url": "/templates/modern.png",
        "is_default": False,
    },
    {
        "id": "compact",
        "name": "Compact",
        "description": "Single-page format optimized for conciseness",
        "preview_url": "/templates/compact.png",
        "is_default": False,
    },
    {
        "id": "executive",
        "name": "Executive",
        "description": "Premium format designed for senior roles",
        "preview_url": "/templates/executive.png",
        "is_default": False,
    },
]


@router.get("/resumes", response_model=ApiResponse)
async def list_resumes(
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_db_session),
):
    """List all resumes with pagination."""
    query = select(Resume).order_by(Resume.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    resumes = result.scalars().all()

    total = await session.scalar(select(func.count(Resume.id)))

    items = []
    for r in resumes:
        items.append({
            "id": str(r.id),
            "job_id": str(r.job_id),
            "job_title": "",
            "company": "",
            "template_id": "",
            "file_path": r.file_path,
            "file_url": r.filename,
            "format": "docx",
            "customization_options": {},
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return ApiResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
    })


@router.get("/resumes/{resume_id}", response_model=ApiResponse)
async def get_resume(
    resume_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get a single resume by ID."""
    from database.repositories import RepositoryFactory

    repo = RepositoryFactory(session)
    resume = await repo.resumes.get_resume(int(resume_id))

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Get job details
    job = await repo.jobs.get_job(resume.job_id)

    return ApiResponse(data={
        "id": str(resume.id),
        "job_id": str(resume.job_id),
        "job_title": job.title if job else "",
        "company": job.company if job else "",
        "template_id": "",
        "file_path": resume.file_path,
        "file_url": resume.filename,
        "format": "docx",
        "customization_options": {},
        "validation_result": {
            "truthfulness_score": resume.truthfulness_score or 0,
            "ats_score": resume.validation_score or 0,
            "issues": resume.validation_issues or [],
            "suggestions": [],
            "validated_at": resume.created_at.isoformat() if resume.created_at else None,
        } if resume.validation_score is not None else None,
        "created_at": resume.created_at.isoformat() if resume.created_at else None,
    })


@router.post("/resumes/generate", response_model=ApiResponse)
async def generate_resume(
    options: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """Generate a customized resume for a job."""
    from resume.agent import ResumeAgent
    from database.repositories import RepositoryFactory

    repo = RepositoryFactory(session)
    job = await repo.jobs.get_job(int(options["job_id"]))

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    profile = await repo.candidates.get_profile()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    agent = await ResumeAgent.create()
    result = await agent.generate_resume(
        job_id=int(options["job_id"]),
        master_resume_path="data/master_resume/test_resume.docx",
        customization=ResumeCustomizationOptionsSchema(**options) if isinstance(options, dict) else options,
    )

    return ApiResponse(data={
        "id": str(result.resume_id),
        "job_id": options["job_id"],
        "job_title": job.title,
        "company": job.company,
        "template_id": options.get("template_id", "professional"),
        "file_path": result.resume_path,
        "file_url": result.resume_path,
        "format": options.get("format", "docx"),
        "customization_options": options,
        "created_at": result.created_at.isoformat() if result.created_at else None,
    })


@router.get("/resumes/{resume_id}/validate", response_model=ApiResponse)
async def validate_resume(
    resume_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Validate a generated resume."""
    from resume.validator import ResumeValidator

    validator = await ResumeValidator.create()
    result = await validator.validate_resume(int(resume_id), "data/master_resume/test_resume.docx")

    return ApiResponse(data={
        "truthfulness_score": result.validation_score or 0,
        "ats_score": result.format_score or 0,
        "issues": [
            {
                "type": i.get("type", "other"),
                "severity": i.get("severity", "medium"),
                "message": i.get("message", ""),
            } for i in (result.issues or [])
        ],
        "suggestions": result.suggestions or [],
        "validated_at": result.validated_at.isoformat() if result.validated_at else None,
    })


@router.get("/resumes/{resume_id}/download")
async def download_resume(
    resume_id: str,
    format: str = "docx",
    session: AsyncSession = Depends(get_db_session),
):
    """Download a resume file."""
    from database.repositories import RepositoryFactory
    from fastapi.responses import FileResponse

    repo = RepositoryFactory(session)
    resume = await repo.resumes.get_resume(int(resume_id))

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    file_path = resume.file_path
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if format == "docx" else "application/pdf",
        filename=f"resume_{resume.id}.{format}",
    )


@router.delete("/resumes/{resume_id}", response_model=ApiResponse)
async def delete_resume(
    resume_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Delete a resume."""
    from database.repositories import RepositoryFactory

    repo = RepositoryFactory(session)
    resume = await repo.resumes.get_resume(int(resume_id))

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    await session.delete(resume)
    await session.flush()

    return ApiResponse(data={"success": True})


@router.get("/resumes/templates", response_model=ApiResponse)
async def get_templates():
    """Get available resume templates."""
    return ApiResponse(data={"templates": RESUME_TEMPLATES})