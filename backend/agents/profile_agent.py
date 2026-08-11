"""
Pydantic models for candidate profile and related structures.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from datetime import date
from enum import Enum
from resume.parser import ParsedResume, parse_resume
from llm.schemas import ProfileAnalysis


class ProficiencyLevel(str, Enum):
    EXPERT = "expert"
    ADVANCED = "advanced"
    INTERMEDIATE = "intermediate"
    BEGINNER = "beginner"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class SkillEntry(BaseModel):
    name: str
    proficiency: ProficiencyLevel = ProficiencyLevel.INTERMEDIATE
    source: str = ""
    verified: bool = True
    category: str = "general"  # technical, business, tool, language


class EducationEntry(BaseModel):
    degree: str
    institution: str
    field_of_study: Optional[str] = None
    graduation_year: Optional[int] = None
    gpa: Optional[str] = None
    details: List[str] = Field(default_factory=list)
    verified: bool = True
    source: str = "master_resume"


class EmploymentEntry(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    current: bool = False
    description: str = ""
    achievements: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    verified: bool = True
    source: str = "master_resume"


class CertificationEntry(BaseModel):
    name: str
    issuer: Optional[str] = None
    year: Optional[int] = None
    expiry_year: Optional[int] = None
    credential_id: Optional[str] = None
    url: Optional[str] = None
    verified: bool = True
    source: str = "master_resume"


class ProjectEntry(BaseModel):
    name: str
    description: str = ""
    technologies: List[str] = Field(default_factory=list)
    role: Optional[str] = None
    duration: Optional[str] = None
    url: Optional[str] = None
    verified: bool = True
    source: str = "master_resume"


class AdditionalExperienceEntry(BaseModel):
    id: str
    original_text: str
    category: Optional[str] = None
    verified: bool = True
    source: str = "current_job_notes"
    extracted_skills: List[str] = Field(default_factory=list)
    extracted_tools: List[str] = Field(default_factory=list)
    extracted_achievements: List[str] = Field(default_factory=list)


class CandidateProfile(BaseModel):
    # Personal Information
    name: str
    email: EmailStr
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

    # Structured Experience
    education: List[EducationEntry] = Field(default_factory=list)
    certifications: List[CertificationEntry] = Field(default_factory=list)
    employment_history: List[EmploymentEntry] = Field(default_factory=list)
    projects: List[ProjectEntry] = Field(default_factory=list)

    # Skills
    skills: List[SkillEntry] = Field(default_factory=list)
    technical_skills: List[SkillEntry] = Field(default_factory=list)
    business_skills: List[SkillEntry] = Field(default_factory=list)
    tools: List[SkillEntry] = Field(default_factory=list)
    programming_languages: List[SkillEntry] = Field(default_factory=list)

    # Categorization
    industries: List[str] = Field(default_factory=list)
    job_titles: List[str] = Field(default_factory=list)
    preferred_job_titles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    remote_preferences: List[str] = Field(default_factory=list)
    employment_preferences: List[str] = Field(default_factory=list)

    # Exclusions
    excluded_titles: List[str] = Field(default_factory=list)
    excluded_industries: List[str] = Field(default_factory=list)
    excluded_requirements: List[str] = Field(default_factory=list)

    # Additional Experience Notes
    additional_experience: List[AdditionalExperienceEntry] = Field(default_factory=list)

    # Metadata
    created_at: str = Field(default_factory=lambda: date.today().isoformat())
    updated_at: str = Field(default_factory=lambda: date.today().isoformat())
    prompt_version: str = "1.0.0"

    def get_all_skills(self) -> List[SkillEntry]:
        """Get all skills combined."""
        all_skills = []
        all_skills.extend(self.technical_skills)
        all_skills.extend(self.business_skills)
        all_skills.extend(self.tools)
        all_skills.extend(self.programming_languages)
        return all_skills

    def get_verified_skills(self) -> List[SkillEntry]:
        """Get only verified skills."""
        return [s for s in self.get_all_skills() if s.verified]

    def get_skill_names(self, verified_only: bool = True) -> List[str]:
        """Get skill names."""
        skills = self.get_verified_skills() if verified_only else self.get_all_skills()
        return [s.name for s in skills]

    def has_skill(self, skill_name: str, verified_only: bool = True) -> bool:
        """Check if candidate has a skill."""
        names = self.get_skill_names(verified_only)
        skill_lower = skill_name.lower()
        return any(skill_lower in name.lower() or name.lower() in skill_lower for name in names)


class JobFilterProfile(BaseModel):
    """Auto-generated job search filters from candidate profile."""
    primary_titles: List[str] = Field(default_factory=list)
    secondary_titles: List[str] = Field(default_factory=list)
    strong_skills: List[str] = Field(default_factory=list)
    moderate_skills: List[str] = Field(default_factory=list)
    supporting_skills: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    industries: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    negative_keywords: List[str] = Field(default_factory=list)
    experience_range: Dict[str, int] = Field(default_factory=lambda: {"min": 0, "max": 10})
    remote_preferences: List[str] = Field(default_factory=list)
    employment_types: List[str] = Field(default_factory=list)
    prompt_version: str = "1.0.0"


class ProfileAgent:
    """Agent responsible for building candidate profile from resume and experience."""

    def __init__(self, llm_client=None):
        from llm.client import get_llm_client
        from llm.prompts import get_prompt
        from resume.parser import parse_resume

        self.llm = llm_client or get_llm_client()
        self.profile_analysis_prompt = get_prompt("profile_analysis")
        self.profile_analysis_schema = ProfileAnalysis

    async def analyze_resume(self, resume_path: str, additional_experience_path: Optional[str] = None) -> CandidateProfile:
        """Analyze master resume and additional experience to build candidate profile."""
        # Parse resume
        parsed_resume = parse_resume(resume_path)

        # Load additional experience
        additional_exp = ""
        if additional_experience_path:
            with open(additional_experience_path, "r") as f:
                additional_exp = f.read()

        # Build master resume text for LLM
        master_resume_text = self._format_resume_for_llm(parsed_resume)

        # Run LLM analysis
        analysis = await self.llm.generate_json(
            system_prompt=self.profile_analysis_prompt,
            user_prompt=f"MASTER RESUME:\n{master_resume_text}\n\nADDITIONAL EXPERIENCE:\n{additional_exp}",
            schema=self.profile_analysis_schema,
        )

        # Convert to CandidateProfile
        profile = self._build_profile(parsed_resume, additional_exp, analysis)
        return profile

    def _format_resume_for_llm(self, parsed: ParsedResume) -> str:
        """Format parsed resume for LLM consumption."""
        parts = []

        if parsed.contact_info:
            parts.append("CONTACT INFO:")
            for k, v in parsed.contact_info.items():
                parts.append(f"  {k}: {v}")

        if parsed.summary:
            parts.append(f"\nSUMMARY:\n{parsed.summary}")

        if parsed.work_history:
            parts.append("\nWORK HISTORY:")
            for i, job in enumerate(parsed.work_history):
                parts.append(f"\n  Job {i+1}:")
                for k, v in job.items():
                    if k != "raw" and v:
                        parts.append(f"    {k}: {v}")

        if parsed.education:
            parts.append("\nEDUCATION:")
            for edu in parsed.education:
                parts.append(f"  {edu.get('degree', '')} - {edu.get('school', '')} ({edu.get('year', '')})")

        if parsed.skills:
            parts.append(f"\nSKILLS: {', '.join(parsed.skills)}")

        if parsed.technical_skills:
            parts.append(f"\nTECHNICAL SKILLS: {', '.join(parsed.technical_skills)}")

        if parsed.tools:
            parts.append(f"\nTOOLS: {', '.join(parsed.tools)}")

        if parsed.certifications:
            parts.append("\nCERTIFICATIONS:")
            for cert in parsed.certifications:
                parts.append(f"  {cert.get('name', '')}")

        if parsed.projects:
            parts.append("\nPROJECTS:")
            for proj in parsed.projects:
                parts.append(f"  {proj.get('name', '')}: {proj.get('description', '')}")

        return "\n".join(parts)

    def _build_profile(
        self,
        parsed: ParsedResume,
        additional_exp: str,
        analysis: ProfileAnalysis,
    ) -> CandidateProfile:
        """Build CandidateProfile from parsed resume and LLM analysis."""
        # Extract contact info
        contact = parsed.contact_info

        # Build skill entries
        def make_skill_entries(items: List, category: str) -> List[SkillEntry]:
            entries = []
            for item in items:
                if isinstance(item, SkillEntry):
                    entries.append(item)
                elif isinstance(item, dict):
                    entries.append(SkillEntry(**item))
                elif hasattr(item, 'skill') and hasattr(item, 'proficiency'):
                    # Handle SkillMatch objects
                    prof_map = {
                        "expert": ProficiencyLevel.EXPERT,
                        "advanced": ProficiencyLevel.ADVANCED,
                        "intermediate": ProficiencyLevel.INTERMEDIATE,
                        "beginner": ProficiencyLevel.BEGINNER,
                    }
                    entries.append(SkillEntry(
                        name=item.skill,
                        proficiency=prof_map.get(item.proficiency, ProficiencyLevel.INTERMEDIATE),
                        source=getattr(item, 'source', ''),
                        verified=getattr(item, 'verified', True),
                        category=category,
                    ))
                else:
                    entries.append(SkillEntry(name=str(item), category=category))
            return entries

        technical_skills = make_skill_entries(analysis.strong_skills, "technical")
        technical_skills.extend(make_skill_entries(analysis.moderate_skills, "technical"))
        technical_skills.extend(make_skill_entries(analysis.supporting_skills, "technical"))

        tools = make_skill_entries(analysis.tools, "tool")

        # Build employment entries
        employment = []
        for i, job in enumerate(parsed.work_history):
            emp = EmploymentEntry(
                title=job.get("title", ""),
                company=job.get("company", ""),
                location=job.get("location"),
                start_date=job.get("start_date"),
                end_date=job.get("end_date"),
                current=job.get("end_date", "").lower() in ("present", "current", ""),
                description=job.get("raw", ""),
                achievements=job.get("bullets", []),
                technologies=[],
                source=f"master_resume.work_history[{i}]",
            )
            employment.append(emp)

        # Build education entries
        education = []
        for i, edu in enumerate(parsed.education):
            education.append(EducationEntry(
                degree=edu.get("degree", ""),
                institution=edu.get("school", ""),
                graduation_year=self._parse_year(edu.get("year", "")),
                source=f"master_resume.education[{i}]",
            ))

        # Build certifications
        certifications = []
        for i, cert in enumerate(parsed.certifications):
            certifications.append(CertificationEntry(
                name=cert.get("name", ""),
                year=self._parse_year(cert.get("year", "")),
                source=f"master_resume.certifications[{i}]",
            ))

        # Build projects
        projects = []
        for i, proj in enumerate(parsed.projects):
            projects.append(ProjectEntry(
                name=proj.get("name", ""),
                description=proj.get("description", ""),
                technologies=proj.get("technologies", []),
                source=f"master_resume.projects[{i}]",
            ))

        # Build additional experience entries
        additional_entries = []
        if additional_exp:
            for i, line in enumerate(additional_exp.strip().split("\n")):
                line = line.strip()
                if line:
                    additional_entries.append(AdditionalExperienceEntry(
                        id=f"exp_{i+1}",
                        original_text=line,
                        category=self._categorize_experience(line),
                        source="current_job_notes",
                    ))

        # Determine experience range
        total_years = self._calculate_total_experience(employment)

        # Extract skill names from SkillMatch objects
        def extract_names(items):
            return [item.skill if hasattr(item, 'skill') else str(item) for item in items]

        profile = CandidateProfile(
            name=contact.get("name", ""),
            email=contact.get("email", ""),
            phone=contact.get("phone"),
            linkedin_url=contact.get("linkedin"),
            github_url=contact.get("github"),
            portfolio_url=contact.get("portfolio"),
            employment_history=employment,
            education=education,
            certifications=certifications,
            projects=projects,
            technical_skills=technical_skills,
            tools=tools,
            industries=extract_names(analysis.industries),
            job_titles=extract_names(analysis.primary_titles + analysis.secondary_titles),
            preferred_job_titles=extract_names(analysis.primary_titles),
            preferred_locations=[],
            remote_preferences=analysis.remote_preferences if isinstance(analysis.remote_preferences, list) else [],
            additional_experience=additional_entries,
        )

        return profile

    def _parse_year(self, year_str: str) -> Optional[int]:
        """Parse year from string."""
        import re
        match = re.search(r"\d{4}", year_str)
        return int(match.group()) if match else None

    def _calculate_total_experience(self, employment: List[EmploymentEntry]) -> int:
        """Calculate total years of experience."""
        from datetime import datetime
        total = 0
        for emp in employment:
            try:
                start = int(emp.start_date) if emp.start_date else 0
                end = int(emp.end_date) if emp.end_date and emp.end_date.lower() not in ("present", "current") else datetime.now().year
                if start and end:
                    total += end - start
            except (ValueError, TypeError):
                pass
        return total

    def _categorize_experience(self, text: str) -> str:
        """Categorize additional experience note."""
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["sql", "database", "query", "data"]):
            return "data_analysis"
        elif any(kw in text_lower for kw in ["python", "code", "script", "develop", "program"]):
            return "development"
        elif any(kw in text_lower for kw in ["lead", "manage", "team", "project"]):
            return "leadership"
        elif any(kw in text_lower for kw in ["report", "dashboard", "visualiz", "tableau", "power bi"]):
            return "reporting"
        elif any(kw in text_lower for kw in ["client", "stakeholder", "present", "communicat"]):
            return "communication"
        return "general"

    async def generate_job_filters(self, profile: CandidateProfile) -> JobFilterProfile:
        """Generate job search filters from candidate profile."""
        # Get skills by proficiency
        strong = [s.name for s in profile.technical_skills if s.proficiency in (ProficiencyLevel.EXPERT, ProficiencyLevel.ADVANCED)]
        moderate = [s.name for s in profile.technical_skills if s.proficiency == ProficiencyLevel.INTERMEDIATE]
        supporting = [s.name for s in profile.technical_skills if s.proficiency == ProficiencyLevel.BEGINNER]

        # Get tools
        tools = [s.name for s in profile.tools]

        # Experience range
        total_exp = self._calculate_total_experience(profile.employment_history)

        # Default negative keywords
        negative = [
            "CPA required", "nursing license", "security clearance",
            "5+ years experience required", "expert Java",
            "mandatory certification", "PhD required",
            "government clearance", "CISSP required",
        ]

        # Add exclusions from profile
        negative.extend(profile.excluded_requirements)
        negative.extend(profile.excluded_titles)
        negative.extend(profile.excluded_industries)

        return JobFilterProfile(
            primary_titles=profile.preferred_job_titles,
            secondary_titles=[t for t in profile.job_titles if t not in profile.preferred_job_titles],
            strong_skills=strong,
            moderate_skills=moderate,
            supporting_skills=supporting,
            tools=tools,
            industries=profile.industries,
            locations=profile.preferred_locations or ["Toronto, ON", "Remote Canada"],
            negative_keywords=list(set(negative)),
            experience_range={"min": max(0, total_exp - 3), "max": total_exp + 5},
            remote_preferences=profile.remote_preferences or ["Remote", "Hybrid"],
            employment_types=profile.employment_preferences or ["Full-time"],
        )

    def save_profile(self, profile: CandidateProfile, output_path: str):
        """Save profile to JSON file."""
        import json
        with open(output_path, "w") as f:
            json.dump(profile.model_dump(), f, indent=2, default=str)

    def load_profile(self, input_path: str) -> CandidateProfile:
        """Load profile from JSON file."""
        import json
        with open(input_path, "r") as f:
            data = json.load(f)
        return CandidateProfile(**data)