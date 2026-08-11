import { ValidationResult } from '@/types'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Progress } from '@/components/ui/Progress'
import { cn, formatRelativeTime } from '@/utils/helpers'
import {
  AlertTriangle,
  XCircle,
  Info,
  Shield,
  FileText,
  Download,
  RefreshCw,
} from 'lucide-react'

interface ResumeValidationProps {
  result: ValidationResult
  onDownload?: (format: 'docx' | 'pdf') => void
  onRevalidate?: () => void
  isDownloading?: boolean
  isRevalidating?: boolean
}

const ISSUE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  exaggeration: XCircle,
  missing_keyword: AlertTriangle,
  formatting: AlertTriangle,
  inconsistency: Info,
  truthfulness: Shield,
}

const ISSUE_COLORS: Record<string, string> = {
  exaggeration: 'text-red-600 dark:text-red-400',
  missing_keyword: 'text-orange-600 dark:text-orange-400',
  formatting: 'text-blue-600 dark:text-blue-400',
  inconsistency: 'text-yellow-600 dark:text-yellow-400',
  truthfulness: 'text-purple-600 dark:text-purple-400',
}

const SEVERITY_VARIANTS: Record<string, 'danger' | 'warning' | 'neutral' | 'success' | 'primary'> = {
  high: 'danger',
  medium: 'warning',
  low: 'neutral',
}

export function ResumeValidation({ result, onDownload, onRevalidate, isDownloading, isRevalidating }: ResumeValidationProps) {
  const truthfulnessScore = Math.round(result.truthfulness_score * 100)
  const atsScore = Math.round(result.ats_score * 100)

  const getScoreVariant = (score: number): 'success' | 'warning' | 'danger' => {
    if (score >= 80) return 'success'
    if (score >= 60) return 'warning'
    return 'danger'
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5" />
              Validation Results
            </CardTitle>
            <CardDescription>
              Validated {formatRelativeTime(result.validated_at)}
            </CardDescription>
          </div>
          {onRevalidate && (
            <Badge variant="neutral" className="text-xs">
              {result.issues.length} issues found
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Score Summary */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Card variant="outline" className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300 flex items-center gap-2">
                <Shield className="w-4 h-4" /> Truthfulness
              </span>
              <Badge variant={getScoreVariant(truthfulnessScore)} className="text-sm">
                {truthfulnessScore}%
              </Badge>
            </div>
            <Progress value={truthfulnessScore} max={100} showLabel={false} className="h-2" />
          </Card>
          <Card variant="outline" className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300 flex items-center gap-2">
                <FileText className="w-4 h-4" /> ATS Compatibility
              </span>
              <Badge variant={getScoreVariant(atsScore)} className="text-sm">
                {atsScore}%
              </Badge>
            </div>
            <Progress value={atsScore} max={100} showLabel={false} className="h-2" />
          </Card>
        </div>

        {/* Issues */}
        {result.issues.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
              Issues ({result.issues.length})
            </h4>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {result.issues.map((issue, i) => {
                const Icon = ISSUE_ICONS[issue.type] || Info
                return (
                  <div
                    key={i}
                    className="flex items-start gap-3 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-slate-700"
                  >
                    <Icon className={cn('w-4 h-4 mt-0.5 flex-shrink-0', ISSUE_COLORS[issue.type])} />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm text-slate-900 dark:text-white">
                          {[issue.type.charAt(0).toUpperCase(), issue.type.slice(1).replace('_', ' ')]}
                        </span>
                        <Badge variant={SEVERITY_VARIANTS[issue.severity]} className="text-xs">
                          {issue.severity}
                        </Badge>
                      </div>
                      <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">{issue.message}</p>
                      {issue.location && (
                        <p className="text-xs text-slate-500 dark:text-slate-500 mt-1">
                          Location: {issue.location}
                        </p>
                      )}
                      {issue.suggestion && (
                        <p className="text-xs text-slate-500 dark:text-slate-500 mt-1">
                          Suggestion: {issue.suggestion}
                        </p>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Suggestions */}
        {result.suggestions.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
              Suggestions ({result.suggestions.length})
            </h4>
            <ul className="list-disc list-inside text-sm text-slate-600 dark:text-slate-400 space-y-1">
              {result.suggestions.map((suggestion, i) => (
                <li key={i}>{suggestion}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Actions */}
        {(onDownload || onRevalidate) && (
          <div className="flex items-center gap-3 pt-4 border-t border-slate-200 dark:border-slate-700">
            {onDownload && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onDownload('pdf')}
                  disabled={isDownloading}
                >
                  <Download className="w-4 h-4 mr-2" />
                  Download PDF
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onDownload('docx')}
                  disabled={isDownloading}
                >
                  <Download className="w-4 h-4 mr-2" />
                  Download DOCX
                </Button>
              </>
            )}
            {onRevalidate && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onRevalidate}
                disabled={isRevalidating}
                loading={isRevalidating}
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Revalidate
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
