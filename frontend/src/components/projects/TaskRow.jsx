import { Check, Diamond, Ban, Layers } from 'lucide-react'
import { cn, formatDate } from '../../lib/utils'
import { PRIORITY_BADGE, isOverdue } from './shared'

export default function TaskRow({ task, projectColor, projectName, subtaskCount = 0, onClick, onToggleComplete }) {
  const overdue = isOverdue(task.due_date, task.completed)

  return (
    <div
      onClick={onClick}
      className="flex items-center gap-2 px-2.5 py-2 rounded-md hover:bg-white/[0.03] cursor-pointer group transition-colors"
    >
      <button
        onClick={(e) => { e.stopPropagation(); onToggleComplete?.(task) }}
        className={cn(
          'w-4 h-4 shrink-0 flex items-center justify-center border transition-colors',
          task.is_milestone ? 'rotate-45' : 'rounded-full',
          task.completed
            ? 'bg-lattice-600 border-lattice-600'
            : 'border-dark-muted hover:border-lattice-500'
        )}
      >
        {task.completed && <Check size={10} className={cn('text-white', task.is_milestone && '-rotate-45')} />}
      </button>

      <span className={cn('flex-1 min-w-0 truncate text-sm', task.completed ? 'text-dark-muted line-through' : 'text-dark-text')}>
        {task.name}
      </span>

      {task.blocked && (
        <span title="Blocked by dependency" className="text-dark-subtle shrink-0">
          <Ban size={12} />
        </span>
      )}

      {subtaskCount > 0 && (
        <span className="flex items-center gap-0.5 text-2xs text-dark-subtle shrink-0">
          <Layers size={10} />{subtaskCount}
        </span>
      )}

      {task.is_milestone && <Diamond size={10} className="text-lattice-400 shrink-0" />}

      {task.priority && (
        <span className={cn('text-2xs px-1.5 py-0.5 rounded border shrink-0', PRIORITY_BADGE[task.priority])}>
          {task.priority}
        </span>
      )}

      {task.effort != null && (
        <span className="text-2xs px-1.5 py-0.5 rounded border border-dark-border text-dark-subtle shrink-0">
          {task.effort}pt
        </span>
      )}

      {projectName && (
        <span className="flex items-center gap-1 text-2xs text-dark-subtle shrink-0">
          <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: projectColor }} />
          {projectName}
        </span>
      )}

      {task.due_date && (
        <span className={cn('text-2xs shrink-0', overdue ? 'text-red-400' : 'text-dark-subtle')}>
          {formatDate(task.due_date)}
        </span>
      )}
    </div>
  )
}
