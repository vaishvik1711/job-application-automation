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
  salary_min: z.number().optional(),
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
  { value: 'indeed', label: 'Indeed' },
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'glassdoor', label: 'Glassdoor' },
  { value: 'jobbank', label: 'JobBank' },
  { value: 'company_careers', label: 'Company Careers' },
  { value: 'other', label: 'Other' },
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
    salary: false,
  })

  const form = useForm<JobSearchFormData & { locations_input: string }>({
    resolver: zodResolver(searchSchema),
    defaultValues: {
      keywords: filters.keywords?.join(', ') || '',
      locations_input: '',
      job_types: filters.job_types || [],
      experience_levels: filters.experience_levels || [],
      sources: filters.sources || [],
      remote_only: filters.remote_only || false,
      posted_within_days: filters.posted_within_days || 7,
      salary_min: filters.salary_min,
      salary_max: filters.salary_max,
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

  const handleSubmit = (data: JobSearchFormData & { locations_input: string }) => {
    const locations = data.locations_input
      ? data.locations_input
          .split(',')
          .map((l) => l.trim())
          .filter(Boolean)
      : []

    const searchData: JobSearchFormData = {
      keywords: data.keywords || '',
      locations,
      job_types: data.job_types || [],
      experience_levels: data.experience_levels || [],
      sources: data.sources || [],
      remote_only: data.remote_only || false,
      posted_within_days: data.posted_within_days || 7,
      salary_min: data.salary_min,
    }

    onSearch(searchData)
  }

  const handleReset = () => {
    resetFilters()
    form.reset()
    setFilters({})
  }

  const selectedCount = form.watch('job_types')?.length + form.watch('experience_levels')?.length + form.watch('sources')?.length

  return (
    <Card className="mb-6">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Search Filters</CardTitle>
            <CardDescription>Filter jobs by keywords, location, type, and more</CardDescription>
          </div>
          {selectedCount > 0 && (
            <Badge variant="primary" className="text-xs">
              {selectedCount} active filters
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
          {/* Keywords & Locations */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label htmlFor="keywords" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Keywords
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  id="keywords"
                  {...form.register('keywords')}
                  placeholder="e.g., React, Python, product manager"
                  className="pl-10"
                />
              </div>
            </div>
            <div>
              <label htmlFor="locations_input" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Locations
              </label>
              <Input
                id="locations_input"
                {...form.register('locations_input')}
                placeholder="e.g., San Francisco, Remote, New York"
              />
            </div>
            <div>
              <label htmlFor="posted_within_days" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Posted Within
              </label>
              <Select
                id="posted_within_days"
                placeholder="Last 7 days"
                options={POSTED_WITHIN_OPTIONS.map((o) => ({ value: String(o.value), label: o.label }))}
                {...form.register('posted_within_days', { valueAsNumber: true })}
                error={form.formState.errors.posted_within_days?.message}
              />
            </div>
          </div>

          {/* Remote Toggle */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="remote_only"
              {...form.register('remote_only')}
              className="w-4 h-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
            />
            <label htmlFor="remote_only" className="text-sm font-medium text-slate-700 dark:text-slate-300 cursor-pointer">
              Remote only
            </label>
          </div>

          {/* Collapsible Sections */}
          <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-slate-700">
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
                <span className="font-medium text-slate-700 dark:text-slate-300">Experience Level</span>
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
                <div className="px-3 pb-3 grid grid-cols-2 md:grid-cols-6 gap-2">
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

            {/* Salary Range */}
            <div className="border border-slate-200 dark:border-slate-700 rounded-lg">
              <button
                type="button"
                onClick={() => toggleSection('salary')}
                className="w-full flex items-center justify-between p-3 text-left"
              >
                <span className="font-medium text-slate-700 dark:text-slate-300">Minimum Salary</span>
                {collapsedSections.salary ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
              </button>
              {!collapsedSections.salary && (
                <div className="px-3 pb-3">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="salary_min" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Min Salary (optional)
                      </label>
                      <Input
                        id="salary_min"
                        type="number"
                        {...form.register('salary_min', { valueAsNumber: true })}
                        placeholder="e.g. 50000"
                      />
                    </div>
                    <div className="flex items-end">
                      <span className="text-sm text-slate-400 dark:text-slate-500 pb-2">per year</span>
                    </div>
                  </div>
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
