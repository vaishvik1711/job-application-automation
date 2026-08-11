import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { MatchingSettings, MatchWeights } from '@/types'
import { Save, Zap, Target, CheckCircle, BarChart3 } from 'lucide-react'

const MATCHING_SCHEMA = z.object({
  default_weights: z.object({
    skills: z.number().min(0).max(1),
    experience: z.number().min(0).max(1),
    education: z.number().min(0).max(1),
    location: z.number().min(0).max(1),
    keywords: z.number().min(0).max(1),
  }),
  auto_qualify_threshold: z.number().min(0).max(100),
  min_skill_match: z.number().min(0).max(100),
})

type MatchingFormData = z.infer<typeof MATCHING_SCHEMA>

const WEIGHT_FIELDS: { key: keyof MatchWeights; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { key: 'skills', label: 'Skills', icon: Zap },
  { key: 'experience', label: 'Experience', icon: BarChart3 },
  { key: 'education', label: 'Education', icon: CheckCircle },
  { key: 'location', label: 'Location', icon: Target },
  { key: 'keywords', label: 'Keywords', icon: Zap },
]

interface MatchingSettingsFormProps {
  settings?: MatchingSettings
  onChange?: (settings: Partial<MatchingSettings>) => void
  onSave?: () => void
}

export function MatchingSettingsForm({ settings, onChange, onSave }: MatchingSettingsFormProps) {
  const form = useForm<MatchingFormData>({
    resolver: zodResolver(MATCHING_SCHEMA),
    defaultValues: {
      default_weights: settings?.default_weights || {
        skills: 0.35,
        experience: 0.25,
        education: 0.15,
        location: 0.1,
        keywords: 0.15,
      },
      auto_qualify_threshold: settings?.auto_qualify_threshold || 70,
      min_skill_match: settings?.min_skill_match || 60,
    },
  })

  const weights = form.watch('default_weights')
  const totalWeight = Object.values(weights).reduce((sum, w) => sum + w, 0)
  const isWeightValid = Math.abs(totalWeight - 1) < 0.01

  const handleWeightChange = (key: keyof MatchWeights, value: number) => {
    const newWeight = value / 100
    form.setValue(`default_weights.${key}` as any, newWeight)

    const newWeights = { ...weights, [key]: newWeight }
    onChange?.({ default_weights: newWeights })
  }

  const handleSubmit = (data: MatchingFormData) => {
    onChange?.({
      default_weights: data.default_weights,
      auto_qualify_threshold: data.auto_qualify_threshold,
      min_skill_match: data.min_skill_match,
    })
    if (onSave) onSave()
  }

  const handleReset = () => {
    form.setValue('default_weights', {
      skills: 0.35,
      experience: 0.25,
      education: 0.15,
      location: 0.1,
      keywords: 0.15,
    })
    form.setValue('auto_qualify_threshold', 70)
    form.setValue('min_skill_match', 60)
    onChange?.({
      default_weights: {
        skills: 0.35,
        experience: 0.25,
        education: 0.15,
        location: 0.1,
        keywords: 0.15,
      },
      auto_qualify_threshold: 70,
      min_skill_match: 60,
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Target className="w-5 h-5" />
          Matching Configuration
        </CardTitle>
        <CardDescription>
          Configure how jobs are scored and qualified against your profile
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
          {/* Weight Distribution */}
          <div className="space-y-4">
            <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-2">
              <Zap className="w-4 h-4" /> Weight Distribution
            </h4>
            {WEIGHT_FIELDS.map(({ key, label, icon: Icon }) => {
              const weightValue = form.watch(`default_weights.${key}` as any) as number
              const weightPercent = Math.round(weightValue * 100)

              return (
                <div key={key} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Icon className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                      <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{label}</span>
                    </div>
                    <Badge variant={weightPercent >= 25 ? 'primary' : weightPercent >= 10 ? 'neutral' : 'warning'}>
                      {weightPercent}%
                    </Badge>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={weightPercent}
                    onChange={(e) => handleWeightChange(key, Number(e.target.value))}
                    className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full appearance-none cursor-pointer"
                  />
                </div>
              )
            })}
          </div>

          {/* Total Weight Check */}
          <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Total Weight</span>
            <Badge variant={isWeightValid ? 'success' : 'danger'} className="text-sm">
              {Math.round(totalWeight * 100)}%
            </Badge>
          </div>

          {/* Thresholds */}
          <div className="space-y-4 pt-4 border-t border-slate-200 dark:border-slate-700">
            <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Qualification Thresholds</h4>

            <div className="space-y-2">
              <label htmlFor="auto_qualify_threshold" className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Auto-Qualify Threshold (%)
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  id="auto_qualify_threshold"
                  min="0"
                  max="100"
                  value={form.watch('auto_qualify_threshold')}
                  onChange={(e) => {
                    const val = Number(e.target.value)
                    form.setValue('auto_qualify_threshold', val)
                    onChange?.({ auto_qualify_threshold: val })
                  }}
                  className="flex-1 h-2 bg-slate-200 dark:bg-slate-700 rounded-full appearance-none cursor-pointer"
                />
                <div className="w-16 text-center">
                  <Badge variant="primary" className="text-sm">
                    {form.watch('auto_qualify_threshold')}%
                  </Badge>
                </div>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Jobs scoring above this threshold are automatically marked as qualified.
              </p>
            </div>

            <div className="space-y-2">
              <label htmlFor="min_skill_match" className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Minimum Skill Match (%)
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  id="min_skill_match"
                  min="0"
                  max="100"
                  value={form.watch('min_skill_match')}
                  onChange={(e) => {
                    const val = Number(e.target.value)
                    form.setValue('min_skill_match', val)
                    onChange?.({ min_skill_match: val })
                  }}
                  className="flex-1 h-2 bg-slate-200 dark:bg-slate-700 rounded-full appearance-none cursor-pointer"
                />
                <div className="w-16 text-center">
                  <Badge variant="primary" className="text-sm">
                    {form.watch('min_skill_match')}%
                  </Badge>
                </div>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Minimum skill match percentage required for a job to be considered.
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 pt-4 border-t border-slate-200 dark:border-slate-700">
            <Button type="submit" disabled={!isWeightValid}>
              <Save className="w-4 h-4 mr-2" /> Save Matching Settings
            </Button>
            <Button type="button" variant="outline" onClick={handleReset}>
              Reset to Defaults
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
