import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { cn } from '@/utils/helpers'
import { NotificationSettings } from '@/types'
import { Save, Bell, Mail, Smartphone, Webhook, Globe, Calendar, FileText } from 'lucide-react'

const NOTIFICATION_SCHEMA = z.object({
  email_enabled: z.boolean(),
  email_address: z.string().email('Invalid email address').optional().or(z.literal('')),
  browser_enabled: z.boolean(),
  webhook_url: z.string().url('Invalid URL').optional().or(z.literal('')),
  events: z.object({
    job_found: z.boolean(),
    match_complete: z.boolean(),
    resume_generated: z.boolean(),
    application_submitted: z.boolean(),
    interview_scheduled: z.boolean(),
  }),
})

type NotificationFormData = z.infer<typeof NOTIFICATION_SCHEMA>

const EVENT_OPTIONS = [
  { key: 'job_found', label: 'Job Found', icon: Globe, description: 'Notify when new jobs are discovered' },
  { key: 'match_complete', label: 'Match Complete', icon: Bell, description: 'Notify when job matching analysis is complete' },
  { key: 'resume_generated', label: 'Resume Generated', icon: FileText, description: 'Notify when a resume is generated' },
  { key: 'application_submitted', label: 'Application Submitted', icon: Mail, description: 'Notify when an application is submitted' },
  { key: 'interview_scheduled', label: 'Interview Scheduled', icon: Calendar, description: 'Notify when an interview is scheduled' },
]

interface NotificationSettingsFormProps {
  settings?: NotificationSettings
  onChange?: (settings: Partial<NotificationSettings>) => void
  onSave?: () => void
}

export function NotificationSettingsForm({ settings, onChange, onSave }: NotificationSettingsFormProps) {
  const form = useForm<NotificationFormData>({
    resolver: zodResolver(NOTIFICATION_SCHEMA),
    defaultValues: {
      email_enabled: settings?.email_enabled || false,
      email_address: settings?.email_address || '',
      browser_enabled: settings?.browser_enabled || true,
      webhook_url: settings?.webhook_url || '',
      events: {
        job_found: settings?.events?.job_found ?? true,
        match_complete: settings?.events?.match_complete ?? true,
        resume_generated: settings?.events?.resume_generated ?? true,
        application_submitted: settings?.events?.application_submitted ?? true,
        interview_scheduled: settings?.events?.interview_scheduled ?? true,
      },
    },
  })

  const handleSubmit = (data: NotificationFormData) => {
    onChange?.(data)
    if (onSave) onSave()
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bell className="w-5 h-5" />
          Notification Settings
        </CardTitle>
        <CardDescription>
          Configure how and when you receive notifications about your job search pipeline
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
          {/* Channels */}
          <div className="space-y-4">
            <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Notification Channels</h4>

            {/* Email */}
            <div className="border border-slate-200 dark:border-slate-700 rounded-lg p-4 space-y-3">
              <div className="flex items-center gap-3">
                <Mail className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                <div>
                  <h5 className="font-medium text-slate-900 dark:text-white">Email Notifications</h5>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    Receive notifications via email
                  </p>
                </div>
                <div className="ml-auto">
                  <button
                    type="button"
                    onClick={() => form.setValue('email_enabled', !form.watch('email_enabled'))}
                    className={cn(
                      'relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2',
                      form.watch('email_enabled') ? 'bg-primary-500' : 'bg-slate-300 dark:bg-slate-600'
                    )}
                  >
                    <span
                      className={cn(
                        'absolute inline-block h-5 w-5 transform rounded-full bg-white transition',
                        form.watch('email_enabled') ? 'translate-x-5' : 'translate-x-1'
                      )}
                    />
                  </button>
                </div>
              </div>

              {form.watch('email_enabled') && (
                <div className="ml-8">
                  <label htmlFor="email_address" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Email Address
                  </label>
                  <Input
                    id="email_address"
                    type="email"
                    {...form.register('email_address')}
                    placeholder="notifications@example.com"
                    error={form.formState.errors.email_address?.message}
                    onChange={(e) => form.setValue('email_address', e.target.value)}
                  />
                </div>
              )}
            </div>

            {/* Browser */}
            <div className="border border-slate-200 dark:border-slate-700 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <Smartphone className="w-5 h-5 text-green-600 dark:text-green-400" />
                <div>
                  <h5 className="font-medium text-slate-900 dark:text-white">Browser Notifications</h5>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    Receive real-time notifications in your browser
                  </p>
                </div>
                <div className="ml-auto">
                  <button
                    type="button"
                    onClick={() => form.setValue('browser_enabled', !form.watch('browser_enabled'))}
                    className={cn(
                      'relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2',
                      form.watch('browser_enabled') ? 'bg-primary-500' : 'bg-slate-300 dark:bg-slate-600'
                    )}
                  >
                    <span
                      className={cn(
                        'absolute inline-block h-5 w-5 transform rounded-full bg-white transition',
                        form.watch('browser_enabled') ? 'translate-x-5' : 'translate-x-1'
                      )}
                    />
                  </button>
                </div>
              </div>
            </div>

            {/* Webhook */}
            <div className="border border-slate-200 dark:border-slate-700 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <Webhook className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                <div className="flex-1">
                  <h5 className="font-medium text-slate-900 dark:text-white">Webhook URL</h5>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    Send notifications to a custom webhook endpoint
                  </p>
                  <div className="mt-2">
                    <Input
                      {...form.register('webhook_url')}
                      placeholder="https://hooks.example.com/webhook"
                      error={form.formState.errors.webhook_url?.message}
                      onChange={(e) => form.setValue('webhook_url', e.target.value)}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Event Toggles */}
          <div className="space-y-3 pt-4 border-t border-slate-200 dark:border-slate-700">
            <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Event Notifications</h4>
            {EVENT_OPTIONS.map(({ key, label, icon: Icon, description }) => {
              const fieldName = key as keyof NotificationFormData['events']
              const isEnabled = form.watch('events')[fieldName]

              return (
                <div
                  key={key}
                  className="flex items-center justify-between p-3 border border-slate-200 dark:border-slate-700 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <Icon className="w-5 h-5 text-slate-500 dark:text-slate-400" />
                    <div>
                      <p className="font-medium text-slate-900 dark:text-white">{label}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">{description}</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      form.setValue('events', {
                        ...form.watch('events'),
                        [key]: !isEnabled,
                      } as any)
                    }
                    className={cn(
                      'relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2',
                      isEnabled ? 'bg-primary-500' : 'bg-slate-300 dark:bg-slate-600'
                    )}
                  >
                    <span
                      className={cn(
                        'absolute inline-block h-5 w-5 transform rounded-full bg-white transition',
                        isEnabled ? 'translate-x-5' : 'translate-x-1'
                      )}
                    />
                  </button>
                </div>
              )
            })}
          </div>

          {/* Save */}
          <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
            <Button type="submit">
              <Save className="w-4 h-4 mr-2" /> Save Notification Settings
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
