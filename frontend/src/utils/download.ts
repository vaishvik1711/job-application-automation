import api from '@/services/api'
import { toast } from 'sonner'

/**
 * Download a generated resume via the backend download endpoint.
 * Uses an authenticated axios blob request (not a plain link) so errors
 * surface as toasts instead of a blank tab.
 */
export async function downloadResume(resumeId: string | number, jobTitle?: string) {
  const id = String(resumeId)
  if (!id || id === 'undefined') {
    toast.error('No resume file available for this application')
    return
  }
  try {
    const res = await api.get(`/resumes/${id}/download`, { responseType: 'blob' })
    const blob = new Blob([res.data as BlobPart])
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    // Content-Disposition filename is not readable from JS; derive one.
    a.download = `resume_${id}.docx`
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
    toast.success(`Download started${jobTitle ? ` — ${jobTitle}` : ''}`)
  } catch (err: any) {
    const status = err?.response?.status
    if (status === 404) {
      toast.error(
        'Resume file no longer exists on the server (generated before cloud storage was enabled). Regenerate it from the job card.'
      )
    } else {
      toast.error('Failed to download resume')
    }
    throw err
  }
}
