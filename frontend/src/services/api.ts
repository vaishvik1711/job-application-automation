import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios'
import type {
  CandidateProfile,
  Job,
  JobSearchRequest,
  JobSearchResponse,
  MatchDetail,
  MatchWeights,
  GeneratedResume,
  ResumeCustomizationOptions,
  ValidationResult,
  Application,
  ApplicationStatus,
  AnalyticsOverview,
  PipelineStats,
  SourceEffectiveness,
  SkillGap,
  ResumeTemplate,
  AppSettings,
  PaginatedResponse,
  ApiResponse,
  ApiError,
} from '@/types'

// Create axios instance
const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || '/api'

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for auth
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('auth_token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - redirect to login or refresh token
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Response types for resume upload/parse
export interface UploadResponse {
  file_id: string
  filename: string
  size: number
}

export interface ParseResponse {
  profile: CandidateProfile
  file_id: string
  confidence?: number
  extracted_fields?: Record<string, unknown>
}

// Profile API
export const profileApi = {
  get: () => api.get<ApiResponse<CandidateProfile>>('/profile'),
  create: (data: Partial<CandidateProfile>) => api.post<ApiResponse<CandidateProfile>>('/profile', data),
  update: (data: Partial<CandidateProfile>) => api.patch<ApiResponse<CandidateProfile>>('/profile', data),
  uploadResume: (file: File, onProgress?: (progress: number) => void) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<ApiResponse<CandidateProfile>>('/profile/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          onProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total))
        }
      },
    })
  },
  parseResume: (fileId: string, onProgress?: (progress: number) => void) =>
    api.post<ApiResponse<ParseResponse>>('/profile/parse', { file_id: fileId }, {
      onDownloadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          onProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total))
        }
      },
    }),
}

// Named exports for backward compatibility / direct usage
export const updateProfile = (data: Partial<CandidateProfile>) =>
  profileApi.update(data).then((res) => res.data.data)

export const uploadResume = (file: File, onProgress?: (progress: number) => void) =>
  api.post<ApiResponse<UploadResponse>>('/profile/upload', file instanceof FormData ? file : (() => {
    const formData = new FormData()
    formData.append('file', file)
    return formData
  })(), {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        onProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total))
      }
    },
  }).then((res) => res.data.data)

export const parseResume = (fileId: string, onProgress?: (progress: number) => void) =>
  profileApi.parseResume(fileId, onProgress).then((res) => res.data.data)

// Jobs API
export const jobsApi = {
  list: (params?: {
    page?: number
    page_size?: number
    status?: string
    search?: string
    sort_by?: string
    sort_order?: 'asc' | 'desc'
  }) => api.get<PaginatedResponse<Job>>('/jobs', { params }),

  get: (id: string) => api.get<ApiResponse<Job>>(`/jobs/${id}`),

  search: (request: JobSearchRequest) =>
    api.post<ApiResponse<JobSearchResponse>>('/jobs/search', request),

  analyze: (id: string, weights?: MatchWeights) =>
    api.post<ApiResponse<MatchDetail>>(`/jobs/${id}/analyze`, { weights }),

  batchAnalyze: (jobIds: string[], weights?: MatchWeights) =>
    api.post<ApiResponse<MatchDetail[]>>('/jobs/batch-analyze', { job_ids: jobIds, weights }),

  getMatches: (params?: {
    page?: number
    page_size?: number
    verdict?: string
    min_score?: number
    max_score?: number
  }) => api.get<PaginatedResponse<MatchDetail>>('/jobs/matches', { params }),

  export: (jobIds?: string[], format: 'csv' | 'excel' = 'csv') =>
    api.get<Blob>('/jobs/export', {
      params: { job_ids: jobIds?.join(','), format },
      responseType: 'blob',
    }),

  getStats: () => api.get<ApiResponse<PipelineStats>>('/jobs/stats'),
}

// Matching API
export const matchingApi = {
  getWeights: () => api.get<ApiResponse<MatchWeights>>('/matching/weights'),
  updateWeights: (weights: MatchWeights) =>
    api.patch<ApiResponse<MatchWeights>>('/matching/weights', weights),
  getThreshold: () => api.get<ApiResponse<{ threshold: number }>>('/matching/threshold'),
  updateThreshold: (threshold: number) =>
    api.patch<ApiResponse<{ threshold: number }>>('/matching/threshold', { threshold }),
}

// Resumes API
export const resumesApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    api.get<PaginatedResponse<GeneratedResume>>('/resumes', { params }),

  get: (id: string) => api.get<ApiResponse<GeneratedResume>>(`/resumes/${id}`),

  generate: (options: ResumeCustomizationOptions) =>
    api.post<ApiResponse<GeneratedResume>>('/resumes/generate', options),

  validate: (id: string) => api.get<ApiResponse<ValidationResult>>(`/resumes/${id}/validate`),

  download: (id: string, format: 'docx' | 'pdf' = 'docx') =>
    api.get<Blob>(`/resumes/${id}/download`, {
      params: { format },
      responseType: 'blob',
    }),

  delete: (id: string) => api.delete<ApiResponse<void>>(`/resumes/${id}`),

  getTemplates: () => api.get<ApiResponse<{ templates: ResumeTemplate[] }>>('/resumes/templates'),
}

// Applications API
export const applicationsApi = {
  list: (params?: {
    page?: number
    page_size?: number
    status?: ApplicationStatus
    sort_by?: string
    sort_order?: 'asc' | 'desc'
  }) => api.get<PaginatedResponse<Application>>('/applications', { params }),

  get: (id: string) => api.get<ApiResponse<Application>>(`/applications/${id}`),

  create: (data: { job_id: string; resume_id: string; cover_letter?: string }) =>
    api.post<ApiResponse<Application>>('/applications', data),

  updateStatus: (id: string, status: ApplicationStatus, notes?: string) =>
    api.patch<ApiResponse<Application>>(`/applications/${id}`, { status, notes }),

  update: (id: string, data: Partial<Application>) =>
    api.patch<ApiResponse<Application>>(`/applications/${id}`, data),

  delete: (id: string) => api.delete<ApiResponse<void>>(`/applications/${id}`),

  bulkUpdateStatus: (ids: string[], status: ApplicationStatus) =>
    api.patch<ApiResponse<{ updated: number }>>('/applications/bulk-status', { ids, status }),
}

// Analytics API
export const analyticsApi = {
  getOverview: () => api.get<ApiResponse<AnalyticsOverview>>('/analytics/overview'),
  getPipeline: () => api.get<ApiResponse<PipelineStats>>('/analytics/pipeline'),
  getSourceEffectiveness: () =>
    api.get<ApiResponse<SourceEffectiveness[]>>('/analytics/sources'),
  getSkillGaps: () => api.get<ApiResponse<SkillGap[]>>('/analytics/skill-gaps'),
  getTimeSeries: (days: number = 30) =>
    api.get<ApiResponse<Array<{ date: string; applications: number; interviews: number; offers: number }>>>('/analytics/timeseries', { params: { days } }),
  exportReport: (format: 'pdf' | 'excel' = 'pdf') =>
    api.get<Blob>('/analytics/export', { params: { format }, responseType: 'blob' }),
}

// Settings API
export const settingsApi = {
  get: () => api.get<ApiResponse<AppSettings>>('/settings'),
  update: (settings: Partial<AppSettings>) => api.patch<ApiResponse<AppSettings>>('/settings', settings),
  testLLM: (config: { provider: string; model: string; api_key?: string }) =>
    api.post<ApiResponse<{ success: boolean; latency_ms: number }>>('/settings/test-llm', config),
  testJobSource: (source: string, config: Record<string, unknown>) =>
    api.post<ApiResponse<{ success: boolean; jobs_found: number }>>('/settings/test-source', { source, config }),
}

// Health check
export const healthApi = {
  check: () => api.get<ApiResponse<{ status: string; version: string }>>('/health'),
}

export default api