import { useState, useEffect, useCallback } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { MatchDetail, MatchWeights } from '@/types'
import { useMatches, useAnalyzeJob, useJobs } from '@/hooks/useApi'
import { useMatchingStore, useJobSearchStore } from '@/store'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Progress } from '@/components/ui/Progress'
import { MatchCard } from '@/components/job-matching/MatchCard'
import { MatchWeightsConfig } from '@/components/job-matching/MatchWeightsConfig'
import { Target, Search, BarChart3, CheckCircle, Clock, LayoutGrid, List, Download } from 'lucide-react'
import { toast } from 'sonner'

type ViewMode = 'grid' | 'list'

export function JobMatching() {
  const navigate = useNavigate()
  const location = useLocation()
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [selectedJobsForAnalysis, setSelectedJobsForAnalysis] = useState<string[]>([])
  const [analysisProgress, setAnalysisProgress] = useState<{ current: number; total: number; message: string } | null>(null)

  const { data: matchesData, isLoading, refetch } = useMatches({ page: 1, page_size: 50 })
  const { data: storedJobs } = useJobs()

  const analyzeJobMutation = useAnalyzeJob()

  const { selectedMatches, toggleMatchSelection } = useMatchingStore()
  const { weights, threshold } = useMatchingStore()
  const { searchResults: searchedJobs } = useJobSearchStore()

  // Get selected jobs from location state (passed from JobSearch page)
  const locationState = location.state as { selectedJobs?: string[] } | null
  const selectedJobIds = locationState?.selectedJobs || []

  // Use searched jobs if available, otherwise use jobs from matches
  const availableJobs = searchedJobs.length > 0 ? searchedJobs : (storedJobs?.items || [])
  const jobsToAnalyze =
    selectedJobIds.length > 0 && availableJobs.length > 0
      ? availableJobs.filter((j) => selectedJobIds.includes(j.id))
      : selectedJobIds.length > 0 && availableJobs.length === 0
      ? searchedJobs
      : []

  // Get existing matches
  const existingMatches = matchesData?.items || []

  // Combined match data - use existing matches plus any jobs we just found
  const displayMatches: MatchDetail[] = [...existingMatches]

  useEffect(() => {
    if (selectedJobIds.length > 0) {
      setSelectedJobsForAnalysis(selectedJobIds)
    }
  }, [selectedJobIds])

  const handleAnalyzeSelected = useCallback(async () => {
    if (selectedJobsForAnalysis.length === 0) {
      toast.warning('Please select at least one job to analyze')
      return
    }

    setAnalysisProgress({ current: 0, total: selectedJobsForAnalysis.length, message: 'Starting analysis...' })

    try {
      const matchWeights: MatchWeights = weights
      let completed = 0

      for (const jobId of selectedJobsForAnalysis) {
        try {
          setAnalysisProgress({
            current: completed + 1,
            total: selectedJobsForAnalysis.length,
            message: `Analyzing "${availableJobs.find((j) => j.id === jobId)?.title || jobId}"...`,
          })

          await analyzeJobMutation.mutateAsync({ id: jobId, weights: matchWeights })
          completed++
        } catch (err: any) {
          console.error(`Failed to analyze job ${jobId}:`, err)
          completed++
        }
      }

      setAnalysisProgress({
        current: selectedJobsForAnalysis.length,
        total: selectedJobsForAnalysis.length,
        message: 'Analysis complete!',
      })

      toast.success(`Analyzed ${completed} jobs`)
      setTimeout(() => setAnalysisProgress(null), 1500)
      refetch()
    } catch (err: any) {
      console.error('Batch analysis failed:', err)
      toast.error('Failed to analyze jobs')
      setAnalysisProgress(null)
    }
  }, [selectedJobsForAnalysis, weights, availableJobs, analyzeJobMutation, refetch])

  const handleGenerateResume = (match: MatchDetail) => {
    navigate(`/resume-builder?job_id=${match.job_id}`)
  }

  const handleExport = () => {
    toast.info('Export feature coming soon')
  }

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Job Matching</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Analyze jobs against your profile and view match scores
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
            <button
              onClick={() => setViewMode('grid')}
              className={
                viewMode === 'grid'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-700'
              }
              style={{ padding: '4px 12px', borderRadius: '6px', fontSize: '14px', fontWeight: 500, cursor: 'pointer', border: 'none' }}
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={
                viewMode === 'list'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-700'
              }
              style={{ padding: '4px 12px', borderRadius: '6px', fontSize: '14px', fontWeight: 500, cursor: 'pointer', border: 'none' }}
            >
              <List className="w-4 h-4" />
            </button>
          </div>
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="w-4 h-4 mr-2" /> Export Results
          </Button>
        </div>
      </div>

      {/* Analysis Progress */}
      {analysisProgress && (
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{analysisProgress.message}</p>
              <span className="text-sm text-slate-500 dark:text-slate-400">
                {analysisProgress.current}/{analysisProgress.total}
              </span>
            </div>
            <Progress value={analysisProgress.current} max={analysisProgress.total} showLabel={false} />
          </CardContent>
        </Card>
      )}

      {/* Two-column layout: Weights Config + Matches */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Weights Configuration */}
        <div className="xl:col-span-1">
          <MatchWeightsConfig />
        </div>

        {/* Match Results */}
        <div className="xl:col-span-3 space-y-4">
          {/* Analyze Button for selected jobs */}
          {jobsToAnalyze.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Jobs Ready for Analysis</CardTitle>
                <CardDescription>{jobsToAnalyze.length} jobs selected from search results</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {jobsToAnalyze.slice(0, 3).map((job) => (
                      <Badge key={job.id} variant="neutral" className="text-xs">
                        {job.title}
                      </Badge>
                    ))}
                    {jobsToAnalyze.length > 3 && (
                      <Badge variant="neutral" className="text-xs">
                        +{jobsToAnalyze.length - 3} more
                      </Badge>
                    )}
                  </div>
                  <Button onClick={handleAnalyzeSelected} loading={analyzeJobMutation.isPending} size="sm">
                    <Target className="w-4 h-4 mr-2" /> Analyze with Current Weights
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Stats Summary */}
          {displayMatches.length > 0 && (
            <Card>
              <CardContent className="py-3">
                <div className="flex items-center gap-6 text-sm">
                  <div className="flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                    <span className="text-slate-600 dark:text-slate-400">Total Matches:</span>
                    <strong className="text-slate-900 dark:text-white">{displayMatches.length}</strong>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    <span className="text-slate-600 dark:text-slate-400">Qualified:</span>
                    <strong className="text-slate-900 dark:text-white">
                      {displayMatches.filter((m) => m.score.verdict === 'QUALIFIED').length}
                    </strong>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-orange-500" />
                    <span className="text-slate-600 dark:text-slate-400">Threshold:</span>
                    <strong className="text-slate-900 dark:text-white">{threshold}%</strong>
                  </div>
                  <div className="flex-1" />
                  {displayMatches.length > 0 && (
                    <Button variant="outline" size="sm" onClick={() => refetch()}>
                      <Search className="w-4 h-4 mr-1" /> Refresh
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Match Results Grid/List */}
          {displayMatches.length > 0 ? (
            <div
              className={
                viewMode === 'grid'
                  ? 'grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4'
                  : 'space-y-3'
              }
            >
              {displayMatches.map((match) => (
                <MatchCard
                  key={match.job_id}
                  match={match}
                  isSelected={selectedMatches.has(match.job_id)}
                  onSelect={() => toggleMatchSelection(match.job_id)}
                  onGenerateResume={() => handleGenerateResume(match)}
                  compact={viewMode === 'list'}
                />
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <Target className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-2">No matches found</h3>
                <p className="text-slate-500 dark:text-slate-400 mb-4">
                  {jobsToAnalyze.length > 0
                    ? 'Click "Analyze with Current Weights" above to start matching your jobs against your profile.'
                    : 'Go to Job Search to find jobs and then analyze them against your profile.'}
                </p>
                <Button variant="outline" onClick={() => navigate('/job-search')}>
                  <Search className="w-4 h-4 mr-2" /> Go to Job Search
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Loading */}
          {isLoading && (
            <div className="space-y-4">
              {[...Array(viewMode === 'grid' ? 6 : 4)].map((_, i) => (
                <Card key={i}>
                  <CardHeader>
                    <div className="h-5 bg-slate-200 dark:bg-slate-700 rounded animate-pulse w-3/4" />
                    <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded animate-pulse w-1/2 mt-2" />
                  </CardHeader>
                  <CardContent>
                    <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded animate-pulse mb-2" />
                    <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded animate-pulse w-5/6" />
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
