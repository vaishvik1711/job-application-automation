import { useState } from 'react'
import { Application, ApplicationStatus } from '@/types'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Input'
import {
  X,
  Calendar,
  Clock,
  FileText,
  ExternalLink,
  CheckCircle,
  Save,
  Edit3,
  Trash2,
} from 'lucide-react'
import { cn, formatDateTime, formatRelativeTime } from '@/utils/helpers'
import { toast } from 'sonner'

const STATUS_OPTIONS: { value: ApplicationStatus; label: string }[] = [
  { value: 'READY_TO_APPLY', label: 'Ready to Apply' },
  { value: 'APPLYING', label: 'Applying' },
  { value: 'SUBMITTED', label: 'Submitted' },
  { value: 'INTERVIEW_SCHEDULED', label: 'Interview Scheduled' },
  { value: 'INTERVIEWED', label: 'Interviewed' },
  { value: 'OFFER', label: 'Offer!' },
  { value: 'REJECTED', label: 'Rejected' },
  { value: 'WITHDRAWN', label: 'Withdrawn' },
]

const STATUS_COLORS: Record<ApplicationStatus, string> = {
  READY_TO_APPLY: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  APPLYING: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  SUBMITTED: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300',
  INTERVIEW_SCHEDULED: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  INTERVIEWED: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  OFFER: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  REJECTED: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  WITHDRAWN: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
}

interface ApplicationDetailProps {
  application: Application | null
  isOpen: boolean
  onClose: () => void
  onUpdateStatus: (id: string, status: ApplicationStatus, notes?: string) => Promise<void>
  onDelete: (id: string) => Promise<void>
}

export function ApplicationDetail({ application, isOpen, onClose, onUpdateStatus, onDelete }: ApplicationDetailProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [notes, setNotes] = useState(application?.notes || '')
  const [followUpDate, setFollowUpDate] = useState(application?.follow_up_date || '')
  const [isSaving, setIsSaving] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  if (!application) return null

  const handleSave = async () => {
    setIsSaving(true)
    try {
      await onUpdateStatus(application.id, application.status, notes)
      toast.success('Application updated')
      setIsEditing(false)
    } catch (err) {
      toast.error('Failed to update application')
    } finally {
      setIsSaving(false)
    }
  }

  const handleStatusChange = async (newStatus: ApplicationStatus) => {
    setIsSaving(true)
    try {
      await onUpdateStatus(application.id, newStatus, notes)
      toast.success(`Status updated to ${STATUS_OPTIONS.find((s) => s.value === newStatus)?.label || newStatus}`)
    } catch (err) {
      toast.error('Failed to update status')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this application? This cannot be undone.')) return
    setIsDeleting(true)
    try {
      await onDelete(application.id)
      toast.success('Application deleted')
      onClose()
    } catch (err) {
      toast.error('Failed to delete application')
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div
      className={cn(
        'fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm transition-opacity duration-200',
        isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
      )}
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-slate-900 rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">{application.job.title}</h2>
            <p className="text-slate-500 dark:text-slate-400 mt-1">{application.job.company}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5 text-slate-500 dark:text-slate-400" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Status Badge */}
          <div className="flex items-center gap-2">
            <Badge className={cn('text-sm', STATUS_COLORS[application.status])}>
              {STATUS_OPTIONS.find((s) => s.value === application.status)?.label || application.status}
            </Badge>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Created {formatRelativeTime(application.created_at)}
            </span>
          </div>

          {/* Timeline */}
          <Card variant="outline">
            <CardHeader>
              <CardTitle className="text-sm font-semibold">Timeline</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {application.applied_at && (
                <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                  <Clock className="w-4 h-4" />
                  <span>Applied</span>
                  <span className="text-slate-500 dark:text-slate-500">{formatDateTime(application.applied_at)}</span>
                </div>
              )}
              {application.submitted_at && (
                <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                  <CheckCircle className="w-4 h-4" />
                  <span>Submitted</span>
                  <span className="text-slate-500 dark:text-slate-500">{formatDateTime(application.submitted_at)}</span>
                </div>
              )}
              {application.interview_date && (
                <div className="flex items-center gap-2 text-purple-600 dark:text-purple-400">
                  <Calendar className="w-4 h-4" />
                  <span>Interview</span>
                  <span className="text-slate-500 dark:text-slate-500">{formatDateTime(application.interview_date)}</span>
                </div>
              )}
              {application.follow_up_date && (
                <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400">
                  <Calendar className="w-4 h-4" />
                  <span>Follow up</span>
                  <span className="text-slate-500 dark:text-slate-500">{formatDateTime(application.follow_up_date)}</span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Status Update */}
          <Card variant="outline">
            <CardHeader>
              <CardTitle className="text-sm font-semibold">Update Status</CardTitle>
              <CardDescription>Move this application to a different stage</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {STATUS_OPTIONS.filter((s) => s.value !== application.status).map((opt) => (
                  <Button
                    key={opt.value}
                    variant="outline"
                    size="sm"
                    onClick={() => handleStatusChange(opt.value)}
                    disabled={isSaving}
                  >
                    {opt.label}
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Notes */}
          <Card variant="outline">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold">Notes</CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsEditing(!isEditing)}
                >
                  {isEditing ? <X className="w-4 h-4" /> : <Edit3 className="w-4 h-4" />}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {isEditing ? (
                <Textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Add notes about this application..."
                  rows={4}
                />
              ) : (
                <p className="text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap">
                  {application.notes || 'No notes added yet.'}
                </p>
              )}
              {isEditing && (
                <div className="flex justify-end gap-2 mt-3">
                  <Button variant="outline" size="sm" onClick={() => setIsEditing(false)}>
                    Cancel
                  </Button>
                  <Button size="sm" onClick={handleSave} loading={isSaving}>
                    <Save className="w-4 h-4 mr-2" /> Save Notes
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Resume & Actions */}
          {application.resume && (
            <Card variant="outline">
              <CardHeader>
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <FileText className="w-4 h-4" /> Resume
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-slate-900 dark:text-white">
                      {application.resume.job_title} at {application.resume.company}
                    </p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      Format: {application.resume.format.toUpperCase()}
                    </p>
                  </div>
                  {application.resume.file_url && (
                    <a
                      href={application.resume.file_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                      aria-label="View resume"
                    >
                      <ExternalLink className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                    </a>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Follow-up Date */}
          {isEditing && (
            <div className="space-y-2">
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Follow-up Date
              </label>
              <Input
                type="date"
                value={followUpDate}
                onChange={(e) => setFollowUpDate(e.target.value)}
              />
            </div>
          )}

          {/* Delete */}
          <div className="flex justify-end pt-4 border-t border-slate-200 dark:border-slate-700">
            <Button variant="danger" size="sm" onClick={handleDelete} loading={isDeleting}>
              <Trash2 className="w-4 h-4 mr-2" /> Delete Application
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
