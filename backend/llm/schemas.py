"""
Pydantic schemas for structured LLM outputs.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class SkillMatch(BaseModel):
    skill: str
    proficiency: Literal["expert", "advanced", "intermediate", "beginner"]
    source: str
    verified: bool = True


class JobAnalysis(BaseModel):
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    required_tools: List[str] = Field(default_factory=list)
    preferred_tools: List[str] = Field(default_factory=list)
    required_experience_years: Optional[int] = None
    required_education: List[str] = Field(default_factory=list)
    required_certifications: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    job_title: str
    company: str
    industry: Optional[str] = None
    seniority_level: Literal["entry", "associate", "mid", "senior", "lead", "principal"]


class ProfileAnalysis(BaseModel):
    strong_skills: List[SkillMatch] = Field(default_factory=list)
    moderate_skills: List[SkillMatch] = Field(default_factory=list)
    supporting_skills: List[SkillMatch] = Field(default_factory=list)
    tools: List[SkillMatch] = Field(default_factory=list)
    industries: List[SkillMatch] = Field(default_factory=list)
    primary_titles: List[SkillMatch] = Field(default_factory=list)
    secondary_titles: List[SkillMatch] = Field(default_factory=list)
    search_keywords: List[str] = Field(default_factory=list)
    negative_keywords: List[str] = Field(default_factory=list)
    experience_range: dict = Field(default_factory=lambda: {"min": 0, "max": 10})
    remote_preferences: List[str] = Field(default_factory=list)


class JobMatchResult(BaseModel):
    match_score: int = Field(ge=0, le=100)
    technical_score: int = Field(ge=0, le=100, description="Technical skills match percentage")
    soft_skills_score: int = Field(ge=0, le=100, description="Soft skills match percentage")
    recommendation: Literal["APPLY", "REVIEW", "REJECT"]
    strong_matches: List[SkillMatch] = Field(default_factory=list)
    partial_matches: List[SkillMatch] = Field(default_factory=list)
    missing_requirements: List[str] = Field(default_factory=list)
    preferred_requirements_missing: List[str] = Field(default_factory=list)
    missing_soft_skills: List[str] = Field(default_factory=list, description="Soft skills from job not in profile - can be added to resume")
    concerns: List[str] = Field(default_factory=list)
    reasoning: str

    @field_validator("match_score", "technical_score", "soft_skills_score")
    @classmethod
    def validate_score(cls, v):
        return max(0, min(100, v))


class ResumeCustomizationPlan(BaseModel):
    summary_rewrite: Optional[str] = None
    bullet_changes: List[dict] = Field(default_factory=list)
    skills_to_emphasize: List[str] = Field(default_factory=list)
    skills_to_deemphasize: List[str] = Field(default_factory=list)
    keywords_to_add: List[str] = Field(default_factory=list)
    section_reorder: Optional[List[str]] = None


class ResumeValidationResult(BaseModel):
    valid: bool
    truthfulness_score: int = Field(ge=0, le=100)
    format_score: int = Field(ge=0, le=100)
    relevance_score: int = Field(ge=0, le=100)
    issues: List[dict] = Field(default_factory=list)
    traceability_check: List[dict] = Field(default_factory=list)


class ScreeningAnswer(BaseModel):
    question: str
    answer: Optional[str] = None
    source: Optional[str] = None
    confidence: float = Field(ge=0, le=1)
    requires_human: bool = False
    question_type: Optional[str] = None


class ScreeningAnalysis(BaseModel):
    answers: List[ScreeningAnswer] = Field(default_factory=list)


class CandidateProfileSchema(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "Canada"
    work_authorization: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    github_url: Optional[str] = None
    notice_period_weeks: int = 2
    salary_expectation_min: Optional[int] = None
    salary_expectation_max: Optional[int] = None
    salary_currency: str = "CAD"
    education: List[dict] = Field(default_factory=list)
    certifications: List[dict] = Field(default_factory=list)
    employment_history: List[dict] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    technical_skills: List[str] = Field(default_factory=list)
    business_skills: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    programming_languages: List[str] = Field(default_factory=list)
    industries: List[str] = Field(default_factory=list)
    job_titles: List[str] = Field(default_factory=list)
    preferred_job_titles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    remote_preferences: List[str] = Field(default_factory=list)
    employment_preferences: List[str] = Field(default_factory=list)
    excluded_titles: List[str] = Field(default_factory=list)
    excluded_industries: List[str] = Field(default_factory=list)
    excluded_requirements: List[str] = Field(default_factory=list)


PROMPT_VERSION = "1.0.0"