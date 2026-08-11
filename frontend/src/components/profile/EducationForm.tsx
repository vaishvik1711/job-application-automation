import { useForm, useFieldArray } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Plus, Trash2, GripVertical, GraduationCap } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { cn } from '@/utils/helpers'
import { Education } from '@/types'
import { useProfileStore } from '@/store/index'

const educationSchema = z.object({
  institution: z.string().min(1, 'Institution name is required'),
  degree: z.string().min(1, 'Degree is required'),
  field_of_study: z.string().optional(),
  location: z.string().optional(),
  start_date: z.string().optional(),
  end_date: z.string().optional(),
  gpa: z.union([z.string(), z.number()]).optional(),
  description: z.string().optional(),
})

const educationFormSchema = z.object({
  education: z.array(educationSchema),
})

type EducationFormData = z.infer<typeof educationFormSchema>

interface EducationFormProps {
  initialData?: Education[]
  onSave: (data: Education[]) => Promise<void>
  isLoading?: boolean
}

export function EducationForm({ initialData, onSave, isLoading }: EducationFormProps) {
  const { profile } = useProfileStore()

  const form = useForm<EducationFormData>({
    resolver: zodResolver(educationFormSchema),
    defaultValues: {
      education: initialData?.length
        ? initialData
        : profile?.education?.length
          ? profile.education
          : [
              {
                institution: '',
                degree: '',
                field_of_study: '',
                location: '',
                start_date: '',
                end_date: '',
                gpa: '',
                description: '',
              },
            ],
    },
  })

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: 'education',
  })

  const handleSubmit = async (data: EducationFormData) => {
    await onSave(data.education as unknown as Education[])
  }

  const addEducation = () => {
    append({
      institution: '',
      degree: '',
      field_of_study: '',
      location: '',
      start_date: '',
      end_date: '',
      gpa: '',
      description: '',
    })
  }

  return (
    <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
      <Card>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <CardTitle className="flex items-center gap-2">
              <GraduationCap className="w-5 h-5" />
              Education
            </CardTitle>
            <CardDescription>Add your educational background</CardDescription>
          </div>
          <Button type="button" variant="outline" onClick={addEducation} className="sm:ml-auto">
            <Plus className="w-4 h-4 mr-2" />
            Add Education
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
                      <label htmlFor={`education.${index}.institution`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Institution *
                      </label>
                      <Input
                        id={`education.${index}.institution`}
                        {...form.register(`education.${index}.institution`)}
                        placeholder="University Name"
                        error={form.formState.errors.education?.[index]?.institution?.message}
                      />
                    </div>
                    <div>
                      <label htmlFor={`education.${index}.degree`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Degree *
                      </label>
                      <Input
                        id={`education.${index}.degree`}
                        {...form.register(`education.${index}.degree`)}
                        placeholder="Bachelor of Science, Master of Arts, PhD, etc."
                        error={form.formState.errors.education?.[index]?.degree?.message}
                      />
                    </div>
                    <div>
                      <label htmlFor={`education.${index}.field_of_study`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Field of Study
                      </label>
                      <Input
                        id={`education.${index}.field_of_study`}
                        {...form.register(`education.${index}.field_of_study`)}
                        placeholder="Computer Science, Business, etc."
                      />
                    </div>
                    <div>
                      <label htmlFor={`education.${index}.location`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Location
                      </label>
                      <Input
                        id={`education.${index}.location`}
                        {...form.register(`education.${index}.location`)}
                        placeholder="City, State/Country"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label htmlFor={`education.${index}.start_date`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Start Date
                      </label>
                      <Input
                        id={`education.${index}.start_date`}
                        type="month"
                        {...form.register(`education.${index}.start_date`)}
                      />
                    </div>
                    <div>
                      <label htmlFor={`education.${index}.end_date`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        End Date
                      </label>
                      <Input
                        id={`education.${index}.end_date`}
                        type="month"
                        {...form.register(`education.${index}.end_date`)}
                      />
                    </div>
                    <div>
                      <label htmlFor={`education.${index}.gpa`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        GPA
                      </label>
                      <Input
                        id={`education.${index}.gpa`}
                        {...form.register(`education.${index}.gpa`)}
                        placeholder="3.8/4.0"
                      />
                    </div>
                  </div>

                  <div>
                    <label htmlFor={`education.${index}.description`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Description (Honors, Awards, Relevant Coursework)
                    </label>
                    <textarea
                      id={`education.${index}.description`}
                      {...form.register(`education.${index}.description`)}
                      rows={2}
                      className={cn(
                        'w-full px-3 py-2 border rounded-lg bg-white dark:bg-slate-800',
                        'text-slate-900 dark:text-white placeholder-slate-400',
                        'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent'
                      )}
                      placeholder="Dean's List, relevant coursework, thesis topic, etc."
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

              {form.formState.errors.education?.[index] && (
                <p className="text-sm text-red-600 dark:text-red-400">
                  {form.formState.errors.education[index].institution?.message ||
                    form.formState.errors.education[index].degree?.message}
                </p>
              )}
            </div>
          ))}

          {fields.length === 0 && (
            <div className="text-center py-8 text-slate-500 dark:text-slate-400">
              No education added yet. Click "Add Education" to get started.
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex justify-end gap-3">
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Saving...' : 'Save Education'}
        </Button>
      </div>
    </form>
  )
}