import { HTMLAttributes, forwardRef } from 'react'
import { cn } from '@/utils/helpers'

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'neutral'
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'neutral', ...props }, ref) => {
    const variantStyles = {
      primary: 'badge-primary',
      success: 'badge-success',
      warning: 'badge-warning',
      danger: 'badge-danger',
      neutral: 'badge-neutral',
    }

    return (
      <span ref={ref} className={cn('badge', variantStyles[variant], className)} {...props} />
    )
  }
)
Badge.displayName = 'Badge'