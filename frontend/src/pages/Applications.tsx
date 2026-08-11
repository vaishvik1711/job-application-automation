import { ApplicationKanban } from '@/components/applications/ApplicationKanban'

export function Applications() {
  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Applications</h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1">
          Track and manage your job applications through the pipeline
        </p>
      </div>

      {/* Kanban Board */}
      <ApplicationKanban />
    </div>
  )
}
