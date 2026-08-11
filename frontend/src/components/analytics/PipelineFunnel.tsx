import { PipelineStats } from '@/types'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { formatNumber } from '@/utils/helpers'
import {
  Briefcase,
  Target,
  CheckCircle,
  FileText,
  ArrowRight,
  BarChart3,
  ClipboardCheck,
  Gift,
  Trash2,
  TrendingUp,
} from 'lucide-react'

const PIPELINE_STAGES = [
  { key: 'discovered', label: 'Discovered', icon: Briefcase, color: 'bg-slate-500' },
  { key: 'deduplicated', label: 'Deduplicated', icon: Target, color: 'bg-blue-500' },
  { key: 'matched', label: 'Matched', icon: BarChart3, color: 'bg-purple-500' },
  { key: 'qualified', label: 'Qualified', icon: CheckCircle, color: 'bg-green-500' },
  { key: 'resume_created', label: 'Resume Created', icon: FileText, color: 'bg-orange-500' },
  { key: 'ready_to_apply', label: 'Ready to Apply', icon: ArrowRight, color: 'bg-indigo-500' },
  { key: 'applied', label: 'Applied', icon: TrendingUp, color: 'bg-pink-500' },
  { key: 'interviewed', label: 'Interviewed', icon: ClipboardCheck, color: 'bg-yellow-500' },
  { key: 'offers', label: 'Offers', icon: Gift, color: 'bg-green-600' },
  { key: 'rejected', label: 'Rejected', icon: Trash2, color: 'bg-red-500' },
] as const

interface PipelineFunnelProps {
  stats: PipelineStats
}

export function PipelineFunnel({ stats }: PipelineFunnelProps) {
  const maxValue = Math.max(...PIPELINE_STAGES.map((s) => stats[s.key as keyof PipelineStats] || 0), 1)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Application Pipeline</CardTitle>
        <CardDescription>Track jobs through each stage of the hiring pipeline</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {PIPELINE_STAGES.map((stage) => {
            const value = stats[stage.key as keyof PipelineStats] || 0
            const percentage = Math.round((value / maxValue) * 100)
            return (
              <div key={stage.key} className="relative">
                <div className="flex items-center gap-3">
                  <div className="w-28 text-right text-sm font-medium text-slate-700 dark:text-slate-300 pr-2">
                    {stage.label}
                  </div>
                  <div className="flex-1 relative">
                    <div className="h-10 rounded-lg bg-slate-100 dark:bg-slate-800 overflow-hidden">
                      <div
                        className="h-full rounded-lg transition-all duration-500 ease-out flex items-center"
                        style={{
                          width: percentage > 0 ? `${percentage}%` : '0%',
                          backgroundColor: stage.color.replace('bg-', '').replace('-500', ''),
                          opacity: stage.color.includes('500') ? 1 : 0.9,
                          minWidth: '2rem',
                        }}
                      >
                        {percentage > 10 && (
                          <span className="text-white text-xs font-medium px-2 whitespace-nowrap">
                            {formatNumber(value)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="w-20 text-right">
                    <span className="text-sm font-medium text-slate-900 dark:text-white">
                      {formatNumber(value)}
                    </span>
                    <span className="text-xs text-slate-500 dark:text-slate-400 block">
                      {percentage}%
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
