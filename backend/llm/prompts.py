"""
Centralized LLM prompts for all agents.
"""
from llm.schemas import PROMPT_VERSION


PROFILE_ANALYSIS_PROMPT = f"""
You are an expert career analyst. Analyze the candidate's master resume and additional experience notes to create a comprehensive profile for job searching.

PROMPT VERSION: {PROMPT_VERSION}

MASTER RESUME:
{{master_resume}}

ADDITIONAL EXPERIENCE NOTES:
{{additional_experience}}

EXTRACT AND CATEGORIZE:

1. STRONG SKILLS - Skills explicitly demonstrated with evidence in resume/experience (proficiency: expert/advanced)
2. MODERATE SKILLS - Skills mentioned but with less evidence (proficiency: intermediate)
3. SUPPORTING SKILLS - Skills mentioned briefly or in passing (proficiency: beginner)
4. TOOLS - Software, platforms, languages explicitly used
5. INDUSTRIES - Industries from work history
6. PRIMARY TITLES - Job titles that directly match experience
7. SECONDARY TITLES - Related/adjacent titles the candidate could qualify for
8. SEARCH KEYWORDS - Keywords for job search queries
9. NEGATIVE KEYWORDS - Terms that indicate unsuitable jobs (e.g., "CPA required", "security clearance")
10. EXPERIENCE RANGE - Min/max years of experience
11. REMOTE PREFERENCES - Based on stated preferences

CRITICAL RULES:
- ONLY use EXPLICITLY VERIFIED information from the provided sources
- Mark each skill/tool with its SOURCE (e.g., "master_resume.technical_skills", "additional_experience[3]")
- Set verified=true only for explicitly verified items
- Do NOT infer or assume skills not directly stated
- Distinguish between REQUIRED vs PREFERRED qualifications in job analysis
- Be conservative - it's better to miss a match than to hallucinate one

RETURN EXACTLY THIS JSON STRUCTURE:
{{
  "strong_skills": [
    {{"skill": "Python", "proficiency": "expert", "source": "master_resume.technical_skills", "verified": true}},
    {{"skill": "React", "proficiency": "advanced", "source": "master_resume.technical_skills", "verified": true}}
  ],
  "moderate_skills": [
    {{"skill": "JavaScript", "proficiency": "intermediate", "source": "master_resume.technical_skills", "verified": true}}
  ],
  "supporting_skills": [
    {{"skill": "Django", "proficiency": "beginner", "source": "master_resume.technical_skills", "verified": true}}
  ],
  "tools": [
    {{"skill": "Docker", "proficiency": "expert", "source": "master_resume.tools", "verified": true}},
    {{"skill": "Kubernetes", "proficiency": "advanced", "source": "master_resume.tools", "verified": true}}
  ],
  "industries": [
    {{"skill": "Software Development", "proficiency": "expert", "source": "master_resume.employment_history[0]", "verified": true}}
  ],
  "primary_titles": [
    {{"skill": "Senior Software Engineer", "proficiency": "expert", "source": "master_resume.employment_history[0]", "verified": true}}
  ],
  "secondary_titles": [
    {{"skill": "Software Engineer", "proficiency": "advanced", "source": "master_resume.employment_history[1]", "verified": true}}
  ],
  "search_keywords": ["Python", "React", "AWS", "Docker"],
  "negative_keywords": ["CPA required", "security clearance"],
  "experience_range": {{"min": 5, "max": 10}},
  "remote_preferences": ["Remote", "Hybrid"]
}}

Return JSON matching the ProfileAnalysis schema exactly.
"""

JOB_ANALYSIS_PROMPT = f"""
You are an expert job description analyzer. Extract structured requirements from the job description.

PROMPT VERSION: {PROMPT_VERSION}

JOB DESCRIPTION:
{{job_description}}

COMPANY: {{company}}
TITLE: {{title}}

EXTRACT:
1. Required skills (must-have)
2. Preferred skills (nice-to-have)
3. Required tools/technologies
4. Preferred tools/technologies
5. Required years of experience
6. Required education level/field
7. Required certifications
8. Key responsibilities
9. Job title normalization
10. Company industry
11. Seniority level

CRITICAL:
- Distinguish EXPLICIT requirements from preferences
- "Must have", "required", "essential" = REQUIRED
- "Preferred", "nice to have", "bonus", "plus" = PREFERRED
- Extract exact phrasing for keywords
- Identify hard requirements that would be deal-breakers

Return JSON matching the JobAnalysis schema.
"""

JOB_MATCHING_PROMPT = f"""
You are an expert job matcher. Compare the candidate profile against the job requirements and produce a match score with SEPARATE technical and soft skills evaluations.

PROMPT VERSION: {{PROMPT_VERSION}}

CANDIDATE PROFILE:
{{candidate_profile}}

MASTER RESUME EXPERIENCE:
{{master_experience}}

ADDITIONAL EXPERIENCE:
{{additional_experience}}

JOB ANALYSIS:
{{job_analysis}}

SCORING WEIGHTS:
- Technical Skills Match: 35%
- Experience Match: 20%
- Responsibilities Match: 15%
- Job Title Match: 10%
- Tools Match: 10%
- Education Match: 5%
- Location Match: 3%
- Industry Match: 2%

TECHNICAL SKILLS THRESHOLD: >= 70% required for APPLY
SOFT SKILLS THRESHOLD: >= 50% required for APPLY
EXCEPTION: If technical_score >= 75% but soft_skills_score < 50%, still recommend APPLY and list missing soft skills in missing_soft_skills field - these can be added to the custom resume as they are easily acquirable.

RULES:
1. ONLY count skills/tools/experience that are EXPLICITLY VERIFIED in candidate sources
2. Mark each match with its SOURCE (e.g., "master_resume.technical_skills", "additional_experience[1]")
3. Hard requirements NOT met must be in missing_requirements
4. Preferred requirements NOT met go in preferred_requirements_missing
5. Soft skills from job that candidate doesn't have go in missing_soft_skills (these can be added to resume)
6. If a hard technical requirement is missing, recommendation should be REJECT or REVIEW (not APPLY)
6. Be conservative - don't inflate scores
7. Distinguish VERIFIED vs NOT_VERIFIED vs UNKNOWN for each requirement
8. match_score must be an INTEGER 0-100 (weighted average)
9. technical_score must be an INTEGER 0-100 (technical skills only)
10. soft_skills_score must be an INTEGER 0-100 (soft skills only)
11. strong_matches and partial_matches must ONLY contain SKILLS and TOOLS (not education, certifications, degrees)
12. proficiency MUST be one of: "expert", "advanced", "intermediate", "beginner" (NOT "verified", "unknown", etc.)

DEFINITIONS:
- TECHNICAL SKILLS: Programming languages, frameworks, databases, cloud platforms, tools, methodologies, data analysis, ML/AI, etc.
- SOFT SKILLS: Communication, leadership, teamwork, problem-solving, adaptability, time management, stakeholder management, mentoring, presentation, agile/scrum, customer service, etc.

RETURN EXACTLY THIS JSON STRUCTURE:
{{
  "match_score": 85,
  "technical_score": 88,
  "soft_skills_score": 65,
  "recommendation": "APPLY",
  "strong_matches": [
    {{"skill": "Python", "proficiency": "advanced", "source": "master_resume.technical_skills", "verified": true}},
    {{"skill": "React", "proficiency": "intermediate", "source": "master_resume.technical_skills", "verified": true}}
  ],
  "partial_matches": [
    {{"skill": "Docker", "proficiency": "beginner", "source": "additional_experience[1]", "verified": true}}
  ],
  "missing_requirements": ["5+ years experience with Kubernetes"],
  "preferred_requirements_missing": ["AWS certification"],
  "missing_soft_skills": ["Stakeholder management", "Cross-functional team leadership"],
  "concerns": ["Salary expectation may be high for this role"],
  "reasoning": "Strong technical match on core skills Python and React (88%). Soft skills match at 65% - missing stakeholder management and cross-functional leadership which can be added to resume. Missing Kubernetes experience which is a preferred requirement."
}}

Return JSON matching the JobMatchResult schema exactly.
"""

RESUME_CUSTOMIZATION_PROMPT = f"""
You are an expert resume writer. Create a customization plan for the master resume to target a specific job.

PROMPT VERSION: {PROMPT_VERSION}

MASTER RESUME:
{{master_resume}}

ADDITIONAL EXPERIENCE:
{{additional_experience}}

JOB DESCRIPTION:
{{job_description}}

JOB MATCH ANALYSIS:
{{job_match_analysis}}

INSTRUCTIONS:
- Modify ONLY information supported by master resume or additional experience
- PRESERVE the master resume's format, structure, fonts, margins, spacing
- Improve relevance through: rewording bullets, reordering bullets, emphasizing relevant skills, adjusting summary
- Use job description terminology WHEN TRUTHFUL
- NEVER add unsupported claims, fake experience, or invented skills
- Target 80-90% relevance score based on TRUTHFUL alignment
- Each change must be traceable to a source

Return JSON matching the ResumeCustomizationPlan schema.
"""

RESUME_VALIDATION_PROMPT = f"""
You are an independent resume validator. Verify the customized resume against sources.

PROMPT VERSION: {PROMPT_VERSION}

ORIGINAL MASTER RESUME:
{{master_resume}}

CANDIDATE PROFILE:
{{candidate_profile}}

ADDITIONAL EXPERIENCE:
{{additional_experience}}

GENERATED RESUME:
{{generated_resume}}

JOB DESCRIPTION:
{{job_description}}

VALIDATE:
1. TRUTHFULNESS - Every factual claim traceable to master resume OR additional experience
2. FORMATTING - Page count, section structure, fonts, margins, spacing, bullets, headers, contact info
3. ATS/RELEVANCE - Important truthful keywords covered, relevant experience prioritized, required skills addressed
4. QUALITY - Grammar, duplicate bullets, broken formatting, strange wording, keyword stuffing, missing sections

RETURN EXACTLY THIS JSON STRUCTURE:
{{
  "valid": true,
  "truthfulness_score": 95,
  "format_score": 100,
  "relevance_score": 90,
  "issues": [
    {{"type": "truthfulness", "severity": "warning", "message": "Missing relevant experience in data analysis role"}},
    {{"type": "formatting", "severity": "info", "message": "Formatting issues in job titles"}}
  ],
  "traceability_check": [
    {{"claim": "5 years SQL experience", "source": "master_resume.employment_history[0]", "verified": true}},
    {{"claim": "Power BI dashboards", "source": "master_resume.technical_skills", "verified": true}}
  ]
}}

Return JSON matching the ResumeValidationResult schema exactly.
"""

SCREENING_QUESTION_PROMPT = f"""
You are a screening question analyzer. Determine if the candidate can truthfully answer each question.

PROMPT VERSION: {PROMPT_VERSION}

CANDIDATE PROFILE:
{{candidate_profile}}

MASTER RESUME:
{{master_resume}}

ADDITIONAL EXPERIENCE:
{{additional_experience}}

QUESTIONS:
{{questions}}

FOR EACH QUESTION:
1. Can the answer be derived from VERIFIED candidate information?
2. If YES: provide answer, source, confidence (0.9-1.0), requires_human=false
3. If NO: answer=null, source=null, confidence=0, requires_human=true
4. Classify question_type: technical, experience, education, legal, salary, authorization, diversity, reference, other

NEVER GUESS. If uncertain, mark requires_human=true.
Legal declarations, salary history, background check consent, diversity surveys, references -> ALWAYS requires_human=true

Return JSON matching the ScreeningAnalysis schema.
"""


def get_prompt(name: str) -> str:
    prompts = {
        "profile_analysis": PROFILE_ANALYSIS_PROMPT,
        "job_analysis": JOB_ANALYSIS_PROMPT,
        "job_matching": JOB_MATCHING_PROMPT,
        "resume_customization": RESUME_CUSTOMIZATION_PROMPT,
        "resume_validation": RESUME_VALIDATION_PROMPT,
        "screening_question": SCREENING_QUESTION_PROMPT,
    }
    return prompts.get(name, "")