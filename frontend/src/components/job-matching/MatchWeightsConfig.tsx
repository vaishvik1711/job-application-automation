import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { useMatchingStore, useUIStore } from '@/store'
import { useUpdateMatchingWeights, useUpdateMatchingThreshold } from '@/hooks/useApi'
import { Settings, Save, RotateCcw, Zap, Award, Target, CheckCircle, BarChart3 } from 'lucide-react'
import { toast } from 'sonner'

const WEIGHT_FIELDS: { key: keyof typeof defaultWeights; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { key: 'skills', label: 'Skills', icon: Zap },
  { key: 'experience', label: 'Experience', icon: Award },
  { key: 'education', label: 'Education', icon: CheckCircle },
  { key: 'location', label: 'Location', icon: Target },
  { key: 'keywords', label: 'Keywords', icon: BarChart3 },
]

const defaultWeights = {
  skills: 0.35,
  experience: 0.25,
  education: 0.15,
  location: 0.1,
  keywords: 0.15,
}

export function MatchWeightsConfig() {
  const { weights, threshold, setWeights, setThreshold } = useMatchingStore()
  const { addNotification } = useUIStore()

  const updateWeightsMutation = useUpdateMatchingWeights()
  const updateThresholdMutation = useUpdateMatchingThreshold()

  const totalWeight = Object.values(weights).reduce((sum, w) => sum + w, 0)
  const isWeightValid = Math.abs(totalWeight - 1) < 0.01
  const isThresholdValid = threshold >= 0 && threshold <= 100

  const handleWeightChange = (key: keyof typeof weights, value: number) => {
    const newWeight = value / 100
    const newWeights = { ...weights, [key]: newWeight }
    setWeights(newWeights)
  }

  const handleThresholdChange = (value: number) => {
    setThreshold(Math.max(0, Math.min(100, value)))
  }

  const handleSave = async () => {
    if (!isWeightValid) {
      toast.error('Weights must sum to 100%')
      return
    }

    try {
      await updateWeightsMutation.mutateAsync(weights as Record<string, never> & typeof defaultWeights)
      await updateThresholdMutation.mutateAsync(threshold)
      toast.success('Matching settings saved successfully')
      addNotification({ type: 'success', message: 'Matching settings updated' })
    } catch (err: any) {
      toast.error('Failed to save settings')
    }
  }

  const handleReset = () => {
    setWeights({
      skills: 0.35,
      experience: 0.25,
      education: 0.15,
      location: 0.1,
      keywords: 0.15,
    })
    setThreshold(70)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Settings className="w-5 h-5" />
          Matching Configuration
        </CardTitle>
        <CardDescription>Configure how jobs are scored against your profile</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Weights */}
        <div className="space-y-4">
          <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-2">
            <Zap className="w-4 h-4" />
            Weight Distribution
          </h4>
          {WEIGHT_FIELDS.map(({ key, label, icon: Icon }) => {
            const weightPercent = Math.round(weights[key] * 100)
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
                  className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full appearance-none cursor-pointer slider"
                />
              </div>
            )
          })}
        </div>

        {/* Total Weight */}
        <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Total Weight</span>
          <Badge variant={isWeightValid ? 'success' : 'danger'} className="text-sm">
            {Math.round(totalWeight * 100)}%
          </Badge>
        </div>

        {/* Threshold */}
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-2">
            <Target className="w-4 h-4" />
            Auto-Qualify Threshold
          </h4>
          <div className="flex items-center gap-4">
            <input
              type="range"
              min="0"
              max="100"
              value={threshold}
              onChange={(e) => handleThresholdChange(Number(e.target.value))}
              className="flex-1 h-2 bg-slate-200 dark:bg-slate-700 rounded-full appearance-none cursor-pointer slider"
            />
            <div className="w-16 text-center">
              <Badge variant="primary" className="text-sm">
                {threshold}%
              </Badge>
            </div>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Jobs scoring above this threshold are automatically marked as qualified.
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 pt-2 border-t border-slate-200 dark:border-slate-700">
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!isWeightValid || !isThresholdValid || updateWeightsMutation.isPending}
            loading={updateWeightsMutation.isPending}
          >
            <Save className="w-4 h-4 mr-2" /> Save Settings
          </Button>
          <Button variant="outline" size="sm" onClick={handleReset}>
            <RotateCcw className="w-4 h-4 mr-2" /> Reset to Defaults
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
