import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useJobSearch, useBatchGenerateResumes, useMatches, useProfile, useResumes } from '@/hooks/useApi'
import { useJobSearchStore } from '@/store'
import { JobCard } from '@/components/job-search/JobCard'
import { SearchFilters } from '@/components/job-search/SearchFilters'
import { MatchDetailModal } from '@/components/job-matching/MatchDetailModal'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Progress } from '@/components/ui/Progress'
import { Badge } from '@/components/ui/Badge'
import {
  Search,
  Sparkles,
  CheckCircle,
  Loader2,
  ArrowRight,
  RefreshCw,
  FileText,
  Download,
  Filter,
  Sliders,
  Bookmark,
  ArrowUpDown,
  X,
} from 'lucide-react'
import { downloadResume } from '@/utils/download'
import { cn } from '@/utils/helpers'
import { toast } from 'sonner'
import type { MatchDetail, JobSearchFormData } from '@/types'

export function Jobs() {
  const navigate = useNavigate()
  const { data: profile } = useProfile()
  const { data: matchesData, isLoading: isLoadingMatches, refetch: refetchMatches } = useMatches({ page_size: 100 })
  const { data: resumesData, refetch: refetchResumes } = useResumes({ page: 1, page_size: 12 })
  const jobSearch = useJobSearch()
  const batchGenerate = useBatchGenerateResumes()

  const { selectedJobs, toggleJobSelection, clearSelection, bookmarkedJobs } = useJobSearchStore()

  const [showFilters, setShowFilters] = useState(false)
  const [isSearching, setIsSearching] = useState(false)
  const [searchProgress, setSearchProgress] = useState<string | null>(null)
  const [matches, setMatches] = useState<MatchDetail[]>([])
  const [threshold, setThreshold] = useState<number>(0)
  const [sortBy, setSortBy] = useState<'match_score' | 'posted_date' | 'company'>('match_score')
  const [onlyBookmarked, setOnlyBookmarked] = useState(false)
  const [inspectingMatch, setInspectingMatch] = useState<MatchDetail | null>(null)

  const [batchProgress, setBatchProgress] = useState<{
    total: number
    current: number
    succeeded: number
    failed: number
    message: string
    isRunning: boolean
  } | null>(null)

  // Sync matches data when query resolves
  useEffect(() => {
    if (matchesData?.items) {
      setMatches(matchesData.items)
    }
  }, [matchesData])

  // Custom search handler from SearchFilters
  const handleSearchWithFilters = useCallback(
    async (data: JobSearchFormData) => {
      if (!profile) {
        toast.error('Please upload your resume first on the Dashboard')
        return
      }

      setIsSearching(true)
      setSearchProgress('Searching job sources and analyzing matches...')

      try {
        const keywordsArray = typeof data.keywords === 'string'
          ? data.keywords.split(',').map((k) => k.trim()).filter(Boolean)
          : data.keywords || []

        await jobSearch.mutateAsync({
          filters: {
            keywords: keywordsArray.length > 0
              ? keywordsArray
              : profile.skills?.slice(0, 10).map((s) => s.name) || [],
            locations: data.locations?.length
              ? data.locations
              : profile.personal_info?.location ? [profile.personal_info.location] : [],
            job_types: data.job_types?.length ? data.job_types : ['full_time', 'contract'],
            remote_only: data.remote_only || false,
            posted_within_days: data.posted_within_days || 30,
            sources: data.sources?.length ? data.sources : ['jobbank'],
            salary_min: data.salary_min,
          },
          max_results_per_source: 50,
        })

        setSearchProgress('Matching jobs against candidate profile...')
        setTimeout(async () => {
          await refetchMatches()
          setIsSearching(false)
          setSearchProgress(null)
          setShowFilters(false)
          toast.success('Job search complete! Matches updated.')
        }, 2000)
      } catch (err: any) {
        console.error('Search failed:', err)
        toast.error(err?.message || 'Search failed')
        setIsSearching(false)
        setSearchProgress(null)
      }
    },
    [profile, jobSearch, refetchMatches]
  )

  // Default quick search using profile
  const handleQuickSearch = useCallback(() => {
    if (!profile) {
      toast.error('Please upload your resume first on the Dashboard')
      return
    }
    handleSearchWithFilters({
      keywords: profile.skills?.slice(0, 10).map((s) => s.name).join(', ') || '',
      locations: profile.personal_info?.location ? [profile.personal_info.location] : [],
      job_types: ['full_time', 'contract'],
      experience_levels: [],
      remote_only: false,
      posted_within_days: 30,
      sources: ['jobbank'],
    })
  }, [profile, handleSearchWithFilters])

  // Batch resume generation
  const handleBatchGenerate = useCallback(async () => {
    if (selectedJobs.size === 0) {
      toast.error('Select at least one job')
      return
    }

    const jobIds = Array.from(selectedJobs)
    setBatchProgress({
      total: jobIds.length,
      current: 0,
      succeeded: 0,
      failed: 0,
      message: 'Starting tailored resume generation...',
      isRunning: true,
    })

    try {
      const result = await batchGenerate.mutateAsync({
        job_ids: jobIds,
        auto_apply: true,
      })

      setBatchProgress({
        total: jobIds.length,
        current: jobIds.length,
        succeeded: result.succeeded,
        failed: result.failed,
        message: `Generated: ${result.succeeded} tailored resume${result.succeeded !== 1 ? 's' : ''}`,
        isRunning: false,
      })

      if (result.succeeded > 0) {
        toast.success(`${result.succeeded} resumes generated and applications created!`, {
          action: {
            label: 'View in Kanban',
            onClick: () => navigate('/applications'),
          },
        })
        clearSelection()
        refetchMatches()
        refetchResumes()
      }

      if (result.failed > 0) {
        toast.error(`${result.failed} job resumes could not be generated.`)
      }
    } catch (err: any) {
      console.error('Batch generation failed:', err)
      toast.error(err?.message || 'Batch generation failed')
      setBatchProgress((prev) => (prev ? { ...prev, isRunning: false, message: 'Failed' } : null))
    }
  }, [selectedJobs, batchGenerate, navigate, clearSelection, refetchMatches, refetchResumes])

  // Filter and sort matches
  const filteredAndSortedMatches = useMemo(() => {
    let result = matches.filter((m) => {
      const score = Math.round(m.score?.overall || 0)
      if (score < threshold) return false
      if (onlyBookmarked && !bookmarkedJobs.includes(m.job_id)) return false
      return true
    })

    result.sort((a, b) => {
      if (sortBy === 'match_score') {
        return (b.score?.overall || 0) - (a.score?.overall || 0)
      }
      if (sortBy === 'posted_date') {
        return new Date(b.job?.posted_date || 0).getTime() - new Date(a.job?.posted_date || 0).getTime()
      }
      if (sortBy === 'company') {
        return (a.job?.company || '').localeCompare(b.job?.company || '')
      }
      return 0
    })

    return result
  }, [matches, threshold, onlyBookmarked, bookmarkedJobs, sortBy])

  const isFirstVisit = !isSearching && !isLoadingMatches && matches.length === 0 && !profile

  return (
    <div className="space-y-6 animate-in">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Discover & Match Jobs</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            {profile
              ? `Showing AI-scored opportunities matching ${profile.personal_info?.full_name || 'your profile'}`
              : 'Upload your resume to discover and score tailored job opportunities'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters((prev) => !prev)}
            className={cn(showFilters && 'border-primary-500 text-primary-600 bg-primary-50 dark:bg-primary-900/20')}
          >
            <Filter className="w-4 h-4 mr-1.5" />
            {showFilters ? 'Hide Filters' : 'Search Filters'}
          </Button>

          {matches.length > 0 && (
            <Button variant="outline" size="sm" onClick={() => refetchMatches()}>
              <RefreshCw className="w-4 h-4 mr-1.5" /> Refresh
            </Button>
          )}

          <Button onClick={handleQuickSearch} disabled={isSearching || !profile} size="sm">
            {isSearching ? (
              <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />
            ) : (
              <Search className="w-4 h-4 mr-1.5" />
            )}
            {isSearching ? 'Searching...' : 'Search Jobs'}
          </Button>
        </div>
      </div>

      {/* Collapsible Search Filters */}
      {showFilters && (
        <div className="animate-in fade-in duration-200">
          <SearchFilters onSearch={handleSearchWithFilters} isSearching={isSearching} />
        </div>
      )}

      {/* Search Progress */}
      {isSearching && searchProgress && (
        <Card className="border-primary-200 dark:border-primary-800 bg-primary-50/50 dark:bg-primary-900/10">
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <Loader2 className="w-5 h-5 animate-spin text-primary-500" />
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{searchProgress}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* First visit — prompt to upload resume */}
      {isFirstVisit && (
        <Card>
          <CardContent className="py-12 text-center">
            <Search className="w-16 h-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-2">
              No Profile Found
            </h2>
            <p className="text-slate-500 dark:text-slate-400 max-w-lg mx-auto mb-6">
              Start by uploading your resume on the Dashboard. We'll parse it, find matching jobs,
              and let you generate tailored resumes in bulk.
            </p>
            <Button onClick={() => navigate('/dashboard')}>
              <ArrowRight className="w-4 h-4 mr-2" /> Go to Dashboard
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Empty state — profile exists but no results yet */}
      {profile && !isSearching && !isLoadingMatches && matches.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <Search className="w-16 h-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-2">
              No Jobs Discovered Yet
            </h2>
            <p className="text-slate-500 dark:text-slate-400 max-w-lg mx-auto mb-6">
              Click "Search Jobs" to scan job boards for postings that match your skills, or open Search Filters to customize keywords and location.
            </p>
            <div className="flex items-center justify-center gap-3">
              <Button onClick={handleQuickSearch} disabled={isSearching}>
                <Search className="w-4 h-4 mr-2" /> Quick Search
              </Button>
              <Button variant="outline" onClick={() => setShowFilters(true)}>
                <Filter className="w-4 h-4 mr-2" /> Custom Filters
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Controls Bar: Threshold Slider, Sort By, Bookmarks, and Selection */}
      {!isLoadingMatches && matches.length > 0 && (
        <Card className="border border-slate-200 dark:border-slate-800">
          <CardContent className="py-3 px-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              {/* Threshold Slider */}
              <div className="flex items-center gap-3 flex-1 max-w-md">
                <div className="flex items-center gap-1.5 min-w-fit text-xs font-medium text-slate-600 dark:text-slate-400">
                  <Sliders className="w-3.5 h-3.5" />
                  <span>Min Match Fit:</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={90}
                  step={5}
                  value={threshold}
                  onChange={(e) => setThreshold(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
                />
                <span className="text-xs font-bold text-primary-600 dark:text-primary-400 min-w-[2.5rem] text-right">
                  {threshold}%+
                </span>
              </div>

              {/* Sorting & Filter Toggles */}
              <div className="flex flex-wrap items-center gap-2">
                <div className="flex items-center gap-1.5 bg-slate-100 dark:bg-slate-800 rounded-lg p-1 text-xs">
                  <ArrowUpDown className="w-3.5 h-3.5 text-slate-400 ml-1.5" />
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as any)}
                    className="bg-transparent border-0 text-xs font-medium text-slate-700 dark:text-slate-300 pr-2 focus:ring-0 cursor-pointer"
                  >
                    <option value="match_score">Highest Fit Score</option>
                    <option value="posted_date">Newest Posted</option>
                    <option value="company">Company (A-Z)</option>
                  </select>
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setOnlyBookmarked((prev) => !prev)}
                  className={cn(
                    'text-xs h-8',
                    onlyBookmarked && 'border-primary-500 bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                  )}
                >
                  <Bookmark className="w-3.5 h-3.5 mr-1" />
                  Saved ({bookmarkedJobs.length})
                </Button>

                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs h-8"
                  onClick={() => {
                    const allIds = filteredAndSortedMatches.map((m) => m.job_id)
                    allIds.forEach((id) => {
                      if (!selectedJobs.has(id)) toggleJobSelection(id)
                    })
                  }}
                >
                  Select Visible ({filteredAndSortedMatches.length})
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Batch Progress */}
      {batchProgress && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center justify-between">
              <span className="flex items-center gap-2">
                {batchProgress.isRunning ? (
                  <Loader2 className="w-5 h-5 animate-spin text-primary-500" />
                ) : (
                  <CheckCircle className="w-5 h-5 text-green-500" />
                )}
                {batchProgress.isRunning ? 'Generating Tailored Resumes...' : 'Batch Generation Complete'}
              </span>
              {!batchProgress.isRunning && (
                <Button variant="ghost" size="sm" onClick={() => setBatchProgress(null)}>
                  <X className="w-4 h-4" />
                </Button>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">{batchProgress.message}</span>
                <span className="font-medium">
                  {batchProgress.current}/{batchProgress.total}
                </span>
              </div>
              <Progress value={batchProgress.current} max={batchProgress.total} />
              <div className="flex items-center justify-between text-sm pt-1">
                <div className="flex gap-4">
                  <span className="text-green-600 dark:text-green-400 font-medium">
                    ✓ {batchProgress.succeeded} created
                  </span>
                  {batchProgress.failed > 0 && (
                    <span className="text-red-600 dark:text-red-400">
                      ✗ {batchProgress.failed} failed
                    </span>
                  )}
                </div>
                {batchProgress.succeeded > 0 && (
                  <Button size="sm" onClick={() => navigate('/applications')}>
                    <span>Open Application Kanban</span>
                    <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sticky Selection Action Bar */}
      {selectedJobs.size > 0 && (
        <Card className="sticky top-20 z-30 border-primary-400 dark:border-primary-600 shadow-xl bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm">
          <CardContent className="py-3 px-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <Badge variant="primary" className="text-sm px-3 py-1 font-semibold">
                  {selectedJobs.size} selected
                </Badge>
                <span className="text-xs text-slate-500 dark:text-slate-400 hidden sm:inline">
                  AI will customize your resume for each target role and queue applications
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={clearSelection}>
                  Clear
                </Button>
                <Button
                  onClick={handleBatchGenerate}
                  disabled={batchGenerate.isPending}
                  size="sm"
                >
                  {batchGenerate.isPending ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4 mr-2" />
                  )}
                  {batchGenerate.isPending
                    ? 'Generating...'
                    : `Generate Resumes (${selectedJobs.size})`}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading Skeleton */}
      {isLoadingMatches && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-44 bg-slate-200 dark:bg-slate-800 rounded-xl animate-pulse" />
          ))}
        </div>
      )}

      {/* Matched Jobs Grid */}
      {!isLoadingMatches && filteredAndSortedMatches.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>
              Showing <strong>{filteredAndSortedMatches.length}</strong> of{' '}
              <strong>{matches.length}</strong> matched opportunities
            </span>
            {threshold > 0 && (
              <span className="text-primary-600 dark:text-primary-400">
                Filtered by $\ge${threshold}% fit
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {filteredAndSortedMatches.map((match) => (
              <JobCard
                key={match.job_id}
                job={match.job}
                isSelected={selectedJobs.has(match.job_id)}
                onSelect={() => toggleJobSelection(match.job_id)}
                showMatchScore
                matchScore={match.score?.overall}
                onInspectMatch={() => setInspectingMatch(match)}
              />
            ))}
          </div>
        </div>
      )}

      {/* No jobs matching current threshold filter */}
      {!isLoadingMatches && matches.length > 0 && filteredAndSortedMatches.length === 0 && (
        <Card>
          <CardContent className="py-10 text-center">
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">
              No jobs meet your current filter of <strong>{threshold}%+ fit</strong>
              {onlyBookmarked ? ' and saved status' : ''}.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setThreshold(0)
                setOnlyBookmarked(false)
              }}
            >
              Reset Filters
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Generated Resumes Library */}
      {resumesData?.items && resumesData.items.length > 0 && (
        <Card className="border border-slate-200 dark:border-slate-800">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <FileText className="w-5 h-5 text-primary-500" />
                Tailored Resumes Library ({resumesData.total ?? resumesData.items.length})
              </CardTitle>
              <Button variant="ghost" size="sm" onClick={() => refetchResumes()} className="text-xs">
                <RefreshCw className="w-3.5 h-3.5 mr-1" /> Refresh
              </Button>
            </div>
            <CardDescription className="text-xs">
              AI-generated ATS-optimized resumes customized for your matched roles
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {resumesData.items.map((r) => (
                <button
                  key={r.id}
                  onClick={() => downloadResume(r.id, r.job_title)}
                  className="group flex items-center justify-between gap-2 rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2.5 text-left hover:border-primary-400 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                  title={`Download ${r.format?.toUpperCase?.() || 'DOCX'} resume`}
                >
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold text-slate-900 dark:text-white truncate">
                      {r.job_title || `Resume #${r.id}`}
                    </span>
                    <span className="block text-xs text-slate-500 dark:text-slate-400 truncate">
                      {r.company || '—'}
                    </span>
                  </span>
                  <Download className="w-4 h-4 flex-shrink-0 text-slate-400 group-hover:text-primary-500 transition-colors" />
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Match Explainability Details Modal */}
      <MatchDetailModal
        match={inspectingMatch}
        isOpen={inspectingMatch !== null}
        onClose={() => setInspectingMatch(null)}
        isSelected={inspectingMatch ? selectedJobs.has(inspectingMatch.job_id) : false}
        onSelectAndApply={(jobId) => {
          if (!selectedJobs.has(jobId)) {
            toggleJobSelection(jobId)
          }
        }}
      />
    </div>
  )
}