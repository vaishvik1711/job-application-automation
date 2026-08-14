import { MatchDetail } from '@/types'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { cn, formatRelativeTime } from '@/utils/helpers'
import {
  CheckCircle,
  Building2,
  Clock,
  Calendar,
  ExternalLink,
  Award,
} from 'lucide-react'

interface MatchCardProps {
  match: MatchDetail
  isSelected?: boolean
  onSelect?: () => void
  onGenerateResume?: () => void
  compact?: boolean
}

const SKILL_COLOR = (score: number): string => {
  if (score >= 85) return 'text-green-600 dark:text-green-400'
  if (score >= 70) return 'text-blue-600 dark:text-blue-400'
  if (score >= 50) return 'text-orange-600 dark:text-orange-400'
  return 'text-red-600 dark:text-red-400'
}

const SKILL_BG = (score: number): string => {
  if (score >= 85) return 'bg-green-500'
  if (score >= 70) return 'bg-blue-500'
  if (score >= 50) return 'bg-orange-500'
  return 'bg-red-500'
}

export function MatchCard({ match, isSelected, onSelect, onGenerateResume, compact = false }: MatchCardProps) {
  const { job, score, analyzed_at } = match
  const skillScore = Math.round(score.skills)
  const skillColor = SKILL_COLOR(skillScore)

  const isQualified = skillScore >= 50

  return (
    <Card
      className={cn(
        'transition-all duration-200 cursor-pointer hover:shadow-md',
        isSelected && 'ring-2 ring-primary-500 shadow-lg',
        compact && 'py-4'
      )}
      onClick={onSelect}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-lg line-clamp-1">{job.title}</CardTitle>
            <CardDescription className="mt-1 flex items-center gap-2 text-slate-600 dark:text-slate-400">
              <Building2 className="w-4 h-4 flex-shrink-0" />
              <span className="truncate">{job.company}</span>
              <span>•</span>
              <span className="truncate">
                {[job.location.city, job.location.state, job.location.country].filter(Boolean).join(', ')}
              </span>
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {isQualified && (
              <CheckCircle className="w-5 h-5 text-green-500" />
            )}
            <div className={cn('text-2xl font-bold', skillColor)}>
              {skillScore}%
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-0">
        {/* Skills Bar — the only metric */}
        {!compact && (
          <div className="space-y-4">
            <div className="text-center">
              <div className="relative pt-1">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Skills Match</span>
                  <span className={cn('text-sm font-bold', skillColor)}>{skillScore}%</span>
                </div>
                <div className="h-2.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className={cn('h-full rounded-full transition-all duration-500', SKILL_BG(skillScore))}
                    style={{ width: `${skillScore}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" /> {formatRelativeTime(analyzed_at)}
            </span>
            <span className="flex items-center gap-1">
              <Calendar className="w-3 h-3" /> Posted {formatRelativeTime(job.posted_date)}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {onGenerateResume && (
              <Button variant="outline" size="sm" onClick={(e) => { e.stopPropagation(); onGenerateResume() }}>
                <Award className="w-4 h-4 mr-1" /> Generate Resume
              </Button>
            )}
            <a
              href={job.source_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              aria-label={`View ${job.title} at ${job.company}`}
            >
              <ExternalLink className="w-4 h-4 text-slate-400 dark:text-slate-500" />
            </a>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
