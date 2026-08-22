import { useState, useCallback, useMemo, useEffect } from 'react'
import {
  DndContext,
  useDraggable,
  useDroppable,
  KeyboardSensor,
  PointerSensor,
  useSensors,
  useSensor,
  closestCenter,
} from '@dnd-kit/core'
import type { DragEndEvent, DragStartEvent } from '@dnd-kit/core'
import { Application, ApplicationStatus, ApplyMode } from '@/types'
import { ApplicationCard } from '@/components/applications/ApplicationCard'
import { ApplicationDetail } from '@/components/applications/ApplicationDetail'
import { ModePickerDialog } from '@/components/applications/ModePickerDialog'
import { useApplicationStore } from '@/store'
import {
  useApplications,
  useUpdateApplicationStatus,
  useDeleteApplication,
  useApplyToJob,
} from '@/hooks/useApi'
import { applicationsApi } from '@/services/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { cn } from '@/utils/helpers'
import {
  RefreshCw,
  Clock,
  Play,
  Search,
  X,
} from 'lucide-react'
import { toast } from 'sonner'

const ALL_COLUMN_ORDER: ApplicationStatus[] = [
  'READY_TO_APPLY',
  'APPLYING',
  'NEEDS_REVIEW',
  'SUBMITTED',
  'INTERVIEW_SCHEDULED',
  'INTERVIEWED',
  'OFFER',
  'FAILED',
  'REJECTED',
  'WITHDRAWN',
]

const ACTIVE_COLUMN_ORDER: ApplicationStatus[] = [
  'READY_TO_APPLY',
  'APPLYING',
  'NEEDS_REVIEW',
  'SUBMITTED',
  'INTERVIEW_SCHEDULED',
  'OFFER',
]

const COLUMN_LABELS: Record<ApplicationStatus, string> = {
  READY_TO_APPLY: 'Ready to Apply',
  APPLYING: 'Applying',
  NEEDS_REVIEW: 'Needs Review',
  SUBMITTED: 'Submitted',
  INTERVIEW_SCHEDULED: 'Interview Scheduled',
  INTERVIEWED: 'Interviewed',
  OFFER: 'Offer',
  FAILED: 'Failed',
  REJECTED: 'Rejected',
  WITHDRAWN: 'Withdrawn',
}

const COLUMN_BG_COLORS: Record<ApplicationStatus, string> = {
  READY_TO_APPLY: 'bg-slate-50 dark:bg-slate-800/50',
  APPLYING: 'bg-blue-50 dark:bg-blue-900/10',
  NEEDS_REVIEW: 'bg-amber-50 dark:bg-amber-900/10',
  SUBMITTED: 'bg-indigo-50 dark:bg-indigo-900/10',
  INTERVIEW_SCHEDULED: 'bg-purple-50 dark:bg-purple-900/10',
  INTERVIEWED: 'bg-orange-50 dark:bg-orange-900/10',
  OFFER: 'bg-green-50 dark:bg-green-900/10',
  FAILED: 'bg-red-50 dark:bg-red-900/10',
  REJECTED: 'bg-red-50 dark:bg-red-900/10',
  WITHDRAWN: 'bg-gray-50 dark:bg-gray-800/50',
}

const COLUMN_BORDER_COLORS: Record<ApplicationStatus, string> = {
  READY_TO_APPLY: 'border-slate-300 dark:border-slate-700',
  APPLYING: 'border-blue-300 dark:border-blue-700',
  NEEDS_REVIEW: 'border-amber-300 dark:border-amber-700',
  SUBMITTED: 'border-indigo-300 dark:border-indigo-700',
  INTERVIEW_SCHEDULED: 'border-purple-300 dark:border-purple-700',
  INTERVIEWED: 'border-orange-300 dark:border-orange-700',
  OFFER: 'border-green-300 dark:border-green-700',
  FAILED: 'border-red-400 dark:border-red-700',
  REJECTED: 'border-red-300 dark:border-red-700',
  WITHDRAWN: 'border-gray-300 dark:border-gray-700',
}

// Draggable Card wrapper using dnd-kit
function DraggableCard({ application, onClick, onApply }: {
  application: Application
  onClick: () => void
  onApply?: (app: Application) => void
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: application.id,
    data: { application },
  })

  const style = {
    transform: transform ? `translate3d(${transform.x}px, ${transform.y}px, 0)` : undefined,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <ApplicationCard
        application={application}
        onClick={onClick}
        isDragging={isDragging}
        onApply={onApply}
      />
    </div>
  )
}

// Droppable Column wrapper
function DroppableColumn({ status, children }: {
  status: ApplicationStatus
  children: React.ReactNode
}) {
  const { setNodeRef } = useDroppable({ id: `column-${status}` })
  return (
    <div ref={setNodeRef} className={cn('w-[270px] flex-shrink-0', COLUMN_BG_COLORS[status], 'rounded-lg')}>
      {children}
    </div>
  )
}

export function ApplicationKanban() {
  const [detailApp, setDetailApp] = useState<Application | null>(null)
  const [showDetail, setShowDetail] = useState(false)
  const [viewFilter, setViewFilter] = useState<'active' | 'all'>('active')
  const [searchQuery, setSearchQuery] = useState('')
  const [batchApply, setBatchApply] = useState<{ ids: string[]; autoSubmitEnabled: boolean } | null>(null)
  const [isBatchApplying, setIsBatchApplying] = useState(false)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor)
  )

  const { data: appsData, isLoading, refetch } = useApplications({ page: 1, page_size: 100 })
  const updateStatusMutation = useUpdateApplicationStatus()
  const deleteMutation = useDeleteApplication()
  const applyMutation = useApplyToJob()

  const {
    columns,
    setColumns,
    moveApplication,
    setDraggedApplication,
  } = useApplicationStore()

  const rawApplications: Application[] = appsData?.items || []

  // Filter applications by search query
  const applications = useMemo(() => {
    if (!searchQuery.trim()) return rawApplications
    const q = searchQuery.toLowerCase()
    return rawApplications.filter((app) =>
      (app.job?.title || '').toLowerCase().includes(q) ||
      (app.job?.company || '').toLowerCase().includes(q) ||
      (app.notes || '').toLowerCase().includes(q)
    )
  }, [rawApplications, searchQuery])

  const applicationMap = useMemo(() => {
    const map = new Map<string, Application>()
    applications.forEach((app) => map.set(app.id, app))
    return map
  }, [applications])

  const activeColumnList = viewFilter === 'active' ? ACTIVE_COLUMN_ORDER : ALL_COLUMN_ORDER

  // Sync store columns with API data when the server list changes
  useEffect(() => {
    if (rawApplications.length === 0) return
    const newColumns = {} as Record<ApplicationStatus, string[]>
    ALL_COLUMN_ORDER.forEach((status) => {
      newColumns[status] = rawApplications
        .filter((app) => app.status === status)
        .map((app) => app.id)
    })
    setColumns(newColumns)
  }, [rawApplications, setColumns])

  const getColumnApplications = (status: ApplicationStatus): Application[] => {
    const ids = columns[status] || []
    return ids.map((id) => applicationMap.get(id)).filter(Boolean) as Application[]
  }

  const totalApplications = rawApplications.length

  const handleDragStart = useCallback(
    (event: DragStartEvent) => {
      setDraggedApplication(event.active.id as string)
    },
    [setDraggedApplication]
  )

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      setDraggedApplication(null)
      const { active, over } = event
      if (!over) return

      const overId = over.id as string
      const activeId = active.id as string

      if (overId.startsWith('column-')) {
        const targetStatus = overId.replace('column-', '') as ApplicationStatus
        const sourceStatus = ALL_COLUMN_ORDER.find((col) => columns[col]?.includes(activeId))

        if (sourceStatus && sourceStatus !== targetStatus) {
          moveApplication(activeId, sourceStatus, targetStatus)
          try {
            await updateStatusMutation.mutateAsync({
              id: activeId,
              status: targetStatus,
            })
            toast.success(`Application moved to ${COLUMN_LABELS[targetStatus]}`)
          } catch (err: any) {
            console.error('Failed to update status:', err)
            toast.error('Failed to update application status')
            moveApplication(activeId, targetStatus, sourceStatus)
          }
        }
      } else if (overId !== activeId) {
        const targetStatus = ALL_COLUMN_ORDER.find((col) => columns[col]?.includes(overId))
        const sourceStatus = ALL_COLUMN_ORDER.find((col) => columns[col]?.includes(activeId))

        if (sourceStatus && targetStatus && sourceStatus !== targetStatus) {
          moveApplication(activeId, sourceStatus, targetStatus)
          try {
            await updateStatusMutation.mutateAsync({
              id: activeId,
              status: targetStatus,
            })
            toast.success(`Application moved to ${COLUMN_LABELS[targetStatus]}`)
          } catch (err: any) {
            console.error('Failed to update status:', err)
            toast.error('Failed to update application status')
            moveApplication(activeId, targetStatus, sourceStatus)
          }
        }
      }
    },
    [columns, moveApplication, setDraggedApplication, updateStatusMutation]
  )

  const handleCardClick = (app: Application) => {
    setDetailApp(app)
    setShowDetail(true)
  }

  const handleApplyOne = useCallback((app: Application) => {
    setBatchApply({ ids: [app.id], autoSubmitEnabled: false })
  }, [])

  const handleApplyAllReady = useCallback(async () => {
    const readyIds = rawApplications
      .filter((a) => a.status === 'READY_TO_APPLY')
      .map((a) => a.id)
    if (readyIds.length === 0) {
      toast.info('No applications are ready to apply')
      return
    }
    let autoSubmitEnabled = false
    try {
      const statusRes = await applicationsApi.applyStatus(readyIds[0])
      autoSubmitEnabled = !!statusRes.data.data?.auto_submit_enabled
    } catch {
      // Status probe failed — default to manual-only
    }
    setBatchApply({ ids: readyIds, autoSubmitEnabled })
  }, [rawApplications])

  const handleStartBatch = useCallback(async (mode: ApplyMode) => {
    if (!batchApply) return
    setIsBatchApplying(true)
    try {
      let started = 0
      for (const id of batchApply.ids) {
        try {
          await applyMutation.mutateAsync({ id, mode })
          started += 1
        } catch (err: any) {
          const detail = err?.response?.data?.detail || 'apply failed'
          toast.error(`${detail}`)
        }
      }
      if (started > 0) {
        toast.success(
          mode === 'auto'
            ? `Auto-applying to ${started} application${started > 1 ? 's' : ''}...`
            : `${started} form${started > 1 ? 's' : ''} filled — review before confirming submission`
        )
      }
      setBatchApply(null)
      refetch()
    } finally {
      setIsBatchApplying(false)
    }
  }, [batchApply, applyMutation, refetch])

  const handleUpdateStatus = async (id: string, status: ApplicationStatus, notes?: string) => {
    await updateStatusMutation.mutateAsync({ id, status, notes })
    refetch()
    setShowDetail(false)
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteMutation.mutateAsync(id)
      toast.success('Application deleted')
      setShowDetail(false)
    } catch (err) {
      toast.error('Failed to delete application')
    }
  }

  // Quick summary counts
  const readyCount = rawApplications.filter((a) => a.status === 'READY_TO_APPLY').length
  const submittedCount = rawApplications.filter((a) => a.status === 'SUBMITTED').length
  const interviewCount = rawApplications.filter((a) => a.status === 'INTERVIEW_SCHEDULED' || a.status === 'INTERVIEWED').length
  const offerCount = rawApplications.filter((a) => a.status === 'OFFER').length

  return (
    <div className="space-y-4">
      {/* Header Controls Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Pipeline Board</h2>
          <div className="flex items-center gap-1.5 text-xs">
            <span className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 font-medium">
              {totalApplications} Total
            </span>
            {readyCount > 0 && (
              <span className="px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium">
                {readyCount} Ready
              </span>
            )}
            {submittedCount > 0 && (
              <span className="px-2 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 font-medium">
                {submittedCount} Submitted
              </span>
            )}
            {interviewCount > 0 && (
              <span className="px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 font-medium">
                {interviewCount} Interviews
              </span>
            )}
            {offerCount > 0 && (
              <span className="px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 font-medium">
                {offerCount} Offer!
              </span>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Quick Search */}
          <div className="relative w-48 sm:w-60">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter company or role..."
              className="pl-8 text-xs h-8"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* View Filter Toggle */}
          <div className="flex items-center rounded-lg border border-slate-200 dark:border-slate-700 p-0.5 bg-slate-50 dark:bg-slate-800 text-xs">
            <button
              onClick={() => setViewFilter('active')}
              className={cn(
                'px-2.5 py-1 rounded-md font-medium transition-colors',
                viewFilter === 'active'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
              )}
            >
              Active Stages
            </button>
            <button
              onClick={() => setViewFilter('all')}
              className={cn(
                'px-2.5 py-1 rounded-md font-medium transition-colors',
                viewFilter === 'all'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
              )}
            >
              All Stages
            </button>
          </div>

          {readyCount > 0 && (
            <Button
              variant="primary"
              size="sm"
              onClick={handleApplyAllReady}
              disabled={isBatchApplying}
              className="h-8 text-xs"
            >
              <Play className="w-3.5 h-3.5 mr-1.5" />
              Apply to Ready ({readyCount})
            </Button>
          )}

          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading} className="h-8 text-xs">
            <RefreshCw className="w-3.5 h-3.5 mr-1.5" /> Refresh
          </Button>
        </div>
      </div>

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="flex gap-4 overflow-x-auto pb-2">
          {activeColumnList.map((status) => (
            <Card key={status} className="w-[270px] flex-shrink-0">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">{COLUMN_LABELS[status]}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {[...Array(2)].map((_, i) => (
                    <div key={i} className="h-32 bg-slate-200 dark:bg-slate-700 rounded-lg animate-pulse" />
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Kanban Board with Drag and Drop */}
      {!isLoading && (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="flex gap-4 items-start overflow-x-auto pb-4">
            {activeColumnList.map((status) => {
              const columnApps = getColumnApplications(status)
              return (
                <DroppableColumn key={status} status={status}>
                  <Card
                    className={cn(
                      'w-full border-2 rounded-xl',
                      COLUMN_BG_COLORS[status],
                      COLUMN_BORDER_COLORS[status],
                      'transition-colors'
                    )}
                  >
                    <CardHeader className="pb-2 pt-3 px-3">
                      <CardTitle className="text-sm font-semibold text-slate-900 dark:text-white flex items-center justify-between">
                        <span>{COLUMN_LABELS[status]}</span>
                        <Badge variant="neutral" className="text-xs">
                          {columnApps.length}
                        </Badge>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-0 pb-3 px-3">
                      <div className="space-y-2.5 min-h-[50px]">
                        {columnApps.map((app) => (
                          <DraggableCard
                            key={app.id}
                            application={app}
                            onClick={() => handleCardClick(app)}
                            onApply={status === 'READY_TO_APPLY' ? handleApplyOne : undefined}
                          />
                        ))}
                        {columnApps.length === 0 && (
                          <div className="text-center py-6 text-xs text-slate-400 dark:text-slate-500 border border-dashed border-slate-200 dark:border-slate-700/50 rounded-lg">
                            Drop card here
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </DroppableColumn>
              )
            })}
          </div>
        </DndContext>
      )}

      {/* Empty State */}
      {!isLoading && totalApplications === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <Clock className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
              No applications in your pipeline yet
            </h3>
            <p className="text-slate-500 dark:text-slate-400 mb-6 max-w-md mx-auto">
              Select matched jobs on the Jobs page and click "Generate Resumes" to automatically populate your application tracking board.
            </p>
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="w-4 h-4 mr-2" /> Check for Applications
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Application Detail Modal */}
      <ApplicationDetail
        application={detailApp}
        isOpen={showDetail}
        onClose={() => setShowDetail(false)}
        onUpdateStatus={handleUpdateStatus}
        onDelete={handleDelete}
      />

      {/* Mode Picker Dialog for Batch / Single Apply */}
      <ModePickerDialog
        open={batchApply !== null}
        count={batchApply?.ids.length ?? 0}
        autoSubmitEnabled={batchApply?.autoSubmitEnabled ?? false}
        isStarting={isBatchApplying}
        onClose={() => setBatchApply(null)}
        onStart={handleStartBatch}
      />
    </div>
  )
}
