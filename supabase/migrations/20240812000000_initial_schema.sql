-- Initial schema for Job Application Automation System
-- Based on backend/database/models.py SQLAlchemy models

-- Job status enum
CREATE TYPE job_status AS ENUM (
  'discovered',
  'deduplicated',
  'matched',
  'qualified',
  'resume_created',
  'resume_validated',
  'ready_to_apply',
  'application_started',
  'applied',
  'tracked',
  'rejected',
  'failed',
  'needs_human_input',
  'captcha_required',
  'mfa_required',
  'duplicate'
);

-- Application status enum
CREATE TYPE application_status AS ENUM (
  'discovered',
  'rejected',
  'qualified',
  'resume_created',
  'ready',
  'applying',
  'applied',
  'failed',
  'needs_human_input',
  'interview',
  'rejected_by_company',
  'offer',
  'withdrawn'
);

-- Remote type enum
CREATE TYPE remote_type AS ENUM ('remote', 'hybrid', 'on_site');

-- Employment type enum
CREATE TYPE employment_type AS ENUM ('full_time', 'part_time', 'contract', 'internship', 'temporary');

-- Candidate profiles
CREATE TABLE candidate_profiles (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  phone TEXT,
  address TEXT,
  city TEXT,
  province TEXT,
  postal_code TEXT,
  country TEXT DEFAULT 'Canada',
  work_authorization TEXT,
  linkedin_url TEXT,
  portfolio_url TEXT,
  github_url TEXT,
  notice_period_weeks INTEGER DEFAULT 2,
  salary_expectation_min INTEGER,
  salary_expectation_max INTEGER,
  salary_currency TEXT DEFAULT 'CAD',
  education JSONB DEFAULT '[]'::jsonb,
  certifications JSONB DEFAULT '[]'::jsonb,
  employment_history JSONB DEFAULT '[]'::jsonb,
  skills TEXT[] DEFAULT '{}',
  technical_skills TEXT[] DEFAULT '{}',
  business_skills TEXT[] DEFAULT '{}',
  tools TEXT[] DEFAULT '{}',
  programming_languages TEXT[] DEFAULT '{}',
  industries TEXT[] DEFAULT '{}',
  job_titles TEXT[] DEFAULT '{}',
  preferred_job_titles TEXT[] DEFAULT '{}',
  preferred_locations TEXT[] DEFAULT '{}',
  remote_preferences TEXT[] DEFAULT '{}',
  employment_preferences TEXT[] DEFAULT '{}',
  excluded_titles TEXT[] DEFAULT '{}',
  excluded_industries TEXT[] DEFAULT '{}',
  excluded_requirements TEXT[] DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Candidate experience notes
CREATE TABLE candidate_experience (
  id BIGSERIAL PRIMARY KEY,
  profile_id BIGINT NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
  original_text TEXT NOT NULL,
  category TEXT,
  verified BOOLEAN DEFAULT TRUE,
  source TEXT DEFAULT 'current_job_notes',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Jobs
CREATE TABLE jobs (
  id BIGSERIAL PRIMARY KEY,
  canonical_url TEXT UNIQUE,
  source_urls JSONB DEFAULT '[]'::jsonb,
  source TEXT NOT NULL,
  title TEXT NOT NULL,
  company TEXT NOT NULL,
  location TEXT NOT NULL,
  remote_type remote_type DEFAULT 'on_site',
  employment_type employment_type DEFAULT 'full_time',
  date_posted TIMESTAMP WITH TIME ZONE,
  salary_min INTEGER,
  salary_max INTEGER,
  currency TEXT DEFAULT 'CAD',
  description TEXT NOT NULL,
  requirements TEXT,
  preferred_qualifications TEXT,
  skills TEXT[] DEFAULT '{}',
  tools TEXT[] DEFAULT '{}',
  education TEXT[] DEFAULT '{}',
  certifications TEXT[] DEFAULT '{}',
  application_url TEXT,
  company_url TEXT,
  discovered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  content_hash TEXT NOT NULL,
  status job_status DEFAULT 'discovered',
  canonical_job_id BIGINT REFERENCES jobs(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_jobs_canonical_url ON jobs(canonical_url);
CREATE INDEX idx_jobs_source ON jobs(source);
CREATE INDEX idx_jobs_title_company_location ON jobs(company, title, location);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_content_hash ON jobs(content_hash);
CREATE INDEX idx_jobs_canonical_job_id ON jobs(canonical_job_id);
CREATE INDEX idx_jobs_date_posted ON jobs(date_posted DESC);
CREATE INDEX idx_jobs_discovered_at ON jobs(discovered_at DESC);

-- Job sources (raw data from different sources)
CREATE TABLE job_sources (
  id BIGSERIAL PRIMARY KEY,
  job_id BIGINT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  source TEXT NOT NULL,
  source_url TEXT NOT NULL,
  source_job_id TEXT,
  raw_data JSONB DEFAULT '{}',
  fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_job_sources_job_id ON job_sources(job_id);

-- Job matches
CREATE TABLE job_matches (
  id BIGSERIAL PRIMARY KEY,
  job_id BIGINT UNIQUE NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  match_score REAL NOT NULL,
  technical_score REAL DEFAULT 0,
  soft_skills_score REAL DEFAULT 0,
  recommendation TEXT NOT NULL, -- APPLY, REVIEW, REJECT
  strong_matches JSONB DEFAULT '[]'::jsonb,
  partial_matches JSONB DEFAULT '[]'::jsonb,
  missing_requirements JSONB DEFAULT '[]'::jsonb,
  preferred_requirements_missing JSONB DEFAULT '[]'::jsonb,
  missing_soft_skills TEXT[] DEFAULT '{}',
  concerns JSONB DEFAULT '[]'::jsonb,
  reasoning TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_job_matches_job_id ON job_matches(job_id);
CREATE INDEX idx_job_matches_match_score ON job_matches(match_score DESC);
CREATE INDEX idx_job_matches_recommendation ON job_matches(recommendation);

-- Resumes
CREATE TABLE resumes (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_profiles(id),
  job_id BIGINT NOT NULL REFERENCES jobs(id),
  version INTEGER DEFAULT 1,
  file_path TEXT NOT NULL,
  filename TEXT NOT NULL,
  validation_score REAL,
  truthfulness_score REAL,
  format_score REAL,
  relevance_score REAL,
  validation_issues JSONB DEFAULT '[]'::jsonb,
  traceability JSONB DEFAULT '[]'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_candidate_job_version ON resumes(candidate_id, job_id, version);
CREATE INDEX idx_resumes_job_id ON resumes(job_id);
CREATE INDEX idx_resumes_candidate_id ON resumes(candidate_id);

-- Applications
CREATE TABLE applications (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_profiles(id),
  job_id BIGINT UNIQUE NOT NULL REFERENCES jobs(id),
  resume_id BIGINT NOT NULL REFERENCES resumes(id),
  application_url TEXT NOT NULL,
  status application_status DEFAULT 'discovered',
  confirmation TEXT,
  cover_letter_path TEXT,
  applied_at TIMESTAMP WITH TIME ZONE,
  submitted_at TIMESTAMP WITH TIME ZONE,
  error_message TEXT,
  human_intervention_reason TEXT,
  fields_remaining TEXT[] DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_applications_job_id ON applications(job_id);
CREATE INDEX idx_applications_candidate_id ON applications(candidate_id);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_applications_applied_at ON applications(applied_at);

-- Screening questions
CREATE TABLE screening_questions (
  id BIGSERIAL PRIMARY KEY,
  application_id BIGINT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  question TEXT NOT NULL,
  answer TEXT,
  source TEXT,
  confidence REAL,
  requires_human BOOLEAN DEFAULT FALSE,
  question_type TEXT,
  answered_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_screening_questions_application_id ON screening_questions(application_id);

-- Application events
CREATE TABLE application_events (
  id BIGSERIAL PRIMARY KEY,
  application_id BIGINT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  description TEXT NOT NULL,
  event_metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_application_events_application_id ON application_events(application_id);
CREATE INDEX idx_application_events_created_at ON application_events(created_at);

-- Application errors
CREATE TABLE application_errors (
  id BIGSERIAL PRIMARY KEY,
  application_id BIGINT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  source TEXT NOT NULL,
  error_type TEXT NOT NULL,
  error_message TEXT NOT NULL,
  current_url TEXT,
  resolution TEXT,
  resolved BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_application_errors_application_id ON application_errors(application_id);
CREATE INDEX idx_application_errors_resolved ON application_errors(resolved);

-- Daily statistics
CREATE TABLE daily_statistics (
  id BIGSERIAL PRIMARY KEY,
  date DATE UNIQUE NOT NULL,
  jobs_found INTEGER DEFAULT 0,
  duplicates_removed INTEGER DEFAULT 0,
  jobs_qualified INTEGER DEFAULT 0,
  resumes_created INTEGER DEFAULT 0,
  resumes_validated INTEGER DEFAULT 0,
  applications_submitted INTEGER DEFAULT 0,
  applications_failed INTEGER DEFAULT 0,
  human_intervention_required INTEGER DEFAULT 0,
  average_match_score REAL,
  top_companies TEXT[] DEFAULT '{}',
  top_job_titles TEXT[] DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_daily_statistics_date ON daily_statistics(date);

-- Matching weights and thresholds (settings)
CREATE TABLE matching_config (
  id BIGSERIAL PRIMARY KEY,
  default_weights JSONB NOT NULL DEFAULT '{"skills": 30, "experience": 25, "education": 10, "location": 15, "keywords": 20}',
  auto_qualify_threshold REAL DEFAULT 75.0,
  min_skill_match REAL DEFAULT 0.5,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Settings (app-level configuration)
CREATE TABLE app_settings (
  key TEXT PRIMARY KEY,
  value JSONB NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Seed data for matching config
INSERT INTO matching_config (id, auto_qualify_threshold, min_skill_match)
VALUES (1, 75.0, 0.5)
ON CONFLICT DO NOTHING;