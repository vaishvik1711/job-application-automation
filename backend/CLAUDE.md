# AI Job Application Automation System - Project Configuration

## Model Configuration
**This project uses the `ANTHROPIC_MODEL` environment variable as the single source of truth for the LLM model.**

The model is set in `.claude/settings.json` (`env.ANTHROPIC_MODEL`). Both the backend (`llm/client.py`) and the frontend (`LLMSettingsForm.tsx`) read it from the environment — no hardcoded model names in application code. To change the model, update `ANTHROPIC_MODEL` in `.claude/settings.json` (or `backend/.env` for deployment).

## Project Overview
This is an AI-powered job application automation system with the following phases:
- Phase 1: Profile Building (resume parsing, candidate profile creation)
- Phase 2: Job Discovery (multi-source job search with deduplication)
- Phase 3: Job Matching & Scoring (LLM-based matching with weighted scoring)
- Phase 4: Resume Customization & Validation (format-preserving DOCX generation + validation)
- Phase 5: Real Job Sources (Indeed, JobBank, LinkedIn, Glassdoor, Company Careers)
- Phase 6: Browser Automation (`browser/` — site flows, login, form filling)
- Phase 7: Application Submission (`application/service.py` ApplyService — implemented, gated below)
- Phase 8: Orchestration & Continuous Execution

## Key Constraints
- **Auto-apply is feature-gated.** Submission is allowed ONLY to these sites: JobBank Canada, Greenhouse-hosted boards, Lever-hosted postings, or the local mock apply target (`ENABLE_MOCK_APPLY_TARGET=1`). LinkedIn/Indeed are explicitly rejected by `browser/sites/detect_site`.
- **MANUAL is the default submission mode** (`AUTO_SUBMIT=false`): the bot fills the form headless, parks it, and the owner confirms the final Submit from the UI. AUTO mode additionally requires `AUTO_SUBMIT=true` in the environment AND an explicit per-run override — never enable either casually.
- **Credentials are secrets**: job-site logins live in `site_credentials` encrypted with Fernet (`CREDENTIAL_ENCRYPTION_KEY`). Never log passwords, never return them from any endpoint (GET returns masked hints only), never commit them. `.env` is gitignored.
- Use mock data and test sources for development; destructive tests run only against a local scratch DB, never production Supabase.
- All LLM calls use structured JSON output via Pydantic schemas
- Database is Postgres (Supabase) in prod / SQLite locally, SQLAlchemy async
- Excel is used as reporting layer only (not source of truth)

## Architecture
- Multi-agent system: ProfileAgent, DiscoveryAgent, MatchingAgent, ResumeAgent, ResumeValidator
- Centralized LLM client with retry logic and prompt versioning
- Job state machine: DISCOVERED → DEDUPLICATED → MATCHED → QUALIFIED → RESUME_CREATED → READY_TO_APPLY → APPLIED → TRACKED
- Truthfulness enforcement: Only verified information from resume/additional experience

## Configuration Files
- `config/settings.yaml` - Main application settings
- `config/job_filters.yaml` - Auto-generated from profile for job search
- `.env` - Environment variables (API keys, etc.)

## Running the Pipeline
```bash
# Setup with resume
python main.py setup --resume "data/master_resume/IT RESUME VAISHVIK PATEL.pdf"

# Search for jobs
python main.py search

# Analyze jobs against profile
python main.py analyze --all-analyze

# Generate and validate resumes
python main.py resumes --all --validate

# Export to Excel
python main.py export

# Check status
python main.py status
```