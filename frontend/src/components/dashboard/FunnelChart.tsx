import { cn } from '@/utils/helpers'

interface FunnelStage {
  label: string
  value: number
  color: string
}

interface FunnelChartProps {
  stages: FunnelStage[]
  className?: string
}

export function FunnelChart({ stages, className }: FunnelChartProps) {
  const maxValue = Math.max(...stages.map((s) => s.value), 1)

  return (
    <div className={cn('space-y-3', className)}>
      {stages.map((stage, index) => {
        const width = (stage.value / maxValue) * 100
        const isLast = index === stages.length - 1

        return (
          <div key={stage.label} className="relative">
            <div className="flex items-center gap-3">
              <div className="w-24 text-right text-sm font-medium text-slate-700 dark:text-slate-300 pr-2">
                {stage.label}
              </div>
              <div className="flex-1 relative">
                <div
                  className="h-10 rounded-lg bg-slate-100 dark:bg-slate-800 overflow-hidden relative"
                  style={{ minWidth: '100%' }}
                >
                  <div
                    className="h-full rounded-lg transition-all duration-500 ease-out flex items-center justify-center"
                    style={{
                      width: `${width}%`,
                      backgroundColor: `var(--${stage.color}-500)`,
                      minWidth: width > 0 ? '2rem' : 0,
                    }}
                  >
                    {width > 15 && (
                      <span className="text-white text-xs font-medium px-2">
                        {stage.value}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="w-16 text-right text-sm text-slate-500 dark:text-slate-400">
                {maxValue > 0 ? `${Math.round((stage.value / maxValue) * 100)}%` : '0%'}
              </div>
            </div>
            {!isLast && (
              <div
                className="absolute left-24 right-16 -top-1.5 h-1.5 bg-gradient-to-r from-transparent via-slate-200 dark:via-slate-700 to-transparent"
              />
            )}
          </div>
        )
      })}
    </div>
  )
}