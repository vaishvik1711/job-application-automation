"""Profile API routes."""
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.schema import CandidateProfileSchema, ApiResponse
from api.dependencies import get_db_session, get_supabase_client
from database.models import CandidateProfile
import json
from uuid import uuid4

router = APIRouter()


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

    return ApiResponse[CandidateProfileSchema](data=profile_dict)


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

    return ApiResponse[CandidateProfileSchema](data={"id": str(profile.id), "updated": True})


@router.post("/profile/upload", response_model=ApiResponse)
async def upload_resume(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
    supabase = Depends(get_supabase_client),
):
    """Upload a resume file to Supabase Storage."""
    file_content = await file.read()
    file_name = f"resumes/{uuid4()}_{file.filename}"

    # Upload to Supabase Storage
    res = supabase.storage.from_("resumes").upload(file_name, file_content)
    if not res.get("path"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload resume to storage",
        )

    file_url = supabase.storage.from_("resumes").get_public_url(file_name)

    # Parse the resume using existing backend logic
    from resume.parser import parse_resume
    parsed = await parse_resume(file_content, file.filename)

    return ApiResponse(data={
        "file_id": file_name,
        "filename": file.filename,
        "size": len(file_content),
        "url": file_url,
        "profile": parsed,
    })


@router.post("/profile/parse", response_model=ApiResponse)
async def parse_resume_endpoint(
    file_id: str = Form(...),
    file_content: bytes = File(None),
    session: AsyncSession = Depends(get_db_session),
    supabase = Depends(get_supabase_client),
):
    """Parse a previously uploaded resume."""
    # Try to get file from Supabase Storage
    if not file_content:
        res = supabase.storage.from_("resumes").download(file_id)
        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found",
            )
        file_content = res

    from resume.parser import parse_resume
    parsed = await parse_resume(file_content, file_id)

    return ApiResponse(data={
        "profile": parsed,
        "file_id": file_id,
        "confidence": 0.95,
        "extracted_fields": {},
    })