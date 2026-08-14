// TypeScript types matching backend Pydantic models

// Profile Types
export interface PersonalInfo {
  full_name: string
  email: string
  phone?: string
  location?: string
  linkedin?: string
  github?: string
  portfolio?: string
  website?: string
  twitter?: string
  summary?: string
}

export interface Skill {
  name: string
  level?: 'Beginner' | 'Intermediate' | 'Advanced' | 'Expert'
  category?: string
}

export interface Experience {
  id?: string
  company: string
  title: string
  location?: string
  start_date: string
  end_date?: string
  current: boolean
  description: string | string[]
  technologies: string[]
  achievements?: string[]
}

export interface Education {
  id?: string
  institution: string
  degree: string
  field_of_study?: string
  location?: string
  start_date?: string
  end_date?: string
  gpa?: string | number
  honors?: string[]
}

export interface Certification {
  id?: string
  name: string
  issuer: string
  date_obtained?: string
  expiry_date?: string
  credential_id?: string
  url?: string
}

export interface Project {
  id?: string
  name: string
  description: string
  technologies: string[]
  url?: string
  github_url?: string
  start_date?: string
  end_date?: string
  highlights?: string[]
}

export interface AdditionalExperience {
  type: 'project' | 'publication' | 'award' | 'volunteer' | 'other'
  title: string
  description?: string
  url?: string
  start_date?: string
  end_date?: string
  technologies?: string[]
}

// Original structured additional experience type (for backend compatibility)
export interface AdditionalExperienceSections {
  projects: Project[]
  publications: Publication[]
  awards: Award[]
  volunteering: Volunteering[]
  languages: Language[]
}

export interface Publication {
  id?: string
  title: string
  venue: string
  date: string
  url?: string
  authors?: string[]
}

export interface Award {
  id?: string
  name: string
  issuer: string
  date: string
  description?: string
}

export interface Volunteering {
  id?: string
  organization: string
  role: string
  start_date: string
  end_date?: string
  description?: string
}

export interface Language {
  id?: string
  name: string
  proficiency: 'Native' | 'Fluent' | 'Professional' | 'Conversational' | 'Basic'
}

export interface CandidateProfile {
  id?: string
  personal_info: PersonalInfo
  skills: Skill[]
  experience: Experience[]
  education: Education[]
  certifications: Certification[]
  additional_experience: AdditionalExperience[]
  created_at?: string
  updated_at?: string
}

// Job Types
export type JobSource = 'jobbank' | 'indeed'

export type JobType = 'full_time' | 'part_time' | 'contract' | 'internship' | 'temporary'

export type ExperienceLevel = 'entry' | 'mid' | 'senior' | 'lead' | 'executive'

export interface JobLocation {
  city?: string
  state?: string
  country: string
  remote: boolean
  timezone?: string
}

export interface SalaryRange {
  min?: number
  max?: number
  currency: string
  period: 'yearly' | 'monthly' | 'hourly'
}

export interface Job {
  id: string
  external_id?: string
  title: string
  company: string
  location: JobLocation
  description: string
  requirements: string[]
  responsibilities?: string[]
  benefits?: string[]
  job_type: JobType
  experience_level: ExperienceLevel
  salary_range?: SalaryRange
  source: JobSource
  source_url: string
  posted_date: string
  discovered_at: string
  status: JobStatus
  deduplication_key?: string
  is_duplicate?: boolean
  duplicate_of?: string
  match_score?: number
  match_verdict?: string
  skill_match_pct?: number
}

export type JobStatus =
  | 'DISCOVERED'
  | 'DEDUPLICATED'
  | 'MATCHED'
  | 'QUALIFIED'
  | 'RESUME_CREATED'
  | 'READY_TO_APPLY'
  | 'APPLIED'
  | 'TRACKED'

// Matching Types
export interface MatchScore {
  overall: number
  skills: number
  experience: number
  education: number
  location: number
  keywords: number
  verdict: 'QUALIFIED' | 'UNQUALIFIED'
}

export interface MatchDetail {
  job_id: string
  job: Job
  score: MatchScore
  skill_matches: SkillMatch[]
  experience_matches: ExperienceMatch[]
  missing_requirements: string[]
  matched_keywords: string[]
  analysis: string
  analyzed_at: string
}

export interface SkillMatch {
  skill: string
  required: boolean
  matched: boolean
  candidate_level?: string
  required_level?: string
}

export interface ExperienceMatch {
  requirement: string
  matched: boolean
  relevant_experience?: Experience
  gap?: string
}

export interface MatchWeights {
  skills: number
  experience: number
  education: number
  location: number
  keywords: number
}

// Resume Types
export interface ResumeTemplate {
  id: string
  name: string
  description: string
  preview_url?: string
  is_default?: boolean
}

export interface ResumeCustomizationOptions {
  job_id: string
  template_id?: string
  emphasize_skills?: string[]
  emphasize_experience?: string[]
  inject_keywords?: string[]
  target_length?: '1_page' | '2_pages' | 'auto'
  format?: 'docx' | 'pdf'
}

export interface GeneratedResume {
  id: string
  job_id: string
  job_title: string
  company: string
  template_id: string
  file_path: string
  file_url?: string
  format: 'docx' | 'pdf'
  customization_options: ResumeCustomizationOptions
  validation_result?: ValidationResult
  created_at: string
}

export interface ValidationResult {
  truthfulness_score: number
  ats_score: number
  issues: ValidationIssue[]
  suggestions: string[]
  validated_at: string
}

export interface ValidationIssue {
  type: 'exaggeration' | 'missing_keyword' | 'formatting' | 'inconsistency' | 'truthfulness'
  severity: 'high' | 'medium' | 'low'
  message: string
  location?: string
  suggestion?: string
}

// Application Types
export type ApplicationStatus =
  | 'READY_TO_APPLY'
  | 'APPLYING'
  | 'SUBMITTED'
  | 'INTERVIEW_SCHEDULED'
  | 'INTERVIEWED'
  | 'OFFER'
  | 'REJECTED'
  | 'WITHDRAWN'

export interface Application {
  id: string
  job_id: string
  job: Job
  resume_id: string
  resume: GeneratedResume
  cover_letter?: string
  status: ApplicationStatus
  applied_at?: string
  submitted_at?: string
  interview_date?: string
  notes?: string
  follow_up_date?: string
  external_application_id?: string
  created_at: string
  updated_at: string
}

// Search & Filter Types
export interface JobSearchFilters {
  keywords?: string[]
  primary_titles?: string[]
  locations?: string[]
  job_types?: JobType[]
  experience_levels?: ExperienceLevel[]
  sources?: JobSource[]
  salary_min?: number
  salary_max?: number
  remote_only?: boolean
  visa_sponsorship?: boolean
  company_size?: string[]
  posted_within_days?: number
  exclude_keywords?: string[]
}

export interface JobSearchRequest {
  filters: JobSearchFilters
  max_results_per_source?: number
  use_cache?: boolean
}

export interface JobSearchResponse {
  jobs: Job[]
  total_found: number
  sources_searched: JobSource[]
  search_duration_ms: number
  duplicates_removed: number
}

// Analytics Types
export interface PipelineStats {
  discovered: number
  deduplicated: number
  matched: number
  qualified: number
  resume_created: number
  ready_to_apply: number
  applied: number
  interviewed: number
  offers: number
  rejected: number
}

export interface SourceEffectiveness {
  source: JobSource
  jobs_found: number
  jobs_qualified?: number
  applications_submitted?: number
  interviews?: number
  offers?: number
  conversion_rate: number
}

export interface SkillGap {
  skill: string
  gap: string
  severity: 'high' | 'medium' | 'low'
  required_count?: number
  candidate_level?: string
}

export interface AnalyticsOverview {
  pipeline: PipelineStats
  source_effectiveness: SourceEffectiveness[]
  skill_gaps: SkillGap[]
  applications_over_time: TimeSeriesData[]
  match_score_distribution: ScoreDistribution[]
  response_rates: ResponseRate[]
}

export interface TimeSeriesData {
  date: string
  applications: number
  interviews: number
  offers: number
}

export interface ScoreDistribution {
  range: string
  count: number
}

export interface ResponseRate {
  category: string
  rate: number
  total: number
}

// Settings Types
export interface LLMSettings {
  provider: 'nvidia'
  model: string
  api_key?: string
  base_url?: string
  temperature: number
  max_tokens: number
}

export interface JobSourceSettings {
  [key: string]: {
    enabled: boolean
    rate_limit?: number
    credentials?: Record<string, string>
    config?: Record<string, unknown>
  }
}

export interface MatchingSettings {
  default_weights: MatchWeights
  auto_qualify_threshold: number
  min_skill_match: number
}

export interface NotificationSettings {
  email_enabled: boolean
  email_address?: string
  browser_enabled: boolean
  webhook_url?: string
  events: {
    job_found: boolean
    match_complete: boolean
    resume_generated: boolean
    application_submitted: boolean
    interview_scheduled: boolean
  }
}

export interface AppSettings {
  llm: LLMSettings
  job_sources: JobSourceSettings
  matching: MatchingSettings
  notifications: NotificationSettings
  resume_templates: ResumeTemplate[]
}

// API Response Types
export interface ApiResponse<T> {
  data: T
  message?: string
  success: boolean
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ApiError {
  detail: string
  code?: string
  status_code: number
}

// WebSocket Types
export interface WSMessage {
  type: 'pipeline_update' | 'job_found' | 'match_complete' | 'resume_generated' | 'error' | 'progress'
  payload: unknown
  timestamp: string
}

export interface PipelineProgress {
  stage: string
  current: number
  total: number
  message: string
  job_id?: string
}

// Form Types
export interface ProfileFormData {
  personal_info: PersonalInfo
  skills: Skill[]
  experience: Experience[]
  education: Education[]
  certifications: Certification[]
  additional_experience: AdditionalExperience
}

export interface JobSearchFormData {
  keywords: string
  locations: string[]
  job_types: JobType[]
  experience_levels: ExperienceLevel[]
  sources: JobSource[]
  remote_only: boolean
  posted_within_days: number
  salary_min?: number
  salary_max?: number
}

export interface ResumeCustomizationFormData {
  job_id: string
  template_id: string
  emphasize_skills: string[]
  emphasize_experience: string[]
  inject_keywords: string[]
  target_length: '1_page' | '2_pages' | 'auto'
  format: 'docx' | 'pdf'
}