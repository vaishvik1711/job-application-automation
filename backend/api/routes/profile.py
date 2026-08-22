"""Profile API routes."""
import logging
import os
import tempfile
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from pydantic import BaseModel
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import ApiResponse
from api.dependencies import get_db_session, get_supabase_client
from database.models import (
    CandidateProfile,
    Resume,
    Application,
    ScreeningQuestion,
    ApplicationEvent,
    ApplicationError,
    JobMatch,
    JobSource,
    Job,
    MasterResume,
)

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


def _parsed_resume_to_profile_dict(parsed) -> dict:
    """Convert a ParsedResume dataclass into the CandidateProfile dict shape the
    frontend forms expect (personal_info, skills, experience, education, certifications)."""
    import re as _re

    ci = getattr(parsed, "contact_info", {}) or {}
    summary = getattr(parsed, "summary", "") or ""
    raw_text = getattr(parsed, "raw_text", "") or ""

    # Fallback: if the structured contact_info is empty, scan the raw text for
    # the first ~20 lines (covers the name/email/phone block at the top).
    if not ci.get("email") and raw_text:
        lines = raw_text.split("\n")[:20]
        for line in lines:
            line = line.strip()
            if not line:
                continue
            email_m = _re.search(r'[\w\.-]+@[\w\.-]+\.\w+', line)
            if email_m and not ci.get("email"):
                ci["email"] = email_m.group()
            phone_m = _re.search(r'[\+]?[\d\s\-\(\)]{10,}', line)
            if phone_m and not ci.get("phone"):
                ci["phone"] = phone_m.group().strip()
            if "linkedin" in line.lower() and not ci.get("linkedin"):
                lnk = _re.search(r'linkedin\.com/\S+', line, _re.I)
                ci["linkedin"] = lnk.group() if lnk else line
            if "github" in line.lower() and not ci.get("github"):
                gh = _re.search(r'github\.com/\S+', line, _re.I)
                ci["github"] = gh.group() if gh else line
        # Pick the first text-only line ≤4 words as the name
        for line in lines:
            line = line.strip()
            if line and not any(kw in line.lower() for kw in ["@", "http", "linkedin", "github",
                                                                "phone", "email", "mobile"]):
                words = line.split()
                if len(words) <= 4:
                    ci["name"] = line
                    break

        # Extract location from the contact-info line (pipe-separated: "City, Province | phone | email")
        if not ci.get("location"):
            for line in lines:
                if "|" in line and any(kw in line.lower() for kw in ["@", "phone", "mobile"]):
                    loc_part = line.split("|")[0].strip()
                    if loc_part and not any(k in loc_part.lower() for k in ("@", "http")):
                        ci["location"] = loc_part
                        break

    # --- personal_info ---
    personal_info = {
        "full_name": ci.get("name", ""),
        "email": ci.get("email", ""),
        "phone": ci.get("phone", ""),
        "location": ci.get("location", ""),
        "linkedin": ci.get("linkedin", ""),
        "github": ci.get("github", ""),
        "portfolio": ci.get("portfolio", ""),
        "website": ci.get("website", ""),
        "twitter": "",
        "summary": summary,
    }

    # --- skills (convert plain strings to Skill[] with a default category) ---
    raw_skills = list(getattr(parsed, "technical_skills", []) or [])
    raw_skills.extend(
        s for s in (getattr(parsed, "skills", []) or [])
        if s not in raw_skills
    )
    skills = [{"name": s, "category": "Programming Languages", "proficiency": 3} for s in raw_skills]

    # --- experience ---
    experience = []
    for wh in getattr(parsed, "work_history", []) or []:
        bullets = wh.get("bullets", [])
        if isinstance(bullets, list):
            description = "\n".join(bullets)
        else:
            description = bullets or ""
        tech = wh.get("technologies", []) or []
        experience.append({
            "company": wh.get("company", ""),
            "title": wh.get("title", ""),
            "location": wh.get("location", ""),
            "start_date": wh.get("start_date", ""),
            "end_date": wh.get("end_date", ""),
            "current": str(wh.get("end_date", "")).lower() in ("present", "current"),
            "description": description,
            "technologies": tech,
        })

    # --- education ---
    education = []
    for ed in getattr(parsed, "education", []) or []:
        education.append({
            "institution": ed.get("school", ed.get("institution", "")),
            "degree": ed.get("degree", ""),
            "field_of_study": ed.get("field_of_study", ""),
            "location": ed.get("location", ""),
            "start_date": ed.get("start_date", ""),
            "end_date": ed.get("year", ed.get("end_date", "")),
            "gpa": ed.get("gpa", ""),
        })

    # --- certifications ---
    certifications = []
    for cert in getattr(parsed, "certifications", []) or []:
        certifications.append({
            "name": cert.get("name", ""),
            "issuer": cert.get("issuer", cert.get("organization", "")),
            "date_obtained": cert.get("year", cert.get("date_obtained", "")),
            "expiry_date": cert.get("expiry_date", ""),
            "credential_id": cert.get("credential_id", ""),
            "credential_url": cert.get("url", ""),
        })

    # Fallback: if the parser didn't split sections correctly, scan sections
    # to find experience/education content and re-parse with lightweight heuristics.
    sections = getattr(parsed, "sections", []) or []
    if not experience or not education:
        for sec in sections:
            name = (getattr(sec, "name", "") or "").lower()
            content = (getattr(sec, "content", "") or "").strip()
            if not content:
                continue
            if not experience and any(kw in name for kw in ("experience", "employment", "work")):
                for block in _re.split(r"\n\s*\n", content):
                    lines = [l.strip() for l in block.split("\n") if l.strip()]
                    if len(lines) < 2:
                        continue
                    entry = {"company": "", "title": "", "location": "", "description": "",
                             "start_date": "", "end_date": "", "current": False, "technologies": []}
                    # Try Title | Company or first-line-heuristic
                    if "|" in lines[0]:
                        parts = [p.strip() for p in lines[0].split("|")]
                        entry["title"] = parts[0]
                        entry["company"] = parts[1] if len(parts) > 1 else ""
                    else:
                        # Fallback: first line is title, second is company
                        entry["title"] = lines[0]
                        if len(lines) > 1:
                            entry["company"] = lines[1]
                    # Date lines
                    for line in lines:
                        dm = _re.search(r"(\d{4})\s*[-–—]\s*(\d{4}|present|current)", line, _re.I)
                        if dm:
                            entry["start_date"] = dm.group(1)
                            entry["end_date"] = dm.group(2)
                            entry["current"] = dm.group(2).lower() in ("present", "current")
                    # Bullets as description
                    bullets = [l for l in lines if l.startswith(("•", "-", "·", "▪", "–", "*"))]
                    if bullets:
                        entry["description"] = "\n".join(b.strip("•-·▪–* ") for b in bullets)
                    else:
                        entry["description"] = "\n".join(lines)
                    # Deduplicate against already-parsed entries
                    already = {(e.get("title", ""), e.get("company", "")) for e in experience}
                    if (entry["title"], entry["company"]) not in already:
                        experience.append(entry)
            if not education and any(kw in name for kw in ("education", "academic")):
                for block in _re.split(r"\n\s*\n", content):
                    lines = [l.strip() for l in block.split("\n") if l.strip()]
                    if not lines:
                        continue
                    entry = {"institution": "", "degree": "", "field_of_study": "",
                             "location": "", "start_date": "", "end_date": "", "gpa": ""}
                    if "|" in lines[0]:
                        parts = [p.strip() for p in lines[0].split("|")]
                        entry["degree"] = parts[0]
                        entry["institution"] = parts[1] if len(parts) > 1 else ""
                    else:
                        entry["degree"] = lines[0]
                    for line in lines[1:]:
                        ym = _re.search(r"\d{4}", line)
                        if ym and not entry["end_date"]:
                            entry["end_date"] = ym.group()
                        elif not entry["institution"]:
                            entry["institution"] = line
                    already = {(e.get("institution", ""), e.get("degree", "")) for e in education}
                    if (entry["institution"], entry["degree"]) not in already:
                        education.append(entry)

    return {
        "personal_info": personal_info,
        "skills": skills,
        "experience": experience,
        "education": education,
        "certifications": certifications,
        "additional_experience": [],
    }


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

    # Serialize the profile from DB model to dict.
    # technical_skills is stored as List[str]; convert back to Skill[] for the frontend.
    stored_skills = profile.technical_skills or []
    skills_out = [
        {"name": s, "category": "Programming Languages", "proficiency": 3}
        if isinstance(s, str) else s
        for s in stored_skills
    ]
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
        "skills": skills_out,
        "experience": profile.employment_history or [],
        "education": profile.education or [],
        "certifications": profile.certifications or [],
        "additional_experience": profile.additional_experience or [],
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }

    return ApiResponse(data=profile_dict)


@router.delete("/profile", response_model=ApiResponse)
async def delete_profile(session: AsyncSession = Depends(get_db_session)):
    """Delete the candidate profile and all related data."""
    result = await session.execute(select(CandidateProfile))
    profile = result.scalars().first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    # Collect all job IDs linked to this profile via applications or resumes
    app_result = await session.execute(
        select(Application).where(Application.candidate_id == profile.id)
    )
    applications = app_result.scalars().all()

    resume_result = await session.execute(
        select(Resume).where(Resume.candidate_id == profile.id)
    )
    resumes = resume_result.scalars().all()

    job_ids = set()
    for app in applications:
        job_ids.add(app.job_id)
    for r in resumes:
        job_ids.add(r.job_id)

    # Delete related data in the correct order to avoid FK violations

    # 1. Applications (cascades to screening_questions, application_events, application_errors)
    for app in applications:
        await session.delete(app)

    # 2. Resumes
    for r in resumes:
        await session.delete(r)

    # 3. Nullify self-referential FK (canonical_job_id → jobs.id) before deleting
    for jid in job_ids:
        await session.execute(
            sa_delete(JobSource).where(JobSource.job_id == jid)
        )
        await session.execute(
            sa_delete(JobMatch).where(JobMatch.job_id == jid)
        )
        await session.execute(
            sa_delete(Job).where(Job.id == jid)
        )

    # 4. Master Resume & CandidateProfile
    await session.execute(sa_delete(MasterResume))
    await session.delete(profile)
    await session.commit()

    # 5. Clean Supabase storage files (best effort)
    try:
        sb = get_supabase_client()
        files = sb.storage.from_("resumes").list()
        if files:
            file_names = [f["name"] for f in files if "name" in f]
            if file_names:
                sb.storage.from_("resumes").remove(file_names)
    except Exception as e:
        logger.debug("Supabase storage clean notice: %s", e)

    return ApiResponse(data={"deleted": True})


@router.patch("/profile", response_model=ApiResponse)
async def update_profile(
    data: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """Create or update the candidate profile (upsert)."""
    result = await session.execute(select(CandidateProfile))
    profile = result.scalars().first()

    if not profile:
        # First save — create a profile row from the frontend data
        pi = data.get("personal_info", {})
        skills_data = data.get("skills", []) or []
        profile = CandidateProfile(
            name=pi.get("full_name", ""),
            email=pi.get("email", ""),
            phone=pi.get("phone", ""),
            city=pi.get("location", ""),
            linkedin_url=pi.get("linkedin", ""),
            github_url=pi.get("github", ""),
            portfolio_url=pi.get("portfolio", ""),
            technical_skills=[s.get("name", s) if isinstance(s, dict) else s for s in skills_data],
            employment_history=data.get("experience", []) or [],
            education=data.get("education", []) or [],
            certifications=data.get("certifications", []) or [],
            additional_experience=data.get("additional_experience", []) or [],
        )
        session.add(profile)
        await session.flush()

        # Build personal_info from DB columns + extra frontend-only fields from request
        pi_resp = {
            "full_name": profile.name,
            "email": profile.email,
            "phone": profile.phone,
            "location": profile.city,
            "linkedin": profile.linkedin_url,
            "github": profile.github_url,
            "portfolio": profile.portfolio_url,
        }
        for extra in ("website", "twitter", "summary"):
            if extra in pi:
                pi_resp[extra] = pi[extra]

        return ApiResponse(data={
            "id": str(profile.id),
            "personal_info": pi_resp,
            "skills": skills_data,
            "experience": data.get("experience", []) or [],
            "education": data.get("education", []) or [],
            "certifications": data.get("certifications", []) or [],
            "additional_experience": data.get("additional_experience", []) or [],
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        })

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
        # technical_skills is stored as List[str] — extract names from Skill[] objects
        profile.technical_skills = [
            s.get("name", s) if isinstance(s, dict) else s
            for s in (data["skills"] or [])
        ]

    if "experience" in data:
        profile.employment_history = data["experience"]

    if "education" in data:
        profile.education = data["education"]

    if "certifications" in data:
        profile.certifications = data["certifications"]

    if "additional_experience" in data:
        profile.additional_experience = data["additional_experience"]

    await session.flush()

    # Return full profile data so the frontend can safely setProfile(response)
    # without losing skills/experience/education/certifications.
    # Note: technical_skills is stored as List[str]; convert back to Skill[] for the frontend.
    stored_skills = profile.technical_skills or []
    skills_out = [
        {"name": s, "category": "Programming Languages", "proficiency": 3}
        if isinstance(s, str) else s
        for s in stored_skills
    ]
    # Build personal_info from DB columns + extra frontend-only fields from request
    req_pi = data.get("personal_info", {})
    pi_resp = {
        "full_name": profile.name,
        "email": profile.email,
        "phone": profile.phone,
        "location": profile.city,
        "linkedin": profile.linkedin_url,
        "github": profile.github_url,
        "portfolio": profile.portfolio_url,
    }
    for extra in ("website", "twitter", "summary"):
        if extra in req_pi:
            pi_resp[extra] = req_pi[extra]

    return ApiResponse(data={
        "id": str(profile.id),
        "personal_info": pi_resp,
        "skills": skills_out,
        "experience": profile.employment_history or [],
        "education": profile.education or [],
        "certifications": profile.certifications or [],
        "additional_experience": profile.additional_experience or [],
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    })


@router.post("/profile/upload", response_model=ApiResponse)
async def upload_resume(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
):
    """Upload a resume file (stores to Supabase Storage if configured, parses locally either way)."""
    file_content = await file.read()

    # Sanitize the filename — never trust it for filesystem paths
    import os as _os
    raw_name = (file.filename or "").replace("\\", "/")
    safe_name = _os.path.basename(raw_name).strip()
    if not safe_name or ".." in safe_name:
        safe_name = safe_name.replace("..", "_").strip("._ ") or "resume.docx"

    file_id = f"resumes/{uuid4()}_{safe_name}"
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

    # Convert ParsedResume dataclass to the CandidateProfile shape the frontend expects
    profile_data = _parsed_resume_to_profile_dict(parsed)

    # Save a copy locally for resume generation to use as the template
    import os
    os.makedirs("data/master_resume", exist_ok=True)
    local_path = f"data/master_resume/{safe_name}"
    with open(local_path, "wb") as f:
        f.write(file_content)

    # Persist to the DB so the master resume survives container redeploys
    # (the container filesystem is ephemeral and Supabase Storage may be
    # unavailable). Single-candidate app: replace any previous master resume.
    try:
        await session.execute(sa_delete(MasterResume))
        ext = os.path.splitext(safe_name)[1].lstrip(".").lower() or "docx"
        session.add(MasterResume(filename=safe_name, file_type=ext, file_data=file_content))
        await session.commit()
        logger.info("Master resume persisted to DB (%s, %d bytes)", file.filename, len(file_content))
    except Exception as e:
        logger.warning("Could not persist master resume to DB: %s", e)

    return ApiResponse(data={
        "file_id": file_id,
        "filename": safe_name,
        "size": len(file_content),
        "url": file_url,
        "profile": profile_data,
    })


@router.post("/profile/generate-filters", response_model=ApiResponse)
async def generate_filters(
    session: AsyncSession = Depends(get_db_session),
):
    """Generate job search filters from the saved candidate profile."""
    from datetime import datetime

    result = await session.execute(select(CandidateProfile))
    profile = result.scalars().first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Save your profile first.",
        )

    # Build keywords from job titles (roles the user has held / wants)
    all_titles = (profile.job_titles or []) + (profile.preferred_job_titles or [])
    keywords = list(set(all_titles)) if all_titles else ["Data Analyst", "Business Analyst"]

    # Calculate experience to infer experience levels
    total_exp_years = 0
    for emp in (profile.employment_history or []):
        try:
            start = int(emp.get("start_date", "0")[:4]) if emp.get("start_date") else 0
            end_str = emp.get("end_date", "").lower()
            if end_str in ("present", "current", "", None):
                end = datetime.now().year
            else:
                end = int(str(end_str)[:4])
            if start and end and end > start:
                total_exp_years += end - start
        except (ValueError, TypeError):
            pass

    experience_levels = []
    if total_exp_years >= 10:
        experience_levels.append("senior")
    if total_exp_years >= 3:
        experience_levels.append("mid")
    if 0 <= total_exp_years < 3:
        experience_levels.append("entry")
    if not experience_levels:
        experience_levels = ["entry", "mid", "senior"]

    # Locations: prefer stored preferences, fall back to profile city
    locations = list(profile.preferred_locations) if profile.preferred_locations else []
    if not locations and profile.city:
        locations = [profile.city, "Remote Canada"]

    # Map employment preferences to JobType enum values (underscore format)
    pref_map = {
        "full_time": "full_time",
        "part_time": "part_time",
        "contract": "contract",
        "internship": "internship",
        "temporary": "temporary",
        "full-time": "full_time",
        "part-time": "part_time",
        "full time": "full_time",
        "part time": "part_time",
    }
    job_types_raw = profile.employment_preferences or ["Full-time"]
    job_types = list(set(
        pref_map.get(jt.lower().replace("-", "_"), "full_time")
        for jt in job_types_raw
    ))

    filters = {
        "keywords": keywords,
        "primary_titles": (profile.job_titles or [])[:5],
        "locations": locations,
        "job_types": job_types,
        "experience_levels": list(set(experience_levels)),
        "sources": ["indeed", "linkedin", "glassdoor", "jobbank", "company_careers"],
        "remote_only": "remote" in [r.lower() for r in (profile.remote_preferences or [])],
        "posted_within_days": 7,
    }

    return ApiResponse(data={"filters": filters})


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
    profile_data = _parsed_resume_to_profile_dict(parsed)

    return ApiResponse(data={
        "profile": profile_data,
        "file_id": file_id,
        "confidence": 0.95,
        "extracted_fields": {},
    })