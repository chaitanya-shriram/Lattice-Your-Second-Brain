import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, LayoutGrid, List as ListIcon } from 'lucide-react'
import { cn, formatRelative } from '../lib/utils'
import { useProjectStore } from '../stores/useProjectStore'
import { useAppStore } from '../stores/useAppStore'
import { STATUS_BADGE } from '../components/projects/shared'
import { STATUS_LABELS } from '../stores/useProjectStore'
import TaskRow from '../components/projects/TaskRow'

function NewProjectForm({ onCreate }) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="flex items-center gap-1.5 text-xs text-dark-subtle hover:text-dark-text px-2.5 py-1.5 border border-dashed border-dark-border rounded-lg">
        <Plus size={13} /> New project
      </button>
    )
  }

  const submit = async () => {
    if (!name.trim() || busy) return
    setBusy(true)
    await onCreate(name.trim())
    setBusy(false)
    setName('')
    setOpen(false)
  }

  return (
    <div className="flex items-center gap-1.5">
      <input
        autoFocus
        value={name}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') submit(); if (e.key === 'Escape') setOpen(false) }}
        placeholder="Project name…"
        className="input-base w-56"
        disabled={busy}
      />
      <button onClick={submit} disabled={busy} className="btn-primary">{busy ? '…' : 'Create'}</button>
    </div>
  )
}

function ProjectColumn({ project }) {
  const total = project.total_count || 0
  const done = project.done_count || 0
  const pct = total > 0 ? Math.round((done / total) * 100) : 0

  return (
    <Link
      to={`/projects/${project.id}`}
      className="flex flex-col w-72 shrink-0 bg-dark-surface/60 rounded-xl border border-dark-border hover:border-dark-muted transition-colors"
    >
      <div className="p-3 border-b border-dark-border/50">
        <div className="flex items-center gap-2 mb-1">
          <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: project.color }} />
          <span className="text-sm font-semibold text-dark-text truncate">{project.name}</span>
        </div>
        {project.description && <p className="text-2xs text-dark-subtle line-clamp-2">{project.description}</p>}
      </div>

      <div className="px-3 pt-2.5 space-y-1.5">
        <div className="flex items-center justify-between text-2xs text-dark-subtle">
          <span>{done}/{total} done</span>
          {project.latest_update && (
            <span className={cn('px-1.5 py-0.5 rounded border', STATUS_BADGE[project.latest_update.status])}>
              {STATUS_LABELS[project.latest_update.status]}
            </span>
          )}
        </div>
        <div className="h-1.5 rounded-full bg-dark-muted/30 overflow-hidden">
          <div className="h-full bg-lattice-500" style={{ width: `${pct}%` }} />
        </div>
      </div>

      <div className="flex-1 p-2 space-y-0.5">
        {project.pending_tasks.length === 0 && (
          <p className="text-2xs text-dark-muted text-center py-3">Nothing pending</p>
        )}
        {project.pending_tasks.map((t) => (
          <div key={t.id} className="text-xs text-dark-subtle truncate px-1.5 py-1">{t.name}</div>
        ))}
      </div>

      {project.latest_update && (
        <div className="px-3 py-2 border-t border-dark-border/40 text-2xs text-dark-muted truncate">
          {formatRelative(project.latest_update.created_at)} — {project.latest_update.body}
        </div>
      )}
    </Link>
  )
}

export default function Projects() {
  const { home, myTasks, error, fetchHome, fetchMyTasks, createProject, updateTask } = useProjectStore()
  const { addToast } = useAppStore()
  const [tab, setTab] = useState('board')

  useEffect(() => {
    fetchHome()
    fetchMyTasks()
  }, [])

  const handleCreate = async (name) => {
    try {
      const project = await createProject(name)
      addToast(`Project "${project.name}" created`, 'success')
      fetchHome()
    } catch (e) {
      addToast(e.message, 'error')
    }
  }

  return (
    <div className="p-4 lg:p-6 animate-fade-in">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-lg font-bold text-dark-text">Projects</h1>
          <p className="text-xs text-dark-subtle">Multi-project task manager</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center bg-dark-card border border-dark-border rounded-md p-0.5">
            <button
              onClick={() => setTab('board')}
              className={cn('p-1.5 rounded', tab === 'board' ? 'bg-lattice-600 text-white' : 'text-dark-subtle')}
            >
              <LayoutGrid size={13} />
            </button>
            <button
              onClick={() => setTab('list')}
              className={cn('p-1.5 rounded', tab === 'list' ? 'bg-lattice-600 text-white' : 'text-dark-subtle')}
            >
              <ListIcon size={13} />
            </button>
          </div>
          <NewProjectForm onCreate={handleCreate} />
        </div>
      </div>

      {error && (
        <p className="text-xs text-red-400 mb-3">Couldn't load projects: {error}</p>
      )}

      {tab === 'board' ? (
        <div className="flex gap-3 overflow-x-auto pb-4">
          {home.map((p) => <ProjectColumn key={p.id} project={p} />)}
        </div>
      ) : (
        <div className="max-w-3xl border border-dark-border/60 rounded-lg divide-y divide-dark-border/40">
          {myTasks.length === 0 && <p className="text-xs text-dark-muted p-4">No pending tasks.</p>}
          {myTasks.map((t) => (
            <Link key={t.id} to={`/projects/${t.project_id}`}>
              <TaskRow
                task={t}
                projectColor={t.project_color}
                projectName={t.project_name}
                onToggleComplete={(task) => updateTask(task.id, { completed: !task.completed })}
              />
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
