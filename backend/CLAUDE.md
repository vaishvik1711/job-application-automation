# AI Job Application Automation System - Project Configuration

## Model Configuration
**This project uses `poolside/laguna-s-2.1:free` as the default model for all operations.**

Do not change this model setting. All LLM interactions, agent operations, and code generation should use this model.

## Project Overview
This is an AI-powered job application automation system with the following phases:
- Phase 1: Profile Building (resume parsing, candidate profile creation)
- Phase 2: Job Discovery (multi-source job search with deduplication)
- Phase 3: Job Matching & Scoring (LLM-based matching with weighted scoring)
- Phase 4: Resume Customization & Validation (format-preserving DOCX generation + validation)
- Phase 5: Real Job Sources (Indeed, JobBank, LinkedIn, Glassdoor, Company Careers)
- Phase 6: Browser Automation (planned)
- Phase 7: Application Submission (planned)
- Phase 8: Orchestration & Continuous Execution (planned)

## Key Constraints
- **NO JOB APPLICATIONS** - This is for testing only. Do not submit any applications until Phase 7+ is implemented and explicitly enabled.
- Use mock data and test sources for development
- All LLM calls use structured JSON output via Pydantic schemas
- Database is SQLite with SQLAlchemy async
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