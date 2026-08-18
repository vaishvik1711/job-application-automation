"""
Pydantic schemas for the API, matching frontend types.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, RootModel, field_validator


# ============ Profile Schemas ============

class PersonalInfoSchema(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    website: Optional[str] = None
    twitter: Optional[str] = None
    summary: Optional[str] = None


class SkillSchema(BaseModel):
    name: str
    level: Optional[str] = None
    category: Optional[str] = None
    years_experience: Optional[int] = None


class ExperienceSchema(BaseModel):
    id: Optional[str] = None
    company: str
    title: str
    location: Optional[str] = None
    start_date: str
    end_date: Optional[str] = None
    current: bool
    description: str | List[str]
    technologies: List[str]
    achievements: Optional[List[str]] = None


class EducationSchema(BaseModel):
    id: Optional[str] = None
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gpa: Optional[str | float] = None
    honors: Optional[List[str]] = None


class CertificationSchema(BaseModel):
    id: Optional[str] = None
    name: str
    issuer: str
    date_obtained: Optional[str] = None
    expiry_date: Optional[str] = None
    credential_id: Optional[str] = None
    url: Optional[str] = None


class AdditionalExperienceSchema(BaseModel):
    type: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    technologies: Optional[List[str]] = None


class CandidateProfileSchema(BaseModel):
    id: Optional[str] = None
    personal_info: PersonalInfoSchema
    skills: List[SkillSchema] = []
    experience: List[ExperienceSchema] = []
    education: List[EducationSchema] = []
    certifications: List[CertificationSchema] = []
    additional_experience: List[AdditionalExperienceSchema] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


class PaginatedProfileResponse(BaseModel):
    items: List[CandidateProfileSchema]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============ Job Schemas ============

class JobLocationSchema(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    country: str
    remote: bool
    timezone: Optional[str] = None


class SalaryRangeSchema(BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None
    currency: str
    period: str  # yearly | monthly | hourly


class JobSchema(BaseModel):
    id: str
    external_id: Optional[str] = None
    title: str
    company: str
    location: JobLocationSchema
    description: str
    requirements: List[str]
    responsibilities: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    job_type: str  # full_time | part_time | contract | internship | temporary
    experience_level: str
    salary_range: Optional[SalaryRangeSchema] = None
    source: str
    source_url: str
    posted_date: str
    discovered_at: str
    status: str

    model_config = {"from_attributes": True}


class PaginatedJobResponse(BaseModel):
    items: List[JobSchema]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============ Match Schemas ============

class MatchScoreSchema(BaseModel):
    overall: float
    skills: float
    experience: float
    education: float
    location: float
    keywords: float
    verdict: str  # QUALIFIED | UNQUALIFIED


class SkillMatchSchema(BaseModel):
    skill: str
    required: bool
    matched: bool
    candidate_level: Optional[str] = None
    required_level: Optional[str] = None


class ExperienceMatchSchema(BaseModel):
    requirement: str
    matched: bool
    relevant_experience: Optional[ExperienceSchema] = None
    gap: Optional[str] = None


class MatchDetailSchema(BaseModel):
    job_id: str
    job: JobSchema
    score: MatchScoreSchema
    skill_matches: List[SkillMatchSchema]
    experience_matches: List[ExperienceMatchSchema]
    missing_requirements: List[str]
    matched_keywords: List[str]
    analysis: str
    analyzed_at: str

    model_config = {"from_attributes": True}


class MatchWeightsSchema(BaseModel):
    skills: float
    experience: float
    education: float
    location: float
    keywords: float


class MatchSummarySchema(BaseModel):
    total: int
    qualified: int
    unqualified: int
    average_score: float

    model_config = {"from_attributes": True}


# ============ Resume Schemas ============

class ResumeTemplateSchema(BaseModel):
    id: str
    name: str
    description: str
    preview_url: Optional[str] = None
    is_default: Optional[bool] = None


class ResumeCustomizationOptionsSchema(BaseModel):
    job_id: str
    template_id: Optional[str] = None
    emphasize_skills: Optional[List[str]] = None
    emphasize_experience: Optional[List[str]] = None
    inject_keywords: Optional[List[str]] = None
    target_length: Optional[str] = None  # 1_page | 2_pages | auto
    format: Optional[str] = None  # docx | pdf


class ValidationIssueSchema(BaseModel):
    type: str
    severity: str
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None


class ValidationResultSchema(BaseModel):
    truthfulness_score: float
    ats_score: float
    issues: List[ValidationIssueSchema]
    suggestions: List[str]
    validated_at: str


class GeneratedResumeSchema(BaseModel):
    id: str
    job_id: str
    job_title: str
    company: str
    template_id: str
    file_path: str
    file_url: Optional[str] = None
    format: str
    customization_options: ResumeCustomizationOptionsSchema
    validation_result: Optional[ValidationResultSchema] = None
    created_at: str

    model_config = {"from_attributes": True}


# ============ Application Schemas ============

class ApplicationSchema(BaseModel):
    id: str
    job_id: str
    job: Optional[JobSchema] = None
    resume_id: str
    resume: Optional[GeneratedResumeSchema] = None
    cover_letter: Optional[str] = None
    status: str
    applied_at: Optional[str] = None
    submitted_at: Optional[str] = None
    interview_date: Optional[str] = None
    notes: Optional[str] = None
    follow_up_date: Optional[str] = None
    external_application_id: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


# ============ Analytics Schemas ============

class PipelineStatsSchema(BaseModel):
    discovered: int = 0
    deduplicated: int = 0
    matched: int = 0
    qualified: int = 0
    resume_created: int = 0
    ready_to_apply: int = 0
    applied: int = 0
    interviewed: int = 0
    offers: int = 0
    rejected: int = 0


class SourceEffectivenessSchema(BaseModel):
    source: str
    jobs_found: int
    jobs_qualified: Optional[int] = None
    applications_submitted: Optional[int] = None
    interviews: Optional[int] = None
    offers: Optional[int] = None
    conversion_rate: float


class SkillGapSchema(BaseModel):
    skill: str
    gap: str
    severity: str  # high | medium | low
    required_count: Optional[int] = None
    candidate_level: Optional[str] = None


class TimeSeriesDataSchema(BaseModel):
    date: str
    applications: int
    interviews: int
    offers: int


class ScoreDistributionSchema(BaseModel):
    range: str
    count: int


class ResponseRateSchema(BaseModel):
    category: str
    rate: float
    total: int


class AnalyticsOverviewSchema(BaseModel):
    pipeline: PipelineStatsSchema
    source_effectiveness: List[SourceEffectivenessSchema]
    skill_gaps: List[SkillGapSchema]
    applications_over_time: List[TimeSeriesDataSchema]
    match_score_distribution: List[ScoreDistributionSchema]
    response_rates: List[ResponseRateSchema]


# ============ Settings Schemas ============

class LLMSettingsSchema(BaseModel):
    provider: str  # nvidia
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float
    max_tokens: int


class JobSourceSettingsSchema(BaseModel):
    enabled: bool = True
    rate_limit: Optional[int] = None
    credentials: Optional[Dict[str, str]] = None
    config: Optional[Dict[str, Any]] = None


class JobSourceSettingsConfigSchema(RootModel[Dict[str, JobSourceSettingsSchema]]):
    pass


class MatchingSettingsSchema(BaseModel):
    default_weights: MatchWeightsSchema
    auto_qualify_threshold: float
    min_skill_match: float


class NotificationEventsSchema(BaseModel):
    job_found: bool = True
    match_complete: bool = True
    resume_generated: bool = True
    application_submitted: bool = True
    interview_scheduled: bool = True


class NotificationSettingsSchema(BaseModel):
    email_enabled: bool = False
    email_address: Optional[str] = None
    browser_enabled: bool = True
    webhook_url: Optional[str] = None
    events: NotificationEventsSchema


class AppSettingsSchema(BaseModel):
    llm: LLMSettingsSchema
    job_sources: Dict[str, JobSourceSettingsSchema]
    matching: MatchingSettingsSchema
    notifications: NotificationSettingsSchema
    resume_templates: List[ResumeTemplateSchema]


# ============ Common Schemas ============

class ApiResponse(BaseModel):
    data: Any
    message: Optional[str] = None
    success: bool = True


class ApiError(BaseModel):
    detail: str
    code: Optional[str] = None
    status_code: int


class HealthResponse(BaseModel):
    status: str
    version: str


class TestLLMResponse(BaseModel):
    success: bool
    latency_ms: int


class TestJobSourceResponse(BaseModel):
    success: bool
    jobs_found: int


class JobSearchRequestSchema(BaseModel):
    filters: Dict[str, Any]
    max_results_per_source: Optional[int] = None
    use_cache: Optional[bool] = None


class JobSearchResponseSchema(BaseModel):
    jobs: List[JobSchema]
    total_found: int
    sources_searched: List[str]
    search_duration_ms: int
    duplicates_removed: int


class MatchSummaryResponseSchema(BaseModel):
    matches: List[MatchDetailSchema]
    total: int
    page: int
    page_size: int


class ThresholdSchema(BaseModel):
    threshold: int


class JobStatsSchema(BaseModel):
    total_jobs: int
    by_status: Dict[str, int]
    by_source: Dict[str, int]


class PipelineProgressSchema(BaseModel):
    stage: str
    current: int
    total: int
    message: str
    job_id: Optional[str] = None


class BatchResumeRequest(BaseModel):
    job_ids: List[str]
    auto_apply: bool = False
    max_concurrent: Optional[int] = 3


class BatchResumeResult(BaseModel):
    job_id: str
    resume_id: Optional[str] = None
    application_id: Optional[str] = None
    success: bool
    error: Optional[str] = None


class BatchResumeResponse(BaseModel):
    results: List[BatchResumeResult]
    total: int
    succeeded: int
    failed: int