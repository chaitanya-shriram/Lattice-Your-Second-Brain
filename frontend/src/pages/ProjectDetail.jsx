import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ChevronLeft, List as ListIcon, LayoutGrid, Activity, Pencil } from 'lucide-react'
import { cn } from '../lib/utils'
import { useProjectStore } from '../stores/useProjectStore'
import { useAppStore } from '../stores/useAppStore'
import ListView from '../components/projects/ListView'
import BoardView from '../components/projects/BoardView'
import StatusView from '../components/projects/StatusView'
import TaskDetailPanel from '../components/projects/TaskDetailPanel'

const TABS = [
  { id: 'list', label: 'List', icon: ListIcon },
  { id: 'board', label: 'Board', icon: LayoutGrid },
  { id: 'status', label: 'Status', icon: Activity },
]

export default function ProjectDetail() {
  const { id } = useParams()
  const { current, loading, error, fetchCurrent, updateProject, deleteProject } = useProjectStore()
  const { addToast } = useAppStore()
  const [tab, setTab] = useState('list')
  const [activeTaskId, setActiveTaskId] = useState(null)
  const [editingDesc, setEditingDesc] = useState(false)
  const [descDraft, setDescDraft] = useState('')

  useEffect(() => {
    fetchCurrent(id)
  }, [id])

  if (error && (!current || String(current.id) !== String(id))) {
    return (
      <div className="p-6 space-y-3">
        <p className="text-sm text-red-400">Couldn't load this project: {error}</p>
        <div className="flex items-center gap-3">
          <button onClick={() => fetchCurrent(id)} className="text-xs text-lattice-400 hover:text-lattice-300">
            Retry
          </button>
          <Link to="/projects" className="text-xs text-dark-subtle hover:text-dark-text">
            Back to Projects
          </Link>
        </div>
      </div>
    )
  }

  if (!current || String(current.id) !== String(id)) {
    return <div className="p-6 text-sm text-dark-subtle">{loading ? 'Loading…' : 'Project not found.'}</div>
  }

  const activeTask = current.tasks.find((t) => t.id === activeTaskId)

  const handleDelete = async () => {
    if (!confirm(`Delete project "${current.name}"? This deletes all its tasks.`)) return
    try {
      await deleteProject(current.id)
      addToast('Project deleted', 'success')
      window.location.href = '/projects'
    } catch (e) {
      addToast(e.message, 'error')
    }
  }

  return (
    <div className="p-4 lg:p-6 animate-fade-in">
      <Link to="/projects" className="inline-flex items-center gap-1 text-xs text-dark-subtle hover:text-dark-text mb-3">
        <ChevronLeft size={13} /> Projects
      </Link>

      <div className="flex items-start justify-between mb-1">
        <div className="flex items-center gap-2.5">
          <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: current.color }} />
          <h1 className="text-lg font-bold text-dark-text">{current.name}</h1>
        </div>
        {!current.is_inbox && (
          <button onClick={handleDelete} className="text-2xs text-dark-subtle hover:text-red-400">
            Delete project
          </button>
        )}
      </div>

      <div className="mb-4 max-w-2xl">
        {editingDesc ? (
          <div className="flex items-center gap-1.5">
            <input
              autoFocus
              value={descDraft}
              onChange={(e) => setDescDraft(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && e.target.blur()}
              onBlur={() => { updateProject(current.id, { description: descDraft }); setEditingDesc(false) }}
              className="input-base flex-1"
            />
          </div>
        ) : (
          <button
            onClick={() => { setDescDraft(current.description || ''); setEditingDesc(true) }}
            className="flex items-center gap-1.5 text-xs text-dark-subtle hover:text-dark-text text-left"
          >
            {current.description || 'Add a description…'}
            <Pencil size={10} className="shrink-0" />
          </button>
        )}
      </div>

      <div className="flex items-center gap-1 bg-dark-card border border-dark-border rounded-md p-0.5 w-fit mb-4">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              'flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded transition-colors',
              tab === t.id ? 'bg-lattice-600 text-white' : 'text-dark-subtle hover:text-dark-text'
            )}
          >
            <t.icon size={12} /> {t.label}
          </button>
        ))}
      </div>

      {tab === 'list' && (
        <ListView project={current} sections={current.sections} tasks={current.tasks} onOpenTask={(t) => setActiveTaskId(t.id)} />
      )}
      {tab === 'board' && (
        <BoardView project={current} sections={current.sections} tasks={current.tasks} onOpenTask={(t) => setActiveTaskId(t.id)} />
      )}
      {tab === 'status' && <StatusView project={current} updates={current.updates} />}

      {activeTask && (
        <TaskDetailPanel
          task={activeTask}
          sections={current.sections}
          allTasks={current.tasks}
          onClose={() => setActiveTaskId(null)}
        />
      )}
    </div>
  )
}
