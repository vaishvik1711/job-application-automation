"""
SQLAlchemy models for the job automation system.
"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean,
    ForeignKey, Enum, Index, UniqueConstraint, JSON, Date
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database.database import Base


class JobStatus(PyEnum):
    DISCOVERED = "discovered"
    DEDUPLICATED = "deduplicated"
    MATCHED = "matched"
    QUALIFIED = "qualified"
    RESUME_CREATED = "resume_created"
    RESUME_VALIDATED = "resume_validated"
    READY_TO_APPLY = "ready_to_apply"
    APPLICATION_STARTED = "application_started"
    APPLIED = "applied"
    TRACKED = "tracked"
    REJECTED = "rejected"
    FAILED = "failed"
    NEEDS_HUMAN_INPUT = "needs_human_input"
    CAPTCHA_REQUIRED = "captcha_required"
    MFA_REQUIRED = "mfa_required"
    DUPLICATE = "duplicate"


class ApplicationStatus(PyEnum):
    DISCOVERED = "discovered"
    REJECTED = "rejected"
    QUALIFIED = "qualified"
    RESUME_CREATED = "resume_created"
    READY = "ready"
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED = "failed"
    NEEDS_HUMAN_INPUT = "needs_human_input"
    INTERVIEW = "interview"
    REJECTED_BY_COMPANY = "rejected_by_company"
    OFFER = "offer"
    WITHDRAWN = "withdrawn"


class RemoteType(PyEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ON_SITE = "on_site"


class EmploymentType(PyEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    province: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="Canada")
    work_authorization: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    portfolio_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    github_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notice_period_weeks: Mapped[int] = mapped_column(Integer, default=2)
    salary_expectation_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_expectation_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(3), default="CAD")

    # JSON fields for structured data
    education: Mapped[List[dict]] = mapped_column(JSON, default=list)
    certifications: Mapped[List[dict]] = mapped_column(JSON, default=list)
    employment_history: Mapped[List[dict]] = mapped_column(JSON, default=list)
    additional_experience: Mapped[List[dict]] = mapped_column(JSON, default=list)
    skills: Mapped[List[str]] = mapped_column(JSON, default=list)
    technical_skills: Mapped[List[str]] = mapped_column(JSON, default=list)
    business_skills: Mapped[List[str]] = mapped_column(JSON, default=list)
    tools: Mapped[List[str]] = mapped_column(JSON, default=list)
    programming_languages: Mapped[List[str]] = mapped_column(JSON, default=list)
    industries: Mapped[List[str]] = mapped_column(JSON, default=list)
    job_titles: Mapped[List[str]] = mapped_column(JSON, default=list)
    preferred_job_titles: Mapped[List[str]] = mapped_column(JSON, default=list)
    title_keywords: Mapped[List[str]] = mapped_column(JSON, default=list)
    preferred_locations: Mapped[List[str]] = mapped_column(JSON, default=list)
    remote_preferences: Mapped[List[str]] = mapped_column(JSON, default=list)
    employment_preferences: Mapped[List[str]] = mapped_column(JSON, default=list)
    excluded_titles: Mapped[List[str]] = mapped_column(JSON, default=list)
    excluded_industries: Mapped[List[str]] = mapped_column(JSON, default=list)
    excluded_requirements: Mapped[List[str]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    experience_notes: Mapped[List["CandidateExperience"]] = relationship(
        "CandidateExperience", back_populates="profile", cascade="all, delete-orphan"
    )
    resumes: Mapped[List["Resume"]] = relationship("Resume", back_populates="candidate")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="candidate")


class CandidateExperience(Base):
    __tablename__ = "candidate_experience"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(Integer, ForeignKey("candidate_profiles.id"), nullable=False)
    original_text: Mapped[str] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(100), default="current_job_notes")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="experience_notes")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    canonical_url: Mapped[str] = mapped_column(Text, unique=True, index=True)
    source_urls: Mapped[List[str]] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(500), index=True)
    company: Mapped[str] = mapped_column(String(255), index=True)
    location: Mapped[str] = mapped_column(String(255))
    remote_type: Mapped[RemoteType] = mapped_column(Enum(RemoteType), default=RemoteType.ON_SITE)
    employment_type: Mapped[EmploymentType] = mapped_column(Enum(EmploymentType), default=EmploymentType.FULL_TIME)
    date_posted: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="CAD")
    description: Mapped[str] = mapped_column(Text)
    requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preferred_qualifications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    skills: Mapped[List[str]] = mapped_column(JSON, default=list)
    tools: Mapped[List[str]] = mapped_column(JSON, default=list)
    education: Mapped[List[str]] = mapped_column(JSON, default=list)
    certifications: Mapped[List[str]] = mapped_column(JSON, default=list)
    application_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    company_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.DISCOVERED, index=True)
    canonical_job_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("jobs.id"), nullable=True, index=True)

    # Relationships
    sources_rel: Mapped[List["JobSource"]] = relationship("JobSource", back_populates="job", cascade="all, delete-orphan")
    match: Mapped[Optional["JobMatch"]] = relationship("JobMatch", back_populates="job", uselist=False, cascade="all, delete-orphan")
    resume: Mapped[Optional["Resume"]] = relationship("Resume", back_populates="job", uselist=False, cascade="all, delete-orphan")
    application: Mapped[Optional["Application"]] = relationship("Application", back_populates="job", uselist=False, cascade="all, delete-orphan")
    canonical_job: Mapped[Optional["Job"]] = relationship("Job", remote_side=[id], backref="duplicates")

    __table_args__ = (
        Index("ix_job_company_title_location", "company", "title", "location"),
    )


class JobSource(Base):
    __tablename__ = "job_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(100))
    source_url: Mapped[str] = mapped_column(Text)
    source_job_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped["Job"] = relationship("Job", back_populates="sources_rel")


class JobMatch(Base):
    __tablename__ = "job_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id"), unique=True, nullable=False)
    match_score: Mapped[float] = mapped_column(Float, index=True)
    technical_score: Mapped[float] = mapped_column(Float, default=0)
    soft_skills_score: Mapped[float] = mapped_column(Float, default=0)
    recommendation: Mapped[str] = mapped_column(String(20))  # APPLY, REVIEW, REJECT
    strong_matches: Mapped[List[dict]] = mapped_column(JSON, default=list)
    partial_matches: Mapped[List[dict]] = mapped_column(JSON, default=list)
    missing_requirements: Mapped[List[dict]] = mapped_column(JSON, default=list)
    preferred_requirements_missing: Mapped[List[dict]] = mapped_column(JSON, default=list)
    missing_soft_skills: Mapped[List[str]] = mapped_column(JSON, default=list)
    concerns: Mapped[List[dict]] = mapped_column(JSON, default=list)
    reasoning: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(String(20))
    # Pre-computed job analysis from matching phase - avoids re-sending full job description
    job_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped["Job"] = relationship("Job", back_populates="match")


class Resume(Base):
    __tablename__ = "resumes"
    __table_args__ = (
        UniqueConstraint("candidate_id", "job_id", "version", name="uq_candidate_job_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(Integer, ForeignKey("candidate_profiles.id"), nullable=False)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    file_path: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(String(255))
    validation_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    truthfulness_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    format_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    validation_issues: Mapped[List[dict]] = mapped_column(JSON, default=list)
    traceability: Mapped[List[dict]] = mapped_column(JSON, default=list)  # bullet -> source mapping
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="resumes")
    job: Mapped["Job"] = relationship("Job", back_populates="resume")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(Integer, ForeignKey("candidate_profiles.id"), nullable=False)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id"), unique=True, nullable=False)
    resume_id: Mapped[int] = mapped_column(Integer, ForeignKey("resumes.id"), nullable=False)
    application_url: Mapped[str] = mapped_column(Text)
    status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus), default=ApplicationStatus.DISCOVERED, index=True)
    confirmation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cover_letter_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    human_intervention_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fields_remaining: Mapped[List[str]] = mapped_column(JSON, default=list)

    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="applications")
    job: Mapped["Job"] = relationship("Job", back_populates="application")
    resume: Mapped["Resume"] = relationship("Resume")
    screening_questions: Mapped[List["ScreeningQuestion"]] = relationship(
        "ScreeningQuestion", back_populates="application", cascade="all, delete-orphan"
    )
    events: Mapped[List["ApplicationEvent"]] = relationship(
        "ApplicationEvent", back_populates="application", cascade="all, delete-orphan"
    )
    errors: Mapped[List["ApplicationError"]] = relationship(
        "ApplicationError", back_populates="application", cascade="all, delete-orphan"
    )


class ScreeningQuestion(Base):
    __tablename__ = "screening_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(Integer, ForeignKey("applications.id"), nullable=False)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    requires_human: Mapped[bool] = mapped_column(Boolean, default=False)
    question_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    application: Mapped["Application"] = relationship("Application", back_populates="screening_questions")


class ApplicationEvent(Base):
    __tablename__ = "application_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(Integer, ForeignKey("applications.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text)
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    application: Mapped["Application"] = relationship("Application", back_populates="events")


class ApplicationError(Base):
    __tablename__ = "application_errors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(Integer, ForeignKey("applications.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source: Mapped[str] = mapped_column(String(100))
    error_type: Mapped[str] = mapped_column(String(100))
    error_message: Mapped[str] = mapped_column(Text)
    current_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)

    application: Mapped["Application"] = relationship("Application", back_populates="errors")


class DailyStatistics(Base):
    __tablename__ = "daily_statistics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[Date] = mapped_column(Date, unique=True, index=True)
    jobs_found: Mapped[int] = mapped_column(Integer, default=0)
    duplicates_removed: Mapped[int] = mapped_column(Integer, default=0)
    jobs_qualified: Mapped[int] = mapped_column(Integer, default=0)
    resumes_created: Mapped[int] = mapped_column(Integer, default=0)
    resumes_validated: Mapped[int] = mapped_column(Integer, default=0)
    applications_submitted: Mapped[int] = mapped_column(Integer, default=0)
    applications_failed: Mapped[int] = mapped_column(Integer, default=0)
    human_intervention_required: Mapped[int] = mapped_column(Integer, default=0)
    average_match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    top_companies: Mapped[List[str]] = mapped_column(JSON, default=list)
    top_job_titles: Mapped[List[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MatchingConfig(Base):
    """Configuration for matching weights and thresholds."""
    __tablename__ = "matching_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    default_weights: Mapped[dict] = mapped_column(JSON, default={
        "skills": 30, "experience": 25, "education": 10, "location": 15, "keywords": 20
    })
    auto_qualify_threshold: Mapped[float] = mapped_column(Float, default=75.0)
    min_skill_match: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AppSettings(Base):
    """Application settings key-value store."""
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)