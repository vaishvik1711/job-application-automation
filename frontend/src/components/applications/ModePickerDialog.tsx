import { useState } from 'react'
import { ApplyMode } from '@/types'
import { Button } from '@/components/ui/Button'
import { cn } from '@/utils/helpers'
import { ShieldCheck, Zap, X } from 'lucide-react'

interface ModePickerDialogProps {
  open: boolean
  count: number
  autoSubmitEnabled: boolean
  isStarting: boolean
  onClose: () => void
  onStart: (mode: ApplyMode) => void
}

/**
 * Choose how the bot submits before an apply run:
 * - Manual (default): fills the form, parks it — nothing is sent until you
 *   review and confirm.
 * - Auto: submits end-to-end. Only selectable when the server has
 *   AUTO_SUBMIT=true; otherwise shown locked with the reason.
 */
export function ModePickerDialog({
  open,
  count,
  autoSubmitEnabled,
  isStarting,
  onClose,
  onStart,
}: ModePickerDialogProps) {
  const [mode, setMode] = useState<ApplyMode>('manual')

  if (!open) return null

  const options: Array<{
    value: ApplyMode
    title: string
    description: string
    icon: React.ComponentType<{ className?: string }>
    disabled?: boolean
    disabledReason?: string
  }> = [
    {
      value: 'manual',
      title: 'Manual review first (recommended)',
      description: 'Bot fills everything headless, then waits for you to check and confirm the final Submit.',
      icon: ShieldCheck,
    },
    {
      value: 'auto',
      title: 'Fully automatic',
      description: 'Bot reviews and submits by itself using verified answers only.',
      icon: Zap,
      disabled: !autoSubmitEnabled,
      disabledReason: 'Disabled — AUTO_SUBMIT=false on the server',
    },
  ]

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-slate-900 rounded-xl shadow-xl max-w-lg w-full mx-4 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              Apply to {count} application{count > 1 ? 's' : ''}
            </h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              How should submissions happen?
            </p>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Close">
            <X className="w-4 h-4 text-slate-500" />
          </button>
        </div>

        <div className="space-y-2">
          {options.map((opt) => (
            <button
              key={opt.value}
              onClick={() => !opt.disabled && setMode(opt.value)}
              disabled={opt.disabled}
              className={cn(
                'w-full flex items-start gap-3 rounded-lg border p-4 text-left transition-colors',
                mode === opt.value && !opt.disabled
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                  : 'border-slate-200 dark:border-slate-700 hover:border-slate-300',
                opt.disabled && 'opacity-60 cursor-not-allowed'
              )}
            >
              <opt.icon className="w-5 h-5 mt-0.5 text-primary-500 flex-shrink-0" />
              <span>
                <span className="block text-sm font-medium text-slate-900 dark:text-white">
                  {opt.title}
                </span>
                <span className="block text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  {opt.disabled ? opt.disabledReason : opt.description}
                </span>
              </span>
            </button>
          ))}
        </div>

        <p className="text-xs text-slate-400 dark:text-slate-500 mt-3">
          Supported sites: JobBank Canada, Greenhouse boards, Lever postings. CAPTCHAs and
          unknown questions always route to Needs Review — never guessed.
        </p>

        <div className="flex justify-end gap-2 mt-4">
          <Button variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button size="sm" loading={isStarting} onClick={() => onStart(mode)}>
            Start apply ({count})
          </Button>
        </div>
      </div>
    </div>
  )
}
