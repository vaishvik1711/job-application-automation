"""Profile API routes."""
import logging
import os
import tempfile
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import ApiResponse
from api.dependencies import get_db_session, get_supabase_client
from database.models import CandidateProfile

logger = logging.getLogger(__name__)


class ParseRequest(BaseModel):
    file_id: str

router = APIRouter()


def _parse_resume_from_bytes(file_content: bytes, filename: str):
    """Parse resume from in-memory bytes by writing to a temp file first."""
    suffix = os.path.splitext(filename)[1].lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name
    try:
        from resume.parser import parse_resume
        return parse_resume(tmp_path)
    finally:
        os.unlink(tmp_path)


@router.get("/profile", response_model=ApiResponse)
async def get_profile(session: AsyncSession = Depends(get_db_session)):
    """Get the candidate profile."""
    result = await session.execute(select(CandidateProfile))
    profile = result.scalars().first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    # Serialize the profile from DB model to dict
    profile_dict = {
        "id": str(profile.id),
        "personal_info": {
            "full_name": profile.name,
            "email": profile.email,
            "phone": profile.phone,
            "location": profile.city,
            "linkedin": profile.linkedin_url,
            "github": profile.github_url,
            "portfolio": profile.portfolio_url,
        },
        "skills": profile.technical_skills or [],
        "experience": profile.employment_history or [],
        "education": profile.education or [],
        "certifications": profile.certifications or [],
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }

    return ApiResponse(data=profile_dict)


@router.patch("/profile", response_model=ApiResponse)
async def update_profile(
    data: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """Update the candidate profile."""
    result = await session.execute(select(CandidateProfile))
    profile = result.scalars().first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    # Update fields from the frontend schema
    if "personal_info" in data:
        pi = data["personal_info"]
        profile.name = pi.get("full_name", profile.name)
        profile.email = pi.get("email", profile.email)
        profile.phone = pi.get("phone", profile.phone)
        profile.city = pi.get("location", profile.city)
        profile.linkedin_url = pi.get("linkedin", profile.linkedin_url)
        profile.github_url = pi.get("github", profile.github_url)
        profile.portfolio_url = pi.get("portfolio", profile.portfolio_url)

    if "skills" in data:
        profile.technical_skills = data["skills"]

    if "experience" in data:
        profile.employment_history = data["experience"]

    if "education" in data:
        profile.education = data["education"]

    if "certifications" in data:
        profile.certifications = data["certifications"]

    await session.flush()

    return ApiResponse(data={"id": str(profile.id), "updated": True})


@router.post("/profile/upload", response_model=ApiResponse)
async def upload_resume(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
):
    """Upload a resume file (stores to Supabase Storage if configured, parses locally either way)."""
    file_content = await file.read()
    file_id = f"resumes/{uuid4()}_{file.filename}"
    file_url = ""

    # Upload to Supabase Storage (optional — gracefully fall back for local dev)
    try:
        supabase = get_supabase_client()
        res = supabase.storage.from_("resumes").upload(file_id, file_content)
        if not (hasattr(res, "get") and not res.get("path")):
            file_url = supabase.storage.from_("resumes").get_public_url(file_id)
    except Exception as e:
        logger.warning("Supabase storage upload failed (resume served in-memory only): %s", e)

    # Parse the resume using existing backend logic
    try:
        parsed = _parse_resume_from_bytes(file_content, file.filename)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse resume: {str(e)}",
        )

    return ApiResponse(data={
        "file_id": file_id,
        "filename": file.filename,
        "size": len(file_content),
        "url": file_url,
        "profile": parsed,
    })


@router.post("/profile/parse", response_model=ApiResponse)
async def parse_resume_endpoint(
    request: ParseRequest,
    supabase = Depends(get_supabase_client),
):
    """Parse a previously uploaded resume by file_id (JSON body)."""
    file_id = request.file_id
    try:
        res = supabase.storage.from_("resumes").download(file_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found in storage",
        )

    parsed = _parse_resume_from_bytes(res, file_id)

    return ApiResponse(data={
        "profile": parsed,
        "file_id": file_id,
        "confidence": 0.95,
        "extracted_fields": {},
    })