import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, CheckCircle, AlertCircle, Loader2, X } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Progress } from '@/components/ui/Progress'
import { cn } from '@/utils/helpers'
import { uploadResume, UploadResponse } from '@/services/api'
import { useProfileStore } from '@/store/index'
import type { CandidateProfile } from '@/types'
import { toast } from 'sonner'

interface ResumeUploadProps {
  onComplete?: (profile: any) => void
}

export function ResumeUpload({ onComplete }: ResumeUploadProps) {
  const [uploadProgress, setUploadProgress] = useState<number>(0)
  const [parseProgress, setParseProgress] = useState<number>(0)
  const [stage, setStage] = useState<'idle' | 'uploading' | 'parsing' | 'complete' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const { setProfile, setResumeUploading } = useProfileStore()

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    // Validate file type
    const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
    if (!allowedTypes.includes(file.type)) {
      setError('Invalid file type. Please upload PDF, DOCX, or TXT files only.')
      setStage('error')
      return
    }

    // Validate file size (10MB)
    if (file.size > 10 * 1024 * 1024) {
      setError('File size must be less than 10MB.')
      setStage('error')
      return
    }

    setUploadedFile(file)
    setError(null)
    setStage('uploading')
    setUploadProgress(0)
    setResumeUploading(true)

    try {
      // Upload resume — the backend parses the resume and returns profile data in one step
      const uploadResponse: UploadResponse = await uploadResume(file, (progress) => {
        setUploadProgress(progress)
      })

      // Use the profile data returned directly by the upload endpoint
      if (uploadResponse.profile) {
        setProfile(uploadResponse.profile as CandidateProfile)
        setStage('complete')
        onComplete?.(uploadResponse.profile)
        toast.success('Profile created from resume!')
      } else {
        // Fallback: profile data wasn't in upload response; use parse endpoint
        const { parseResume } = await import('@/services/api')
        setStage('parsing')
        setParseProgress(0)
        const parseResponse = await parseResume(uploadResponse.file_id, (progress) => {
          setParseProgress(progress)
        })
        if (parseResponse.profile) {
          setProfile(parseResponse.profile as CandidateProfile)
          setStage('complete')
          onComplete?.(parseResponse.profile)
          toast.success('Profile created from resume!')
        } else {
          setError('Failed to parse resume. Please try again or create profile manually.')
          setStage('error')
        }
      }
    } catch (err: any) {
      console.error('Resume upload/parse error:', err)
      setError(err.response?.data?.detail || 'Failed to process resume. Please try again.')
      setStage('error')
    } finally {
      setResumeUploading(false)
    }
  }, [setProfile, setResumeUploading, onComplete])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    maxFiles: 1,
    disabled: stage === 'uploading' || stage === 'parsing',
  })

  const handleRemoveFile = () => {
    setUploadedFile(null)
    setStage('idle')
    setUploadProgress(0)
    setParseProgress(0)
    setError(null)
  }

  const handleRetry = () => {
    if (uploadedFile) {
      onDrop([uploadedFile])
    }
  }

  if (stage === 'complete' && uploadedFile) {
    return (
      <Card className="border-green-200 dark:border-green-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
            Resume Processed Successfully
          </CardTitle>
          <CardDescription>Your profile has been created from the uploaded resume.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
            <FileText className="w-6 h-6 text-green-600 dark:text-green-400 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="font-medium text-slate-900 dark:text-white truncate">{uploadedFile.name}</p>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {Math.round(uploadedFile.size / 1024)} KB
              </p>
            </div>
            <Button variant="ghost" size="sm" onClick={handleRemoveFile}>
              <X className="w-4 h-4" />
            </Button>
          </div>
          <Button onClick={handleRemoveFile} variant="outline">
            Upload Another Resume
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload Resume</CardTitle>
        <CardDescription>
          Upload your resume (PDF, DOCX, or TXT) to automatically extract and populate your profile information.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-red-700 dark:text-red-300 font-medium">Error</p>
              <p className="text-sm text-red-600 dark:text-red-400 mt-1">{error}</p>
            </div>
            <Button variant="ghost" size="sm" onClick={handleRetry}>
              Retry
            </Button>
          </div>
        )}

        <div
          {...getRootProps()}
          className={cn(
            'relative border-2 border-dashed rounded-xl p-8 text-center transition-all',
            isDragActive
              ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
              : 'border-slate-300 dark:border-slate-600 hover:border-primary-400 dark:hover:border-primary-600'
          )}
        >
          <input {...getInputProps()} />
          {stage === 'uploading' && (
            <div className="space-y-4">
              <Loader2 className="w-10 h-10 text-primary-600 dark:text-primary-400 animate-spin mx-auto" />
              <p className="text-slate-600 dark:text-slate-400">Uploading resume...</p>
              <Progress value={uploadProgress} label="Upload Progress" />
            </div>
          )}
          {stage === 'parsing' && (
            <div className="space-y-4">
              <Loader2 className="w-10 h-10 text-primary-600 dark:text-primary-400 animate-spin mx-auto" />
              <p className="text-slate-600 dark:text-slate-400">Parsing resume with AI...</p>
              <Progress value={parseProgress} label="Parse Progress" />
            </div>
          )}
          {stage === 'idle' && (
            <div className="space-y-4">
              <Upload className="w-12 h-12 text-slate-400 dark:text-slate-500 mx-auto" />
              <div className="space-y-2">
                <p className="text-lg font-medium text-slate-900 dark:text-white">Drag & drop your resume here</p>
                <p className="text-slate-500 dark:text-slate-400">or click to browse</p>
              </div>
              <p className="text-xs text-slate-400 dark:text-slate-500">
                Supported formats: PDF, DOCX, TXT (max 10MB)
              </p>
            </div>
          )}
        </div>

        {uploadedFile && stage === 'idle' && (
          <div className="mt-4 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg flex items-center gap-3">
            <FileText className="w-6 h-6 text-slate-500 dark:text-slate-400 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="font-medium text-slate-900 dark:text-white truncate">{uploadedFile.name}</p>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {Math.round(uploadedFile.size / 1024)} KB
              </p>
            </div>
            <Button variant="ghost" size="sm" onClick={handleRemoveFile}>
              <X className="w-4 h-4" />
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}