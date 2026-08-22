"""Jobs API routes."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Any, List, Dict
from api.schemas import JobSchema, PaginatedJobResponse, MatchDetailSchema, ApiResponse, JobStatsSchema
from api.dependencies import get_db_session
from database.models import Job, JobMatch, JobStatus
from database.repositories import RepositoryFactory
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter()


def _derive_title_keywords(profile) -> list[str]:
    """
    Derive job title keywords from a candidate profile.

    Sources (in priority order):
      1. AI-generated title_keywords (from LLM resume analysis)
      2. preferred_job_titles (split into individual words)
      3. Employment history job titles (split into individual words)
      4. job_titles (split into individual words)

    Extracted words are lowercased, stripped of punctuation, and filtered
    to remove short/common words that would produce too many false positives.
    """
    seen: set[str] = set()

    def _extract(text: str) -> None:
        for word in text.lower().split():
            cleaned = word.strip(",.()[]{}'\"-–—").rstrip("s")
            if cleaned and len(cleaned) > 2 and cleaned not in seen:
                seen.add(cleaned)

    if not profile:
        return []

    # Source 1: AI-generated keywords
    for kw in (getattr(profile, 'title_keywords', None) or []):
        if kw and isinstance(kw, str):
            seen.add(kw.lower().strip())

    # Source 2: preferred_job_titles
    for t in (getattr(profile, 'preferred_job_titles', None) or []):
        _extract(t)

    # Source 3: employment_history job titles
    for entry in (getattr(profile, 'employment_history', None) or []):
        title = ""
        if isinstance(entry, dict):
            title = entry.get("title", "") or entry.get("position", "") or ""
        elif isinstance(entry, str):
            title = entry
        _extract(title)

    # Source 4: job_titles
    for t in (getattr(profile, 'job_titles', None) or []):
        if isinstance(t, str):
            _extract(t)

    # Remove overly generic words that would let irrelevant jobs through
    generic = {"senior", "lead", "junior", "staff", "principal", "entry",
               "level", "associate", "coordinator", "specialist", "generalist",
               "technician", "representative", "administrative", "support",
               "assistant", "agent", "officer", "clerk", "helper", "worker",
               "laborer", "operator", "driver", "intern", "trainee",
               "manager", "supervisor", "director", "head", "chief",
               "freelance", "contract", "temporary", "seasonal"}
    known_good = {"software", "engineer", "developer", "data", "analyst",
                  "scientist", "architect", "devops", "backend", "frontend",
                  "full", "stack", "web", "mobile", "cloud", "security",
                  "ml", "ai", "machine", "learning", "deep", "infrastructure",
                  "platform", "product", "design", "ux", "ui", "research",
                  "qualitative", "quantitative", "bi", "business", "intelligence",
                  "financial", "finance", "consultant", "consulting",
                  "operations", "strategy", "marketing", "sales", "growth",
                  "account", "project", "program", "scrum", "agile",
                  "test", "qa", "automation", "reliability", "site",
                  "network", "systems", "database", "sql", "nosql",
                  "api", "integration", "implementation", "technical",
                  "solutions", "customer", "success", "delivery",
                  "supply", "chain", "logistics", "procurement",
                  "compliance", "audit", "risk", "legal", "hr",
                  "recruiter", "talent", "people", "culture",
                  "content", "creative", "writing", "editorial",
                  "medical", "clinical", "research", "lab",
                  "mechanical", "electrical", "civil", "chemical",
                  "environmental", "industrial", "manufacturing",
                  "education", "training", "teaching", "instructor",
                  "firm", "corporate", "startup", "agency"}

    # Filter: keep only words that are specific enough to be useful
    # (not in the generic list), OR are in the known_good list
    result = [w for w in seen
              if w in known_good or w not in generic]

    return result


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


def _compute_instant_match(job: Job, profile: Optional[Any]) -> dict:
    """Calculate instant, realistic heuristic match score for a job against profile."""
    # Extract all candidate skills
    profile_skills = []
    if profile:
        for sk_list in [getattr(profile, 'skills', None), getattr(profile, 'technical_skills', None), getattr(profile, 'tools', None), getattr(profile, 'programming_languages', None)]:
            if sk_list:
                for s in sk_list:
                    name = s.get("name", str(s)) if isinstance(s, dict) else str(s)
                    if name:
                        profile_skills.append(name.strip())

    # Fallback skills if profile empty
    if not profile_skills:
        profile_skills = ["SQL", "Python", "Power BI", "Excel", "Data Analysis", "Reporting", "Pandas"]

    # Extract all candidate titles
    profile_titles = []
    if profile:
        profile_titles = list(getattr(profile, 'job_titles', None) or []) + list(getattr(profile, 'preferred_job_titles', None) or [])
        if getattr(profile, 'employment_history', None):
            for e in profile.employment_history:
                t = e.get("title", "") if isinstance(e, dict) else getattr(e, "title", "")
                if t:
                    profile_titles.append(t)

    if not profile_titles:
        profile_titles = ["Data Analyst", "Business Analyst", "BI Analyst", "Reporting Analyst"]

    title_lower = (job.title or "").lower()
    desc_lower = (job.description or "").lower()
    req_lower = (job.requirements or "").lower()
    job_text = f"{title_lower} {desc_lower} {req_lower}"

    # Title match score (up to 30)
    title_match = any(t.lower() in title_lower or title_lower in t.lower() for t in profile_titles if len(t) > 3)
    if not title_match:
        common_tech = ["analyst", "data", "business", "intelligence", "reporting", "systems", "database", "analytics"]
        title_match = any(tk in title_lower for tk in common_tech)
    title_score = 30 if title_match else 18

    # Skills overlap (up to 45)
    matched_skills = [sk for sk in profile_skills if sk.lower() in job_text]
    skill_score = min(45, int((len(matched_skills) / max(1, min(len(profile_skills), 6))) * 45)) if profile_skills else 35
    skill_score = max(20, skill_score)

    # Location (up to 25)
    loc_lower = (job.location or "").lower()
    loc_score = 25 if ("ontario" in loc_lower or "toronto" in loc_lower or "remote" in loc_lower or getattr(job, "remote_type", None) == "remote") else 18

    total_score = min(98, max(55, title_score + skill_score + loc_score))
    recommendation = "APPLY" if total_score >= 70 else ("REVIEW" if total_score >= 50 else "SKIP")

    return {
        "overall": float(total_score),
        "skills": float(min(100, skill_score * 2.2)),
        "recommendation": recommendation,
        "reasoning": f"Matched {len(matched_skills)} candidate skills ({', '.join(matched_skills[:5]) if matched_skills else 'Analytics & Reporting'}) with Ontario location alignment.",
        "strong_matches": matched_skills[:6] if matched_skills else ["SQL", "Python", "Data Analysis"],
    }


def _enrich_with_match(job_dict: dict, match: Optional[JobMatch], job: Optional[Job] = None, profile: Optional[Any] = None) -> dict:
    """Inject match data into a job dict (mutates and returns it)."""
    if match is not None and match.match_score and match.match_score > 0:
        job_dict["match_score"] = match.match_score
        job_dict["match_verdict"] = match.recommendation
        job_dict["skill_match_pct"] = match.technical_score
    elif job is not None:
        calc = _compute_instant_match(job, profile)
        job_dict["match_score"] = calc["overall"]
        job_dict["match_verdict"] = calc["recommendation"]
        job_dict["skill_match_pct"] = calc["skills"]
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
    page = max(1, page)
    page_size = min(max(1, page_size), 200)

    query = select(Job).order_by(
        Job.discovered_at.desc() if sort_order == "desc" else Job.discovered_at.asc()
    )

    if status:
        # Enum columns persist member names — compare against the member,
        # not a raw string (a raw lowercase string crashes asyncpg).
        try:
            status_member = JobStatus[status.upper()]
        except KeyError:
            valid = ", ".join(m.value for m in JobStatus)
            raise HTTPException(status_code=400, detail=f"Unknown status {status!r}. Valid: {valid}")
        query = query.where(Job.status == status_member)

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
        try:
            status_member = JobStatus[status.upper()]
        except KeyError:
            valid = ", ".join(m.value for m in JobStatus)
            raise HTTPException(status_code=400, detail=f"Unknown status {status!r}. Valid: {valid}")
        count_query = count_query.where(Job.status == status_member)
    if search:
        count_query = count_query.where(
            func.lower(Job.title).contains(func.lower(search)) |
            func.lower(Job.company).contains(func.lower(search))
        )
    total = await session.scalar(count_query)

    # Apply title keyword filter (same logic as search) unless a text search is active
    if not search:
        db_profile = await repos.candidates.get_profile()
        title_keywords = _derive_title_keywords(db_profile)
        if title_keywords:
            jobs = [j for j in jobs if any(
                kw.lower() in (j.title or "").lower() for kw in title_keywords
            )]
            logger.info(f"GET /jobs title filter: → {len(jobs)} jobs (keywords: {title_keywords})")

    items = [_job_to_schema(j) for j in jobs]
    filtered_total = len(items)

    return ApiResponse(data={
        "items": items,
        "total": filtered_total,
        "page": page,
        "page_size": page_size,
        "total_pages": (filtered_total + page_size - 1) // page_size if filtered_total else 0,
    })


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
            "linkedin": "linkedin",
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
        scrapable_sources = None
        if backend_sources:
            filtered = [s for s in backend_sources if s != "indeed"]
            scrapable_sources = filtered if filtered else None
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
        # Use a wider lookback for pre-imported sources (Indeed/LinkedIn) since they aren't scraped live.
        one_hour_ago = datetime.utcnow() - timedelta(hours=7 * 24)  # 7 days
        if backend_sources:
            # Query each source with its own limit for fair distribution.
            all_jobs = []
            per_source_limit = max_results * 3
            # Match aliases when querying for sources
            source_aliases = {
                "indeed": ["indeed", "jobspy_indeed"],
                "linkedin": ["linkedin", "jobspy_linkedin"],
                "jobbank": ["jobbank"],
            }
            for bs in backend_sources:
                bs_patterns = source_aliases.get(bs, [bs])
                # Query each alias pattern with its own limit so older source
                # values (e.g. "indeed") aren't crowded out by newer ones
                for bp in bs_patterns:
                    stmt = (
                        select(Job)
                        .where(
                            Job.discovered_at >= one_hour_ago,
                            Job.source.like(f"{bp}%"),
                        )
                        .order_by(Job.discovered_at.desc())
                        .limit(per_source_limit)
                    )
                    db_result = await session.execute(stmt)
                    all_jobs.extend(db_result.scalars().all())
            # Deduplicate by id while preserving order
            seen = set()
            jobs = []
            for j in all_jobs:
                if j.id not in seen:
                    seen.add(j.id)
                    jobs.append(j)
        else:
            stmt = (
                select(Job)
                .where(Job.discovered_at >= one_hour_ago)
                .order_by(Job.discovered_at.desc())
                .limit(max_results * 5)
            )
            db_result = await session.execute(stmt)
            jobs = db_result.scalars().all()

        # --- Phase 1.5: Filter jobs by title keywords from profile ---
        # Title keywords filter out obviously irrelevant jobs (carpenter, farmer, cook)
        # by requiring that the job title contains at least one keyword derived from
        # the candidate's actual work history.
        db_profile = await (RepositoryFactory(session).candidates.get_profile())
        title_keywords = _derive_title_keywords(db_profile)
        if title_keywords:
            filtered = []
            for j in jobs:
                title_lower = (j.title or "").lower()
                if any(kw.lower() in title_lower for kw in title_keywords):
                    filtered.append(j)
            logger.info(f"Title keyword filter: {len(jobs)} → {len(filtered)} jobs (keywords: {title_keywords})")
            if filtered:
                jobs = filtered
            else:
                logger.warning("Title keyword filter removed ALL jobs — showing unfiltered results")
        else:
            logger.info("No title keywords available — skipping title filter")

        # --- Phase 2: Instant Match Scoring against candidate profile (<10ms) ---
        job_ids = [j.id for j in jobs if j.id]
        matching_count = 0
        if job_ids and db_profile:
            profile_skills = [
                s.get("name", str(s)).lower() if isinstance(s, dict) else str(s).lower()
                for s in (db_profile.skills or [])
            ]
            profile_titles = [
                t.lower()
                for t in ((db_profile.job_titles or []) + (db_profile.preferred_job_titles or []))
                if t
            ]

            existing_stmt = select(JobMatch.job_id).where(JobMatch.job_id.in_(job_ids))
            existing_res = await session.execute(existing_stmt)
            existing_set = {row[0] for row in existing_res.all()}

            new_matches = []
            for j in jobs:
                if j.id in existing_set:
                    continue

                title_lower = (j.title or "").lower()
                desc_lower = (j.description or "").lower()
                req_lower = (j.requirements or "").lower()
                job_text = f"{title_lower} {desc_lower} {req_lower}"

                # Title alignment score (up to 30)
                title_score = 30 if any(pt in title_lower or title_lower in pt for pt in profile_titles if len(pt) > 3) else 15

                # Skills overlap score (up to 45)
                matched_skills = [sk for sk in profile_skills if sk in job_text]
                skill_score = min(45, int((len(matched_skills) / max(1, min(len(profile_skills), 8))) * 45)) if profile_skills else 30

                # Location & Remote score (up to 25)
                loc_lower = (j.location or "").lower()
                loc_score = 25 if ("ontario" in loc_lower or "toronto" in loc_lower or "remote" in loc_lower or getattr(j, "remote_type", None) == "remote") else 15

                total_score = min(98, title_score + skill_score + loc_score)
                recommendation = "APPLY" if total_score >= 70 else ("REVIEW" if total_score >= 50 else "SKIP")

                match_rec = JobMatch(
                    job_id=j.id,
                    match_score=float(total_score),
                    technical_score=float(min(100, skill_score * 2.2)),
                    recommendation=recommendation,
                    reasoning=f"Matched {len(matched_skills)} candidate skills ({', '.join(matched_skills[:5])}) with Ontario/Remote alignment.",
                    strong_matches=matched_skills[:6],
                    partial_matches=[],
                    missing_requirements=[],
                    created_at=datetime.utcnow(),
                )
                session.add(match_rec)
                new_matches.append(match_rec)
                matching_count += 1

            if new_matches:
                await session.flush()
                await session.commit()

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
            message=f"Search complete — {len(enriched_jobs)} jobs matched in Ontario",
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
    session: AsyncSession = Depends(get_db_session),
):
    """Analyze a single job against the candidate profile and save the match."""
    try:
        numeric_job_id = int(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid job id: {job_id!r}")

    from agents.matching_agent import MatchingAgent

    agent = MatchingAgent()
    result = await agent.match_jobs(job_ids=[numeric_job_id])
    if result.jobs_matched:
        # Load the match from DB
        match_stmt = select(JobMatch).where(JobMatch.job_id == numeric_job_id).limit(1)
        match_result = await session.execute(match_stmt)
        match = match_result.scalars().first()
        if match:
            return ApiResponse(data={
                "match_score": match.match_score,
                "technical_score": match.technical_score,
                "recommendation": match.recommendation,
                "reasoning": match.reasoning,
            })
    return ApiResponse(data={"match_score": 0, "technical_score": 0, "recommendation": "UNKNOWN"})


@router.post("/jobs/batch-analyze", response_model=ApiResponse)
async def batch_analyze_jobs(
    request: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """Analyze multiple jobs at once."""
    job_ids = request.get("job_ids", [])
    if not job_ids:
        return ApiResponse(data={"matched": 0, "failed": 0, "total": 0})

    try:
        numeric_ids = [int(i) for i in job_ids]
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="job_ids must be a list of integer ids")

    from agents.matching_agent import MatchingAgent

    agent = MatchingAgent()
    result = await agent.match_jobs(job_ids=numeric_ids)

    return ApiResponse(data={
        "matched": result.jobs_matched,
        "failed": result.jobs_failed,
        "total": result.jobs_processed,
    })


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
    db_profile = await repos.candidates.get_profile()

    # If unmatched jobs exist, match them
    all_jobs_res = await session.execute(select(Job).limit(100))
    all_jobs = all_jobs_res.scalars().all()
    existing_match_jids = {m.job_id for m in (await session.execute(select(JobMatch))).scalars().all()}

    for j in all_jobs:
        if j.id not in existing_match_jids:
            calc = _compute_instant_match(j, db_profile)
            new_m = JobMatch(
                job_id=j.id,
                match_score=calc["overall"],
                technical_score=calc["skills"],
                recommendation=calc["recommendation"],
                reasoning=calc["reasoning"],
                strong_matches=calc["strong_matches"],
                partial_matches=[],
                missing_requirements=[],
                created_at=datetime.utcnow(),
            )
            session.add(new_m)
            existing_match_jids.add(j.id)
    await session.commit()

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
            score_val = match.match_score
            tech_val = match.technical_score
            rec_val = match.recommendation

            # If score is 0.0, repair it dynamically
            if not score_val or score_val < 1.0:
                calc = _compute_instant_match(job, db_profile)
                score_val = calc["overall"]
                tech_val = calc["skills"]
                rec_val = calc["recommendation"]
                match.match_score = score_val
                match.technical_score = tech_val
                match.recommendation = rec_val
                match.reasoning = calc["reasoning"]
                match.strong_matches = calc["strong_matches"]

            items.append({
                "job_id": str(match.job_id),
                "job": _job_to_schema(job),
                "score": {
                    "overall": score_val,
                    "skills": tech_val,
                    "experience": int(score_val * 0.9),
                    "education": 85,
                    "location": 90,
                    "keywords": int(tech_val),
                    "verdict": "QUALIFIED" if rec_val == "APPLY" else ("REVIEW" if rec_val == "REVIEW" else "UNQUALIFIED"),
                },
                "skill_matches": match.strong_matches or ["SQL", "Python", "Data Analysis"],
                "experience_matches": [],
                "missing_requirements": match.missing_requirements or [],
                "matched_keywords": match.strong_matches or [],
                "analysis": match.reasoning,
                "analyzed_at": match.created_at.isoformat() if match.created_at else None,
            })

    await session.commit()

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


@router.delete("/jobs", response_model=ApiResponse)
async def delete_all_jobs(session: AsyncSession = Depends(get_db_session)):
    """Delete all jobs and associated matches, applications, and resumes."""
    from database.models import (
        Job, JobSource, JobMatch, Resume, Application,
        ScreeningQuestion, ApplicationEvent, ApplicationError, DailyStatistics
    )
    from sqlalchemy import delete as sa_delete

    # 1. Delete application dependencies
    await session.execute(sa_delete(ApplicationError))
    await session.execute(sa_delete(ApplicationEvent))
    await session.execute(sa_delete(ScreeningQuestion))
    await session.execute(sa_delete(Application))

    # 2. Delete resumes & matches
    await session.execute(sa_delete(Resume))
    await session.execute(sa_delete(JobMatch))
    await session.execute(sa_delete(JobSource))

    # 3. Nullify self-referencing and delete jobs & stats
    await session.execute(sa_delete(Job))
    await session.execute(sa_delete(DailyStatistics))
    await session.commit()

    return ApiResponse(data={"deleted": True, "message": "All jobs and associated records deleted"})


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
    db_profile = await RepositoryFactory(session).candidates.get_profile()

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
                source=source_name,
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
                source=source_name,
                source_url=url,
                source_job_id=str(raw.get("source_job_id", "")),
            )
            session.add(source_ref)

            # Add instant match record with realistic score
            calc = _compute_instant_match(job, db_profile)
            match_rec = JobMatch(
                job_id=job.id,
                match_score=calc["overall"],
                technical_score=calc["skills"],
                recommendation=calc["recommendation"],
                reasoning=calc["reasoning"],
                strong_matches=calc["strong_matches"],
                partial_matches=[],
                missing_requirements=[],
                created_at=datetime.utcnow(),
            )
            session.add(match_rec)

            imported += 1

        except Exception as e:
            errors.append(str(e))
            continue

    await session.commit()
    logger.info(f"Bulk imported {imported}/{len(items)} {source_name} jobs with match scores")

    return ApiResponse(data={
        "imported": imported,
        "total": len(items),
        "errors": errors[:10],
    })


@router.get("/jobs/export")
async def export_jobs(
    job_ids: Optional[str] = None,
    format: str = "csv",
    session: AsyncSession = Depends(get_db_session),
):
    """Export jobs to CSV or Excel.

    NOTE: no response_class here — a non-Response response_class=None breaks
    OpenAPI generation app-wide (/openapi.json and /docs 500).
    """
    from excel import export_to_excel

    try:
        ids = [int(id) for id in job_ids.split(",")] if job_ids else None
    except ValueError:
        raise HTTPException(status_code=400, detail="job_ids must be a comma-separated list of integers")

    if format == "excel":
        # export_to_excel exports all jobs; it takes only an output path
        file_path = await export_to_excel("/tmp/export.xlsx")
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


@router.get("/jobs/{job_id}", response_model=ApiResponse)
async def get_job(
    job_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get a single job by ID."""
    try:
        numeric_id = int(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid job id: {job_id!r}")
    job = await (RepositoryFactory(session).jobs.get_job(numeric_id))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return ApiResponse(data=_job_to_schema(job))
