import { useForm, useFieldArray } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Plus, Trash2, GripVertical, FolderOpen, BookOpen, Code, Star } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Textarea } from '@/components/ui/Input'
import { cn } from '@/utils/helpers'
import { AdditionalExperience } from '@/types'
import { useProfileStore } from '@/store/index'

const additionalExpSchema = z.object({
  type: z.enum(['project', 'publication', 'award', 'volunteer', 'other']),
  title: z.string().min(1, 'Title is required'),
  description: z.string().optional(),
  url: z.string().url('Invalid URL').optional().or(z.literal('')),
  start_date: z.string().optional(),
  end_date: z.string().optional(),
  technologies: z.array(z.string()).default([]),
})

const additionalExpFormSchema = z.object({
  additional_experience: z.array(additionalExpSchema),
})

type AdditionalExpFormData = z.infer<typeof additionalExpFormSchema>

const EXPERIENCE_TYPES = [
  { value: 'project', label: 'Project', icon: FolderOpen },
  { value: 'publication', label: 'Publication', icon: BookOpen },
  { value: 'award', label: 'Award', icon: Star },
  { value: 'volunteer', label: 'Volunteer', icon: Code },
  { value: 'other', label: 'Other', icon: Star },
]

interface AdditionalExperienceFormProps {
  initialData?: AdditionalExperience[]
  onSave: (data: AdditionalExperience[]) => Promise<void>
  isLoading?: boolean
}

export function AdditionalExperienceForm({ initialData, onSave, isLoading }: AdditionalExperienceFormProps) {
  const { profile } = useProfileStore()

  const form = useForm<AdditionalExpFormData>({
    resolver: zodResolver(additionalExpFormSchema),
    defaultValues: {
      additional_experience: initialData?.length
        ? initialData
        : profile?.additional_experience?.length
          ? profile.additional_experience
          : [
              {
                type: 'project',
                title: '',
                description: '',
                url: '',
                start_date: '',
                end_date: '',
                technologies: [],
              },
            ],
    },
  })

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: 'additional_experience',
  })

  const handleSubmit = async (data: AdditionalExpFormData) => {
    await onSave(data.additional_experience)
  }

  const addItem = () => {
    append({
      type: 'project',
      title: '',
      description: '',
      url: '',
      start_date: '',
      end_date: '',
      technologies: [],
    })
  }

  return (
    <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
      <Card>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Star className="w-5 h-5" />
              Additional Experience
            </CardTitle>
            <CardDescription>Projects, publications, awards, volunteer work, and more</CardDescription>
          </div>
          <Button type="button" variant="outline" onClick={addItem} className="sm:ml-auto">
            <Plus className="w-4 h-4 mr-2" />
            Add Item
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {fields.map((field, index) => (
            <div
              key={field.id}
              className="border border-slate-200 dark:border-slate-700 rounded-lg p-4 space-y-4 relative"
            >
              <div className="flex items-start gap-2">
                <button
                  type="button"
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 p-1"
                  onMouseDown={(e) => e.preventDefault()}
                >
                  <GripVertical className="w-5 h-5" />
                </button>
                <div className="flex-1 space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor={`additional_experience.${index}.type`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Type *
                      </label>
                      <select
                        id={`additional_experience.${index}.type`}
                        {...form.register(`additional_experience.${index}.type`)}
                        className={cn(
                          'w-full px-3 py-2 border rounded-lg bg-white dark:bg-slate-800',
                          'text-slate-900 dark:text-white',
                          'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent'
                        )}
                      >
                        {EXPERIENCE_TYPES.map((t) => (
                          <option key={t.value} value={t.value}>
                            {t.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label htmlFor={`additional_experience.${index}.title`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Title *
                      </label>
                      <Input
                        id={`additional_experience.${index}.title`}
                        {...form.register(`additional_experience.${index}.title`)}
                        placeholder="Project/Publication/Award Title"
                        error={form.formState.errors.additional_experience?.[index]?.title?.message}
                      />
                    </div>
                  </div>

                  <div>
                    <label htmlFor={`additional_experience.${index}.description`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Description
                    </label>
                    <Textarea
                      id={`additional_experience.${index}.description`}
                      {...form.register(`additional_experience.${index}.description`)}
                      rows={3}
                      placeholder="Describe this project, publication, award, or experience..."
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label htmlFor={`additional_experience.${index}.url`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        URL
                      </label>
                      <Input
                        id={`additional_experience.${index}.url`}
                        type="url"
                        {...form.register(`additional_experience.${index}.url`)}
                        placeholder="https://github.com/... or https://..."
                        error={form.formState.errors.additional_experience?.[index]?.url?.message}
                      />
                    </div>
                    <div>
                      <label htmlFor={`additional_experience.${index}.start_date`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Start Date
                      </label>
                      <Input
                        id={`additional_experience.${index}.start_date`}
                        type="month"
                        {...form.register(`additional_experience.${index}.start_date`)}
                      />
                    </div>
                    <div>
                      <label htmlFor={`additional_experience.${index}.end_date`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        End Date
                      </label>
                      <Input
                        id={`additional_experience.${index}.end_date`}
                        type="month"
                        {...form.register(`additional_experience.${index}.end_date`)}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Technologies / Tags
                    </label>
                    <TechnologiesInput
                      form={form}
                      index={index}
                      control={form.control}
                    />
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => remove(index)}
                  className="text-red-500 hover:text-red-700 p-1 mt-8"
                  disabled={fields.length === 1}
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>

              {form.formState.errors.additional_experience?.[index] && (
                <p className="text-sm text-red-600 dark:text-red-400">
                  {form.formState.errors.additional_experience[index].title?.message ||
                    form.formState.errors.additional_experience[index].url?.message}
                </p>
              )}
            </div>
          ))}

          {fields.length === 0 && (
            <div className="text-center py-8 text-slate-500 dark:text-slate-400">
              No additional experience added yet. Click "Add Item" to get started.
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex justify-end gap-3">
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Saving...' : 'Save Additional Experience'}
        </Button>
      </div>
    </form>
  )
}

interface TechnologiesInputProps {
  form: any
  index: number
  control: any
}

function TechnologiesInput({ form, index, control }: TechnologiesInputProps) {
  const { fields, append, remove } = useFieldArray({
    control,
    name: `additional_experience.${index}.technologies`,
  })

  return (
    <div className="flex flex-wrap gap-2">
      {fields.map((techField, techIndex) => (
        <span key={techField.id} className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-3 py-1 rounded-full text-sm">
          <input
            type="text"
            {...form.register(`additional_experience.${index}.technologies.${techIndex}`)}
            className="bg-transparent border-none outline-none text-sm w-32"
            placeholder="Tag"
          />
          <button
            type="button"
            onClick={() => remove(techIndex)}
            className="text-slate-500 hover:text-slate-700 p-0.5"
          >
            <span className="text-xs">×</span>
          </button>
        </span>
      ))}
      <button
        type="button"
        onClick={() => append('')}
        className="px-3 py-1 text-sm text-slate-500 dark:text-slate-400 hover:text-primary-600 dark:hover:text-primary-400 border border-dashed border-slate-300 dark:border-slate-600 rounded-full transition-colors"
      >
        + Add Tag
      </button>
    </div>
  )
}