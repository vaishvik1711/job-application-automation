import { Briefcase, Target, FileText, CheckCircle, TrendingUp, Clock, ArrowRight } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { formatRelativeTime, cn } from '@/utils/helpers'
import { useApplications, useResumes, useMatches } from '@/hooks/useApi'
import { useNavigate } from 'react-router-dom'

interface ActivityItem {
  id: string
  type: 'job_found' | 'match_complete' | 'resume_generated' | 'application_submitted' | 'interview_scheduled'
  title: string
  description: string
  timestamp: string
}

const activityIcons = {
  job_found: Briefcase,
  match_complete: Target,
  resume_generated: FileText,
  application_submitted: CheckCircle,
  interview_scheduled: TrendingUp,
}

const activityColors = {
  job_found: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  match_complete: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  resume_generated: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  application_submitted: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  interview_scheduled: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300',
}

export function RecentActivity() {
  const navigate = useNavigate()
  const { data: appsData } = useApplications({ page: 1, page_size: 5 })
  const { data: resumesData } = useResumes({ page: 1, page_size: 5 })
  const { data: matchesData } = useMatches({ page_size: 5 })

  // Derive recent activities from real data
  const activities: ActivityItem[] = []

  if (appsData?.items) {
    appsData.items.forEach((app) => {
      if (app.status === 'SUBMITTED' || app.status === 'APPLYING') {
        activities.push({
          id: `app-${app.id}`,
          type: 'application_submitted',
          title: `Application ${app.status.toLowerCase()}`,
          description: `${app.job?.title || 'Role'} at ${app.job?.company || 'Company'}`,
          timestamp: app.applied_at || app.created_at,
        })
      } else if (app.status === 'INTERVIEW_SCHEDULED' || app.status === 'INTERVIEWED') {
        activities.push({
          id: `app-${app.id}`,
          type: 'interview_scheduled',
          title: 'Interview Stage',
          description: `${app.job?.title || 'Role'} at ${app.job?.company || 'Company'}`,
          timestamp: app.interview_date || app.created_at,
        })
      }
    })
  }

  if (resumesData?.items) {
    resumesData.items.slice(0, 3).forEach((r) => {
      activities.push({
        id: `res-${r.id}`,
        type: 'resume_generated',
        title: 'Tailored resume generated',
        description: `Targeted for ${r.job_title || 'role'} at ${r.company || 'company'}`,
        timestamp: r.created_at,
      })
    })
  }

  if (matchesData?.items) {
    matchesData.items.slice(0, 3).forEach((m) => {
      activities.push({
        id: `match-${m.job_id}`,
        type: 'match_complete',
        title: 'Match score calculated',
        description: `${m.job?.title || 'Job'} (${Math.round(m.score?.overall || 0)}% fit)`,
        timestamp: m.analyzed_at || m.job?.posted_date || new Date().toISOString(),
      })
    })
  }

  // Sort latest first and cap at 5
  activities.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
  const displayActivities = activities.slice(0, 5)

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <CardTitle className="text-base flex items-center justify-between">
          <span>Recent Activity</span>
          {displayActivities.length > 0 && (
            <span className="text-xs font-normal text-slate-400">Live feed</span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0 flex-1 flex flex-col justify-between">
        {displayActivities.length === 0 ? (
          <div className="py-8 px-4 text-center text-slate-500 dark:text-slate-400">
            <Clock className="w-8 h-8 mx-auto mb-2 text-slate-300 dark:text-slate-600" />
            <p className="text-sm">No activity recorded yet</p>
            <p className="text-xs text-slate-400 mt-1">Upload a resume or search jobs to see activity here.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {displayActivities.map((activity) => {
              const Icon = activityIcons[activity.type] || Briefcase
              return (
                <div key={activity.id} className="p-3.5 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                  <div className="flex items-start gap-3">
                    <div className={cn('w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5', activityColors[activity.type])}>
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-slate-900 dark:text-white truncate">{activity.title}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 truncate">{activity.description}</p>
                      <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">{formatRelativeTime(activity.timestamp)}</p>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
        <div className="p-3 border-t border-slate-100 dark:border-slate-800 text-center">
          <button
            onClick={() => navigate('/applications')}
            className="text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400 font-medium inline-flex items-center gap-1"
          >
            <span>View application pipeline</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      </CardContent>
    </Card>
  )
}