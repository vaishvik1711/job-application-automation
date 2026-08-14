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

EXTRACT AND CATEGORIZE AS PLAIN STRING LISTS (no proficiency levels or years of experience on skills):

1. STRONG SKILLS - Skills explicitly demonstrated with evidence in resume/experience
2. MODERATE SKILLS - Skills mentioned but with less evidence
3. SUPPORTING SKILLS - Skills mentioned briefly or in passing
4. TOOLS - Software, platforms, languages explicitly used
5. TITLE KEYWORDS - 5-10 single words that must appear in relevant job titles. Extract these from the candidate's resume by analyzing their job history, skills, and experience. Examples: consultant, analyst, engineer, developer, BI, data, business, finance, product, manager, architect, operations, sales, marketing. These are used to FILTER OUT irrelevant jobs (like carpenter, farmer, cook). Pick words that best match the candidate's career.
6. INDUSTRIES - Industries from work history
7. PRIMARY TITLES - Job titles that directly match experience
8. SECONDARY TITLES - Related/adjacent titles the candidate could qualify for
9. SEARCH KEYWORDS - Keywords for job search queries
10. NEGATIVE KEYWORDS - Terms that indicate unsuitable jobs (e.g., "CPA required", "security clearance")
11. EXPERIENCE RANGE - Min/max years of experience
12. REMOTE PREFERENCES - Based on stated preferences

CRITICAL RULES:
- ONLY use EXPLICITLY VERIFIED information from the provided sources
- Do NOT infer or assume skills not directly stated
- Distinguish between REQUIRED vs PREFERRED qualifications in job analysis
- Be conservative - it's better to miss a match than to hallucinate one
- Skill/tool/industry/title fields are plain string lists — do NOT include proficiency, source, or verification info

RETURN EXACTLY THIS JSON STRUCTURE:
{{
  "strong_skills": ["Python", "React", "SQL"],
  "moderate_skills": ["JavaScript", "TypeScript"],
  "supporting_skills": ["Django"],
  "tools": ["Docker", "Kubernetes", "AWS"],
  "title_keywords": ["engineer", "developer", "software", "data", "analyst", "architect"],
  "industries": ["Software Development", "FinTech"],
  "primary_titles": ["Senior Software Engineer"],
  "secondary_titles": ["Software Engineer", "Full Stack Developer"],
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
You are a technical skills matcher. Compare the candidate's technical skills against the job's required technical skills. Only evaluate technical skills — ignore soft skills, education, location, industry, and job titles.

PROMPT VERSION: {{PROMPT_VERSION}}

CANDIDATE PROFILE:
{{candidate_profile}}

JOB ANALYSIS:
{{job_analysis}}

SCORING:
- Evaluate ONLY technical skills: programming languages, frameworks, databases, cloud platforms, tools, data analysis, ML/AI, and other hard technical requirements.
- technical_score = percentage of job's required technical skills that the candidate has (0-100).
- match_score = same as technical_score (there is no other dimension).
- soft_skills_score = always 100 (not evaluated — kept for schema compatibility).

THRESHOLD: >= 50% technical match = APPLY, < 50% = REJECT.

RULES:
1. ONLY count skills/tools that are EXPLICITLY VERIFIED in candidate sources
2. Mark each match with its SOURCE (e.g., "master_resume.technical_skills", "additional_experience[1]")
3. Missing technical requirements go in missing_requirements
4. strong_matches = skills the candidate has that the job requires
5. partial_matches = skills the candidate has some exposure to (beginner/intermediate level)
6. Be conservative — don't inflate scores
7. match_score must be an INTEGER 0-100 (same as technical_score)
8. technical_score must be an INTEGER 0-100
9. soft_skills_score must be an INTEGER 0-100 (always 100)
10. proficiency MUST be one of: "expert", "advanced", "intermediate", "beginner"

RETURN EXACTLY THIS JSON STRUCTURE:
{{
  "match_score": 75,
  "technical_score": 75,
  "soft_skills_score": 100,
  "recommendation": "APPLY",
  "strong_matches": [
    {{"skill": "Python", "proficiency": "advanced", "source": "master_resume.technical_skills", "verified": true}},
    {{"skill": "SQL", "proficiency": "expert", "source": "master_resume.technical_skills", "verified": true}}
  ],
  "partial_matches": [
    {{"skill": "Docker", "proficiency": "beginner", "source": "additional_experience[1]", "verified": true}}
  ],
  "missing_requirements": ["Kubernetes"],
  "preferred_requirements_missing": [],
  "missing_soft_skills": [],
  "concerns": [],
  "reasoning": "Candidate has 3 of 4 required technical skills (75%): Python, SQL, and AWS. Missing Kubernetes. Above 50% threshold, recommending APPLY."
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