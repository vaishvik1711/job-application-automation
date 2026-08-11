import {
  useAnalyticsOverview,
  usePipelineStats,
  useSourceEffectiveness,
  useSkillGaps,
  useTimeSeries,
} from '@/hooks/useApi'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import {
  PipelineFunnel,
} from '@/components/analytics/PipelineFunnel'
import { SourceEffectivenessTable } from '@/components/analytics/SourceEffectivenessTable'
import { SkillGapsList } from '@/components/analytics/SkillGapsList'
import { MatchScoreDistribution } from '@/components/analytics/MatchScoreDistribution'
import { ApplicationsTimeline } from '@/components/analytics/ApplicationsTimeline'
import {
  RefreshCw,
  Download,
  Target,
  Calendar,
  Clock,
  PieChart,
  Search,
} from 'lucide-react'
import { formatNumber } from '@/utils/helpers'
import { toast } from 'sonner'

export function Analytics() {
  const { data: overview, isLoading, refetch } = useAnalyticsOverview()
  const { data: pipeline } = usePipelineStats()
  const { data: sources, isLoading: isLoadingSources } = useSourceEffectiveness()
  const { data: skillGaps, isLoading: isLoadingSkillGaps } = useSkillGaps()
  const { data: timeSeries, isLoading: isLoadingTimeSeries } = useTimeSeries(30)

  const handleExport = (format: string) => {
    toast.info(`Exporting report as ${format}...`)
  }

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Analytics</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Track your job search performance and metrics
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
            <RefreshCw className="w-4 h-4 mr-2" /> Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={() => handleExport('pdf')}>
            <Download className="w-4 h-4 mr-2" /> Export PDF
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      {overview && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="stat-card">
            <CardContent className="p-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="stat-label">Total Jobs</p>
                  <p className="stat-value">{formatNumber(overview.pipeline.discovered || 0)}</p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                  <Search className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="stat-card">
            <CardContent className="p-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="stat-label">Qualified Matches</p>
                  <p className="stat-value">{formatNumber(overview.pipeline.qualified || 0)}</p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                  <Target className="w-5 h-5 text-green-600 dark:text-green-400" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="stat-card">
            <CardContent className="p-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="stat-label">Applications</p>
                  <p className="stat-value">{formatNumber(overview.pipeline.applied || 0)}</p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-pink-100 dark:bg-pink-900/30 flex items-center justify-center">
                  <Clock className="w-5 h-5 text-pink-600 dark:text-pink-400" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="stat-card">
            <CardContent className="p-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="stat-label">Interview Rate</p>
                  <p className="stat-value">
                    {overview.pipeline.interviewed > 0
                      ? `${Math.round(((overview.pipeline.interviewed || 0) / Math.max(overview.pipeline.applied || 1, 1)) * 100)}%`
                      : '0%'}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                  <Calendar className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Pipeline Funnel */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2">
          {overview ? (
            <PipelineFunnel stats={overview.pipeline} />
          ) : pipeline ? (
            <PipelineFunnel stats={pipeline} />
          ) : isLoading ? (
            <Card>
              <CardContent className="py-8">
                <div className="space-y-3">
                  {[...Array(8)].map((_, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className="w-28 h-4 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
                      <div className="flex-1 h-6 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="py-8 text-center">
                <p className="text-slate-500 dark:text-slate-400">No pipeline data available</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Source Effectiveness */}
        <div>
          {sources ? (
            <SourceEffectivenessTable sources={sources} />
          ) : isLoadingSources ? (
            <Card>
              <CardHeader>
                <CardTitle>Source Effectiveness</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="space-y-2">
                      <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded animate-pulse w-1/2" />
                      <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded animate-pulse w-full" />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : (
            <SourceEffectivenessTable sources={[]} />
          )}
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Match Score Distribution */}
        <div>
          {overview ? (
            <MatchScoreDistribution distribution={overview.match_score_distribution} />
          ) : (
            <MatchScoreDistribution distribution={[]} />
          )}
        </div>

        {/* Applications Timeline */}
        <div>
          {timeSeries ? (
            <ApplicationsTimeline data={timeSeries} />
          ) : isLoadingTimeSeries ? (
            <Card>
              <CardHeader>
                <CardTitle>Applications Over Time</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64 flex items-center justify-center">
                  <div className="animate-pulse text-slate-400">Loading chart...</div>
                </div>
              </CardContent>
            </Card>
          ) : (
            <ApplicationsTimeline data={[]} />
          )}
        </div>
      </div>

      {/* Skill Gaps */}
      <div>
        {skillGaps ? (
          <SkillGapsList gaps={skillGaps} />
        ) : isLoadingSkillGaps ? (
          <Card>
            <CardHeader>
              <CardTitle>Skill Gap Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="h-14 bg-slate-200 dark:bg-slate-700 rounded-lg animate-pulse" />
                ))}
              </div>
            </CardContent>
          </Card>
        ) : (
          <SkillGapsList gaps={[]} />
        )}
      </div>

      {/* Response Rates (if available from overview) */}
      {overview && overview.response_rates && overview.response_rates.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PieChart className="w-5 h-5" />
              Response Rates by Category
            </CardTitle>
            <CardDescription>How quickly you get responses across different opportunities</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {overview.response_rates.map((rate) => (
                <div key={rate.category} className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg text-center">
                  <p className="font-medium text-slate-900 dark:text-white">{rate.category}</p>
                  <p className="text-2xl font-bold text-primary-600 dark:text-primary-400 mt-1">
                    {Math.round(rate.rate * 100)}%
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    {rate.total} total
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
