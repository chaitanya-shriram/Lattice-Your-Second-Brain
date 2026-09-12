import { useState } from 'react'
import { ChevronDown, ChevronRight, Plus, Trash2 } from 'lucide-react'
import { cn } from '../../lib/utils'
import { useProjectStore } from '../../stores/useProjectStore'
import TaskRow from './TaskRow'

function AddTaskInline({ onAdd }) {
  const [value, setValue] = useState('')
  const [open, setOpen] = useState(false)

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="flex items-center gap-1.5 text-xs text-dark-subtle hover:text-dark-text px-2.5 py-1.5">
        <Plus size={12} /> Add task
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
      className="input-base mx-2.5 w-[calc(100%-20px)] text-sm"
    />
  )
}

export default function ListView({ project, sections, tasks, onOpenTask }) {
  const { createTask, deleteSection, updateTask, createSection } = useProjectStore()
  const [collapsed, setCollapsed] = useState({})
  const [addingSection, setAddingSection] = useState(false)
  const [sectionName, setSectionName] = useState('')

  const topLevel = tasks.filter((t) => !t.parent_id)
  const groups = [...sections, { id: null, name: 'No section' }]

  const subtaskCount = (id) => tasks.filter((t) => t.parent_id === id).length

  return (
    <div className="space-y-3">
      {groups.map((sec) => {
        const group = topLevel.filter((t) => t.section_id === sec.id)
        if (sec.id === null && group.length === 0) return null
        const isCollapsed = collapsed[sec.id ?? 'none']
        return (
          <div key={sec.id ?? 'none'} className="border border-dark-border/60 rounded-lg overflow-hidden">
            <div className="flex items-center justify-between px-2.5 py-2 bg-dark-card/50 group">
              <button
                onClick={() => setCollapsed((c) => ({ ...c, [sec.id ?? 'none']: !c[sec.id ?? 'none'] }))}
                className="flex items-center gap-1.5 text-xs font-semibold text-dark-text"
              >
                {isCollapsed ? <ChevronRight size={13} /> : <ChevronDown size={13} />}
                {sec.name}
                <span className="text-2xs text-dark-subtle font-normal">{group.length}</span>
              </button>
              {sec.id !== null && (
                <button
                  onClick={() => { if (confirm(`Delete section "${sec.name}"? Its tasks move to no section.`)) deleteSection(sec.id) }}
                  className="opacity-0 group-hover:opacity-100 text-dark-subtle hover:text-red-400 transition-opacity"
                >
                  <Trash2 size={12} />
                </button>
              )}
            </div>
            {!isCollapsed && (
              <div className="py-1">
                {group.map((t) => (
                  <TaskRow
                    key={t.id}
                    task={t}
                    subtaskCount={subtaskCount(t.id)}
                    onClick={() => onOpenTask(t)}
                    onToggleComplete={(task) => updateTask(task.id, { completed: !task.completed })}
                  />
                ))}
                <AddTaskInline onAdd={(name) => createTask(project.id, { name, section_id: sec.id })} />
              </div>
            )}
          </div>
        )
      })}

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
        <button onClick={() => setAddingSection(true)} className="flex items-center gap-1.5 text-xs text-dark-subtle hover:text-dark-text">
          <Plus size={12} /> Add section
        </button>
      )}
    </div>
  )
}
