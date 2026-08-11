import { useForm, useFieldArray } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Plus, Trash2, GripVertical, Briefcase } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Textarea } from '@/components/ui/Input'
import { Experience } from '@/types'
import { useProfileStore } from '@/store/index'

const experienceSchema = z.object({
  company: z.string().min(1, 'Company name is required'),
  title: z.string().min(1, 'Job title is required'),
  location: z.string().optional(),
  start_date: z.string().min(1, 'Start date is required'),
  end_date: z.string().optional(),
  current: z.boolean().default(false),
  description: z.union([z.string(), z.array(z.string())]).optional(),
  technologies: z.array(z.string()).default([]),
})

const experienceFormSchema = z.object({
  experiences: z.array(experienceSchema),
})

type ExperienceFormData = z.infer<typeof experienceFormSchema>

interface ExperienceFormProps {
  initialData?: Experience[]
  onSave: (data: Experience[]) => Promise<void>
  isLoading?: boolean
}

export function ExperienceForm({ initialData, onSave, isLoading }: ExperienceFormProps) {
  const { profile } = useProfileStore()

  const form = useForm<ExperienceFormData>({
    resolver: zodResolver(experienceFormSchema),
    defaultValues: {
      experiences: initialData?.length
        ? initialData
        : profile?.experience?.length
          ? profile.experience
          : [
              {
                company: '',
                title: '',
                location: '',
                start_date: '',
                end_date: '',
                current: false,
                description: '',
                technologies: [],
              },
            ],
    },
  })

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: 'experiences',
  })

  const handleSubmit = async (data: ExperienceFormData) => {
    await onSave(data.experiences as unknown as Experience[])
  }

  const addExperience = () => {
    append({
      company: '',
      title: '',
      location: '',
      start_date: '',
      end_date: '',
      current: false,
      description: '',
      technologies: [],
    })
  }

  return (
    <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
      <Card>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Briefcase className="w-5 h-5" />
              Work Experience
            </CardTitle>
            <CardDescription>Add your professional work history</CardDescription>
          </div>
          <Button type="button" variant="outline" onClick={addExperience} className="sm:ml-auto">
            <Plus className="w-4 h-4 mr-2" />
            Add Experience
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
                      <label htmlFor={`experiences.${index}.company`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Company *
                      </label>
                      <Input
                        id={`experiences.${index}.company`}
                        {...form.register(`experiences.${index}.company`)}
                        placeholder="Company Name"
                        error={form.formState.errors.experiences?.[index]?.company?.message}
                      />
                    </div>
                    <div>
                      <label htmlFor={`experiences.${index}.title`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Job Title *
                      </label>
                      <Input
                        id={`experiences.${index}.title`}
                        {...form.register(`experiences.${index}.title`)}
                        placeholder="Software Engineer"
                        error={form.formState.errors.experiences?.[index]?.title?.message}
                      />
                    </div>
                    <div>
                      <label htmlFor={`experiences.${index}.location`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Location
                      </label>
                      <Input
                        id={`experiences.${index}.location`}
                        {...form.register(`experiences.${index}.location`)}
                        placeholder="San Francisco, CA (or Remote)"
                      />
                    </div>
                    <div>
                      <label htmlFor={`experiences.${index}.start_date`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Start Date *
                      </label>
                      <Input
                        id={`experiences.${index}.start_date`}
                        type="month"
                        {...form.register(`experiences.${index}.start_date`)}
                        error={form.formState.errors.experiences?.[index]?.start_date?.message}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label htmlFor={`experiences.${index}.end_date`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        End Date
                      </label>
                      <Input
                        id={`experiences.${index}.end_date`}
                        type="month"
                        {...form.register(`experiences.${index}.end_date`)}
                        disabled={form.watch(`experiences.${index}.current`)}
                      />
                    </div>
                    <div className="flex items-end">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          {...form.register(`experiences.${index}.current`)}
                          className="w-4 h-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                        />
                        <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Currently working here</span>
                      </label>
                    </div>
                  </div>

                  <div>
                    <label htmlFor={`experiences.${index}.description`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Description
                    </label>
                    <Textarea
                      id={`experiences.${index}.description`}
                      {...form.register(`experiences.${index}.description`)}
                      rows={3}
                      placeholder="Describe your responsibilities, achievements, and impact..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Technologies Used
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

              {form.formState.errors.experiences?.[index] && (
                <p className="text-sm text-red-600 dark:text-red-400">
                  {form.formState.errors.experiences[index].company?.message ||
                    form.formState.errors.experiences[index].title?.message ||
                    form.formState.errors.experiences[index].start_date?.message}
                </p>
              )}
            </div>
          ))}

          {fields.length === 0 && (
            <div className="text-center py-8 text-slate-500 dark:text-slate-400">
              No experience added yet. Click "Add Experience" to get started.
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex justify-end gap-3">
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Saving...' : 'Save Experience'}
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
    name: `experiences.${index}.technologies`,
  })

  return (
    <div className="flex flex-wrap gap-2">
      {fields.map((techField, techIndex) => (
        <span key={techField.id} className="flex items-center gap-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 px-3 py-1 rounded-full text-sm">
          <input
            type="text"
            {...form.register(`experiences.${index}.technologies.${techIndex}`)}
            className="bg-transparent border-none outline-none text-sm text-primary-700 dark:text-primary-300 w-32"
            placeholder="Tech"
          />
          <button
            type="button"
            onClick={() => remove(techIndex)}
            className="text-primary-500 hover:text-primary-700 p-0.5"
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
        + Add Technology
      </button>
    </div>
  )
}