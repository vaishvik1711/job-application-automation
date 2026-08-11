import { Briefcase, Target, FileText, CheckCircle, TrendingUp } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { formatRelativeTime, cn } from '@/utils/helpers'

interface ActivityItem {
  id: string
  type: 'job_found' | 'match_complete' | 'resume_generated' | 'application_submitted' | 'interview_scheduled'
  title: string
  description: string
  timestamp: string
  metadata?: Record<string, unknown>
}

const mockActivities: ActivityItem[] = [
  {
    id: '1',
    type: 'job_found',
    title: 'New job discovered',
    description: 'Senior Software Engineer at TechCorp',
    timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
  },
  {
    id: '2',
    type: 'match_complete',
    title: 'Match analysis complete',
    description: 'Frontend Developer at StartupXYZ - Score: 87%',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
  },
  {
    id: '3',
    type: 'resume_generated',
    title: 'Resume generated',
    description: 'Customized for Backend Engineer at DataFlow Inc',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(),
  },
  {
    id: '4',
    type: 'application_submitted',
    title: 'Application submitted',
    description: 'Full Stack Developer at CloudNine',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
  },
  {
    id: '5',
    type: 'interview_scheduled',
    title: 'Interview scheduled',
    description: 'Technical interview with DevTeam Co - Tomorrow 2pm',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(),
  },
]

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
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y divide-slate-200 dark:divide-slate-700">
          {mockActivities.map((activity) => {
            const Icon = activityIcons[activity.type]
            return (
              <div key={activity.id} className="p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                <div className="flex items-start gap-3">
                  <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0', activityColors[activity.type])}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900 dark:text-white">{activity.title}</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{activity.description}</p>
                    <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">{formatRelativeTime(activity.timestamp)}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
        <div className="p-4 text-center">
          <button className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 font-medium">
            View all activity →
          </button>
        </div>
      </CardContent>
    </Card>
  )
}