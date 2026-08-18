import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useJobSearch } from '@/hooks/useApi'
import { useBatchGenerateResumes, useMatches, useProfile } from '@/hooks/useApi'
import { useJobSearchStore } from '@/store'
import { JobCard } from '@/components/job-search/JobCard'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Progress } from '@/components/ui/Progress'
import { Badge } from '@/components/ui/Badge'
import {
  Search,
  Sparkles,
  CheckCircle,
  Loader2,
  ArrowRight,
  RefreshCw,
} from 'lucide-react'
import { toast } from 'sonner'
import type { MatchDetail } from '@/types'

export function Jobs() {
  const navigate = useNavigate()
  const { data: profile } = useProfile()
  const { data: matchesData, isLoading: isLoadingMatches, refetch: refetchMatches } = useMatches({ page_size: 50 })
  const jobSearch = useJobSearch()
  const batchGenerate = useBatchGenerateResumes()

  const { selectedJobs, toggleJobSelection, clearSelection } = useJobSearchStore()

  const [isSearching, setIsSearching] = useState(false)
  const [searchProgress, setSearchProgress] = useState<string | null>(null)
  const [matches, setMatches] = useState<MatchDetail[]>([])
  const [batchProgress, setBatchProgress] = useState<{
    total: number
    current: number
    succeeded: number
    failed: number
    message: string
    isRunning: boolean
  } | null>(null)

  // Sync matches data when it loads
  useEffect(() => {
    if (matchesData?.items) {
      setMatches(matchesData.items)
    }
  }, [matchesData])

  // Auto-search on mount if profile exists but no matches
  const handleSearch = useCallback(async () => {
    if (!profile) {
      toast.error('Please upload your resume first on the Dashboard')
      return
    }

    setIsSearching(true)
    setSearchProgress('Searching for jobs matching your profile...')

    try {
      await jobSearch.mutateAsync({
        filters: {
          keywords: profile.skills?.slice(0, 10).map((s) => s.name) || [],
          locations: profile.personal_info?.location ? [profile.personal_info.location] : [],
          job_types: ['full_time', 'contract'],
          remote_only: false,
          posted_within_days: 30,
          sources: ['jobbank'],
        },
        max_results_per_source: 50,
      })
      setSearchProgress('Analyzing matches...')
      // Wait a moment for backend analysis to complete, then refetch
      setTimeout(async () => {
        await refetchMatches()
        setIsSearching(false)
        setSearchProgress(null)
        toast.success('Jobs found and analyzed!')
      }, 2000)
    } catch (err: any) {
      console.error('Search failed:', err)
      toast.error(err?.message || 'Search failed')
      setIsSearching(false)
      setSearchProgress(null)
    }
  }, [profile, jobSearch, refetchMatches])

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
      message: 'Starting batch generation...',
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
        message: `Done: ${result.succeeded} succeeded, ${result.failed} failed`,
        isRunning: false,
      })

      if (result.succeeded > 0) {
        toast.success(`${result.succeeded} resumes generated and applications created!`, {
          action: {
            label: 'View Applications',
            onClick: () => navigate('/applications'),
          },
        })
        clearSelection()
        refetchMatches()
      }

      if (result.failed > 0) {
        toast.error(`${result.failed} jobs failed. Check the backend logs for details.`)
      }
    } catch (err: any) {
      console.error('Batch generation failed:', err)
      toast.error(err?.message || 'Batch generation failed')
      setBatchProgress((prev) => prev ? { ...prev, isRunning: false, message: 'Failed' } : null)
    }
  }, [selectedJobs, batchGenerate, navigate, clearSelection, refetchMatches])

  const isFirstVisit = !isSearching && !isLoadingMatches && matches.length === 0 && !profile

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Jobs</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            {profile
              ? 'Review matched jobs. Select and generate resumes with one click.'
              : 'Upload your resume on the Dashboard first to find matching jobs.'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {matches.length > 0 && (
            <Button variant="outline" size="sm" onClick={() => refetchMatches()}>
              <RefreshCw className="w-4 h-4 mr-2" /> Refresh
            </Button>
          )}
          <Button
            onClick={handleSearch}
            disabled={isSearching || !profile}
            size="sm"
          >
            {isSearching ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Search className="w-4 h-4 mr-2" />
            )}
            {isSearching ? 'Searching...' : 'Search Jobs'}
          </Button>
        </div>
      </div>

      {/* Search Progress */}
      {isSearching && searchProgress && (
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <Loader2 className="w-5 h-5 animate-spin text-primary-500" />
              <span className="text-sm text-slate-600 dark:text-slate-400">{searchProgress}</span>
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
              No Jobs Yet
            </h2>
            <p className="text-slate-500 dark:text-slate-400 max-w-lg mx-auto mb-6">
              Click "Search Jobs" to discover and analyze jobs that match your profile.
            </p>
            <Button onClick={handleSearch} disabled={isSearching}>
              {isSearching ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Search className="w-4 h-4 mr-2" />
              )}
              Search Jobs
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Batch Progress */}
      {batchProgress && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              {batchProgress.isRunning ? (
                <Loader2 className="w-5 h-5 animate-spin text-primary-500" />
              ) : (
                <CheckCircle className="w-5 h-5 text-green-500" />
              )}
              {batchProgress.isRunning ? 'Generating Resumes...' : 'Complete'}
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
              <div className="flex gap-4 text-sm">
                <span className="text-green-600 dark:text-green-400">
                  ✓ {batchProgress.succeeded} succeeded
                </span>
                {batchProgress.failed > 0 && (
                  <span className="text-red-600 dark:text-red-400">
                    ✗ {batchProgress.failed} failed
                  </span>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Selection bar */}
      {selectedJobs.size > 0 && (
        <Card className="sticky top-20 z-30 border-primary-300 dark:border-primary-700">
          <CardContent className="py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Badge variant="primary" className="text-sm px-3 py-1">
                  {selectedJobs.size} selected
                </Badge>
                <span className="text-sm text-slate-500 dark:text-slate-400">
                  Generate resumes and create application records
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
                    : `Generate & Apply (${selectedJobs.size})`}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading State */}
      {isLoadingMatches && (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-32 bg-slate-200 dark:bg-slate-700 rounded-lg animate-pulse" />
          ))}
        </div>
      )}

      {/* Matched Jobs Grid */}
      {!isLoadingMatches && matches.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {matches.length} matched jobs found
            </p>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                const allIds = matches.map((m) => m.job_id)
                allIds.forEach((id) => {
                  if (!selectedJobs.has(id)) toggleJobSelection(id)
                })
              }}
            >
              Select All
            </Button>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {matches.map((match) => (
              <JobCard
                key={match.job_id}
                job={match.job}
                isSelected={selectedJobs.has(match.job_id)}
                onSelect={() => toggleJobSelection(match.job_id)}
                showMatchScore
                matchScore={match.score.overall}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}