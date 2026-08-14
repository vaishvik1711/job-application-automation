import { useForm, useFieldArray } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Plus, Trash2, GripVertical, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { cn } from '@/utils/helpers'
import { Skill } from '@/types'
import { useProfileStore } from '@/store/index'

const skillSchema = z.object({
  name: z.string().min(1, 'Skill name is required'),
  category: z.string().min(1, 'Category is required'),
  proficiency: z.number().min(1).max(5),
})

const skillsFormSchema = z.object({
  skills: z.array(skillSchema).min(1, 'At least one skill is required'),
})

type SkillsFormData = z.infer<typeof skillsFormSchema>

const SKILL_CATEGORIES = [
  'Programming Languages',
  'Frameworks & Libraries',
  'Cloud & DevOps',
  'Databases',
  'Tools & Platforms',
  'Design & UI/UX',
  'Testing & QA',
  'Project Management',
  'Soft Skills',
  'Other',
]

const PROFICIENCY_LABELS = {
  1: 'Beginner',
  2: 'Novice',
  3: 'Intermediate',
  4: 'Advanced',
  5: 'Expert',
}

interface SkillsFormProps {
  initialData?: Skill[]
  onSave: (data: Skill[]) => Promise<void>
  isLoading?: boolean
}

export function SkillsForm({ initialData, onSave, isLoading }: SkillsFormProps) {
  const { profile } = useProfileStore()

  const form = useForm<SkillsFormData>({
    resolver: zodResolver(skillsFormSchema),
    defaultValues: {
      skills: initialData?.length
        ? initialData
        : profile?.skills?.length
          ? profile.skills
          : [
              { name: '', category: 'Programming Languages', proficiency: 3 },
            ],
    },
  })

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: 'skills',
  })

  const handleSubmit = async (data: SkillsFormData) => {
    await onSave(data.skills)
  }

  const addSkill = () => {
    append({ name: '', category: 'Programming Languages', proficiency: 3 })
  }

  return (
    <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
      <Card>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5" />
              Skills & Expertise
            </CardTitle>
            <CardDescription>Add your technical and soft skills with proficiency levels</CardDescription>
          </div>
          <Button type="button" variant="outline" onClick={addSkill} className="sm:ml-auto">
            <Plus className="w-4 h-4 mr-2" />
            Add Skill
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
                <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label htmlFor={`skills.${index}.name`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Skill Name *
                    </label>
                    <Input
                      id={`skills.${index}.name`}
                      {...form.register(`skills.${index}.name`)}
                      placeholder="e.g., TypeScript, React, Project Management"
                      error={form.formState.errors.skills?.[index]?.name?.message}
                    />
                  </div>
                  <div>
                    <label htmlFor={`skills.${index}.category`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Category *
                    </label>
                    <select
                      id={`skills.${index}.category`}
                      {...form.register(`skills.${index}.category`)}
                      className={cn(
                        'w-full px-3 py-2 border rounded-lg bg-white dark:bg-slate-800',
                        'text-slate-900 dark:text-white',
                        'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent'
                      )}
                    >
                      {SKILL_CATEGORIES.map((cat) => (
                        <option key={cat} value={cat}>
                          {cat}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor={`skills.${index}.proficiency`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Proficiency *
                    </label>
                    <select
                      id={`skills.${index}.proficiency`}
                      {...form.register(`skills.${index}.proficiency`, { valueAsNumber: true })}
                      className={cn(
                        'w-full px-3 py-2 border rounded-lg bg-white dark:bg-slate-800',
                        'text-slate-900 dark:text-white',
                        'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent'
                      )}
                    >
                      {[1, 2, 3, 4, 5].map((level) => (
                        <option key={level} value={level}>
                          {level} - {PROFICIENCY_LABELS[level as keyof typeof PROFICIENCY_LABELS]}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="flex items-end gap-4">
                  <button
                    type="button"
                    onClick={() => remove(index)}
                    className="text-red-500 hover:text-red-700 p-1"
                    disabled={fields.length === 1}
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {form.formState.errors.skills?.[index] && (
                <p className="text-sm text-red-600 dark:text-red-400">
                  {form.formState.errors.skills[index].name?.message ||
                    form.formState.errors.skills[index].category?.message}
                </p>
              )}
            </div>
          ))}

          {fields.length === 0 && (
            <div className="text-center py-8 text-slate-500 dark:text-slate-400">
              No skills added yet. Click "Add Skill" to get started.
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex justify-end gap-3">
        <Button type="submit" disabled={isLoading || fields.length === 0}>
          {isLoading ? 'Saving...' : 'Save Skills'}
        </Button>
      </div>
    </form>
  )
}