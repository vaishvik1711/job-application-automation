import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Input, Select } from '@/components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { cn } from '@/utils/helpers'
import { JobSearchFormData, JobType, ExperienceLevel, JobSource } from '@/types'
import { Search, X, ChevronDown, ChevronUp } from 'lucide-react'
import { useJobSearchStore } from '@/store'

const searchSchema = z.object({
  keywords: z.string().optional(),
  locations: z.array(z.string()).optional(),
  job_types: z.array(z.string()).optional(),
  experience_levels: z.array(z.string()).optional(),
  sources: z.array(z.string()).optional(),
  remote_only: z.boolean().optional(),
  posted_within_days: z.number().optional(),
})

const JOB_TYPE_OPTIONS: { value: JobType; label: string }[] = [
  { value: 'full_time', label: 'Full Time' },
  { value: 'part_time', label: 'Part Time' },
  { value: 'contract', label: 'Contract' },
  { value: 'internship', label: 'Internship' },
  { value: 'temporary', label: 'Temporary' },
]

const EXPERIENCE_LEVEL_OPTIONS: { value: ExperienceLevel; label: string }[] = [
  { value: 'entry', label: 'Entry Level' },
  { value: 'mid', label: 'Mid Level' },
  { value: 'senior', label: 'Senior Level' },
  { value: 'lead', label: 'Lead / Principal' },
  { value: 'executive', label: 'Executive' },
]

const JOB_SOURCE_OPTIONS: { value: JobSource; label: string }[] = [
  { value: 'linkedin', label: 'LinkedIn (Stealth Scraper)' },
  { value: 'jobbank', label: 'JobBank (Gov. Canada)' },
  { value: 'indeed', label: 'Indeed (Scraper)' },
]

const POSTED_WITHIN_OPTIONS = [
  { value: 1, label: 'Last 24 hours' },
  { value: 3, label: 'Last 3 days' },
  { value: 7, label: 'Last 7 days' },
  { value: 14, label: 'Last 14 days' },
  { value: 30, label: 'Last 30 days' },
]

interface SearchFiltersProps {
  onSearch: (data: JobSearchFormData) => void
  isSearching: boolean
}

export function SearchFilters({ onSearch, isSearching }: SearchFiltersProps) {
  const { filters, setFilters, resetFilters } = useJobSearchStore()
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({
    jobTypes: false,
    experience: false,
    sources: false,
  })

  const form = useForm<JobSearchFormData & { locations_input: string }>({
    resolver: zodResolver(searchSchema),
    defaultValues: {
      keywords: filters.keywords?.join(', ') || '',
      locations_input: filters.locations?.join(', ') || 'Ontario, Canada',
      job_types: filters.job_types || [],
      experience_levels: filters.experience_levels || [],
      sources: filters.sources || ['linkedin', 'jobbank', 'indeed'],
      remote_only: filters.remote_only || false,
      posted_within_days: filters.posted_within_days || 7,
    },
  })

  const toggleSection = (section: string) => {
    setCollapsedSections((prev) => ({ ...prev, [section]: !prev[section] }))
  }

  const toggleSelection = (field: 'job_types' | 'experience_levels' | 'sources', value: string) => {
    const current = form.getValues(field) as string[]
    const updated = current.includes(value) ? current.filter((v) => v !== value) : [...current, value]
    form.setValue(field, updated as any)
  }

  const handleSubmit = (data: {
    keywords?: string
    locations_input?: string
    job_types?: string[]
    experience_levels?: string[]
    sources?: string[]
    remote_only?: boolean
    posted_within_days?: number
  }) => {
    const locations = data.locations_input
      ? data.locations_input
          .split(',')
          .map((l) => l.trim())
          .filter(Boolean)
      : ['Ontario, Canada']

    const keywordsStr = data.keywords || ''
    const keywordsArray = keywordsStr
      .split(',')
      .map((k) => k.trim())
      .filter(Boolean)

    const formData: JobSearchFormData = {
      keywords: keywordsStr,
      locations,
      job_types: (data.job_types || []) as any,
      experience_levels: (data.experience_levels || []) as any,
      sources: (data.sources || ['linkedin', 'jobbank', 'indeed']) as any,
      remote_only: data.remote_only || false,
      posted_within_days: data.posted_within_days || 7,
    }

    setFilters({
      keywords: keywordsArray,
      locations,
      job_types: (data.job_types || []) as any,
      experience_levels: (data.experience_levels || []) as any,
      sources: (data.sources || ['linkedin', 'jobbank', 'indeed']) as any,
      remote_only: data.remote_only,
      posted_within_days: data.posted_within_days,
    })

    onSearch(formData)
  }

  const handleReset = () => {
    resetFilters()
    form.reset({
      keywords: '',
      locations_input: 'Ontario, Canada',
      job_types: [],
      experience_levels: [],
      sources: ['linkedin', 'jobbank', 'indeed'],
      remote_only: false,
      posted_within_days: 7,
    })
  }

  return (
    <Card className="mb-6 border-slate-200 dark:border-slate-800 shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Search className="w-5 h-5 text-primary-500" />
              Job Search & Anti-Blocking Filters
            </CardTitle>
            <CardDescription className="text-xs text-slate-500 mt-0.5">
              Target fresh postings across Ontario, Canada with stealth anti-detection
            </CardDescription>
          </div>
          <Badge variant="neutral" className="text-xs font-normal">
            Ontario, Canada
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
          {/* Row 1: Keywords & Location */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="keywords" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Job Titles / Keywords
              </label>
              <Input
                id="keywords"
                {...form.register('keywords')}
                placeholder="e.g. Data Analyst, Business Analyst"
              />
            </div>
            <div>
              <label htmlFor="locations_input" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Locations
              </label>
              <Input
                id="locations_input"
                {...form.register('locations_input')}
                placeholder="Ontario, Canada"
              />
            </div>
          </div>

          {/* Row 2: Date Posted & Remote Toggle */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
            <div>
              <label htmlFor="posted_within_days" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Posting Freshness
              </label>
              <Select
                id="posted_within_days"
                {...form.register('posted_within_days', { valueAsNumber: true })}
                options={POSTED_WITHIN_OPTIONS.map((o) => ({ value: String(o.value), label: o.label }))}
              />
            </div>
            <div className="flex items-center gap-2 pt-6">
              <input
                type="checkbox"
                id="remote_only"
                {...form.register('remote_only')}
                className="w-4 h-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
              />
              <label htmlFor="remote_only" className="text-sm font-medium text-slate-700 dark:text-slate-300 cursor-pointer">
                Remote & Hybrid Only
              </label>
            </div>
          </div>

          {/* Collapsible Sections */}
          <div className="space-y-3 pt-2">
            {/* Job Types */}
            <div className="border border-slate-200 dark:border-slate-700 rounded-lg">
              <button
                type="button"
                onClick={() => toggleSection('jobTypes')}
                className="w-full flex items-center justify-between p-3 text-left"
              >
                <span className="font-medium text-slate-700 dark:text-slate-300">Job Types</span>
                {collapsedSections.jobTypes ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
              </button>
              {!collapsedSections.jobTypes && (
                <div className="px-3 pb-3 grid grid-cols-2 md:grid-cols-5 gap-2">
                  {JOB_TYPE_OPTIONS.map((opt) => {
                    const selected = form.watch('job_types')?.includes(opt.value)
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => toggleSelection('job_types', opt.value)}
                        className={cn(
                          'px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
                          selected
                            ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 border-primary-300'
                            : 'bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700 hover:bg-slate-100'
                        )}
                      >
                        {opt.label}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Experience Levels */}
            <div className="border border-slate-200 dark:border-slate-700 rounded-lg">
              <button
                type="button"
                onClick={() => toggleSection('experience')}
                className="w-full flex items-center justify-between p-3 text-left"
              >
                <span className="font-medium text-slate-700 dark:text-slate-300">Experience Levels</span>
                {collapsedSections.experience ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
              </button>
              {!collapsedSections.experience && (
                <div className="px-3 pb-3 grid grid-cols-2 md:grid-cols-5 gap-2">
                  {EXPERIENCE_LEVEL_OPTIONS.map((opt) => {
                    const selected = form.watch('experience_levels')?.includes(opt.value)
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => toggleSelection('experience_levels', opt.value)}
                        className={cn(
                          'px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
                          selected
                            ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 border-primary-300'
                            : 'bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700 hover:bg-slate-100'
                        )}
                      >
                        {opt.label}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Sources */}
            <div className="border border-slate-200 dark:border-slate-700 rounded-lg">
              <button
                type="button"
                onClick={() => toggleSection('sources')}
                className="w-full flex items-center justify-between p-3 text-left"
              >
                <span className="font-medium text-slate-700 dark:text-slate-300">Job Sources</span>
                {collapsedSections.sources ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
              </button>
              {!collapsedSections.sources && (
                <div className="px-3 pb-3 grid grid-cols-2 md:grid-cols-3 gap-2">
                  {JOB_SOURCE_OPTIONS.map((opt) => {
                    const selected = form.watch('sources')?.includes(opt.value)
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => toggleSelection('sources', opt.value)}
                        className={cn(
                          'px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
                          selected
                            ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 border-primary-300'
                            : 'bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700 hover:bg-slate-100'
                        )}
                      >
                        {opt.label}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Form Actions */}
          <div className="flex items-center justify-between pt-2 border-t border-slate-200 dark:border-slate-700">
            <Button type="button" variant="outline" size="sm" onClick={handleReset}>
              <X className="w-4 h-4 mr-2" /> Reset Filters
            </Button>
            <Button type="submit" loading={isSearching} size="sm">
              <Search className="w-4 h-4 mr-2" />
              {isSearching ? 'Searching...' : 'Search Jobs'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
