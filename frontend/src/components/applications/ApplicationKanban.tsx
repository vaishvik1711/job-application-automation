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
import { cn } from '@/utils/helpers'
import {
  RefreshCw,
  Clock,
  Play,
} from 'lucide-react'
import { toast } from 'sonner'

const COLUMN_ORDER: ApplicationStatus[] = [
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
  // Batch apply state: null = dialog closed
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

  const applications: Application[] = appsData?.items || []
  const applicationMap = useMemo(() => {
    const map = new Map<string, Application>()
    applications.forEach((app) => map.set(app.id, app))
    return map
  }, [applications])

  // Sync store columns with API data when the server list changes.
  // Runs in an effect — writing to the store during render can loop.
  useEffect(() => {
    if (applications.length === 0) return
    const newColumns = {} as Record<ApplicationStatus, string[]>
    COLUMN_ORDER.forEach((status) => {
      newColumns[status] = applications
        .filter((app) => app.status === status)
        .map((app) => app.id)
    })
    setColumns(newColumns)
  }, [applications, setColumns])

  const getColumnApplications = (status: ApplicationStatus): Application[] => {
    const ids = columns[status] || []
    return ids.map((id) => applicationMap.get(id)).filter(Boolean) as Application[]
  }

  const totalApplications = Object.values(columns).flat().length

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

      // Determine the source and target columns
      const overId = over.id as string
      const activeId = active.id as string

      // Check if dropped on a column
      if (overId.startsWith('column-')) {
        const targetStatus = overId.replace('column-', '') as ApplicationStatus
        const sourceStatus = COLUMN_ORDER.find((col) => columns[col]?.includes(activeId))

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
        // Dropped on another card - determine columns
        const targetStatus = COLUMN_ORDER.find((col) => columns[col]?.includes(overId))
        const sourceStatus = COLUMN_ORDER.find((col) => columns[col]?.includes(activeId))

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

  // Quick "Apply" from a Ready card — opens the mode picker for that one app.
  const handleApplyOne = useCallback((app: Application) => {
    setBatchApply({ ids: [app.id], autoSubmitEnabled: false })
  }, [])

  // Header action — apply to every card in the Ready column.
  const handleApplyAllReady = useCallback(async () => {
    const readyIds = applications
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
      // Status probe failed — default to manual-only.
    }
    setBatchApply({ ids: readyIds, autoSubmitEnabled })
  }, [applications])

  // Run the batch with the chosen mode. Backend serializes browser runs to
  // one at a time; we fire sequentially so each gets a clean start.
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
            : `${started} form${started > 1 ? 's' : ''} being filled — you'll review before anything is submitted`
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

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Application Pipeline</h2>
          <Badge variant="neutral" className="text-xs">
            {totalApplications} applications
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          {(() => {
            const readyCount = applications.filter((a) => a.status === 'READY_TO_APPLY').length
            if (readyCount === 0) return null
            return (
              <Button
                variant="primary"
                size="sm"
                onClick={handleApplyAllReady}
                disabled={isBatchApplying}
              >
                <Play className="w-4 h-4 mr-2" />
                Apply to all ready ({readyCount})
              </Button>
            )
          })()}
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
            <RefreshCw className="w-4 h-4 mr-2" /> Refresh
          </Button>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8 gap-4 overflow-x-auto">
          {COLUMN_ORDER.map((status) => (
            <Card key={status} className="min-w-[180px]">
              <CardHeader>
                <CardTitle className="text-sm font-medium">{COLUMN_LABELS[status]}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-40 bg-slate-200 dark:bg-slate-700 rounded-lg animate-pulse" />
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Kanban Board */}
      {!isLoading && (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          {/* Fixed-width columns in a scrollable row — an 8-col grid squeezes
              cards below readable width on smaller screens. */}
          <div className="flex gap-4 items-start overflow-x-auto pb-2">
            {COLUMN_ORDER.map((status) => {
              const columnApps = getColumnApplications(status)
              return (
                <DroppableColumn key={status} status={status}>
                  <Card
                    className={cn(
                      'w-full border-2 rounded-lg',
                      COLUMN_BG_COLORS[status],
                      COLUMN_BORDER_COLORS[status],
                      'transition-colors'
                    )}
                  >
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-slate-900 dark:text-white flex items-center justify-between">
                        <span>{COLUMN_LABELS[status]}</span>
                        <Badge variant="neutral" className="text-xs">
                          {columnApps.length}
                        </Badge>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-0 pb-2">
                      <div className="space-y-2 min-h-[40px]">
                        {columnApps.map((app) => (
                          <DraggableCard
                            key={app.id}
                            application={app}
                            onClick={() => handleCardClick(app)}
                            onApply={status === 'READY_TO_APPLY' ? handleApplyOne : undefined}
                          />
                        ))}
                        {columnApps.length === 0 && (
                          <div className="text-center py-4 text-xs text-slate-500 dark:text-slate-400">
                            Drop here
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
            <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-2">
              No applications yet
            </h3>
            <p className="text-slate-500 dark:text-slate-400 mb-4">
              Applications from your job matching will appear here as you track them through the pipeline.
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

      {/* Submission mode picker for batch/one-off apply */}
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
