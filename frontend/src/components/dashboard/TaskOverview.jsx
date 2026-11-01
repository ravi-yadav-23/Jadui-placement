import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { ProgressBar } from '@/components/ui'
import { cn } from '@/lib/utils'
import { useApp, ACTIONS } from '@/context/AppContext'

const CATEGORY_COLORS = {
  DSA:       'text-primary bg-primary/10',
  Design:    'text-secondary bg-secondary/10',
  Interview: 'text-accent bg-accent/10',
  Project:   'text-success bg-success/10',
  Core:      'text-warning bg-warning/10',
  Career:    'text-muted bg-muted/10',
}

export default function TaskOverview({ todayTasks, completedToday }) {
  const { dispatch } = useApp()

  const handleComplete = (id) => {
    dispatch({ type: ACTIONS.COMPLETE_TASK, payload: id })
  }

  return (
    <div className="lg:col-span-2 bg-card border border-border rounded-xl overflow-hidden flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <h3 className="font-semibold text-white">Today&apos;s Tasks</h3>
        <Link href="/dashboard/tasks" className="text-xs text-primary hover:underline flex items-center gap-1">
          View all <ArrowRight className="w-3 h-3" />
        </Link>
      </div>
      <div className="divide-y divide-border flex-1 overflow-y-auto">
        {todayTasks.length === 0 ? (
          <div className="px-6 py-8 text-center text-muted text-sm">No tasks for today.</div>
        ) : (
          todayTasks.map((task) => (
            <div key={task.id} className="flex items-center gap-4 px-6 py-4 hover:bg-surface/40 transition-colors group">
              <button onClick={() => handleComplete(task.id)} className="flex-shrink-0">
                <div className={cn(
                  'w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all duration-200',
                  task.completed
                    ? 'bg-success border-success'
                    : 'border-muted/40 group-hover:border-primary'
                )}>
                  {task.completed && <div className="w-2 h-2 rounded-full bg-white" />}
                </div>
              </button>
              <div className="flex-1 min-w-0">
                <p className={cn('text-sm font-medium truncate', task.completed ? 'line-through text-muted' : 'text-white')}>
                  {task.title}
                </p>
              </div>
              <span className={cn('text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0', CATEGORY_COLORS[task.category] || 'text-muted bg-muted/10')}>
                {task.category}
              </span>
            </div>
          ))
        )}
      </div>
      {todayTasks.length > 0 && (
        <div className="px-6 py-4 border-t border-border mt-auto">
          <div className="flex items-center justify-between text-xs text-muted mb-2">
            <span>Daily progress</span>
            <span className="font-medium text-white">{completedToday}/{todayTasks.length} done</span>
          </div>
          <ProgressBar value={completedToday} max={todayTasks.length} color="success" />
        </div>
      )}
    </div>
  )
}
