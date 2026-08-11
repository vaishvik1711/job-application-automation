import { HTMLAttributes, forwardRef } from 'react'
import { cn } from '@/utils/helpers'

export interface ProgressProps extends HTMLAttributes<HTMLDivElement> {
  value: number
  max?: number
  showLabel?: boolean
  label?: string
}

export const Progress = forwardRef<HTMLDivElement, ProgressProps>(
  ({ className, value, max = 100, showLabel = true, label, ...props }, ref) => {
    const percentage = Math.min(Math.max((value / max) * 100, 0), 100)

    return (
      <div ref={ref} className={cn('w-full', className)} {...props}>
        {(showLabel || label) && (
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-slate-600 dark:text-slate-400">{label || 'Progress'}</span>
            <span className="font-medium text-slate-900 dark:text-white">{Math.round(percentage)}%</span>
          </div>
        )}
        <div className="progress-bar" role="progressbar" aria-valuenow={percentage} aria-valuemin={0} aria-valuemax={100}>
          <div className="progress-fill" style={{ width: `${percentage}%` }} />
        </div>
      </div>
    )
  }
)
Progress.displayName = 'Progress'