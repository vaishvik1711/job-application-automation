import { useState, useEffect, useCallback, useMemo } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { MatchDetail } from '@/types'
import { useMatches } from '@/hooks/useApi'
import { useMatchingStore } from '@/store'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader } from '@/components/ui/Card'
import { Progress } from '@/components/ui/Progress'
import { MatchCard } from '@/components/job-matching/MatchCard'
import { Target, Search, BarChart3, Sliders, LayoutGrid, List, CheckCircle } from 'lucide-react'
import { toast } from 'sonner'
import { jobsApi } from '@/services/api'

type ViewMode = 'grid' | 'list'

export function JobMatching() {
  const navigate = useNavigate()
  const location = useLocation()
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisProgress, setAnalysisProgress] = useState<{ current: number; total: number; message: string } | null>(null)
  const [threshold, setThreshold] = useState(50)

  const { data: matchesData, isLoading, refetch } = useMatches({ page: 1, page_size: 100 })
  const { selectedMatches, toggleMatchSelection } = useMatchingStore()

  // Get selected jobs from location state (passed from JobSearch page)
  const locationState = location.state as { selectedJobs?: string[] } | null
  const selectedJobIds = locationState?.selectedJobs || []

  // Auto-analyze when jobs are passed in
  useEffect(() => {
    if (selectedJobIds.length > 0 && !isAnalyzing) {
      // Check if we already have match data
      const currentMatches = matchesData?.items || []
      const alreadyMatchedIds = new Set(currentMatches.map((m) => m.job_id))
      const needsAnalysis = selectedJobIds.filter((id) => !alreadyMatchedIds.has(id))

      if (needsAnalysis.length > 0 && currentMatches.length < selectedJobIds.length) {
        handleBatchAnalyze(needsAnalysis)
      }
    }
  }, [selectedJobIds])

  const handleBatchAnalyze = useCallback(async (jobIds?: string[]) => {
    const ids = jobIds || selectedJobIds
    if (ids.length === 0) return

    setIsAnalyzing(true)
    setAnalysisProgress({ current: 0, total: ids.length, message: 'Analyzing jobs...' })

    try {
      await jobsApi.batchAnalyze(ids)
      setAnalysisProgress({ current: ids.length, total: ids.length, message: 'Analysis complete!' })
      toast.success(`Analyzed ${ids.length} jobs`)
      setTimeout(() => setAnalysisProgress(null), 1000)
      refetch()
    } catch (err: any) {
      console.error('Batch analysis failed:', err)
      toast.error('Analysis failed — try refreshing')
    } finally {
      setIsAnalyzing(false)
    }
  }, [selectedJobIds, refetch])

  // Filter matches by technical_score >= threshold
  const existingMatches: MatchDetail[] = matchesData?.items || []
  const filteredMatches = useMemo(() => {
    return existingMatches.filter((m) => (m.score?.skills || 0) >= threshold)
  }, [existingMatches, threshold])

  const handleGenerateResume = (match: MatchDetail) => {
    navigate(`/resume-builder?job_id=${match.job_id}`)
  }

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Job Matching</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Jobs matching your skills — filtered by technical score
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
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <Search className="w-4 h-4 mr-1" /> Refresh
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

      {/* Simple single-column layout */}
      <div className="space-y-4">
        {/* Skill Match Threshold Slider */}
        <Card>
          <CardContent className="py-4">
            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
              <div className="flex items-center gap-2 min-w-fit">
                <Sliders className="w-4 h-4 text-slate-500" />
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Skill Match Threshold
                </span>
              </div>
              <div className="flex items-center gap-3 flex-1">
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={5}
                  value={threshold}
                  onChange={(e) => setThreshold(Number(e.target.value))}
                  className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
                />
                <span className="text-sm font-semibold text-primary-600 dark:text-primary-400 min-w-[3rem] text-right">
                  {threshold}%
                </span>
              </div>
              <div className="flex items-center gap-4 text-sm text-slate-500 dark:text-slate-400 min-w-fit">
                <span>Matched: <strong className="text-slate-900 dark:text-white">{existingMatches.length}</strong></span>
                <span>Filtered: <strong className="text-slate-900 dark:text-white">{filteredMatches.length}</strong></span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Stats Summary */}
        {filteredMatches.length > 0 && (
          <Card>
            <CardContent className="py-3">
              <div className="flex items-center gap-6 text-sm">
                <div className="flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                  <span className="text-slate-600 dark:text-slate-400">Showing:</span>
                  <strong className="text-slate-900 dark:text-white">{filteredMatches.length} jobs</strong>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-green-500" />
                  <span className="text-slate-600 dark:text-slate-400">Above {threshold}% skill match</span>
                </div>
                <div className="flex-1" />
                {existingMatches.length > filteredMatches.length && (
                  <span className="text-xs text-slate-400">
                    ({existingMatches.length - filteredMatches.length} below threshold hidden)
                  </span>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* No matches yet — auto-analyzing */}
        {existingMatches.length === 0 && !isAnalyzing && selectedJobIds.length > 0 && (
          <Card>
            <CardContent className="py-8 text-center">
              <Target className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-2">Analyzing jobs...</h3>
              <p className="text-slate-500 dark:text-slate-400">
                Matching {selectedJobIds.length} jobs against your skills. This may take a moment.
              </p>
            </CardContent>
          </Card>
        )}

        {/* Match Results Grid/List */}
        {filteredMatches.length > 0 ? (
          <div
            className={
              viewMode === 'grid'
                ? 'grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4'
                : 'space-y-3'
            }
          >
            {filteredMatches.map((match) => (
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
        ) : existingMatches.length > 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Target className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-2">No jobs match your threshold</h3>
              <p className="text-slate-500 dark:text-slate-400 mb-4">
                {existingMatches.length} jobs matched, but none have a skill score of {threshold}% or higher.
                Try lowering the threshold slider above.
              </p>
            </CardContent>
          </Card>
        ) : !isLoading && (
          <Card>
            <CardContent className="py-12 text-center">
              <Target className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-2">No matches found</h3>
              <p className="text-slate-500 dark:text-slate-400 mb-4">
                Go to Job Search to find jobs and analyze them against your profile.
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
  )
}
