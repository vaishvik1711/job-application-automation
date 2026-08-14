import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { User, Globe, Linkedin, Github, Twitter } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { cn } from '@/utils/helpers'
import { PersonalInfo } from '@/types'
import { useProfileStore } from '@/store/index'

const personalInfoSchema = z.object({
  full_name: z.string().min(2, 'Full name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  phone: z.string().optional(),
  location: z.string().optional(),
  website: z.string().url('Invalid URL').optional().or(z.literal('')),
  linkedin: z.string().url('Invalid URL').optional().or(z.literal('')),
  github: z.string().url('Invalid URL').optional().or(z.literal('')),
  twitter: z.string().url('Invalid URL').optional().or(z.literal('')),
  summary: z.string().max(600, 'Summary must be less than 600 characters').optional(),
})

type PersonalInfoFormData = z.infer<typeof personalInfoSchema>

interface PersonalInfoFormProps {
  initialData?: PersonalInfo
  onSave: (data: PersonalInfoFormData) => Promise<void>
  isLoading?: boolean
}

export function PersonalInfoForm({ initialData, onSave, isLoading }: PersonalInfoFormProps) {
  const { profile } = useProfileStore()

  const form = useForm<PersonalInfoFormData>({
    resolver: zodResolver(personalInfoSchema),
    defaultValues: {
      full_name: initialData?.full_name || profile?.personal_info?.full_name || '',
      email: initialData?.email || profile?.personal_info?.email || '',
      phone: initialData?.phone || profile?.personal_info?.phone || '',
      location: initialData?.location || profile?.personal_info?.location || '',
      website: initialData?.website || profile?.personal_info?.website || '',
      linkedin: initialData?.linkedin || profile?.personal_info?.linkedin || '',
      github: initialData?.github || profile?.personal_info?.github || '',
      twitter: initialData?.twitter || profile?.personal_info?.twitter || '',
      summary: initialData?.summary || profile?.personal_info?.summary || '',
    },
  })

  const handleSubmit = async (data: PersonalInfoFormData) => {
    await onSave(data)
  }

  const socialLinks: Array<{ key: keyof PersonalInfoFormData; label: string; icon: React.ComponentType<{ className?: string }>; placeholder: string }> = [
    { key: 'website', label: 'Website', icon: Globe, placeholder: 'https://yourwebsite.com' },
    { key: 'linkedin', label: 'LinkedIn', icon: Linkedin, placeholder: 'https://linkedin.com/in/yourprofile' },
    { key: 'github', label: 'GitHub', icon: Github, placeholder: 'https://github.com/yourusername' },
    { key: 'twitter', label: 'Twitter/X', icon: Twitter, placeholder: 'https://twitter.com/yourusername' },
  ]

  return (
    <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="w-5 h-5" />
            Personal Information
          </CardTitle>
          <CardDescription>Your basic contact information and professional summary</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="full_name" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Full Name *
              </label>
              <Input
                id="full_name"
                {...form.register('full_name')}
                placeholder="John Doe"
                error={form.formState.errors.full_name?.message}
              />
            </div>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Email *
              </label>
              <Input
                id="email"
                type="email"
                {...form.register('email')}
                placeholder="john@example.com"
                error={form.formState.errors.email?.message}
              />
            </div>
            <div>
              <label htmlFor="phone" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Phone
              </label>
              <Input
                id="phone"
                {...form.register('phone')}
                placeholder="+1 (555) 123-4567"
                error={form.formState.errors.phone?.message}
              />
            </div>
            <div>
              <label htmlFor="location" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Location
              </label>
              <Input
                id="location"
                {...form.register('location')}
                placeholder="San Francisco, CA"
                error={form.formState.errors.location?.message}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              Social Links
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {socialLinks.map(({ key, label, icon: Icon, placeholder }) => (
                <div key={key}>
                  <label htmlFor={key} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    {label}
                  </label>
                  <div className="relative">
                    <Icon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input
                      id={key}
                      {...form.register(key)}
                      placeholder={placeholder}
                      className="pl-10"
                      error={form.formState.errors[key as keyof PersonalInfoFormData]?.message}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="summary" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Professional Summary
            </label>
            <textarea
              id="summary"
              {...form.register('summary')}
              rows={4}
              className={cn(
                'w-full px-3 py-2 border rounded-lg bg-white dark:bg-slate-800',
                'text-slate-900 dark:text-white placeholder-slate-400',
                'focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-transparent',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
              placeholder="Brief overview of your experience, skills, and career goals..."
            />
            <p className="text-xs text-slate-400 dark:text-slate-600 mt-1 text-right">
              {form.watch('summary')?.length || 0}/600 characters
            </p>
            {form.formState.errors.summary && (
              <p className="text-sm text-red-600 dark:text-red-400 mt-1">{form.formState.errors.summary.message}</p>
            )}
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-3">
        <Button type="button" variant="outline" onClick={() => form.reset()}>
          Reset
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Saving...' : 'Save Personal Info'}
        </Button>
      </div>
    </form>
  )
}