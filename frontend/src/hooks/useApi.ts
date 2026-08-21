import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { profileApi, jobsApi, matchingApi, resumesApi, applicationsApi, analyticsApi, settingsApi, credentialsApi } from '@/services/api'
import type {
  CandidateProfile,
  JobSearchRequest,
  MatchWeights,
  ResumeCustomizationOptions,
  ApplicationStatus,
  AppSettings,
  BatchGenerateRequest,
  ApplyMode,
  ApplyStatusInfo,
} from '@/types'

// Query Keys
export const queryKeys = {
  profile: ['profile'] as const,
  jobs: (params?: Record<string, unknown>) => ['jobs', params] as const,
  job: (id: string) => ['jobs', id] as const,
  matches: (params?: Record<string, unknown>) => ['matches', params] as const,
  match: (id: string) => ['matches', id] as const,
  resumes: (params?: Record<string, unknown>) => ['resumes', params] as const,
  resume: (id: string) => ['resumes', id] as const,
  applications: (params?: Record<string, unknown>) => ['applications', params] as const,
  application: (id: string) => ['applications', id] as const,
  analytics: {
    overview: ['analytics', 'overview'] as const,
    pipeline: ['analytics', 'pipeline'] as const,
    sources: ['analytics', 'sources'] as const,
    skillGaps: ['analytics', 'skill-gaps'] as const,
    timeSeries: (days: number) => ['analytics', 'timeseries', days] as const,
  },
  settings: ['settings'] as const,
  credentials: ['credentials'] as const,
  applyStatus: (id: string) => ['applications', id, 'apply-status'] as const,
  matching: {
    weights: ['matching', 'weights'] as const,
    threshold: ['matching', 'threshold'] as const,
  },
} as const

// Profile Hooks
export function useProfile() {
  return useQuery({
    queryKey: queryKeys.profile,
    queryFn: () => profileApi.get().then((res) => res.data.data),
  })
}

export function useUploadResume() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ file, onProgress }: { file: File; onProgress?: (p: number) => void }) =>
      profileApi.uploadResume(file, onProgress).then((res) => res.data.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.profile })
    },
  })
}

export function useUpdateProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<CandidateProfile>) => profileApi.update(data).then((res) => res.data.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.profile })
    },
  })
}

// Jobs Hooks
export function useJobs(params?: { page?: number; page_size?: number; status?: string; search?: string }) {
  return useQuery({
    queryKey: queryKeys.jobs(params),
    queryFn: () => jobsApi.list(params).then((res) => res.data.data),
  })
}

export function useJob(id: string) {
  return useQuery({
    queryKey: queryKeys.job(id),
    queryFn: () => jobsApi.get(id).then((res) => res.data.data),
    enabled: !!id,
  })
}

export function useJobSearch() {
  return useMutation({
    mutationFn: (request: JobSearchRequest) => jobsApi.search(request).then((res) => res.data.data),
  })
}

export function useJobStats() {
  return useQuery({
    queryKey: ['jobs', 'stats'],
    queryFn: () => jobsApi.getStats().then((res) => res.data.data),
  })
}

export function useAnalyzeJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, weights }: { id: string; weights?: MatchWeights }) =>
      jobsApi.analyze(id, weights).then((res) => res.data.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.matches() })
      queryClient.invalidateQueries({ queryKey: queryKeys.jobs() })
    },
  })
}

export function useBatchAnalyzeJobs() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ jobIds, weights }: { jobIds: string[]; weights?: MatchWeights }) =>
      jobsApi.batchAnalyze(jobIds, weights).then((res) => res.data.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.matches() })
      queryClient.invalidateQueries({ queryKey: queryKeys.jobs() })
    },
  })
}

export function useExportJobs() {
  return useMutation({
    mutationFn: ({ jobIds, format }: { jobIds?: string[]; format?: 'csv' | 'excel' }) =>
      jobsApi.export(jobIds, format),
  })
}

// Matches Hooks
export function useMatches(params?: { page?: number; page_size?: number; verdict?: string; min_score?: number }) {
  return useQuery({
    queryKey: queryKeys.matches(params),
    queryFn: () => jobsApi.getMatches(params).then((res) => res.data.data),
  })
}

// Matching Settings Hooks
export function useMatchingWeights() {
  return useQuery({
    queryKey: queryKeys.matching.weights,
    queryFn: () => matchingApi.getWeights().then((res) => res.data.data),
  })
}

export function useUpdateMatchingWeights() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (weights: MatchWeights) => matchingApi.updateWeights(weights).then((res) => res.data.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.matching.weights })
    },
  })
}

export function useMatchingThreshold() {
  return useQuery({
    queryKey: queryKeys.matching.threshold,
    queryFn: () => matchingApi.getThreshold().then((res) => res.data.data.threshold),
  })
}

export function useUpdateMatchingThreshold() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (threshold: number) => matchingApi.updateThreshold(threshold).then((res) => res.data.data.threshold),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.matching.threshold })
    },
  })
}

// Resumes Hooks
export function useResumes(params?: { page?: number; page_size?: number }) {
  return useQuery({
    queryKey: queryKeys.resumes(params),
    queryFn: () => resumesApi.list(params).then((res) => res.data.data),
  })
}

export function useResume(id: string) {
  return useQuery({
    queryKey: queryKeys.resume(id),
    queryFn: () => resumesApi.get(id).then((res) => res.data.data),
    enabled: !!id,
  })
}

export function useGenerateResume() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (options: ResumeCustomizationOptions) => resumesApi.generate(options).then((res) => res.data.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.resumes() })
    },
  })
}

export function useBatchGenerateResumes() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: BatchGenerateRequest) =>
      resumesApi.batchGenerate(data).then((res) => res.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.applications() })
      queryClient.invalidateQueries({ queryKey: queryKeys.resumes() })
    },
  })
}

export function useValidateResume() {
  return useMutation({
    mutationFn: (id: string) => resumesApi.validate(id).then((res) => res.data.data),
  })
}

export function useDownloadResume() {
  return useMutation({
    mutationFn: ({ id, format }: { id: string; format?: 'docx' | 'pdf' }) =>
      resumesApi.download(id, format),
  })
}

export function useResumeTemplates() {
  return useQuery({
    queryKey: ['resumes', 'templates'],
    queryFn: () => resumesApi.getTemplates().then((res) => res.data.data.templates),
  })
}

// Applications Hooks
export function useApplications(params?: { page?: number; page_size?: number; status?: ApplicationStatus }) {
  return useQuery({
    queryKey: queryKeys.applications(params),
    queryFn: () => applicationsApi.list(params).then((res) => res.data.data),
  })
}

export function useApplication(id: string) {
  return useQuery({
    queryKey: queryKeys.application(id),
    queryFn: () => applicationsApi.get(id).then((res) => res.data.data),
    enabled: !!id,
  })
}

export function useCreateApplication() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: { job_id: string; resume_id: string; cover_letter?: string }) =>
      applicationsApi.create(data).then((res) => res.data.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.applications() })
    },
  })
}

export function useUpdateApplicationStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status, notes }: { id: string; status: ApplicationStatus; notes?: string }) =>
      applicationsApi.updateStatus(id, status, notes).then((res) => res.data.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.applications() })
    },
  })
}

export function useBulkUpdateApplicationStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ ids, status }: { ids: string[]; status: ApplicationStatus }) =>
      applicationsApi.bulkUpdateStatus(ids, status).then((res) => res.data.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.applications() })
    },
  })
}

// Delete Application Hook
export function useDeleteApplication() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => applicationsApi.delete(id).then((res) => res.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.applications() })
    },
  })
}

// Auto-apply hooks
export function useApplyToJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, mode }: { id: string; mode?: ApplyMode }) =>
      applicationsApi.startApply(id, mode ?? 'manual').then((res) => res.data.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.applications() })
    },
  })
}

export function useApplyStatus(id: string | null) {
  return useQuery({
    queryKey: ['applications', id, 'apply-status'] as const,
    queryFn: () => applicationsApi.applyStatus(id!).then((res) => res.data.data),
    enabled: !!id,
    // Poll while the run is live so the UI flips to review/failed promptly.
    refetchInterval: (query) => {
      const data = query.state.data as ApplyStatusInfo | undefined
      if (data && (data.running || (!data.parked && data.status === 'APPLYING'))) return 3000
      return false
    },
  })
}

export function useConfirmSubmit() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => applicationsApi.confirmSubmit(id).then((res) => res.data.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.applications() })
    },
  })
}

export function useCancelApply() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => applicationsApi.cancelApply(id).then((res) => res.data.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.applications() })
    },
  })
}

// Credentials hooks (job-site logins)
export function useCredentials() {
  return useQuery({
    queryKey: queryKeys.credentials,
    queryFn: () => credentialsApi.list().then((res) => res.data.data),
  })
}

export function useSaveCredential() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ site, ...data }: { site: string; username?: string; password?: string }) =>
      credentialsApi.save(site, data).then((res) => res.data.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.credentials })
    },
  })
}

export function useDeleteCredential() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (site: string) => credentialsApi.remove(site).then((res) => res.data.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.credentials })
    },
  })
}

// Analytics Hooks
export function useAnalyticsOverview() {
  return useQuery({
    queryKey: queryKeys.analytics.overview,
    queryFn: () => analyticsApi.getOverview().then((res) => res.data.data),
  })
}

export function usePipelineStats() {
  return useQuery({
    queryKey: queryKeys.analytics.pipeline,
    queryFn: () => analyticsApi.getPipeline().then((res) => res.data.data),
  })
}

export function useSourceEffectiveness() {
  return useQuery({
    queryKey: queryKeys.analytics.sources,
    queryFn: () => analyticsApi.getSourceEffectiveness().then((res) => res.data.data),
  })
}

export function useSkillGaps() {
  return useQuery({
    queryKey: queryKeys.analytics.skillGaps,
    queryFn: () => analyticsApi.getSkillGaps().then((res) => res.data.data),
  })
}

export function useTimeSeries(days: number = 30) {
  return useQuery({
    queryKey: queryKeys.analytics.timeSeries(days),
    queryFn: () => analyticsApi.getTimeSeries(days).then((res) => res.data.data),
  })
}

// Settings Hooks
export function useSettings() {
  return useQuery({
    queryKey: queryKeys.settings,
    queryFn: () => settingsApi.get().then((res) => res.data.data),
  })
}

export function useUpdateSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (settings: Partial<AppSettings>) => settingsApi.update(settings).then((res) => res.data.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.settings })
    },
  })
}

export function useTestLLM() {
  return useMutation({
    mutationFn: (config: { provider: string; model: string; api_key?: string }) =>
      settingsApi.testLLM(config).then((res) => res.data.data),
  })
}

export function useTestJobSource() {
  return useMutation({
    mutationFn: ({ source, config }: { source: string; config: Record<string, unknown> }) =>
      settingsApi.testJobSource(source, config).then((res) => res.data.data),
  })
}