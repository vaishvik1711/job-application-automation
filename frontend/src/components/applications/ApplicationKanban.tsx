import { useState, useCallback, useMemo } from 'react'
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
import { Application, ApplicationStatus } from '@/types'
import { ApplicationCard } from '@/components/applications/ApplicationCard'
import { ApplicationDetail } from '@/components/applications/ApplicationDetail'
import { useApplicationStore } from '@/store'
import { useApplications, useUpdateApplicationStatus, useDeleteApplication } from '@/hooks/useApi'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { cn } from '@/utils/helpers'
import {
  RefreshCw,
  Plus,
  Clock,
} from 'lucide-react'
import { toast } from 'sonner'

const COLUMN_ORDER: ApplicationStatus[] = [
  'READY_TO_APPLY',
  'APPLYING',
  'SUBMITTED',
  'INTERVIEW_SCHEDULED',
  'INTERVIEWED',
  'OFFER',
  'REJECTED',
  'WITHDRAWN',
]

const COLUMN_LABELS: Record<ApplicationStatus, string> = {
  READY_TO_APPLY: 'Ready to Apply',
  APPLYING: 'Applying',
  SUBMITTED: 'Submitted',
  INTERVIEW_SCHEDULED: 'Interview Scheduled',
  INTERVIEWED: 'Interviewed',
  OFFER: 'Offer',
  REJECTED: 'Rejected',
  WITHDRAWN: 'Withdrawn',
}

const COLUMN_BG_COLORS: Record<ApplicationStatus, string> = {
  READY_TO_APPLY: 'bg-slate-50 dark:bg-slate-800/50',
  APPLYING: 'bg-blue-50 dark:bg-blue-900/10',
  SUBMITTED: 'bg-indigo-50 dark:bg-indigo-900/10',
  INTERVIEW_SCHEDULED: 'bg-purple-50 dark:bg-purple-900/10',
  INTERVIEWED: 'bg-orange-50 dark:bg-orange-900/10',
  OFFER: 'bg-green-50 dark:bg-green-900/10',
  REJECTED: 'bg-red-50 dark:bg-red-900/10',
  WITHDRAWN: 'bg-gray-50 dark:bg-gray-800/50',
}

const COLUMN_BORDER_COLORS: Record<ApplicationStatus, string> = {
  READY_TO_APPLY: 'border-slate-300 dark:border-slate-700',
  APPLYING: 'border-blue-300 dark:border-blue-700',
  SUBMITTED: 'border-indigo-300 dark:border-indigo-700',
  INTERVIEW_SCHEDULED: 'border-purple-300 dark:border-purple-700',
  INTERVIEWED: 'border-orange-300 dark:border-orange-700',
  OFFER: 'border-green-300 dark:border-green-700',
  REJECTED: 'border-red-300 dark:border-red-700',
  WITHDRAWN: 'border-gray-300 dark:border-gray-700',
}

// Draggable Card wrapper using dnd-kit
function DraggableCard({ application, onClick }: {
  application: Application
  onClick: () => void
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
      <ApplicationCard application={application} onClick={onClick} isDragging={isDragging} />
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
    <div ref={setNodeRef} className={cn('flex-1 min-w-[180px]', COLUMN_BG_COLORS[status], 'rounded-lg')}>
      {children}
    </div>
  )
}

export function ApplicationKanban() {
  const [detailApp, setDetailApp] = useState<Application | null>(null)
  const [showDetail, setShowDetail] = useState(false)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor)
  )

  const { data: appsData, isLoading, refetch } = useApplications({ page: 1, page_size: 100 })
  const updateStatusMutation = useUpdateApplicationStatus()
  const deleteMutation = useDeleteApplication()

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

  // Sync store columns with API data on initial load
  const totalInStore = Object.values(columns).flat().length
  if (applications.length > 0 && totalInStore !== applications.length) {
    const newColumns = { ...columns }
    COLUMN_ORDER.forEach((status) => {
      newColumns[status] = applications
        .filter((app) => app.status === status)
        .map((app) => app.id)
    })
    setColumns(newColumns)
  }

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
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
            <RefreshCw className="w-4 h-4 mr-2" /> Refresh
          </Button>
          <Button size="sm">
            <Plus className="w-4 h-4 mr-2" /> New Application
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
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8 gap-4 overflow-x-auto pb-2">
            {COLUMN_ORDER.map((status) => {
              const columnApps = getColumnApplications(status)
              return (
                <DroppableColumn key={status} status={status}>
                  <Card
                    className={cn(
                      'min-w-[180px] border-2 rounded-lg',
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
    </div>
  )
}
