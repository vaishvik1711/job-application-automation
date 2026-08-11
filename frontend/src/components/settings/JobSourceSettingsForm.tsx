import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { cn } from '@/utils/helpers'
import { JobSourceSettings } from '@/types'
import { useTestJobSource } from '@/hooks/useApi'
import {
  Globe,
  TestTube,
  CheckCircle,
  AlertCircle,
  Save,
  ToggleLeft,
  ToggleRight,
} from 'lucide-react'
import { toast } from 'sonner'

const JOB_SOURCE_CONFIGS: Record<string, { name: string; description: string }> = {
  indeed: { name: 'Indeed', description: 'Large job board with wide coverage' },
  linkedin: { name: 'LinkedIn', description: 'Professional network job listings' },
  glassdoor: { name: 'Glassdoor', description: 'Job listings with salary data' },
  jobbank: { name: 'JobBank', description: 'Canadian job board' },
  company_careers: { name: 'Company Careers', description: 'Direct company career sites' },
  other: { name: 'Other', description: 'Custom job sources' },
}

const DEFAULT_SOURCES = ['indeed', 'linkedin', 'glassdoor', 'jobbank', 'company_careers']

interface JobSourceSettingsFormProps {
  settings?: JobSourceSettings
  onChange?: (settings: JobSourceSettings) => void
  onSave?: () => void
}

export function JobSourceSettingsForm({ settings, onChange, onSave }: JobSourceSettingsFormProps) {
  const [testingSource, setTestingSource] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string; jobsFound: number } | null>>(
    {}
  )

  const testSourceMutation = useTestJobSource()

  const sourceSettings = settings || {}

  const handleToggleSource = (sourceKey: string) => {
    const current = sourceSettings[sourceKey] || { enabled: true }
    const newSettings: JobSourceSettings = {
      ...sourceSettings,
      [sourceKey]: { ...current, enabled: !current.enabled },
    }
    onChange?.(newSettings)
  }

  const handleConfigChange = (sourceKey: string, field: string, value: any) => {
    const current = sourceSettings[sourceKey] || { enabled: true }
    const newSettings: JobSourceSettings = {
      ...sourceSettings,
      [sourceKey]: { ...current, [field]: value },
    }
    onChange?.(newSettings)
  }

  const handleTestSource = async (sourceKey: string) => {
    const config = sourceSettings[sourceKey]
    if (!config) return

    setTestingSource(sourceKey)
    setTestResults((prev) => ({ ...prev, [sourceKey]: null }))

    try {
      const result = await testSourceMutation.mutateAsync({ source: sourceKey, config: config.config || {} })

      setTestResults((prev) => ({
        ...prev,
        [sourceKey]: {
          success: result.success,
          message: result.success ? 'Connection successful!' : 'Connection failed',
          jobsFound: result.jobs_found || 0,
        },
      }))

      if (result.success) {
        toast.success(`${JOB_SOURCE_CONFIGS[sourceKey]?.name || sourceKey} connection test passed`)
      } else {
        toast.error(`${JOB_SOURCE_CONFIGS[sourceKey]?.name || sourceKey} connection test failed`)
      }
    } catch (err: any) {
      setTestResults((prev) => ({
        ...prev,
        [sourceKey]: {
          success: false,
          message: err.message || 'Connection failed',
          jobsFound: 0,
        },
      }))
      toast.error('Job source test failed')
    } finally {
      setTestingSource(null)
    }
  }

  const enabledCount = DEFAULT_SOURCES.filter((s) => sourceSettings[s]?.enabled !== false).length

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Globe className="w-5 h-5" />
          Job Sources
        </CardTitle>
        <CardDescription>
          Configure which job boards to search and their API credentials
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary */}
        <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400 mb-4">
          <Badge variant="primary" className="text-xs">
            {enabledCount} of {DEFAULT_SOURCES.length} sources enabled
          </Badge>
        </div>

        {/* Source List */}
        <div className="space-y-3">
          {DEFAULT_SOURCES.map((sourceKey) => {
            const config = sourceSettings[sourceKey] || { enabled: true }
            const isEnabled = config.enabled
            const sourceInfo = JOB_SOURCE_CONFIGS[sourceKey] || { name: sourceKey, description: '' }
            const testResult = testResults[sourceKey]

            return (
              <div
                key={sourceKey}
                className="border border-slate-200 dark:border-slate-700 rounded-lg p-4 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                      <Globe className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                    </div>
                    <div>
                      <h4 className="font-medium text-slate-900 dark:text-white">{sourceInfo.name}</h4>
                      <p className="text-sm text-slate-500 dark:text-slate-400">{sourceInfo.description}</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleToggleSource(sourceKey)}
                    className={cn(
                      'relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500',
                      isEnabled ? 'bg-primary-500' : 'bg-slate-300 dark:bg-slate-600'
                    )}
                    aria-label={isEnabled ? 'Disable' : 'Enable'}
                  >
                    {isEnabled ? (
                      <ToggleRight className="w-5 h-5 text-white absolute left-6" />
                    ) : (
                      <ToggleLeft className="w-5 h-5 text-white absolute left-1" />
                    )}
                  </button>
                </div>

                {/* Credentials (visible when enabled) */}
                {isEnabled && config.credentials && Object.keys(config.credentials).length > 0 && (
                  <div className="ml-12 space-y-2 pt-2">
                    <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                      Credentials
                    </label>
                    {Object.entries(config.credentials).map(([key, value]) => (
                      <Input
                        key={key}
                        placeholder={key}
                        defaultValue={value as string}
                        type="password"
                        className="text-sm"
                        onChange={(e) =>
                          handleConfigChange(sourceKey, 'credentials', {
                            ...config.credentials,
                            [key]: e.target.value,
                          })
                        }
                      />
                    ))}
                  </div>
                )}

                {/* Additional Config */}
                {isEnabled && config.config && Object.keys(config.config).length > 0 && (
                  <div className="ml-12 space-y-2 pt-2">
                    <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                      Additional Configuration
                    </label>
                    {Object.entries(config.config).map(([key, value]) => (
                      <Input
                        key={key}
                        placeholder={key}
                        defaultValue={String(value)}
                        className="text-sm"
                        onChange={(e) =>
                          handleConfigChange(sourceKey, 'config', {
                            ...config.config,
                            [key]: e.target.value,
                          })
                        }
                      />
                    ))}
                  </div>
                )}

                {/* Rate Limit */}
                {isEnabled && (
                  <div className="ml-12 pt-2">
                    <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                      Rate Limit (requests/minute)
                    </label>
                    <Input
                      type="number"
                      defaultValue={config.rate_limit || 60}
                      onChange={(e) => handleConfigChange(sourceKey, 'rate_limit', Number(e.target.value))}
                    />
                  </div>
                )}

                {/* Test Button */}
                <div className="ml-12 pt-2">
                  {testResult ? (
                    <div
                      className={cn(
                        'flex items-center gap-2 text-sm',
                        testResult.success
                          ? 'text-green-600 dark:text-green-400'
                          : 'text-red-600 dark:text-red-400'
                      )}
                    >
                      {testResult.success ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                      <span>{testResult.message}</span>
                      {testResult.success && testResult.jobsFound > 0 && <span>(Found {testResult.jobsFound} jobs)</span>}
                    </div>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTestSource(sourceKey)}
                      disabled={!isEnabled || testingSource === sourceKey}
                      loading={testingSource === sourceKey}
                    >
                      <TestTube className="w-4 h-4 mr-2" /> Test Connection
                    </Button>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {/* Save Button */}
        {onSave && (
          <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
            <Button onClick={onSave}>
              <Save className="w-4 h-4 mr-2" /> Save Job Source Settings
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
