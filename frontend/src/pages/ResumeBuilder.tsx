import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useResumeTemplates, useResumes, useGenerateResume, useDownloadResume, useValidateResume } from '@/hooks/useApi'
import { useUIStore } from '@/store'
import { ResumeTemplate, GeneratedResume, ValidationResult, ResumeCustomizationOptions } from '@/types'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { TemplateSelector } from '@/components/resume-builder/TemplateSelector'
import { ResumeCustomizationForm } from '@/components/resume-builder/ResumeCustomizationForm'
import { ResumeValidation } from '@/components/resume-builder/ResumeValidation'
import {
  FileText,
  Sparkles,
  Download,
  History,
  CheckCircle,
  RefreshCw,
  LayoutGrid,
  List,
} from 'lucide-react'
import { formatRelativeTime, formatNumber } from '@/utils/helpers'
import { toast } from 'sonner'

type ViewMode = 'grid' | 'list'

export function ResumeBuilder() {
  const [searchParams] = useSearchParams()
  const jobId = searchParams.get('job_id')

  const [selectedTemplate, setSelectedTemplate] = useState<ResumeTemplate | null>(null)
  const [generatedResume, setGeneratedResume] = useState<GeneratedResume | null>(null)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationProgress, setGenerationProgress] = useState<{ step: string; progress: number } | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('grid')

  const { data: templatesData, isLoading: isLoadingTemplates } = useResumeTemplates()
  const { data: resumesData, isLoading: isLoadingResumes, refetch: refetchResumes } = useResumes({ page: 1, page_size: 50 })
  const generateMutation = useGenerateResume()
  const downloadMutation = useDownloadResume()
  const validateMutation = useValidateResume()
  const { addNotification } = useUIStore()

  const templates = templatesData || [
    {
      id: 'default',
      name: 'Classic Professional',
      description: 'Clean, traditional resume layout with clear section hierarchy',
      preview_url: undefined,
      is_default: true,
    },
    {
      id: 'modern',
      name: 'Modern Minimal',
      description: 'Contemporary design with subtle color accents and whitespace',
      preview_url: undefined,
      is_default: false,
    },
    {
      id: 'executive',
      name: 'Executive',
      description: 'Premium layout for senior-level and executive positions',
      preview_url: undefined,
      is_default: false,
    },
  ]

  const resumes = resumesData?.items || []

  const handleGenerate = useCallback(
    async (data: any) => {
      if (!jobId) {
        toast.error('Please select a job to generate a resume for')
        return
      }

      const options: ResumeCustomizationOptions = {
        job_id: jobId,
        template_id: data.template_id,
        emphasize_skills: data.emphasize_skills || [],
        emphasize_experience: data.emphasize_experience || [],
        inject_keywords: data.inject_keywords || [],
        target_length: data.target_length || 'auto',
        format: data.format || 'docx',
      }

      setIsGenerating(true)
      setGenerationProgress({ step: 'Generating resume with AI...', progress: 30 })

      try {
        const result = await generateMutation.mutateAsync(options)
        setGeneratedResume(result)
        setGenerationProgress({ step: 'Validating resume...', progress: 70 })

        // Validate the resume
        try {
          const validation = await validateMutation.mutateAsync(result.id)
          setValidationResult(validation)
          setGenerationProgress({ step: 'Complete!', progress: 100 })
          toast.success('Resume generated and validated successfully!')
          addNotification({ type: 'success', message: `Resume generated for ${result.job_title}` })
        } catch (err: any) {
          console.warn('Validation failed:', err)
          toast.warning('Resume generated but validation failed')
        }

        setTimeout(() => {
          setGenerationProgress(null)
          refetchResumes()
        }, 500)
      } catch (err: any) {
        console.error('Resume generation failed:', err)
        toast.error(err.message || 'Failed to generate resume')
        setGenerationProgress(null)
      } finally {
        setIsGenerating(false)
      }
    },
    [jobId, generateMutation, validateMutation, refetchResumes, addNotification]
  )

  const handleDownload = useCallback(
    async (format: 'docx' | 'pdf') => {
      if (!generatedResume) return

      try {
        await downloadMutation.mutateAsync({ id: generatedResume.id, format })
        toast.success(`Downloaded ${format.toUpperCase()} file`)
      } catch (err: any) {
        toast.error('Failed to download resume')
      }
    },
    [generatedResume, downloadMutation]
  )

  const handleSelectResume = (resume: GeneratedResume) => {
    setGeneratedResume(resume)
    if (resume.validation_result) {
      setValidationResult(resume.validation_result)
    } else {
      // Validate existing resume
      validateMutation.mutateAsync(resume.id).then((result) => {
        setValidationResult(result)
        setGeneratedResume({ ...resume, validation_result: result })
      })
    }
  }

  const handleTemplateSelect = (templateId: string) => {
    const template = templates.find((t) => t.id === templateId)
    setSelectedTemplate(template || null)
  }

  const resetBuilder = () => {
    setGeneratedResume(null)
    setValidationResult(null)
    setSelectedTemplate(null)
  }

  // Auto-select default template on load
  useEffect(() => {
    const defaultTemplate = templates.find((t) => t.is_default) || templates[0]
    if (defaultTemplate) {
      setSelectedTemplate(defaultTemplate)
    }
  }, [templates])

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Resume Builder</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            {jobId
              ? `Generate a tailored resume for job ${jobId}`
              : 'Generate tailored resumes for your matched jobs'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {generatedResume && (
            <Button variant="outline" size="sm" onClick={resetBuilder}>
              <RefreshCw className="w-4 h-4 mr-2" /> New Resume
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={() => refetchResumes()}>
            <History className="w-4 h-4 mr-2" /> Refresh Library
          </Button>
        </div>
      </div>

      {/* Generation Progress */}
      {isGenerating && generationProgress && (
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                {generationProgress.step}
              </p>
              <span className="text-sm text-slate-500 dark:text-slate-400">
                {generationProgress.progress}%
              </span>
            </div>
            <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-500 rounded-full transition-all duration-500"
                style={{ width: `${generationProgress.progress}%` }}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Template Selection */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Templates</CardTitle>
              <CardDescription>Choose a resume template</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoadingTemplates ? (
                <div className="space-y-3">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-32 bg-slate-200 dark:bg-slate-700 rounded-lg animate-pulse" />
                  ))}
                </div>
              ) : (
                <TemplateSelector
                  templates={templates}
                  selectedId={selectedTemplate?.id}
                  onSelect={handleTemplateSelect}
                />
              )}
            </CardContent>
          </Card>
        </div>

        {/* Customization Form */}
        <div className="xl:col-span-2">
          <ResumeCustomizationForm
            jobId={jobId || undefined}
            disabled={isGenerating}
            onSave={handleGenerate}
          />
        </div>
      </div>

      {/* Generated Resume Results */}
      {generatedResume && (
        <div className="space-y-6">
          {/* Resume Header */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
                    Resume Generated
                  </CardTitle>
                  <CardDescription>
                    {generatedResume.job_title} at {generatedResume.company} • Created{' '}
                    {formatRelativeTime(generatedResume.created_at)}
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="success" className="text-xs">
                    {generatedResume.format.toUpperCase()}
                  </Badge>
                  <Badge variant="primary" className="text-xs">
                    Resume #{generatedResume.id.slice(0, 8)}
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <Button onClick={() => handleDownload(generatedResume.format)} loading={isGenerating}>
                  <Download className="w-4 h-4 mr-2" /> Download {generatedResume.format.toUpperCase()}
                </Button>
                <Button variant="outline" onClick={() => handleDownload(generatedResume.format === 'pdf' ? 'docx' : 'pdf')}>
                  Download as {generatedResume.format === 'pdf' ? 'DOCX' : 'PDF'}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Validation Results */}
          {validationResult && (
            <ResumeValidation
              result={validationResult}
              onDownload={handleDownload}
              onRevalidate={async () => {
                const result = await validateMutation.mutateAsync(generatedResume.id)
                setValidationResult(result)
                toast.success('Resume revalidated')
              }}
              isRevalidating={validateMutation.isPending}
            />
          )}

          {/* Missing Issues */}
          {!validationResult && (
            <Card>
              <CardContent className="py-8 text-center">
                <Sparkles className="w-8 h-8 text-slate-400 dark:text-slate-500 mx-auto mb-3 animate-pulse" />
                <p className="text-slate-500 dark:text-slate-400">Validation in progress...</p>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Resume Library */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <History className="w-5 h-5" />
                Resume Library
              </CardTitle>
              <CardDescription>{formatNumber(resumes.length)} resumes saved</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('grid')}
                  className={
                    viewMode === 'grid'
                      ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
                      : 'text-slate-500 dark:text-slate-400 hover:text-slate-700'
                  }
                  style={{ padding: '4px 12px', borderRadius: '6px', fontSize: '14px', fontWeight: 500, cursor: 'pointer', border: 'none' }}
                >
                  <LayoutGrid className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setViewMode('list')}
                  className={
                    viewMode === 'list'
                      ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
                      : 'text-slate-500 dark:text-slate-400 hover:text-slate-700'
                  }
                  style={{ padding: '4px 12px', borderRadius: '6px', fontSize: '14px', fontWeight: 500, cursor: 'pointer', border: 'none' }}
                >
                  <List className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoadingResumes ? (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-20 bg-slate-200 dark:bg-slate-700 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : resumes.length > 0 ? (
            <div
              className={
                viewMode === 'grid'
                  ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4'
                  : 'space-y-2'
              }
            >
              {resumes.map((resume) => (
                <Card
                  key={resume.id}
                  className="group cursor-pointer transition-all hover:shadow-md"
                  onClick={() => handleSelectResume(resume)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                        <FileText className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-slate-900 dark:text-white truncate">
                          {resume.job_title}
                        </p>
                        <p className="text-sm text-slate-500 dark:text-slate-400 truncate">
                          {resume.company}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="neutral" className="text-xs">
                            {resume.format.toUpperCase()}
                          </Badge>
                          <span className="text-xs text-slate-500 dark:text-slate-400">
                            {formatRelativeTime(resume.created_at)}
                          </span>
                        </div>
                      </div>
                      {resume.validation_result && (
                        <Badge
                          variant={
                            resume.validation_result.ats_score >= 0.8
                              ? 'success'
                              : resume.validation_result.ats_score >= 0.6
                              ? 'warning'
                              : 'danger'
                          }
                          className="text-xs"
                        >
                          ATS: {Math.round(resume.validation_result.ats_score * 100)}%
                        </Badge>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-slate-500 dark:text-slate-400">
              <FileText className="w-8 h-8 mx-auto mb-3" />
              <p>No resumes generated yet. Create your first resume above!</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
