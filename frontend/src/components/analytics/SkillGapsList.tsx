import { SkillGap } from '@/types'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { cn } from '@/utils/helpers'
import {
  AlertTriangle,
  AlertCircle,
  CheckCircle,
  BookOpen,
  ExternalLink,
} from 'lucide-react'

interface SkillGapsListProps {
  gaps: SkillGap[]
}

const SEVERITY_VARIANTS: Record<string, 'danger' | 'warning' | 'neutral' | 'success'> = {
  high: 'danger',
  medium: 'warning',
  low: 'neutral',
}

const SEVERITY_COLORS: Record<string, string> = {
  high: 'text-red-600 dark:text-red-400',
  medium: 'text-orange-600 dark:text-orange-400',
  low: 'text-yellow-600 dark:text-yellow-400',
}

const SEVERITY_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  high: AlertCircle,
  medium: AlertTriangle,
  low: CheckCircle,
}

export function SkillGapsList({ gaps }: SkillGapsListProps) {
  if (!gaps || gaps.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Skill Gap Analysis</CardTitle>
          <CardDescription>No skill gaps identified</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8 text-center">
            <CheckCircle className="w-8 h-8 text-green-500 mb-2" />
            <p className="text-slate-500 dark:text-slate-400">
              No significant skill gaps found. Your profile is well-aligned.
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Sort by severity
  const sortedGaps = [...gaps].sort((a, b) => {
    const order = { high: 0, medium: 1, low: 2 }
    return (order[a.severity] || 3) - (order[b.severity] || 3)
  })

  const highCount = gaps.filter((g) => g.severity === 'high').length
  const mediumCount = gaps.filter((g) => g.severity === 'medium').length
  const lowCount = gaps.filter((g) => g.severity === 'low').length

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BookOpen className="w-5 h-5" />
          Skill Gap Analysis
        </CardTitle>
        <CardDescription>
          Skills that are frequently required but missing from your profile
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary */}
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="p-2 bg-red-50 dark:bg-red-900/10 rounded-lg">
            <p className="text-2xl font-bold text-red-600 dark:text-red-400">{highCount}</p>
            <p className="text-xs text-slate-600 dark:text-slate-400">High Priority</p>
          </div>
          <div className="p-2 bg-orange-50 dark:bg-orange-900/10 rounded-lg">
            <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">{mediumCount}</p>
            <p className="text-xs text-slate-600 dark:text-slate-400">Medium Priority</p>
          </div>
          <div className="p-2 bg-yellow-50 dark:bg-yellow-900/10 rounded-lg">
            <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">{lowCount}</p>
            <p className="text-xs text-slate-600 dark:text-slate-400">Low Priority</p>
          </div>
        </div>

        {/* Gap List */}
        <div className="space-y-2">
          {sortedGaps.map((gap) => {
            const Icon = SEVERITY_ICONS[gap.severity] || AlertTriangle
            return (
              <div
                key={gap.skill}
                className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-slate-700"
              >
                <div className="flex items-center gap-3">
                  <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center', 'bg-slate-200 dark:bg-slate-700')}>
                    <Icon className={cn('w-4 h-4', SEVERITY_COLORS[gap.severity])} />
                  </div>
                  <div>
                    <p className="font-medium text-slate-900 dark:text-white">{gap.skill}</p>
                    {gap.candidate_level && (
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                        Your level: {gap.candidate_level}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={SEVERITY_VARIANTS[gap.severity]} className="text-xs">
                    {gap.severity}
                  </Badge>
                  <Badge variant="neutral" className="text-xs">
                    Required by {gap.required_count || 0} jobs
                  </Badge>
                  <a
                    href={`https://www.linkedin.com/search/results/all/?keywords=${encodeURIComponent(gap.skill)}}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                    title={`Search for ${gap.skill} learning resources`}
                  >
                    <ExternalLink className="w-3 h-3 text-slate-400 dark:text-slate-500" />
                  </a>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
