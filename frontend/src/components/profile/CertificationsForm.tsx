import { useForm, useFieldArray } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Plus, Trash2, GripVertical, Award } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Certification } from '@/types'
import { useProfileStore } from '@/store/index'

const certificationSchema = z.object({
  name: z.string().min(1, 'Certification name is required'),
  issuer: z.string().min(1, 'Issuer is required'),
  date_obtained: z.string().optional(),
  expiry_date: z.string().optional(),
  credential_id: z.string().optional(),
  credential_url: z.string().url('Invalid URL').optional().or(z.literal('')),
})

const certificationFormSchema = z.object({
  certifications: z.array(certificationSchema),
})

type CertificationFormData = z.infer<typeof certificationFormSchema>

interface CertificationsFormProps {
  initialData?: Certification[]
  onSave: (data: Certification[]) => Promise<void>
  isLoading?: boolean
}

export function CertificationsForm({ initialData, onSave, isLoading }: CertificationsFormProps) {
  const { profile } = useProfileStore()

  const form = useForm<CertificationFormData>({
    resolver: zodResolver(certificationFormSchema),
    defaultValues: {
      certifications: initialData?.length
        ? initialData
        : profile?.certifications?.length
          ? profile.certifications
          : [
              {
                name: '',
                issuer: '',
                date_obtained: '',
                expiry_date: '',
                credential_id: '',
                credential_url: '',
              },
            ],
    },
  })

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: 'certifications',
  })

  const handleSubmit = async (data: CertificationFormData) => {
    await onSave(data.certifications)
  }

  const addCertification = () => {
    append({
      name: '',
      issuer: '',
      date_obtained: '',
      expiry_date: '',
      credential_id: '',
      credential_url: '',
    })
  }

  return (
    <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
      <Card>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Award className="w-5 h-5" />
              Certifications
            </CardTitle>
            <CardDescription>Add your professional certifications and credentials</CardDescription>
          </div>
          <Button type="button" variant="outline" onClick={addCertification} className="sm:ml-auto">
            <Plus className="w-4 h-4 mr-2" />
            Add Certification
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
                      <label htmlFor={`certifications.${index}.name`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Certification Name *
                      </label>
                      <Input
                        id={`certifications.${index}.name`}
                        {...form.register(`certifications.${index}.name`)}
                        placeholder="AWS Certified Solutions Architect"
                        error={form.formState.errors.certifications?.[index]?.name?.message}
                      />
                    </div>
                    <div>
                      <label htmlFor={`certifications.${index}.issuer`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Issuing Organization *
                      </label>
                      <Input
                        id={`certifications.${index}.issuer`}
                        {...form.register(`certifications.${index}.issuer`)}
                        placeholder="Amazon Web Services"
                        error={form.formState.errors.certifications?.[index]?.issuer?.message}
                      />
                    </div>
                    <div>
                      <label htmlFor={`certifications.${index}.date_obtained`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Date Obtained
                      </label>
                      <Input
                        id={`certifications.${index}.date_obtained`}
                        type="month"
                        {...form.register(`certifications.${index}.date_obtained`)}
                      />
                    </div>
                    <div>
                      <label htmlFor={`certifications.${index}.expiry_date`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Expiry Date
                      </label>
                      <Input
                        id={`certifications.${index}.expiry_date`}
                        type="month"
                        {...form.register(`certifications.${index}.expiry_date`)}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor={`certifications.${index}.credential_id`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Credential ID
                      </label>
                      <Input
                        id={`certifications.${index}.credential_id`}
                        {...form.register(`certifications.${index}.credential_id`)}
                        placeholder="ABC123XYZ"
                      />
                    </div>
                    <div>
                      <label htmlFor={`certifications.${index}.credential_url`} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Credential URL
                      </label>
                      <Input
                        id={`certifications.${index}.credential_url`}
                        type="url"
                        {...form.register(`certifications.${index}.credential_url`)}
                        placeholder="https://credly.com/badges/..."
                        error={form.formState.errors.certifications?.[index]?.credential_url?.message}
                      />
                    </div>
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

              {form.formState.errors.certifications?.[index] && (
                <p className="text-sm text-red-600 dark:text-red-400">
                  {form.formState.errors.certifications[index].name?.message ||
                    form.formState.errors.certifications[index].issuer?.message ||
                    form.formState.errors.certifications[index].credential_url?.message}
                </p>
              )}
            </div>
          ))}

          {fields.length === 0 && (
            <div className="text-center py-8 text-slate-500 dark:text-slate-400">
              No certifications added yet. Click "Add Certification" to get started.
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex justify-end gap-3">
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Saving...' : 'Save Certifications'}
        </Button>
      </div>
    </form>
  )
}