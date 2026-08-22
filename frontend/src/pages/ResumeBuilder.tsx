import { useState, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useResumes, useGenerateResume } from '@/hooks/useApi'
import { useUIStore } from '@/store'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import {
  FileText,
  Sparkles,
  Download,
  History,
  CheckCircle,
  RefreshCw,
  LayoutGrid,
  List,
  ArrowLeft,
} from 'lucide-react'
import { formatRelativeTime, formatNumber } from '@/utils/helpers'
import { downloadResume } from '@/utils/download'
import { toast } from 'sonner'

type ViewMode = 'grid' | 'list'

export function ResumeBuilder() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const jobId = searchParams.get('job_id')

  const [generatedResume, setGeneratedResume] = useState<any>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationProgress, setGenerationProgress] = useState<{ step: string; progress: number } | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('grid')

  const { data: resumesData, isLoading: isLoadingResumes, refetch: refetchResumes } = useResumes({ page: 1, page_size: 50 })
  const generateMutation = useGenerateResume()
  const { addNotification } = useUIStore()

  const resumes = resumesData?.items || []

  const handleGenerate = useCallback(async () => {
    if (!jobId) {
      toast.error('Please select a job to generate a resume for')
      return
    }

    setIsGenerating(true)
    setGenerationProgress({ step: 'Reading your resume and job requirements...', progress: 20 })

    try {
      const result = await generateMutation.mutateAsync({
        job_id: jobId,
        format: 'docx',
      })
      setGeneratedResume(result)
      setGenerationProgress({ step: 'Resume generated!', progress: 100 })
      toast.success('Resume generated successfully!')
      addNotification({ type: 'success', message: `Resume generated for ${result.job_title}` })

      setTimeout(() => {
        setGenerationProgress(null)
        refetchResumes()
      }, 500)
    } catch (err: any) {
      console.error('Resume generation failed:', err)
      const msg = err?.response?.data?.detail || err?.message || 'Failed to generate resume'
      toast.error(msg)
      setGenerationProgress(null)
    } finally {
      setIsGenerating(false)
    }
  }, [jobId, generateMutation, refetchResumes, addNotification])

  const handleDownload = useCallback(
    (_format: 'docx' | 'pdf') => {
      if (!generatedResume) return
      // Shared helper: authenticated blob request with error toasts.
      downloadResume(generatedResume.id, generatedResume.job_title)
    },
    [generatedResume]
  )

  const handleSelectResume = (resume: any) => {
    setGeneratedResume(resume)
  }

  const resetBuilder = () => {
    setGeneratedResume(null)
  }

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/job-matching')}
              className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              aria-label="Back to job matching"
            >
              <ArrowLeft className="w-5 h-5 text-slate-500" />
            </button>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Resume Builder</h1>
          </div>
          <p className="text-slate-500 dark:text-slate-400 mt-1 ml-9">
            {jobId
              ? 'Generate a tailored resume — your uploaded resume as the template, text rewritten to match the job'
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

      {/* Generate Button — the only action needed */}
      {!generatedResume && !isGenerating && (
        <Card>
          <CardContent className="py-12 text-center">
            <FileText className="w-16 h-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-2">
              {jobId ? 'Ready to Generate Your Resume' : 'Select a job first'}
            </h2>
            <p className="text-slate-500 dark:text-slate-400 max-w-lg mx-auto mb-6">
              Your uploaded resume will be used as the template. The text will be rewritten
              to emphasize skills and experience that match this job — using only your
              verified skills from your profile.
            </p>
            <Button
              size="lg"
              onClick={handleGenerate}
              disabled={!jobId}
            >
              <Sparkles className="w-5 h-5 mr-2" />
              {jobId ? 'Generate Resume' : 'Go to Job Matching first'}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Generated Resume Results */}
      {generatedResume && (
        <div className="space-y-6">
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
                    {generatedResume.format?.toUpperCase() || 'DOCX'}
                  </Badge>
                  <Badge variant="primary" className="text-xs">
                    Resume #{generatedResume.id?.slice(0, 8) || 'New'}
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <Button onClick={() => handleDownload('docx')}>
                  <Download className="w-4 h-4 mr-2" /> Download DOCX
                </Button>
              </div>
            </CardContent>
          </Card>
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
              {resumes.map((resume: any) => (
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
                            {resume.format?.toUpperCase() || 'DOCX'}
                          </Badge>
                          <span className="text-xs text-slate-500 dark:text-slate-400">
                            {formatRelativeTime(resume.created_at)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-slate-500 dark:text-slate-400">
              <FileText className="w-8 h-8 mx-auto mb-3" />
              <p>No resumes generated yet. Click "Generate Resume" above!</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}