import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  Briefcase,
  Target,
  FileText,
  CheckCircle,
  TrendingUp,
  ArrowRight,
  RefreshCw,
  Upload,
  Search,
  User,
} from 'lucide-react'
import { usePipelineStats, useProfile } from '@/hooks/useApi'
import { cn, formatNumber } from '@/utils/helpers'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Progress } from '@/components/ui/Progress'
import { ResumeUpload } from '@/components/profile/ResumeUpload'
import { toast } from 'sonner'

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
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: stats } = usePipelineStats()
  const { data: profile } = useProfile()

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['analytics', 'pipeline'] })
    queryClient.invalidateQueries({ queryKey: ['jobs', 'stats'] })
  }

  const handleResumeComplete = useCallback(() => {
    toast.success('Resume uploaded and parsed!')
    queryClient.invalidateQueries({ queryKey: ['profile'] })
  }, [queryClient])

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
            Upload your resume, search jobs, and apply — all in one place
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={handleRefresh} size="sm">
            <RefreshCw className="w-4 h-4 mr-2" /> Refresh
          </Button>
          {profile && (
            <Button onClick={() => navigate('/jobs')} size="sm">
              <Search className="w-4 h-4 mr-2" /> Search Jobs
            </Button>
          )}
        </div>
      </div>

      {/* Resume Upload / Profile Summary */}
      {!profile ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="w-5 h-5 text-primary-500" />
              Upload Your Resume
            </CardTitle>
            <CardDescription>
              Upload your existing resume (PDF or DOCX). We'll parse it and auto-fill your profile.
              Then you can search for matching jobs in one click.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResumeUpload onComplete={handleResumeComplete} />
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <User className="w-5 h-5 text-primary-500" />
                  Profile Ready
                </CardTitle>
                <CardDescription>
                  {profile.personal_info?.full_name || 'Your profile'} • {profile.personal_info?.email || ''}
                  {profile.skills?.length ? ` • ${profile.skills.length} skills` : ''}
                </CardDescription>
              </div>
              <Button onClick={() => navigate('/jobs')}>
                <Search className="w-4 h-4 mr-2" /> Find Matching Jobs
              </Button>
            </div>
          </CardHeader>
        </Card>
      )}

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
    </div>
  )
}