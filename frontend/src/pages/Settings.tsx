import { useState } from 'react'
import { useSettings, useUpdateSettings } from '@/hooks/useApi'
import {
  AppSettings,
  LLMSettings,
  JobSourceSettings,
  MatchingSettings,
  NotificationSettings,
} from '@/types'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs'
import { LLMSettingsForm } from '@/components/settings/LLMSettingsForm'
import { JobSourceSettingsForm } from '@/components/settings/JobSourceSettingsForm'
import { MatchingSettingsForm } from '@/components/settings/MatchingSettingsForm'
import { NotificationSettingsForm } from '@/components/settings/NotificationSettingsForm'
import {
  Save,
  RefreshCw,
  Brain,
  Globe,
  Target,
  Bell,
  FileText,
} from 'lucide-react'
import { toast } from 'sonner'

export function Settings() {
  const { data: settings, isLoading, error, refetch } = useSettings()
  const updateSettingsMutation = useUpdateSettings()

  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState('llm')

  const [localSettings, setLocalSettings] = useState<Partial<AppSettings>>(settings || {})

  // Update local settings when data loads
  if (settings && !localSettings.llm) {
    setLocalSettings(settings)
  }

  const handleLLMChange = (llm: Partial<LLMSettings>) => {
    const newSettings = { ...localSettings, llm: { ...(localSettings.llm || {}), ...llm } } as Partial<AppSettings>
    setLocalSettings(newSettings)
  }

  const handleJobSourcesChange = (sources: JobSourceSettings) => {
    const newSettings = { ...localSettings, job_sources: sources }
    setLocalSettings(newSettings)
  }

  const handleMatchingChange = (matching: Partial<MatchingSettings>) => {
    const newSettings = { ...localSettings, matching: { ...(localSettings.matching || {}), ...matching } } as Partial<AppSettings>
    setLocalSettings(newSettings)
  }

  const handleNotificationsChange = (notifications: Partial<NotificationSettings>) => {
    const newSettings = { ...localSettings, notifications: { ...(localSettings.notifications || {}), ...notifications } } as Partial<AppSettings>
    setLocalSettings(newSettings)
  }

  const handleSaveAll = async () => {
    setSaving(true)
    try {
      await updateSettingsMutation.mutateAsync(localSettings)
      toast.success('All settings saved successfully')
      refetch()
    } catch (err: any) {
      console.error('Failed to save settings:', err)
      toast.error('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveSection = (section: string) => {
    toast.success(`${section} settings saved`)
  }

  if (isLoading) {
    return (
      <div className="space-y-6 animate-in">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Settings</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">Loading configuration...</p>
        </div>
        <div className="space-y-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <div className="h-5 bg-slate-200 dark:bg-slate-700 rounded animate-pulse w-1/4" />
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {[...Array(3)].map((_, j) => (
                    <div key={j} className="h-4 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6 animate-in">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Settings</h1>
        <Card className="border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20">
          <CardContent className="py-4">
            <p className="text-red-700 dark:text-red-300">
              Failed to load settings: {(error as Error).message}
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Settings</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Configure your job automation system
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
            <RefreshCw className="w-4 h-4 mr-2" /> Reload
          </Button>
          <Button onClick={handleSaveAll} disabled={saving || updateSettingsMutation.isPending}>
            <Save className="w-4 h-4 mr-2" />
            {saving ? 'Saving...' : 'Save All Settings'}
          </Button>
        </div>
      </div>

      {/* Settings Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-4 lg:w-auto">
          <TabsTrigger value="llm" className="flex items-center gap-2">
            <Brain className="w-4 h-4" /> LLM
          </TabsTrigger>
          <TabsTrigger value="sources" className="flex items-center gap-2">
            <Globe className="w-4 h-4" /> Job Sources
          </TabsTrigger>
          <TabsTrigger value="matching" className="flex items-center gap-2">
            <Target className="w-4 h-4" /> Matching
          </TabsTrigger>
          <TabsTrigger value="notifications" className="flex items-center gap-2">
            <Bell className="w-4 h-4" /> Notifications
          </TabsTrigger>
        </TabsList>

        {/* LLM Settings */}
        <TabsContent value="llm">
          <LLMSettingsForm
            settings={settings?.llm}
            onChange={handleLLMChange}
            onSave={() => handleSaveSection('LLM')}
          />
        </TabsContent>

        {/* Job Sources */}
        <TabsContent value="sources">
          <JobSourceSettingsForm
            settings={settings?.job_sources}
            onChange={handleJobSourcesChange}
            onSave={() => handleSaveSection('Job Sources')}
          />
        </TabsContent>

        {/* Matching Settings */}
        <TabsContent value="matching">
          <MatchingSettingsForm
            settings={settings?.matching}
            onChange={handleMatchingChange}
            onSave={() => handleSaveSection('Matching')}
          />
        </TabsContent>

        {/* Notifications */}
        <TabsContent value="notifications">
          <NotificationSettingsForm
            settings={settings?.notifications}
            onChange={handleNotificationsChange}
            onSave={() => handleSaveSection('Notifications')}
          />
        </TabsContent>
      </Tabs>

      {/* Resume Templates (always visible at bottom) */}
      {settings?.resume_templates && settings.resume_templates.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Resume Templates
            </CardTitle>
            <CardDescription>
              {settings.resume_templates.length} templates configured
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {settings.resume_templates.map((template) => (
                <div
                  key={template.id}
                  className="flex items-center justify-between p-3 border border-slate-200 dark:border-slate-700 rounded-lg"
                >
                  <div>
                    <p className="font-medium text-slate-900 dark:text-white">{template.name}</p>
                    {template.description && (
                      <p className="text-sm text-slate-500 dark:text-slate-400">{template.description}</p>
                    )}
                  </div>
                  {template.is_default && (
                    <Badge variant="primary" className="text-xs">
                      Default
                    </Badge>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
