import { ResumeTemplate } from '@/types'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { cn } from '@/utils/helpers'
import { CheckCircle, FileText } from 'lucide-react'

interface TemplateSelectorProps {
  templates: ResumeTemplate[]
  selectedId?: string
  onSelect: (templateId: string) => void
}

export function TemplateSelector({ templates, selectedId, onSelect }: TemplateSelectorProps) {
  if (!templates || templates.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <FileText className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
          <p className="text-slate-500 dark:text-slate-400">No templates available</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {templates.map((template) => {
        const isSelected = selectedId === template.id
        return (
          <Card
            key={template.id}
            className={cn(
              'cursor-pointer transition-all duration-200',
              isSelected
                ? 'ring-2 ring-primary-500 shadow-lg'
                : 'hover:shadow-md hover:border-primary-300 dark:hover:border-primary-700'
            )}
            onClick={() => onSelect(template.id)}
          >
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                  <CardTitle className="text-base">{template.name}</CardTitle>
                </div>
                {isSelected && (
                  <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
                )}
                {template.is_default && (
                  <Badge variant="neutral" className="text-xs">
                    Default
                  </Badge>
                )}
              </div>
              {template.preview_url && (
                <div className="mt-2 aspect-video bg-slate-100 dark:bg-slate-800 rounded-lg overflow-hidden">
                  <img
                    src={template.preview_url}
                    alt={template.name}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none'
                    }}
                  />
                </div>
              )}
            </CardHeader>
            {template.description && (
              <CardContent className="pt-0">
                <CardDescription className="text-sm">{template.description}</CardDescription>
              </CardContent>
            )}
          </Card>
        )
      })}
    </div>
  )
}
