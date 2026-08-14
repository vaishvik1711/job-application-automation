import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { LLMSettings } from '@/types'
import { useTestLLM } from '@/hooks/useApi'
import {
  Brain,
  TestTube,
  CheckCircle,
  AlertCircle,
  Save,
  Key,
  Server,
  Thermometer,
  Hash,
} from 'lucide-react'
import { toast } from 'sonner'

const LLM_SCHEMA = z.object({
  provider: z.enum(['nvidia']),
  model: z.string().min(1, 'Model name is required'),
  api_key: z.string().optional(),
  base_url: z.string().url('Invalid URL').optional().or(z.literal('')),
  temperature: z.number().min(0).max(1),
  max_tokens: z.number().min(1).max(100000),
})

type LLMFormData = z.infer<typeof LLM_SCHEMA>

interface LLMSettingsFormProps {
  settings?: LLMSettings
  onChange?: (settings: Partial<LLMSettings>) => void
  onSave?: () => void
}

const PROVIDER_OPTIONS = [
  { value: 'nvidia', label: 'NVIDIA', description: 'Nemotron (free via OpenRouter)' },
]

export function LLMSettingsForm({ settings, onChange, onSave }: LLMSettingsFormProps) {
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; latency: number } | null>(null)
  const [showApiKey, setShowApiKey] = useState(false)

  const testLLMMutation = useTestLLM()

  const form = useForm<LLMFormData>({
    resolver: zodResolver(LLM_SCHEMA),
    defaultValues: settings || {
      provider: 'nvidia',
      model: 'nvidia/nemotron-3-ultra-550b-a55b:free',
      api_key: '',
      base_url: '',
      temperature: 0.7,
      max_tokens: 4000,
    },
  })

  const provider = form.watch('provider')

  // Auto-update model when provider changes
  const handleProviderChange = (newProvider: string) => {
    form.setValue('provider', newProvider as LLMFormData['provider'])
    form.setValue('model', 'nvidia/nemotron-3-ultra-550b-a55b:free')
  }

  const handleTestConnection = async () => {
    const data = form.getValues()
    setIsTesting(true)
    setTestResult(null)

    const start = Date.now()
    try {
      const result = await testLLMMutation.mutateAsync({
        provider: data.provider,
        model: data.model,
        api_key: data.api_key,
      })
      const latency = Date.now() - start

      setTestResult({
        success: result.success,
        message: result.success ? 'Connection successful!' : 'Connection failed',
        latency,
      })

      if (result.success) {
        toast.success('LLM connection test passed')
      } else {
        toast.error('LLM connection test failed')
      }
    } catch (err: any) {
      const latency = Date.now() - start
      setTestResult({
        success: false,
        message: err.message || 'Connection failed',
        latency,
      })
      toast.error('LLM connection test failed')
    } finally {
      setIsTesting(false)
    }
  }

  const handleFormChange = (updated: Partial<LLMFormData>) => {
    onChange?.({ ...settings, ...updated })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Brain className="w-5 h-5" />
          LLM Configuration
        </CardTitle>
        <CardDescription>
          Configure the language model used for resume parsing, job matching, and analysis
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Provider Selection */}
        <div className="space-y-3">
          <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Provider</label>
          <div className="grid grid-cols-1 gap-3">
            {PROVIDER_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => handleProviderChange(opt.value)}
                className={
                  provider === opt.value
                    ? 'border-2 border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                    : 'border border-slate-200 dark:border-slate-700 hover:border-primary-300'
                }
                style={{ padding: '12px', borderRadius: '8px', textAlign: 'left' }}
              >
                <p className="font-medium text-slate-900 dark:text-white text-sm">{opt.label}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{opt.description}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Model */}
        <div>
          <label htmlFor="model" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Model Name
          </label>
          <Input
            id="model"
            {...form.register('model')}
            placeholder="nvidia/nemotron-3-ultra-550b-a55b:free"
            error={form.formState.errors.model?.message}
            onChange={(e) => handleFormChange({ model: e.target.value })}
          />
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
            Free model via OpenRouter
          </p>
        </div>

        {/* API Key */}
        <div>
          <label htmlFor="api_key" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            API Key
          </label>
          <div className="relative">
            <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              id="api_key"
              type={showApiKey ? 'text' : 'password'}
              {...form.register('api_key')}
              placeholder="sk-..."
              className="pl-10"
              onChange={(e) => handleFormChange({ api_key: e.target.value })}
            />
            <button
              type="button"
              onClick={() => setShowApiKey(!showApiKey)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              aria-label={showApiKey ? 'Hide API key' : 'Show API key'}
            >
              {showApiKey ? 'Hide' : 'Show'}
            </button>
          </div>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
            API key is stored securely and never logged
          </p>
        </div>

        {/* Base URL */}
        <div>
          <label htmlFor="base_url" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Base URL (Optional)
          </label>
          <div className="relative">
            <Server className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              id="base_url"
              {...form.register('base_url')}
              placeholder="https://openrouter.ai/api/v1"
              className="pl-10"
              onChange={(e) => handleFormChange({ base_url: e.target.value })}
            />
          </div>
        </div>

        {/* Temperature & Max Tokens */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label htmlFor="temperature" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Temperature
            </label>
            <div className="flex items-center gap-2">
              <Thermometer className="w-4 h-4 text-slate-400" />
              <input
                type="range"
                id="temperature"
                min="0"
                max="1"
                step="0.1"
                value={form.watch('temperature')}
                onChange={(e) => {
                  const temp = Number(e.target.value)
                  form.setValue('temperature', temp)
                  handleFormChange({ temperature: temp })
                }}
                className="flex-1 h-2 bg-slate-200 dark:bg-slate-700 rounded-full appearance-none cursor-pointer"
              />
              <span className="text-sm font-medium text-slate-900 dark:text-white w-12">
                {form.watch('temperature').toFixed(1)}
              </span>
            </div>
            <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 mt-1">
              <span>Conservative (0)</span>
              <span>Creative (1)</span>
            </div>
          </div>

          <div>
            <label htmlFor="max_tokens" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Max Tokens
            </label>
            <div className="relative">
              <Hash className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                id="max_tokens"
                type="number"
                {...form.register('max_tokens', { valueAsNumber: true })}
                placeholder="4000"
                className="pl-10"
                onChange={(e) => handleFormChange({ max_tokens: Number(e.target.value) })}
                error={form.formState.errors.max_tokens?.message}
              />
            </div>
          </div>
        </div>

        {/* Test Connection */}
        <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={handleTestConnection} loading={isTesting}>
              <TestTube className="w-4 h-4 mr-2" /> Test Connection
            </Button>
            {testResult && (
              <div
                className={
                  testResult.success
                    ? 'flex items-center gap-2 text-green-600 dark:text-green-400'
                    : 'flex items-center gap-2 text-red-600 dark:text-red-400'
                }
              >
                {testResult.success ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                <span className="text-sm font-medium">
                  {testResult.message} ({testResult.latency}ms)
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Save Button */}
        {onSave && (
          <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
            <Button onClick={onSave} disabled={isTesting}>
              <Save className="w-4 h-4 mr-2" /> Save LLM Settings
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
