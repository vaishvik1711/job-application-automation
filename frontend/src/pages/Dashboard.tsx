import { useQueryClient } from '@tanstack/react-query'
import {
  LayoutDashboard,
  Briefcase,
  Target,
  FileText,
  CheckCircle,
  TrendingUp,
  ArrowRight,
  RefreshCw,
  Download,
} from 'lucide-react'
import { usePipelineStats } from '@/hooks/useApi'
import { useJobSearchStore } from '@/store'
import { cn, formatNumber } from '@/utils/helpers'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Progress } from '@/components/ui/Progress'
import { FunnelChart } from '@/components/dashboard/FunnelChart'
import { RecentActivity } from '@/components/dashboard/RecentActivity'
import { QuickActions } from '@/components/dashboard/QuickActions'

const pipelineStages = [
  { key: 'discovered', label: 'Discovered', icon: Briefcase, color: 'bg-slate-500' },
  { key: 'deduplicated', label: 'Deduplicated', icon: Target, color: 'bg-blue-500' },
  { key: 'matched', label: 'Matched', icon: Target, color: 'bg-purple-500' },
  { key: 'qualified', label: 'Qualified', icon: CheckCircle, color: 'bg-green-500' },
  { key: 'resume_created', label: 'Resume Created', icon: FileText, color: 'bg-orange-500' },
  { key: 'ready_to_apply', label: 'Ready to Apply', icon: ArrowRight, color: 'bg-indigo-500' },
  { key: 'applied', label: 'Applied', icon: TrendingUp, color: 'bg-pink-500' },
] as const

type PipelineKey = (typeof pipelineStages)[number]['key']

export function Dashboard() {
  const queryClient = useQueryClient()
  const { data: stats } = usePipelineStats()
  const { setSearching, setSearchProgress } = useJobSearchStore()

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['analytics', 'pipeline'] })
    queryClient.invalidateQueries({ queryKey: ['jobs', 'stats'] })
  }

  const handleStartSearch = async () => {
    setSearching(true)
    setSearchProgress({ current: 0, total: 100, message: 'Initializing search...' })
    // This would trigger the backend search
    // For now, just simulate
    setTimeout(() => {
      setSearching(false)
      setSearchProgress(null)
    }, 3000)
  }

  const getStatValue = (key: PipelineKey): number => {
    if (!stats) return 0
    return stats[key as keyof typeof stats] || 0
  }

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Dashboard</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Overview of your job application pipeline
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={handleRefresh} size="sm">
            <RefreshCw className="w-4 h-4 mr-2" /> Refresh
          </Button>
          <Button onClick={handleStartSearch} size="sm">
            <LayoutDashboard className="w-4 h-4 mr-2" /> New Search
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-4">
        {pipelineStages.map((stage) => (
          <Card key={stage.key} className="stat-card">
            <CardContent className="p-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="stat-label">{stage.label}</p>
                  <p className="stat-value">{formatNumber(getStatValue(stage.key))}</p>
                </div>
                <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center', stage.color)}>
                  <stage.icon className="w-5 h-5 text-white" />
                </div>
              </div>
              {/* Mini progress bar */}
              <Progress
                value={getStatValue(stage.key)}
                max={getStatValue('discovered') || 1}
                className="mt-3 h-1.5"
                showLabel={false}
              />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pipeline Funnel */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Application Pipeline</CardTitle>
                  <CardDescription>Track jobs through each stage of the process</CardDescription>
                </div>
                <Button variant="outline" size="sm">
                  <Download className="w-4 h-4 mr-2" /> Export
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <FunnelChart
                stages={pipelineStages.map((s) => ({
                  label: s.label,
                  value: getStatValue(s.key),
                  color: s.color.replace('bg-', '').replace('-500', ''),
                }))}
              />
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <div className="lg:col-span-1">
          <QuickActions />
        </div>
      </div>

      {/* Recent Activity & Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RecentActivity />
        <Card>
          <CardHeader>
            <CardTitle>Match Score Distribution</CardTitle>
            <CardDescription>Distribution of job match scores</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64 flex items-center justify-center text-slate-400">
              <span className="text-sm">Chart coming soon - integrates with Recharts</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}