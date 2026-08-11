import { SourceEffectiveness } from '@/types'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { cn, formatNumber } from '@/utils/helpers'
import { Globe } from 'lucide-react'

interface SourceEffectivenessTableProps {
  sources: SourceEffectiveness[]
}

const SOURCE_COLORS: Record<string, string> = {
  indeed: 'bg-blue-500',
  linkedin: 'bg-blue-700',
  glassdoor: 'bg-green-500',
  jobbank: 'bg-purple-500',
  company_careers: 'bg-orange-500',
  other: 'bg-gray-500',
}

export function SourceEffectivenessTable({ sources }: SourceEffectivenessTableProps) {
  if (!sources || sources.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Source Effectiveness</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-slate-500 dark:text-slate-400 text-center py-8">
            No source data available yet. Run job searches to see effectiveness metrics.
          </p>
        </CardContent>
      </Card>
    )
  }

  const maxConversion = Math.max(...sources.map((s) => s.conversion_rate), 0.01)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Globe className="w-5 h-5" />
          Source Effectiveness
        </CardTitle>
        <CardDescription>Performance breakdown by job board / source</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {sources.map((source) => {
            const sourceKey = source.source as string
            const sourceColor = SOURCE_COLORS[sourceKey] || SOURCE_COLORS.other
            const barWidth = (source.conversion_rate / maxConversion) * 100

            return (
              <div key={source.source} className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={cn('w-3 h-3 rounded-full', sourceColor)} />
                    <span className="font-medium text-slate-900 dark:text-white capitalize">
                      {source.source.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant="neutral" className="text-xs">
                      {formatNumber(source.conversion_rate)}% conversion
                    </Badge>
                    <span className="text-xs text-slate-500 dark:text-slate-400">
                      {(source.offers || 0) > 0 && `${source.offers} offer(s)`}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-5 gap-2 text-center">
                  <div className="text-center">
                    <p className="text-sm font-medium text-slate-900 dark:text-white">{formatNumber(source.jobs_found)}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Found</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-medium text-slate-900 dark:text-white">{formatNumber(source.jobs_qualified || 0)}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Qualified</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-medium text-slate-900 dark:text-white">{formatNumber(source.applications_submitted || 0)}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Submitted</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-medium text-slate-900 dark:text-white">{formatNumber(source.interviews || 0)}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Interviews</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-medium text-slate-900 dark:text-white">{formatNumber(source.offers || 0)}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Offers</p>
                  </div>
                </div>

                <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary-500 rounded-full transition-all"
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
