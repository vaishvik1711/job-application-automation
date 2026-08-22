import { MatchDetail } from '@/types'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Progress } from '@/components/ui/Progress'
import { cn, formatRelativeTime } from '@/utils/helpers'
import {
  X,
  Building2,
  MapPin,
  Calendar,
  ExternalLink,
  CheckCircle,
  Sparkles,
  Briefcase,
} from 'lucide-react'

interface MatchDetailModalProps {
  match: MatchDetail | null
  isOpen: boolean
  onClose: () => void
  onSelectAndApply?: (jobId: string) => void
  isSelected?: boolean
}

export function MatchDetailModal({
  match,
  isOpen,
  onClose,
  onSelectAndApply,
  isSelected,
}: MatchDetailModalProps) {
  if (!isOpen || !match) return null

  const { job, score } = match
  const overallScore = Math.round(score?.overall || 0)
  const skillsScore = Math.round(score?.skills || 0)
  const expScore = Math.round(score?.experience || 0)
  const eduScore = Math.round(score?.education || 0)

  // Extract matched skills vs missing skills
  const matchedSkills: string[] = (score as any)?.matched_skills || []
  const missingSkills: string[] = (score as any)?.missing_skills || []

  return (
    <div
      className={cn(
        'fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm transition-opacity duration-200',
        isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
      )}
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-slate-900 rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto border border-slate-200 dark:border-slate-800"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-start justify-between p-6 border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm">
          <div className="flex-1 min-w-0 pr-4">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-primary-600 dark:text-primary-400 flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5" /> AI Match Analysis
              </span>
            </div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white mt-1 line-clamp-1">
              {job.title}
            </h2>
            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 dark:text-slate-400 mt-1">
              <span className="flex items-center gap-1 font-medium text-slate-700 dark:text-slate-300">
                <Building2 className="w-3.5 h-3.5" /> {job.company}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5" />
                {[job.location.city, job.location.state, job.location.country].filter(Boolean).join(', ')}
                {job.location.remote && <Badge variant="success" className="text-[10px] ml-1 py-0 px-1">Remote</Badge>}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" /> Posted {formatRelativeTime(job.posted_date)}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Overall Match Gauge */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3.5 rounded-xl bg-primary-50/70 dark:bg-primary-900/20 border border-primary-100 dark:border-primary-800/40 text-center">
              <p className="text-xs font-medium text-slate-600 dark:text-slate-400">Overall Fit</p>
              <p className="text-2xl font-bold text-primary-600 dark:text-primary-400 mt-1">
                {overallScore}%
              </p>
              <Progress value={overallScore} className="mt-2 h-1" />
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-center">
              <p className="text-xs font-medium text-slate-600 dark:text-slate-400">Skills Match</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
                {skillsScore}%
              </p>
              <Progress value={skillsScore} className="mt-2 h-1" />
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-center">
              <p className="text-xs font-medium text-slate-600 dark:text-slate-400">Experience</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
                {expScore}%
              </p>
              <Progress value={expScore} className="mt-2 h-1" />
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-center">
              <p className="text-xs font-medium text-slate-600 dark:text-slate-400">Education</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
                {eduScore}%
              </p>
              <Progress value={eduScore} className="mt-2 h-1" />
            </div>
          </div>

          {/* Skills Breakdown */}
          <Card variant="outline">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-500" />
                Skills Alignment
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 pt-0">
              {matchedSkills.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">
                    Verified Matched Skills ({matchedSkills.length})
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {matchedSkills.map((s, i) => (
                      <span
                        key={i}
                        className="text-xs px-2.5 py-1 rounded-md bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800 font-medium"
                      >
                        ✓ {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {missingSkills.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">
                    Suggested Keywords to Emphasize ({missingSkills.length})
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {missingSkills.map((s, i) => (
                      <span
                        key={i}
                        className="text-xs px-2.5 py-1 rounded-md bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800"
                      >
                        + {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {matchedSkills.length === 0 && missingSkills.length === 0 && (
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Skills analysis scored this role at <strong>{skillsScore}%</strong> match based on your candidate profile.
                </p>
              )}
            </CardContent>
          </Card>

          {/* Job Description Preview */}
          <Card variant="outline">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Briefcase className="w-4 h-4 text-slate-500" />
                  Job Description
                </CardTitle>
                {job.source_url && (
                  <a
                    href={job.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400 flex items-center gap-1 font-medium"
                  >
                    <span>View original posting</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-slate-600 dark:text-slate-300 whitespace-pre-line leading-relaxed max-h-48 overflow-y-auto pr-2">
                {job.description || 'No detailed description available.'}
              </p>
            </CardContent>
          </Card>

          {/* Action Footer */}
          <div className="flex items-center justify-between pt-4 border-t border-slate-200 dark:border-slate-800">
            <Button variant="outline" size="sm" onClick={onClose}>
              Close
            </Button>
            {onSelectAndApply && (
              <Button
                size="sm"
                onClick={() => {
                  onSelectAndApply(job.id)
                  onClose()
                }}
              >
                <Sparkles className="w-4 h-4 mr-2" />
                {isSelected ? 'Selected for Batch Resume' : 'Select for Tailored Resume'}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
