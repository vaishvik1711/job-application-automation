"""
Form-profile construction for auto-apply.

Converts the CandidateProfile DB model into the flat dict FormFiller expects
(first_name/last_name/email/phone/...). Derived values (name split,
years-of-experience) are approximations — the apply pipeline flags them so
uncertain fields land in human review rather than being submitted blind.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def split_name(full_name: str) -> tuple:
    """'Vaishvik Patel' -> ('Vaishvik', 'Patel'). Falls back to putting
    everything in first_name when there's a single token."""
    parts = (full_name or "").strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return " ".join(parts[:-1]), parts[-1]


def _highest_education(education: List[dict]) -> str:
    """Pick the highest education level from profile education entries."""
    if not education:
        return ""
    order = ["phd", "doctorate", "master", "graduate", "bachelor", "undergraduate", "diploma", "certificate"]
    text = " ".join(
        " ".join(str(v) for v in (e.get("degree"), e.get("field"), e.get("level")) if v).lower()
        for e in education
        if isinstance(e, dict)
    )
    for level in order:
        if level in text:
            return level.capitalize()
    # Unknown structure — surface it rather than guess.
    return ""


def _years_of_experience(employment_history: List[dict]) -> int:
    """Sum overlapping employment spans conservatively (calendar years only)."""
    total = 0
    for job in employment_history or []:
        if not isinstance(job, dict):
            continue
        start = _parse_year(job.get("start_date") or job.get("start"))
        end = _parse_year(job.get("end_date") or job.get("end")) or 2026
        if start:
            total += max(end - start, 0)
    return total


def _parse_year(value: Any) -> Optional[int]:
    if value is None:
        return None
    text = str(value)
    for token in text.replace("/", "-").split("-"):
        if token.isdigit() and len(token) == 4 and 1950 <= int(token) <= 2030:
            return int(token)
    return None


def build_form_profile(profile) -> Dict[str, Any]:
    """Build the flat form profile from a CandidateProfile row.

    Returns (profile_dict, derived_fields) where derived_fields lists the
    keys whose values were computed rather than stored — the ApplyService
    treats those as review-worthy when they end up empty.
    """
    derived: List[str] = []
    first, last = split_name(getattr(profile, "name", "") or "")
    if not last:
        derived.append("last_name")

    education = getattr(profile, "education", None) or []
    highest = _highest_education(education)
    if not highest:
        derived.append("education_level")

    years = _years_of_experience(getattr(profile, "employment_history", None) or [])

    form_profile: Dict[str, Any] = {
        "full_name": getattr(profile, "name", "") or "",
        "first_name": first,
        "last_name": last,
        "email": getattr(profile, "email", "") or "",
        "phone": getattr(profile, "phone", "") or "",
        "address": getattr(profile, "address", "") or "",
        "city": getattr(profile, "city", "") or "",
        "province": getattr(profile, "province", "") or "",
        "postal_code": getattr(profile, "postal_code", "") or "",
        "country": getattr(profile, "country", "") or "Canada",
        "work_authorization": getattr(profile, "work_authorization", "") or "",
        "linkedin_url": getattr(profile, "linkedin_url", "") or "",
        "portfolio_url": getattr(profile, "portfolio_url", "") or "",
        "github_url": getattr(profile, "github_url", "") or "",
        "education_level": highest,
        "years_of_experience": str(years) if years else "",
        "skills": getattr(profile, "skills", []) or [],
        "employment_history": getattr(profile, "employment_history", []) or [],
        "certifications": getattr(profile, "certifications", []) or [],
        "salary_expectation_min": getattr(profile, "salary_expectation_min", None),
        "salary_expectation_max": getattr(profile, "salary_expectation_max", None),
        "notice_period_weeks": getattr(profile, "notice_period_weeks", 2),
    }

    if not form_profile["phone"]:
        derived.append("phone")
    if not form_profile["work_authorization"]:
        derived.append("work_authorization")

    logger.info(
        "Built form profile for %s (%d derived fields need review)", form_profile["email"], len(derived)
    )
    return form_profile, derived
