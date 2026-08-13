import { useState, useCallback, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { JobSearchFormData, Job } from '@/types'
import { useJobSearch, useJobs } from '@/hooks/useApi'
import { useJobSearchStore } from '@/store'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Card, CardContent, CardHeader } from '@/components/ui/Card'
import { Progress } from '@/components/ui/Progress'
import { SearchFilters } from '@/components/job-search/SearchFilters'
import { JobCard } from '@/components/job-search/JobCard'
import { formatNumber } from '@/utils/helpers'
import {
  Search,
  RefreshCw,
  CheckSquare,
  Square,
  Target,
} from 'lucide-react'
import { toast } from 'sonner'

export function JobSearch() {
  const navigate = useNavigate()
  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 20

  const { data: jobsData, isLoading: isLoadingJobs, refetch: refetchJobs, error } = useJobs({
    page: currentPage,
    page_size: pageSize,
  })

  const jobSearchMutation = useJobSearch()
  const { isSearching, searchProgress, searchResults, setSearching, setSearchProgress, setSearchResults } = useJobSearchStore()
  const { selectedJobs, toggleJobSelection, selectAllJobs, clearSelection } = useJobSearchStore()

  const jobs = jobsData?.items || []
  const totalJobs = jobsData?.total || 0
  const totalPages = jobsData?.total_pages || 1

  const handleSearch = useCallback(
    async (data: JobSearchFormData) => {
      setSearching(true)
      setSearchProgress({ current: 0, total: 100, message: 'Initializing search...' })

      try {
        const requestData = {
          filters: {
            keywords: data.keywords ? [data.keywords] : [],
            locations: data.locations,
            job_types: data.job_types as JobSearchFormData['job_types'],
            experience_levels: data.experience_levels as JobSearchFormData['experience_levels'],
            sources: data.sources as JobSearchFormData['sources'],
            remote_only: data.remote_only,
            posted_within_days: data.posted_within_days,
            salary_min: data.salary_min,
            salary_max: data.salary_max,
          },
          max_results_per_source: 50,
          use_cache: false,
        }

        setSearchProgress({ current: 30, total: 100, message: 'Searching job sources...' })

        const response = await jobSearchMutation.mutateAsync(requestData)
        setSearchResults(response.jobs || [])
        setSearchProgress({ current: 100, total: 100, message: 'Search complete!' })
        toast.success(`Found ${response.total_found} jobs from ${response.sources_searched.length} sources`)

        // Select all found jobs by default
        const jobIds = (response.jobs || []).map((j) => j.id)
        selectAllJobs(jobIds)
      } catch (err: any) {
        console.error('Search failed:', err)
        toast.error(err.message || 'Failed to search for jobs')
        setSearchProgress(null)
      } finally {
        setTimeout(() => {
          setSearching(false)
          setSearchProgress(null)
        }, 1000)
      }
    },
    [jobSearchMutation, setSearching, setSearchProgress, setSearchResults, selectAllJobs]
  )

  // Auto-trigger search if the store has pre-filled filters (from profile → jobs flow)
  const autoSearchFired = useRef(false)
  useEffect(() => {
    const storeFilters = useJobSearchStore.getState().filters
    if (autoSearchFired.current || !storeFilters.keywords?.length) return
    autoSearchFired.current = true

    const searchData: JobSearchFormData = {
      keywords: storeFilters.keywords.join(', '),
      locations: storeFilters.locations || [],
      job_types: storeFilters.job_types || [],
      experience_levels: storeFilters.experience_levels || [],
      sources: storeFilters.sources || ['indeed', 'linkedin', 'glassdoor', 'jobbank', 'company_careers'],
      remote_only: storeFilters.remote_only || false,
      posted_within_days: storeFilters.posted_within_days || 7,
      salary_min: storeFilters.salary_min,
      salary_max: storeFilters.salary_max,
    }
    handleSearch(searchData)
  }, [handleSearch])

  const handleSelectAll = () => {
    if (selectedJobs.size === jobs.length && jobs.length > 0) {
      clearSelection()
    } else {
      selectAllJobs(jobs.map((j) => j.id))
    }
  }

  const handleAnalyzeSelected = () => {
    if (selectedJobs.size === 0) {
      toast.warning('Please select at least one job to analyze')
      return
    }
    navigate('/job-matching', { state: { selectedJobs: Array.from(selectedJobs) } })
  }

  const handleAnalyzeSingle = (job: Job) => {
    navigate('/job-matching', { state: { selectedJobs: [job.id] } })
  }

  const isLoading = isLoadingJobs || jobSearchMutation.isPending

  const displayJobs = searchResults.length > 0 ? searchResults : jobs

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Job Search</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Discover and search for jobs across multiple sources
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => refetchJobs()} disabled={isLoading}>
            <RefreshCw className="w-4 h-4 mr-2" /> Refresh Results
          </Button>
          <Button size="sm" onClick={handleAnalyzeSelected} disabled={selectedJobs.size === 0 || isLoading}>
            <Target className="w-4 h-4 mr-2" /> Analyze Selected ({selectedJobs.size})
          </Button>
        </div>
      </div>

      {/* Search Progress */}
      {isSearching && searchProgress && (
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{searchProgress.message}</p>
              <span className="text-sm text-slate-500 dark:text-slate-400">
                {searchProgress.current}/{searchProgress.total}
              </span>
            </div>
            <Progress value={searchProgress.current} max={searchProgress.total} showLabel={false} />
          </CardContent>
        </Card>
      )}

      {/* Search Filters */}
      <SearchFilters onSearch={handleSearch} isSearching={isSearching} />

      {/* Results Summary */}
      {displayJobs.length > 0 && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Showing <strong>{Math.min((currentPage - 1) * pageSize + 1, totalJobs)}</strong> -{' '}
              <strong>{Math.min(currentPage * pageSize, totalJobs)}</strong> of{' '}
              <strong>{formatNumber(totalJobs)}</strong> jobs
            </p>
          </div>
          <div className="flex items-center gap-2">
            {selectedJobs.size > 0 && (
              <Badge variant="primary" className="text-xs">
                {selectedJobs.size} selected
              </Badge>
            )}
            <Button variant="outline" size="sm" onClick={handleSelectAll}>
              {selectedJobs.size === jobs.length && jobs.length > 0 ? (
                <span className="flex items-center gap-1">
                  <Square className="w-4 h-4" /> Clear Selection
                </span>
              ) : (
                <span className="flex items-center gap-1">
                  <CheckSquare className="w-4 h-4" /> Select All
                </span>
              )}
            </Button>
          </div>
        </div>
      )}

      {/* Results Grid */}
      {displayJobs.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {displayJobs.map((job: Job) => (
            <JobCard
              key={job.id}
              job={job}
              isSelected={selectedJobs.has(job.id)}
              onSelect={() => toggleJobSelection(job.id)}
              showMatchScore={job.status === 'MATCHED' || job.status === 'QUALIFIED'}
              matchScore={job.status === 'MATCHED' ? 75 : job.status === 'QUALIFIED' ? 88 : undefined}
              onAnalyze={() => handleAnalyzeSingle(job)}
            />
          ))}
        </div>
      ) : (
        !isLoading && (
          <Card>
            <CardContent className="py-12 text-center">
              <Search className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-2">No jobs found</h3>
              <p className="text-slate-500 dark:text-slate-400 mb-4">
                Adjust your search filters to find more jobs, or try different keywords.
              </p>
              <Button variant="outline" onClick={() => { refetchJobs() }}>
                Try Again
              </Button>
            </CardContent>
          </Card>
        )
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <div className="h-5 bg-slate-200 dark:bg-slate-700 rounded animate-pulse w-3/4" />
                <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded animate-pulse w-1/2 mt-2" />
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
                  <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded animate-pulse w-5/6" />
                  <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded animate-pulse w-3/4" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Error State */}
      {error && (
        <Card className="border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20">
          <CardContent className="py-4">
            <p className="text-red-700 dark:text-red-300">
              Failed to load jobs: {(error as Error).message}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Pagination */}
      {displayJobs.length > 0 && totalPages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t border-slate-200 dark:border-slate-700">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Page {currentPage} of {totalPages}
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage === 1 || isLoading}
              onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage >= totalPages || isLoading}
              onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
