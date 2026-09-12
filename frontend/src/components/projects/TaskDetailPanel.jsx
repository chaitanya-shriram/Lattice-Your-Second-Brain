import { useState } from 'react'
import { X, Trash2, Plus, Diamond, Check } from 'lucide-react'
import { cn } from '../../lib/utils'
import { useProjectStore } from '../../stores/useProjectStore'
import { PRIORITY_BADGE } from './shared'

const PRIORITIES = ['Low', 'Medium', 'High', 'Urgent']

export default function TaskDetailPanel({ task, sections, allTasks, onClose }) {
  const { updateTask, deleteTask, addDependency, removeDependency, createTask } = useProjectStore()
  const [name, setName] = useState(task.name)
  const [notes, setNotes] = useState(task.notes || '')
  const [newSubtask, setNewSubtask] = useState('')
  const [depPick, setDepPick] = useState('')

  const subtasks = allTasks.filter((t) => t.parent_id === task.id)
  const dependencies = (task.depends_on || []).map((id) => allTasks.find((t) => t.id === id)).filter(Boolean)
  const dependencyCandidates = allTasks.filter(
    (t) => t.id !== task.id && !t.parent_id && !(task.depends_on || []).includes(t.id)
  )

  const commitName = () => {
    if (name.trim() && name !== task.name) updateTask(task.id, { name: name.trim() })
  }
  const commitNotes = () => {
    if (notes !== task.notes) updateTask(task.id, { notes })
  }

  return (
    <div className="fixed inset-0 z-40 flex justify-end" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40" />
      <div
        className="relative w-96 max-w-full h-full bg-dark-surface border-l border-dark-border overflow-y-auto animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 h-11 border-b border-dark-border/60 sticky top-0 bg-dark-surface z-10">
          <span className="section-label">Task</span>
          <button onClick={onClose} className="text-dark-subtle hover:text-dark-text">
            <X size={16} />
          </button>
        </div>

        <div className="p-4 space-y-4">
          <textarea
            value={name}
            onChange={(e) => setName(e.target.value)}
            onBlur={commitName}
            rows={2}
            className="textarea-base text-base font-medium"
          />

          <div className="flex items-center gap-2">
            <button
              onClick={() => updateTask(task.id, { completed: !task.completed })}
              className={cn(
                'flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-md border transition-colors',
                task.completed
                  ? 'bg-lattice-600 border-lattice-600 text-white'
                  : 'border-dark-border text-dark-subtle hover:text-dark-text'
              )}
            >
              <Check size={12} /> {task.completed ? 'Completed' : 'Mark complete'}
            </button>
            <button
              onClick={() => updateTask(task.id, { is_milestone: !task.is_milestone })}
              className={cn(
                'flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-md border transition-colors',
                task.is_milestone
                  ? 'bg-lattice-900/40 border-lattice-600 text-lattice-400'
                  : 'border-dark-border text-dark-subtle hover:text-dark-text'
              )}
            >
              <Diamond size={12} /> Milestone
            </button>
          </div>

          <Field label="Due date">
            <input
              type="date"
              value={task.due_date || ''}
              onChange={(e) => updateTask(task.id, { due_date: e.target.value || null })}
              className="input-base"
            />
          </Field>

          <Field label="Priority">
            <div className="flex flex-wrap gap-1.5">
              <button
                onClick={() => updateTask(task.id, { priority: null })}
                className={cn('text-2xs px-2 py-1 rounded border', !task.priority ? 'border-lattice-500 text-lattice-400' : 'border-dark-border text-dark-subtle')}
              >
                None
              </button>
              {PRIORITIES.map((p) => (
                <button
                  key={p}
                  onClick={() => updateTask(task.id, { priority: p })}
                  className={cn('text-2xs px-2 py-1 rounded border', task.priority === p ? PRIORITY_BADGE[p] : 'border-dark-border text-dark-subtle')}
                >
                  {p}
                </button>
              ))}
            </div>
          </Field>

          <Field label="Section">
            <select
              value={task.section_id || ''}
              onChange={(e) => updateTask(task.id, { section_id: e.target.value ? Number(e.target.value) : null })}
              className="input-base"
            >
              <option value="">No section</option>
              {sections.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </Field>

          <Field label="Effort (points)">
            <input
              type="number"
              min="0"
              value={task.effort ?? ''}
              onChange={(e) => updateTask(task.id, { effort: e.target.value === '' ? null : Number(e.target.value) })}
              className="input-base"
            />
          </Field>

          <Field label="Tags">
            <input
              defaultValue={task.tags || ''}
              onBlur={(e) => e.target.value !== task.tags && updateTask(task.id, { tags: e.target.value })}
              placeholder="comma, separated"
              className="input-base"
            />
          </Field>

          <Field label="Notes">
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              onBlur={commitNotes}
              rows={4}
              className="textarea-base"
            />
          </Field>

          <Field label={`Blocked by (${dependencies.length})`}>
            <div className="space-y-1.5">
              {dependencies.map((d) => (
                <div key={d.id} className="flex items-center justify-between text-xs bg-dark-card rounded px-2 py-1.5">
                  <span className={cn('truncate', d.completed && 'line-through text-dark-muted')}>{d.name}</span>
                  <button onClick={() => removeDependency(task.id, d.id)} className="text-dark-subtle hover:text-red-400 shrink-0">
                    <X size={12} />
                  </button>
                </div>
              ))}
              {dependencyCandidates.length > 0 && (
                <div className="flex gap-1.5">
                  <select value={depPick} onChange={(e) => setDepPick(e.target.value)} className="input-base flex-1">
                    <option value="">Add dependency…</option>
                    {dependencyCandidates.map((t) => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                  <button
                    onClick={() => { if (depPick) { addDependency(task.id, Number(depPick)); setDepPick('') } }}
                    className="btn-ghost px-2"
                  >
                    <Plus size={14} />
                  </button>
                </div>
              )}
            </div>
          </Field>

          <Field label={`Subtasks (${subtasks.length})`}>
            <div className="space-y-1">
              {subtasks.map((s) => (
                <div key={s.id} className="flex items-center justify-between text-xs bg-dark-card rounded px-2 py-1.5">
                  <span className={cn('truncate', s.completed && 'line-through text-dark-muted')}>{s.name}</span>
                  <button
                    onClick={() => { if (confirm(`Delete subtask "${s.name}"?`)) deleteTask(s.id) }}
                    className="text-dark-subtle hover:text-red-400 shrink-0"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))}
              <div className="flex gap-1.5">
                <input
                  value={newSubtask}
                  onChange={(e) => setNewSubtask(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && newSubtask.trim()) {
                      createTask(task.project_id, { name: newSubtask.trim(), parent_id: task.id })
                      setNewSubtask('')
                    }
                  }}
                  placeholder="New subtask…"
                  className="input-base flex-1"
                />
              </div>
            </div>
          </Field>

          <button
            onClick={() => { if (confirm(`Delete task "${task.name}"?`)) { deleteTask(task.id); onClose() } }}
            className="flex items-center gap-1.5 text-xs text-red-400 hover:text-red-300 pt-2"
          >
            <Trash2 size={13} /> Delete task
          </button>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div className="space-y-1.5">
      <label className="section-label">{label}</label>
      {children}
    </div>
  )
}
