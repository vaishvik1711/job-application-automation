"""Resumes API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from api.schemas import (
    GeneratedResumeSchema,
    ValidationResultSchema,
    ResumeTemplateSchema,
    ApiResponse,
)
from api.dependencies import get_db_session
from database.models import Resume, CandidateProfile, Job

from utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

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
    import glob
    from resume.agent import create_resume_agent
    from database.repositories import RepositoryFactory
    from sqlalchemy import select
    from database.models import Job

    logger.info(f"Generate resume called with options: {options}")
    job_id = int(options["job_id"])
    logger.info(f"Looking for job_id: {job_id}")

    repo = RepositoryFactory(session)
    job = await repo.jobs.get_job(job_id)
    logger.info(f"Repository get_job result: {job}")

    # Also try direct query
    direct = await session.execute(select(Job).where(Job.id == job_id))
    direct_job = direct.scalars().first()
    logger.info(f"Direct query result: {direct_job}")

    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found (id={job_id})")

    profile = await repo.candidates.get_profile()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Find the user's uploaded resume (DOCX or PDF) in the master_resume directory
    import os, glob
    resume_dir = "data/master_resume"
    resume_files = glob.glob(f"{resume_dir}/*.docx") + glob.glob(f"{resume_dir}/*.pdf")

    # Fallback: try to download from Supabase Storage
    if not resume_files:
        try:
            from api.routes.profile import get_supabase_client
            sb = get_supabase_client()
            # List files in the resumes bucket
            files = sb.storage.from_("resumes").list()
            if files:
                # Download the most recently uploaded resume
                latest = files[-1]
                file_data = sb.storage.from_("resumes").download(latest["name"])
                os.makedirs(resume_dir, exist_ok=True)
                local_path = f"{resume_dir}/{latest['name'].split('/')[-1]}"
                with open(local_path, "wb") as f:
                    f.write(file_data)
                resume_files = [local_path]
        except Exception as e:
            logger.warning("Could not download resume from Supabase: %s", e)

    if not resume_files:
        raise HTTPException(status_code=404, detail="No master resume found. Upload your resume first.")
    master_resume_path = resume_files[0]

    agent = await create_resume_agent()
    result = await agent.generate_resume(
        job_id=int(options["job_id"]),
        master_resume_path=master_resume_path,
    )

    return ApiResponse(data={
        "id": str(result.resume_id),
        "job_id": options["job_id"],
        "job_title": job.title,
        "company": job.company,
        "template_id": "user_uploaded",
        "file_path": result.resume_path,
        "file_url": result.resume_path,
        "format": "docx",
        "created_at": result.created_at.isoformat() if result.created_at else None,
    })


@router.get("/resumes/{resume_id}/validate", response_model=ApiResponse)
async def validate_resume(
    resume_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Validate a generated resume."""
    import glob, os
    from resume.validator import ResumeValidator

    # Find the user's uploaded resume
    resume_dir = "data/master_resume"
    resume_files = glob.glob(f"{resume_dir}/*.docx") + glob.glob(f"{resume_dir}/*.pdf")
    if not resume_files:
        # Try Supabase fallback
        try:
            from api.routes.profile import get_supabase_client
            sb = get_supabase_client()
            files = sb.storage.from_("resumes").list()
            if files:
                latest = files[-1]
                file_data = sb.storage.from_("resumes").download(latest["name"])
                os.makedirs(resume_dir, exist_ok=True)
                local_path = f"{resume_dir}/{latest['name'].split('/')[-1]}"
                with open(local_path, "wb") as f:
                    f.write(file_data)
                resume_files = [local_path]
        except Exception as e:
            logger.warning("Could not download resume from Supabase: %s", e)

    master_resume_path = resume_files[0] if resume_files else None
    if not master_resume_path:
        raise HTTPException(status_code=404, detail="No master resume found")

    validator = await ResumeValidator.create()
    result = await validator.validate_resume(int(resume_id), master_resume_path)

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