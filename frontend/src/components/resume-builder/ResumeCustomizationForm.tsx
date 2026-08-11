import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { cn } from '@/utils/helpers'
import { ResumeCustomizationFormData } from '@/types'
import { useResumeStore } from '@/store'
import { Tag, X, FileText, Save } from 'lucide-react'

const customizationSchema = z.object({
  template_id: z.string().min(1, 'Template selection is required'),
  emphasize_skills: z.array(z.string()).default([]),
  emphasize_experience: z.array(z.string()).default([]),
  inject_keywords: z.array(z.string()).default([]),
  target_length: z.enum(['1_page', '2_pages', 'auto']).default('auto'),
  format: z.enum(['docx', 'pdf']).default('docx'),
})

type CustomizationFormData = z.infer<typeof customizationSchema>

interface ResumeCustomizationFormProps {
  jobId?: string
  disabled?: boolean
  onSave: (data: ResumeCustomizationFormData) => void
}

export function ResumeCustomizationForm({ jobId, disabled, onSave }: ResumeCustomizationFormProps) {
  const { customizationOptions, setCustomizationOptions } = useResumeStore()

  const form = useForm<CustomizationFormData>({
    resolver: zodResolver(customizationSchema),
    defaultValues: {
      template_id: customizationOptions.templateId || '',
      emphasize_skills: customizationOptions.emphasizeSkills,
      emphasize_experience: customizationOptions.emphasizeExperience,
      inject_keywords: customizationOptions.injectKeywords,
      target_length: customizationOptions.targetLength,
      format: customizationOptions.format,
    },
  })

  const emphasizeSkills = form.watch('emphasize_skills')
  const emphasizeExperience = form.watch('emphasize_experience')
  const injectKeywords = form.watch('inject_keywords')

  const addTag = (field: 'emphasize_skills' | 'emphasize_experience' | 'inject_keywords', value: string) => {
    const current = form.getValues(field) as string[]
    if (value && !current.includes(value)) {
      form.setValue(field, [...current, value])
    }
  }

  const removeTag = (field: 'emphasize_skills' | 'emphasize_experience' | 'inject_keywords', value: string) => {
    const current = form.getValues(field) as string[]
    form.setValue(field, current.filter((v) => v !== value))
  }

  const handleTagInput = (
    field: 'emphasize_skills' | 'emphasize_experience' | 'inject_keywords',
    e: React.KeyboardEvent<HTMLInputElement>
  ) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      const input = e.currentTarget
      const value = input.value.trim()
      if (value) {
        addTag(field, value)
        input.value = ''
      }
    }
  }

  const TagInput = ({
    field,
    label,
    placeholder,
    values,
  }: {
    field: 'emphasize_skills' | 'emphasize_experience' | 'inject_keywords'
    label: string
    placeholder: string
    values: string[]
  }) => (
    <div>
      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{label}</label>
      <div className="flex flex-wrap gap-1.5 mb-2 min-h-[2.5rem] items-start">
        {values.map((v) => (
          <Badge key={v} variant="primary" className="text-xs py-0.5 flex items-center gap-1">
            {v}
            <button
              type="button"
              onClick={() => removeTag(field, v)}
              className="hover:text-slate-700 dark:hover:text-slate-300"
            >
              <X className="w-3 h-3" />
            </button>
          </Badge>
        ))}
      </div>
      <div className="relative">
        <Tag className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          type="text"
          placeholder={placeholder}
          onKeyDown={(e) => handleTagInput(field, e)}
          className={cn(
            'w-full pl-10 pr-3 py-2 border rounded-lg bg-white dark:bg-slate-800',
            'text-slate-900 dark:text-white placeholder-slate-400',
            'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent'
          )}
          disabled={disabled}
        />
      </div>
      <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
        Press Enter or comma to add. Current: {values.length}
      </p>
    </div>
  )

  const handleSubmit = (data: CustomizationFormData) => {
    setCustomizationOptions({
      templateId: data.template_id,
      emphasizeSkills: data.emphasize_skills,
      emphasizeExperience: data.emphasize_experience,
      injectKeywords: data.inject_keywords,
      targetLength: data.target_length,
      format: data.format,
    })

    onSave({ ...data, job_id: jobId || '' })
  }

  return (
    <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Resume Customization
          </CardTitle>
          <CardDescription>
            {jobId ? `Customizing resume for job ID: ${jobId}` : 'Select a job and customize your resume'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Template Selection */}
          <div>
            <label htmlFor="template_id" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Template ID *
            </label>
            <Input
              id="template_id"
              {...form.register('template_id')}
              placeholder="default"
              error={form.formState.errors.template_id?.message}
              disabled={disabled}
            />
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
              Select a template from the Template Selector above, then enter its ID here.
            </p>
          </div>

          {/* Emphasis Tags */}
          <div className="space-y-4 pt-4 border-t border-slate-200 dark:border-slate-700">
            <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Emphasize</h4>
            <TagInput
              field="emphasize_skills"
              label="Emphasize Skills"
              placeholder="e.g., React, TypeScript, AWS"
              values={emphasizeSkills}
            />
            <TagInput
              field="emphasize_experience"
              label="Emphasize Experience"
              placeholder="e.g., Senior Software Engineer, TechCorp"
              values={emphasizeExperience}
            />
          </div>

          {/* Keyword Injection */}
          <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
            <TagInput
              field="inject_keywords"
              label="Inject Keywords"
              placeholder="e.g., Kubernetes, microservices, CI/CD"
              values={injectKeywords}
            />
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
              Keywords from the job description will be injected to improve ATS compatibility.
            </p>
          </div>

          {/* Format Selection */}
          <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
            <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">Output Format</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Target Length
                </label>
                <select
                  {...form.register('target_length')}
                  className="input"
                  disabled={disabled}
                >
                  <option value="1_page">1 Page</option>
                  <option value="2_pages">2 Pages</option>
                  <option value="auto">Auto (Best Fit)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Format
                </label>
                <select
                  {...form.register('format')}
                  className="input"
                  disabled={disabled}
                >
                  <option value="docx">DOCX (.docx)</option>
                  <option value="pdf">PDF (.pdf)</option>
                </select>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button type="submit" disabled={disabled || !jobId} variant={jobId ? 'primary' : 'outline'}>
          <Save className="w-4 h-4 mr-2" />
          {jobId ? 'Generate Resume' : 'Save Customization (select a job first)'}
        </Button>
      </div>
    </form>
  )
}
