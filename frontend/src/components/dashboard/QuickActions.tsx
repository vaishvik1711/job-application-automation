import {
  Upload,
  Search,
  Kanban,
  BarChart3,
  Settings,
  ArrowRight,
  CheckCircle,
  Clock,
  AlertTriangle,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { cn } from '@/utils/helpers'
import { useNavigate } from 'react-router-dom'

interface QuickAction {
  label: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  href: string
  status?: 'ready' | 'in_progress' | 'completed' | 'needs_setup'
  badge?: string
}

const quickActions: QuickAction[] = [
  {
    label: 'Build Profile',
    description: 'Upload resume & refine candidate profile',
    icon: Upload,
    href: '/profile',
    status: 'ready',
    badge: 'Step 1',
  },
  {
    label: 'Search & Match Jobs',
    description: 'Discover jobs and score against your profile',
    icon: Search,
    href: '/jobs',
    status: 'ready',
    badge: 'Step 2',
  },
  {
    label: 'Track Applications',
    description: 'Manage your active application pipeline',
    icon: Kanban,
    href: '/applications',
    status: 'ready',
  },
  {
    label: 'View Analytics',
    description: 'Track conversion funnel and skill gaps',
    icon: BarChart3,
    href: '/analytics',
    status: 'ready',
  },
  {
    label: 'System Settings',
    description: 'Configure LLM model and job search sources',
    icon: Settings,
    href: '/settings',
    status: 'ready',
  },
]

const statusStyles = {
  ready: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  in_progress: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  completed: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  needs_setup: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
}

const statusIcons = {
  ready: ArrowRight,
  in_progress: Clock,
  completed: CheckCircle,
  needs_setup: AlertTriangle,
}

export function QuickActions() {
  const navigate = useNavigate()

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Quick Actions</CardTitle>
      </CardHeader>
      <CardContent className="p-4 space-y-3">
        {quickActions.map((action) => {
          const Icon = action.icon
          const StatusIcon = statusIcons[action.status || 'ready']
          return (
            <button
              key={action.label}
              onClick={() => navigate(action.href)}
              className={cn(
                'w-full p-4 rounded-lg border border-slate-200 dark:border-slate-700',
                'hover:border-primary-300 dark:hover:border-primary-700',
                'hover:bg-primary-50 dark:hover:bg-primary-900/10',
                'transition-all duration-200 text-left flex items-center gap-4'
              )}
            >
              <div className="w-10 h-10 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
                <Icon className="w-5 h-5 text-primary-600 dark:text-primary-400" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-medium text-slate-900 dark:text-white">{action.label}</p>
                  {action.badge && (
                    <Badge variant="primary" className="text-xs">
                      {action.badge}
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{action.description}</p>
              </div>
              <div className={cn('flex items-center gap-1.5 text-xs font-medium', statusStyles[action.status || 'ready'])}>
                <StatusIcon className="w-3 h-3" />
                <span>{action.status?.replace('_', ' ') || 'Ready'}</span>
              </div>
            </button>
          )
        })}
      </CardContent>
    </Card>
  )
}