import { useEffect, useState } from 'react'
import { Plus, Check, Trash2, AlertCircle, Clock, MoreHorizontal } from 'lucide-react'
import { useTaskStore, BUCKETS } from '../stores/useTaskStore'
import { useAppStore } from '../stores/useAppStore'
import { cn, formatDate } from '../lib/utils'

const BUCKET_LABELS = {
  inbox: 'Inbox',
  daily: 'Daily',
  weekly: 'Weekly',
  'long-term': 'Long-term',
  someday: 'Someday',
}

const BUCKET_COLORS = {
  inbox: 'border-dark-muted',
  daily: 'border-lattice-700/60',
  weekly: 'border-purple-700/60',
  'long-term': 'border-blue-700/60',
  someday: 'border-dark-muted/60',
}

const PRIORITY_COLORS = {
  urgent: 'bg-red-900/30 text-red-400 border-red-800/30',
  high: 'bg-yellow-900/30 text-yellow-400 border-yellow-800/30',
  normal: 'bg-dark-muted/20 text-dark-subtle border-dark-border',
  low: 'bg-dark-muted/10 text-dark-muted border-dark-border',
}

function TaskCard({ task, onComplete, onDelete }) {
  const [open, setOpen] = useState(false)

  return (
    <div className={cn(
      'bg-dark-surface border rounded-lg p-2.5 group',
      task.priority === 'urgent' ? 'border-red-800/40' :
      task.priority === 'high' ? 'border-yellow-800/30' : 'border-dark-border/60',
      'hover:border-lattice-700/40 transition-colors'
    )}>
      <div className="flex items-start gap-1.5">
        <button
          onClick={() => onComplete(task.id)}
          className="mt-0.5 w-4 h-4 rounded-full border border-dark-muted hover:border-lattice-500
                     hover:bg-lattice-900/30 flex items-center justify-center shrink-0 transition-colors"
        >
          <Check size={10} className="text-lattice-400 opacity-0 group-hover:opacity-100" />
        </button>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-dark-text leading-tight">{task.title}</p>
          {task.domain && (
            <span className="text-[10px] text-dark-subtle">{task.domain}</span>
          )}
          {task.due_date && (
            <div className="flex items-center gap-1 mt-1">
              <Clock size={9} className="text-dark-subtle" />
              <span className="text-[10px] text-dark-subtle">{formatDate(task.due_date)}</span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 shrink-0">
          <span className={cn(
            'text-[9px] px-1 py-0.5 rounded border',
            PRIORITY_COLORS[task.priority] || PRIORITY_COLORS.normal
          )}>
            {task.priority}
          </span>
          <button
            onClick={() => onDelete(task.id)}
            className="p-0.5 rounded hover:bg-red-900/30 text-dark-subtle hover:text-red-400 transition-colors"
          >
            <Trash2 size={10} />
          </button>
        </div>
      </div>
    </div>
  )
}

function NewTaskForm({ bucket, onSave, onCancel }) {
  const [title, setTitle] = useState('')
  const [priority, setPriority] = useState('normal')

  const save = () => {
    if (!title.trim()) return
    onSave({ title: title.trim(), bucket, priority, status: 'pending' })
    setTitle('')
  }

  return (
    <div className="border border-lattice-700/40 rounded-lg p-2 bg-dark-card/60">
      <input
        autoFocus
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') save()
          if (e.key === 'Escape') onCancel()
        }}
        placeholder="Task title…"
        className="w-full bg-transparent text-xs text-dark-text placeholder:text-dark-muted
                   focus:outline-none mb-2"
      />
      <div className="flex items-center gap-1.5">
        {['low', 'normal', 'high', 'urgent'].map((p) => (
          <button
            key={p}
            onClick={() => setPriority(p)}
            className={cn(
              'text-[9px] px-1.5 py-0.5 rounded border transition-colors',
              priority === p ? PRIORITY_COLORS[p] : 'border-dark-muted text-dark-subtle'
            )}
          >
            {p}
          </button>
        ))}
        <div className="flex-1" />
        <button
          onClick={onCancel}
          className="text-[10px] text-dark-subtle hover:text-dark-text px-1.5"
        >
          cancel
        </button>
        <button
          onClick={save}
          className="text-[10px] px-2 py-1 rounded bg-lattice-600 text-white"
        >
          add
        </button>
      </div>
    </div>
  )
}

function Column({ bucket, tasks, onCreate, onComplete, onDelete }) {
  const [adding, setAdding] = useState(false)
  const label = BUCKET_LABELS[bucket]
  const borderColor = BUCKET_COLORS[bucket]

  const save = async (data) => {
    await onCreate(data)
    setAdding(false)
  }

  return (
    <div className={cn(
      'flex flex-col bg-dark-surface/60 rounded-xl border-t-2 min-h-[300px]',
      'border-l border-r border-b border-dark-border',
      borderColor
    )}>
      {/* Column header */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-dark-border/50">
        <span className="text-xs font-semibold text-dark-text uppercase tracking-wide">{label}</span>
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-dark-subtle bg-dark-muted/30 px-1.5 py-0.5 rounded-full">
            {tasks.length}
          </span>
          <button
            onClick={() => setAdding(true)}
            className="p-0.5 rounded hover:bg-lattice-900/30 text-dark-subtle hover:text-lattice-400 transition-colors"
          >
            <Plus size={12} />
          </button>
        </div>
      </div>

      {/* Tasks */}
      <div className="flex-1 p-2 space-y-1.5 overflow-y-auto max-h-[500px]">
        {adding && (
          <NewTaskForm
            bucket={bucket}
            onSave={save}
            onCancel={() => setAdding(false)}
          />
        )}
        {tasks.length === 0 && !adding && (
          <p className="text-[10px] text-dark-muted text-center py-4">empty</p>
        )}
        {tasks.map((t) => (
          <TaskCard
            key={t.id}
            task={t}
            onComplete={onComplete}
            onDelete={onDelete}
          />
        ))}
      </div>
    </div>
  )
}

export default function Tasks() {
  const { fetch, byBucket, create, complete, remove, loading } = useTaskStore()
  const { addToast } = useAppStore()
  const [filter, setFilter] = useState('all')
  const buckets = byBucket()

  useEffect(() => {
    fetch()
  }, [])

  const handleCreate = async (data) => {
    try {
      await create(data)
    } catch (e) {
      addToast(e.message, 'error')
    }
  }

  const handleComplete = async (id) => {
    try {
      await complete(id)
      addToast('Task completed ✓', 'success')
    } catch (e) {
      addToast(e.message, 'error')
    }
  }

  const handleDelete = async (id) => {
    try {
      await remove(id)
    } catch (e) {
      addToast(e.message, 'error')
    }
  }

  return (
    <div className="p-4 lg:p-6 animate-fade-in">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-lg font-bold text-dark-text">Tasks</h1>
          <p className="text-xs text-dark-subtle">Kanban across all buckets</p>
        </div>
        {loading && (
          <div className="w-2 h-2 rounded-full bg-lattice-500 animate-pulse" />
        )}
      </div>

      {/* Kanban grid — scrollable horizontally on mobile */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 overflow-x-auto pb-4">
        {BUCKETS.map((b) => (
          <Column
            key={b}
            bucket={b}
            tasks={buckets[b] || []}
            onCreate={handleCreate}
            onComplete={handleComplete}
            onDelete={handleDelete}
          />
        ))}
      </div>
    </div>
  )
}
