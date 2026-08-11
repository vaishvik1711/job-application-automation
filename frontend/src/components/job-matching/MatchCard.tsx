import { MatchDetail } from '@/types'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { cn, formatRelativeTime } from '@/utils/helpers'
import {
  CheckCircle,
  XCircle,
  Building2,
  Clock,
  Calendar,
  ExternalLink,
  Zap,
  Award,
} from 'lucide-react'

interface MatchCardProps {
  match: MatchDetail
  isSelected?: boolean
  onSelect?: () => void
  onGenerateResume?: () => void
  compact?: boolean
}

const SCORE_COLORS = (score: number): string => {
  if (score >= 85) return 'text-green-600 dark:text-green-400'
  if (score >= 70) return 'text-blue-600 dark:text-blue-400'
  if (score >= 50) return 'text-orange-600 dark:text-orange-400'
  return 'text-red-600 dark:text-red-400'
}

const VERDICT_STYLES = {
  QUALIFIED: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  UNQUALIFIED: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
}

const VERDICT_ICONS = {
  QUALIFIED: CheckCircle,
  UNQUALIFIED: XCircle,
}

function ScoreBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-600 dark:text-slate-400">{label}</span>
        <span className={cn('font-medium', color)}>{Math.round(value)}%</span>
      </div>
      <div className="h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${value}%`,
            backgroundColor: color.includes('green') ? '#10b981' : color.includes('blue') ? '#3b82f6' : color.includes('orange') ? '#f97316' : '#ef4444',
          }}
        />
      </div>
    </div>
  )
}

export function MatchCard({ match, isSelected, onSelect, onGenerateResume, compact = false }: MatchCardProps) {
  const { job, score, missing_requirements, matched_keywords, analyzed_at } = match
  const overallScore = Math.round(score.overall)
  const scoreColor = SCORE_COLORS(overallScore)
  const VerdictIcon = VERDICT_ICONS[score.verdict]

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
            <div className={cn('flex items-center gap-1 px-3 py-1 rounded-full', VERDICT_STYLES[score.verdict])}>
              <VerdictIcon className="w-3 h-3" />
              <span className="text-xs font-medium">{score.verdict.replace('_', ' ')}</span>
            </div>
            <div className={cn('text-2xl font-bold', scoreColor)}>
              {overallScore}%
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-0">
        {/* Score Breakdown */}
        {!compact && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <ScoreBar label="Skills" value={score.skills} color={scoreColor} />
            <ScoreBar label="Experience" value={score.experience} color={scoreColor} />
            <ScoreBar label="Education" value={score.education} color={scoreColor} />
            <ScoreBar label="Location" value={score.location} color={scoreColor} />
            <ScoreBar label="Keywords" value={score.keywords} color={scoreColor} />
          </div>
        )}

        {/* Skill & Keyword Matches */}
        {!compact && (
          <div className="space-y-3">
            {matched_keywords.length > 0 && (
              <div>
                <p className="text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5 flex items-center gap-1">
                  <Zap className="w-3 h-3" /> Matched Keywords
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {matched_keywords.slice(0, 8).map((kw) => (
                    <Badge key={kw} variant="primary" className="text-xs py-0.5">
                      {kw}
                    </Badge>
                  ))}
                  {matched_keywords.length > 8 && (
                    <Badge variant="neutral" className="text-xs py-0.5">
                      +{matched_keywords.length - 8} more
                    </Badge>
                  )}
                </div>
              </div>
            )}

            {missing_requirements.length > 0 && (
              <div>
                <p className="text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5 flex items-center gap-1">
                  <XCircle className="w-3 h-3" /> Missing Requirements
                </p>
                <ul className="list-disc list-inside text-sm text-slate-600 dark:text-slate-400 space-y-0.5">
                  {missing_requirements.slice(0, 5).map((req, i) => (
                    <li key={i}>{req}</li>
                  ))}
                  {missing_requirements.length > 5 && (
                    <li>+{missing_requirements.length - 5} more</li>
                  )}
                </ul>
              </div>
            )}
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
