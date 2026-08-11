import { useState } from 'react'
import { Job } from '@/types'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { cn, formatRelativeTime, truncate } from '@/utils/helpers'
import {
  ExternalLink,
  Bookmark,
  BookmarkCheck,
  MapPin,
  Building2,
  Clock,
  Briefcase,
  ArrowRight,
  CheckCircle,
} from 'lucide-react'

const STATUS_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  DISCOVERED: Clock,
  DEDUPLICATED: Briefcase,
  MATCHED: Bookmark,
  QUALIFIED: CheckCircle,
  RESUME_CREATED: ArrowRight,
  READY_TO_APPLY: ArrowRight,
  APPLIED: Briefcase,
  TRACKED: Bookmark,
}

const STATUS_COLORS: Record<string, string> = {
  DISCOVERED: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  DEDUPLICATED: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  MATCHED: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  QUALIFIED: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  RESUME_CREATED: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  READY_TO_APPLY: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300',
  APPLIED: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300',
  TRACKED: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
}

const JOB_TYPE_COLORS: Record<string, string> = {
  full_time: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  part_time: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  contract: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  internship: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  temporary: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
}

const EXPERIENCE_LEVEL_LABELS: Record<string, string> = {
  entry: 'Entry',
  mid: 'Mid',
  senior: 'Senior',
  lead: 'Lead',
  executive: 'Executive',
}

interface JobCardProps {
  job: Job
  isSelected?: boolean
  onSelect?: () => void
  showMatchScore?: boolean
  matchScore?: number
  onAnalyze?: () => void
}

export function JobCard({ job, isSelected, onSelect, showMatchScore, matchScore, onAnalyze }: JobCardProps) {
  const [isBookmarked, setIsBookmarked] = useState(false)
  const StatusIcon = STATUS_ICONS[job.status] || Clock

  const handleBookmark = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsBookmarked(!isBookmarked)
  }

  const handleExternalLink = (e: React.MouseEvent) => {
    e.stopPropagation()
    window.open(job.source_url, '_blank', 'noopener,noreferrer')
  }

  return (
    <Card
      className={cn(
        'transition-all duration-200 cursor-pointer hover:shadow-md',
        isSelected && 'ring-2 ring-primary-500 shadow-lg'
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
            </CardDescription>
          </div>
          <div className="flex items-center gap-1">
            {isSelected && (
              <div className="w-5 h-5 rounded bg-primary-500 flex items-center justify-center">
                <span className="text-white text-xs">✓</span>
              </div>
            )}
            <button
              onClick={handleBookmark}
              className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              aria-label={isBookmarked ? 'Remove bookmark' : 'Bookmark this job'}
            >
              {isBookmarked ? (
                <BookmarkCheck className="w-4 h-4 text-primary-600 dark:text-primary-400" />
              ) : (
                <Bookmark className="w-4 h-4 text-slate-400 dark:text-slate-500" />
              )}
            </button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3 pt-0">
        {/* Location and Type */}
        <div className="flex flex-wrap gap-2 text-sm">
          <Badge variant="neutral" className="flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            <span>
              {[job.location.city, job.location.state, job.location.country]
                .filter(Boolean)
                .join(', ')}
            </span>
          </Badge>
          <Badge className={cn('text-xs', JOB_TYPE_COLORS[job.job_type] || 'bg-slate-100 text-slate-700')}>
            {job.job_type.replace('_', ' ')}
          </Badge>
          <Badge variant="neutral" className="text-xs">
            {EXPERIENCE_LEVEL_LABELS[job.experience_level] || job.experience_level}
          </Badge>
          {job.location.remote && (
            <Badge variant="success" className="text-xs">
              Remote
            </Badge>
          )}
        </div>

        {/* Match Score */}
        {showMatchScore && matchScore !== undefined && (
          <div className="flex items-center gap-2">
            <div className="flex-1 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-500 transition-all"
                style={{ width: `${matchScore}%` }}
              />
            </div>
            <span className="text-xs font-medium text-slate-700 dark:text-slate-300 w-12">
              {matchScore}% match
            </span>
          </div>
        )}

        {/* Source & Status */}
        <div className="flex items-center justify-between pt-2">
          <div className="flex items-center gap-2">
            <Badge className={cn('text-xs', STATUS_COLORS[job.status] || STATUS_COLORS.DISCOVERED)}>
              <StatusIcon className="w-3 h-3 mr-1" />
              {job.status.replace('_', ' ')}
            </Badge>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              from {job.source.replace('_', ' ')}
            </span>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              • {formatRelativeTime(job.posted_date)}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {onAnalyze && (
              <Button variant="outline" size="sm" onClick={(e) => { e.stopPropagation(); onAnalyze() }}>
                Analyze
              </Button>
            )}
            <button
              onClick={handleExternalLink}
              className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              aria-label={`View ${job.title} at ${job.company}`}
            >
              <ExternalLink className="w-4 h-4 text-slate-400 dark:text-slate-500" />
            </button>
          </div>
        </div>

        {/* Description Preview */}
        {job.description && (
          <p className="text-sm text-slate-600 dark:text-slate-400 line-clamp-2">
            {truncate(job.description, 200)}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
