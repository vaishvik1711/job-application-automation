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
  Sparkles,
  Kanban,
} from 'lucide-react'
import { usePipelineStats, useProfile, useMatches, useResumes, useApplications } from '@/hooks/useApi'
import { cn, formatNumber } from '@/utils/helpers'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Progress } from '@/components/ui/Progress'
import { ResumeUpload } from '@/components/profile/ResumeUpload'
import { QuickActions } from '@/components/dashboard/QuickActions'
import { RecentActivity } from '@/components/dashboard/RecentActivity'
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
  const { data: matchesData } = useMatches({ page_size: 1 })
  const { data: resumesData } = useResumes({ page: 1, page_size: 1 })
  const { data: appsData } = useApplications({ page: 1, page_size: 1 })

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['analytics', 'pipeline'] })
    queryClient.invalidateQueries({ queryKey: ['jobs', 'stats'] })
    queryClient.invalidateQueries({ queryKey: ['profile'] })
    queryClient.invalidateQueries({ queryKey: ['applications'] })
  }

  const handleResumeComplete = useCallback(() => {
    toast.success('Resume uploaded and parsed!')
    queryClient.invalidateQueries({ queryKey: ['profile'] })
  }, [queryClient])

  const getStatValue = (key: PipelineKey): number => {
    if (!stats) return 0
    return stats[key as keyof typeof stats] || 0
  }

  const hasProfile = !!profile
  const hasMatches = (matchesData?.items?.length || 0) > 0 || getStatValue('matched') > 0
  const hasResumes = (resumesData?.items?.length || 0) > 0 || getStatValue('resume_created') > 0
  const hasApplications = (appsData?.items?.length || 0) > 0 || getStatValue('applied') > 0

  const workflowSteps = [
    {
      step: 1,
      title: 'Profile & Resume',
      desc: hasProfile ? `${profile.personal_info?.full_name || 'Completed'}` : 'Upload your resume',
      done: hasProfile,
      active: !hasProfile,
      href: '/profile',
      icon: User,
    },
    {
      step: 2,
      title: 'Job Matching',
      desc: hasMatches ? `${getStatValue('qualified') || matchesData?.total || 0} qualified jobs` : 'Search & analyze matches',
      done: hasMatches,
      active: hasProfile && !hasMatches,
      href: '/jobs',
      icon: Search,
    },
    {
      step: 3,
      title: 'Tailor Resumes',
      desc: hasResumes ? `${resumesData?.total || getStatValue('resume_created')} resumes generated` : 'Batch generate tailored resumes',
      done: hasResumes,
      active: hasMatches && !hasResumes,
      href: '/jobs',
      icon: FileText,
    },
    {
      step: 4,
      title: 'Track Pipeline',
      desc: hasApplications ? `${appsData?.total || getStatValue('applied')} in pipeline` : 'Auto & manual applications',
      done: hasApplications,
      active: hasResumes && !hasApplications,
      href: '/applications',
      icon: Kanban,
    },
  ]

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Dashboard</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Automate your job search, tailor resumes, and track applications with AI
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

      {/* Guided 4-Step Onboarding Stepper */}
      <Card className="border-primary-100 dark:border-slate-800 bg-gradient-to-r from-primary-50/50 via-white to-blue-50/50 dark:from-slate-900 dark:via-slate-900 dark:to-slate-800">
        <CardContent className="p-4 sm:p-6">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-semibold uppercase tracking-wider text-primary-700 dark:text-primary-400 flex items-center gap-1.5">
              <Sparkles className="w-4 h-4" /> Application Workflow
            </span>
            <span className="text-xs text-slate-500">
              {workflowSteps.filter((s) => s.done).length} of 4 steps completed
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {workflowSteps.map((step) => {
              const Icon = step.icon
              return (
                <button
                  key={step.step}
                  onClick={() => navigate(step.href)}
                  className={cn(
                    'flex items-center gap-3 p-3.5 rounded-xl border text-left transition-all',
                    step.done
                      ? 'bg-green-50/80 dark:bg-green-900/20 border-green-200 dark:border-green-800/50 hover:bg-green-100/60'
                      : step.active
                      ? 'bg-primary-50 dark:bg-primary-900/20 border-primary-300 dark:border-primary-700 shadow-sm ring-1 ring-primary-400 hover:bg-primary-100/60'
                      : 'bg-white/80 dark:bg-slate-800/60 border-slate-200 dark:border-slate-700 hover:bg-slate-100/60'
                  )}
                >
                  <div
                    className={cn(
                      'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-sm font-semibold',
                      step.done
                        ? 'bg-green-500 text-white'
                        : step.active
                        ? 'bg-primary-500 text-white'
                        : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400'
                    )}
                  >
                    {step.done ? <CheckCircle className="w-4 h-4" /> : step.step}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold text-slate-900 dark:text-white truncate flex items-center gap-1.5">
                        <Icon className="w-3.5 h-3.5 text-slate-400" />
                        <span>{step.title}</span>
                      </p>
                      <ArrowRight className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">
                      {step.desc}
                    </p>
                  </div>
                </button>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Resume Upload / Profile Summary Banner */}
      {!profile ? (
        <Card className="border-dashed border-2 border-primary-300 dark:border-primary-700">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Upload className="w-5 h-5 text-primary-500" />
              Step 1: Upload Your Resume
            </CardTitle>
            <CardDescription>
              Upload your existing resume (PDF or DOCX). AI will extract your skills, experience, and contact details to auto-generate personalized job search criteria and tailored resumes.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResumeUpload onComplete={handleResumeComplete} />
          </CardContent>
        </Card>
      ) : (
        <Card className="border border-slate-200 dark:border-slate-700">
          <CardHeader className="py-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center text-primary-700 dark:text-primary-300 font-bold">
                  {profile.personal_info?.full_name?.charAt(0) || 'U'}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-base font-semibold">
                      {profile.personal_info?.full_name || 'Candidate Profile'}
                    </CardTitle>
                    <Badge variant="success" className="text-xs">
                      Ready
                    </Badge>
                  </div>
                  <CardDescription className="text-xs mt-0.5">
                    {profile.personal_info?.email || ''}
                    {profile.skills?.length ? ` • ${profile.skills.length} verified skills` : ''}
                    {profile.personal_info?.location ? ` • ${profile.personal_info.location}` : ''}
                  </CardDescription>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={() => navigate('/profile')}>
                  <User className="w-3.5 h-3.5 mr-1.5" /> Edit Profile
                </Button>
                <Button size="sm" onClick={() => navigate('/jobs')}>
                  <Search className="w-3.5 h-3.5 mr-1.5" /> Find Matching Jobs
                </Button>
              </div>
            </div>
          </CardHeader>
        </Card>
      )}

      {/* Pipeline Funnel Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-3">
        {pipelineStages.map((stage) => (
          <Card key={stage.key} className="stat-card hover:shadow-sm transition-all">
            <CardContent className="p-4 sm:p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="stat-label text-xs">{stage.label}</p>
                  <p className="stat-value text-xl">{formatNumber(getStatValue(stage.key))}</p>
                </div>
                <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center', stage.color)}>
                  <stage.icon className="w-4 h-4 text-white" />
                </div>
              </div>
              <Progress
                value={getStatValue(stage.key)}
                max={getStatValue('discovered') || 1}
                className="mt-2.5 h-1.5"
                showLabel={false}
              />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Interactive Bottom Widgets: Quick Actions + Live Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <QuickActions />
        <RecentActivity />
      </div>
    </div>
  )
}