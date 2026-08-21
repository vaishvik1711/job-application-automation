import { Application, ApplicationStatus } from '@/types'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { cn, formatRelativeTime, formatDateTime } from '@/utils/helpers'
import {
  Building2,
  MapPin,
  Calendar,
  Clock,
  FileText,
  Download,
  ExternalLink,
  Play,
  CheckCircle,
  XCircle,
  AlertCircle,
} from 'lucide-react'
import { downloadResume } from '@/utils/download'

const STATUS_COLORS: Record<ApplicationStatus, string> = {
  READY_TO_APPLY: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  APPLYING: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  NEEDS_REVIEW: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  SUBMITTED: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300',
  INTERVIEW_SCHEDULED: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  INTERVIEWED: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  OFFER: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  FAILED: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  REJECTED: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  WITHDRAWN: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
}

const STATUS_ICONS: Record<ApplicationStatus, React.ComponentType<{ className?: string }>> = {
  READY_TO_APPLY: Clock,
  APPLYING: AlertCircle,
  NEEDS_REVIEW: AlertCircle,
  SUBMITTED: CheckCircle,
  INTERVIEW_SCHEDULED: Calendar,
  INTERVIEWED: Calendar,
  OFFER: CheckCircle,
  FAILED: XCircle,
  REJECTED: XCircle,
  WITHDRAWN: XCircle,
}

const STATUS_LABELS: Record<ApplicationStatus, string> = {
  READY_TO_APPLY: 'Ready to Apply',
  APPLYING: 'Applying',
  NEEDS_REVIEW: 'Needs Review',
  SUBMITTED: 'Submitted',
  INTERVIEW_SCHEDULED: 'Interview Scheduled',
  INTERVIEWED: 'Interviewed',
  OFFER: 'Offer!',
  FAILED: 'Failed',
  REJECTED: 'Rejected',
  WITHDRAWN: 'Withdrawn',
}

interface ApplicationCardProps {
  application: Application
  onClick?: () => void
  isDragging?: boolean
  /** Present only on Ready-to-Apply cards — quick apply button */
  onApply?: (app: Application) => void
}

export function ApplicationCard({ application, onClick, isDragging, onApply }: ApplicationCardProps) {
  const { job, resume, status, applied_at, interview_date, notes, follow_up_date } = application
  const StatusIcon = STATUS_ICONS[status]
  const statusLabel = STATUS_LABELS[status]

  return (
    <Card
      className={cn(
        'cursor-pointer transition-all duration-200',
        isDragging && 'opacity-50 rotate-2',
        'hover:shadow-md'
      )}
      onClick={onClick}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-sm font-semibold text-slate-900 dark:text-white line-clamp-1">
              {job.title}
            </CardTitle>
            <CardDescription className="mt-1 flex items-center gap-1 text-xs text-slate-600 dark:text-slate-400">
              <Building2 className="w-3 h-3 flex-shrink-0" />
              <span className="truncate">{job.company}</span>
            </CardDescription>
          </div>
          <Badge className={cn('text-xs', STATUS_COLORS[status])}>
            <StatusIcon className="w-3 h-3 mr-1" />
            {statusLabel}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="pt-0 space-y-3">
        {/* Location */}
        <div className="flex items-center gap-1 text-xs text-slate-600 dark:text-slate-400">
          <MapPin className="w-3 h-3" />
          {[job.location.city, job.location.state, job.location.country]
            .filter(Boolean)
            .join(', ')}
          {job.location.remote && <span className="text-green-600 dark:text-green-400">· Remote</span>}
        </div>

        {/* Timeline Info */}
        <div className="flex flex-col gap-1.5 text-xs">
          {applied_at && (
            <div className="flex items-center gap-1 text-slate-600 dark:text-slate-400">
              <Clock className="w-3 h-3" />
              Applied {formatRelativeTime(applied_at)}
            </div>
          )}
          {interview_date && (
            <div className="flex items-center gap-1 text-purple-600 dark:text-purple-400">
              <Calendar className="w-3 h-3" />
              Interview {formatDateTime(interview_date)}
            </div>
          )}
          {follow_up_date && (
            <div className="flex items-center gap-1 text-amber-600 dark:text-amber-400">
              <Calendar className="w-3 h-3" />
              Follow up {formatDateTime(follow_up_date)}
            </div>
          )}
        </div>

        {/* Resume & Notes */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-200 dark:border-slate-700">
          {resume && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                downloadResume(resume.id, job.title)
              }}
              className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
              title="Download resume"
            >
              <FileText className="w-3 h-3" />
              <span>{resume.format?.toUpperCase?.() || 'DOCX'} resume</span>
              <Download className="w-3 h-3 ml-1" />
            </button>
          )}
          <div className="flex items-center gap-1">
            {job.source_url && (
              <a
                href={job.source_url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                aria-label={`View ${job.title} posting`}
              >
                <ExternalLink className="w-3 h-3 text-slate-400 dark:text-slate-500" />
              </a>
            )}
          </div>
        </div>

        {/* Notes Preview */}
        {notes && (
          <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2">{notes}</p>
        )}

        {/* Quick apply — only offered on Ready cards; stops drag/click propagation */}
        {onApply && (
          <Button
            size="sm"
            className="w-full"
            onClick={(e) => {
              e.stopPropagation()
              onApply(application)
            }}
          >
            <Play className="w-3 h-3 mr-1" /> Apply
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
