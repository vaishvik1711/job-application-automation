import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Job, JobSearchFilters, MatchWeights, CandidateProfile, ApplicationStatus } from '@/types'

// UI State Store
interface UIState {
  sidebarOpen: boolean
  theme: 'light' | 'dark' | 'system'
  notifications: Array<{ id: string; type: 'success' | 'error' | 'warning' | 'info'; message: string }>
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  setTheme: (theme: 'light' | 'dark' | 'system') => void
  addNotification: (notification: Omit<UIState['notifications'][0], 'id'>) => void
  removeNotification: (id: string) => void
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      theme: 'system',
      notifications: [],
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setTheme: (theme) => set({ theme }),
      addNotification: (notification) =>
        set((state) => ({
          notifications: [...state.notifications, { ...notification, id: Math.random().toString(36).slice(2) }],
        })),
      removeNotification: (id) =>
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        })),
    }),
    {
      name: 'ui-store',
      partialize: (state) => ({ theme: state.theme, sidebarOpen: state.sidebarOpen }),
    }
  )
)

// Job Search Store
interface JobSearchState {
  filters: JobSearchFilters
  selectedJobs: Set<string>
  bookmarkedJobs: string[]
  searchResults: Job[]
  isSearching: boolean
  searchProgress: { current: number; total: number; message: string } | null
  setFilters: (filters: Partial<JobSearchFilters>) => void
  resetFilters: () => void
  toggleJobSelection: (jobId: string) => void
  toggleBookmark: (jobId: string) => void
  selectAllJobs: (jobIds: string[]) => void
  clearSelection: () => void
  setSearchResults: (jobs: Job[]) => void
  setSearching: (searching: boolean) => void
  setSearchProgress: (progress: JobSearchState['searchProgress']) => void
}

const defaultFilters: JobSearchFilters = {
  keywords: [],
  locations: [],
  job_types: [],
  experience_levels: [],
  sources: ['jobbank', 'indeed'],
  remote_only: false,
  posted_within_days: 7,
}

export const useJobSearchStore = create<JobSearchState>()(
  persist(
    (set) => ({
      filters: defaultFilters,
      selectedJobs: new Set(),
      bookmarkedJobs: [],
      searchResults: [],
      isSearching: false,
      searchProgress: null,
      setFilters: (filters) => set((state) => ({ filters: { ...state.filters, ...filters } })),
      resetFilters: () => set({ filters: defaultFilters }),
      toggleJobSelection: (jobId) =>
        set((state) => {
          const newSelection = new Set(state.selectedJobs)
          if (newSelection.has(jobId)) {
            newSelection.delete(jobId)
          } else {
            newSelection.add(jobId)
          }
          return { selectedJobs: newSelection }
        }),
      toggleBookmark: (jobId) =>
        set((state) => ({
          bookmarkedJobs: state.bookmarkedJobs.includes(jobId)
            ? state.bookmarkedJobs.filter((id) => id !== jobId)
            : [...state.bookmarkedJobs, jobId],
        })),
      selectAllJobs: (jobIds) => set({ selectedJobs: new Set(jobIds) }),
      clearSelection: () => set({ selectedJobs: new Set() }),
      setSearchResults: (jobs) => set({ searchResults: jobs }),
      setSearching: (searching) => set({ isSearching: searching }),
      setSearchProgress: (progress) => set({ searchProgress: progress }),
    }),
    {
      name: 'job-search-store',
      partialize: (state) => ({
        filters: state.filters,
        bookmarkedJobs: state.bookmarkedJobs,
      }),
    }
  )
)

// Matching Store
interface MatchingState {
  weights: MatchWeights
  threshold: number
  selectedMatches: Set<string>
  setWeights: (weights: Partial<MatchWeights>) => void
  setThreshold: (threshold: number) => void
  toggleMatchSelection: (matchId: string) => void
  selectAllMatches: (matchIds: string[]) => void
  clearMatchSelection: () => void
}

const defaultWeights: MatchWeights = {
  skills: 0.35,
  experience: 0.25,
  education: 0.15,
  location: 0.1,
  keywords: 0.15,
}

export const useMatchingStore = create<MatchingState>()(
  persist(
    (set) => ({
      weights: defaultWeights,
      threshold: 70,
      selectedMatches: new Set(),
      setWeights: (weights) => set((state) => ({ weights: { ...state.weights, ...weights } })),
      setThreshold: (threshold) => set({ threshold }),
      toggleMatchSelection: (matchId) =>
        set((state) => {
          const newSelection = new Set(state.selectedMatches)
          if (newSelection.has(matchId)) {
            newSelection.delete(matchId)
          } else {
            newSelection.add(matchId)
          }
          return { selectedMatches: newSelection }
        }),
      selectAllMatches: (matchIds) => set({ selectedMatches: new Set(matchIds) }),
      clearMatchSelection: () => set({ selectedMatches: new Set() }),
    }),
    {
      name: 'matching-store',
      partialize: (state) => ({ weights: state.weights, threshold: state.threshold }),
    }
  )
)

// Resume Store
interface ResumeState {
  customizationOptions: {
    templateId: string
    emphasizeSkills: string[]
    emphasizeExperience: string[]
    injectKeywords: string[]
    targetLength: '1_page' | '2_pages' | 'auto'
    format: 'docx' | 'pdf'
  }
  setCustomizationOptions: (options: Partial<ResumeState['customizationOptions']>) => void
  resetCustomizationOptions: () => void
}

const defaultCustomizationOptions = {
  templateId: 'default',
  emphasizeSkills: [],
  emphasizeExperience: [],
  injectKeywords: [],
  targetLength: 'auto' as const,
  format: 'docx' as const,
}

export const useResumeStore = create<ResumeState>()(
  persist(
    (set) => ({
      customizationOptions: defaultCustomizationOptions,
      setCustomizationOptions: (options) =>
        set((state) => ({ customizationOptions: { ...state.customizationOptions, ...options } })),
      resetCustomizationOptions: () => set({ customizationOptions: defaultCustomizationOptions }),
    }),
    {
      name: 'resume-store',
    }
  )
)

// Profile Store
export interface ProfileState {
  profile: CandidateProfile | null
  resumeUploading: boolean
  setProfile: (profile: CandidateProfile | null) => void
  updateProfileField: <K extends keyof CandidateProfile>(field: K, value: CandidateProfile[K]) => void
  setResumeUploading: (uploading: boolean) => void
  resetProfile: () => void
}

export const useProfileStore = create<ProfileState>()(
  persist(
    (set) => ({
      profile: null,
      resumeUploading: false,
      setProfile: (profile) => set({ profile }),
      updateProfileField: (field, value) =>
        set((state) => ({
          profile: state.profile ? { ...state.profile, [field]: value } : null,
        })),
      setResumeUploading: (uploading) => set({ resumeUploading: uploading }),
      resetProfile: () => set({ profile: null }),
    }),
    {
      name: 'profile-store',
      partialize: (state) => ({ profile: state.profile }),
    }
  )
)

// Application Store (Kanban)
interface ApplicationState {
  columns: Record<ApplicationStatus, string[]>
  draggedApplication: string | null
  setColumns: (columns: Record<ApplicationStatus, string[]>) => void
  moveApplication: (applicationId: string, fromStatus: ApplicationStatus, toStatus: ApplicationStatus, index?: number) => void
  setDraggedApplication: (id: string | null) => void
}

const defaultColumns: Record<ApplicationStatus, string[]> = {
  READY_TO_APPLY: [],
  APPLYING: [],
  NEEDS_REVIEW: [],
  SUBMITTED: [],
  INTERVIEW_SCHEDULED: [],
  INTERVIEWED: [],
  OFFER: [],
  FAILED: [],
  REJECTED: [],
  WITHDRAWN: [],
}

export const useApplicationStore = create<ApplicationState>()(
  persist(
    (set) => ({
      columns: defaultColumns,
      draggedApplication: null,
      setColumns: (columns) => set({ columns }),
      moveApplication: (applicationId, fromStatus, toStatus, index) =>
        set((state) => {
          const newColumns = { ...state.columns }
          const fromColumn = [...newColumns[fromStatus]]
          const toColumn = [...newColumns[toStatus]]
          const appIndex = fromColumn.indexOf(applicationId)
          if (appIndex === -1) return state
          fromColumn.splice(appIndex, 1)
          if (index !== undefined && index >= 0 && index <= toColumn.length) {
            toColumn.splice(index, 0, applicationId)
          } else {
            toColumn.push(applicationId)
          }
          return { columns: { ...newColumns, [fromStatus]: fromColumn, [toStatus]: toColumn } }
        }),
      setDraggedApplication: (id) => set({ draggedApplication: id }),
    }),
    {
      name: 'application-store',
      partialize: (state) => ({ columns: state.columns }),
    }
  )
)