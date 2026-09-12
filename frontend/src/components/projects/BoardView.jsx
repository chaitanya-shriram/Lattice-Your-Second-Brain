import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useProjectStore } from '../../stores/useProjectStore'
import TaskRow from './TaskRow'

function AddTaskInline({ onAdd }) {
  const [value, setValue] = useState('')
  const [open, setOpen] = useState(false)

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="flex items-center gap-1.5 text-2xs text-dark-subtle hover:text-dark-text px-2 py-1.5">
        <Plus size={11} /> Add task
      </button>
    )
  }

  const submit = () => {
    if (value.trim()) onAdd(value.trim())
    setValue('')
    setOpen(false)
  }

  return (
    <input
      autoFocus
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onBlur={submit}
      onKeyDown={(e) => {
        if (e.key === 'Enter') submit()
        if (e.key === 'Escape') { setValue(''); setOpen(false) }
      }}
      placeholder="Task name…"
      className="input-base mx-2 w-[calc(100%-16px)] text-sm"
    />
  )
}

export default function BoardView({ project, sections, tasks, onOpenTask }) {
  const { createTask, updateTask, createSection } = useProjectStore()
  const [addingSection, setAddingSection] = useState(false)
  const [sectionName, setSectionName] = useState('')

  const topLevel = tasks.filter((t) => !t.parent_id)
  const columns = sections.length > 0 ? sections : [{ id: null, name: 'Tasks' }]
  const subtaskCount = (id) => tasks.filter((t) => t.parent_id === id).length

  return (
    <div className="flex gap-3 overflow-x-auto pb-4">
      {columns.map((sec) => {
        const group = topLevel.filter((t) => t.section_id === sec.id)
        const done = group.filter((t) => t.completed).length
        return (
          <div key={sec.id ?? 'none'} className="flex flex-col w-64 shrink-0 bg-dark-surface/60 rounded-xl border border-dark-border min-h-[200px]">
            <div className="flex items-center justify-between px-3 py-2.5 border-b border-dark-border/50">
              <span className="text-xs font-semibold text-dark-text truncate">{sec.name}</span>
              <span className="text-2xs text-dark-subtle bg-dark-muted/30 px-1.5 py-0.5 rounded-full shrink-0">{done}/{group.length}</span>
            </div>
            <div className="flex-1 p-1.5 space-y-1">
              {group.map((t) => (
                <div key={t.id} className="bg-dark-card border border-dark-border/60 rounded-lg">
                  <TaskRow
                    task={t}
                    subtaskCount={subtaskCount(t.id)}
                    onClick={() => onOpenTask(t)}
                    onToggleComplete={(task) => updateTask(task.id, { completed: !task.completed })}
                  />
                </div>
              ))}
              <AddTaskInline onAdd={(name) => createTask(project.id, { name, section_id: sec.id })} />
            </div>
          </div>
        )
      })}

      <div className="w-64 shrink-0">
        {addingSection ? (
          <input
            autoFocus
            value={sectionName}
            onChange={(e) => setSectionName(e.target.value)}
            onBlur={() => {
              if (sectionName.trim()) createSection(project.id, sectionName.trim())
              setSectionName('')
              setAddingSection(false)
            }}
            onKeyDown={(e) => e.key === 'Enter' && e.target.blur()}
            placeholder="Section name…"
            className="input-base"
          />
        ) : (
          <button onClick={() => setAddingSection(true)} className="flex items-center gap-1.5 text-xs text-dark-subtle hover:text-dark-text px-2 py-2">
            <Plus size={13} /> Add section
          </button>
        )}
      </div>
    </div>
  )
}
