import { useState } from 'react'
import { Trash2 } from 'lucide-react'
import { cn, formatRelative } from '../../lib/utils'
import { useProjectStore, STATUSES, STATUS_LABELS } from '../../stores/useProjectStore'
import { STATUS_BADGE } from './shared'

export default function StatusView({ project, updates }) {
  const { createStatusUpdate, deleteStatusUpdate } = useProjectStore()
  const [status, setStatus] = useState('on_track')
  const [body, setBody] = useState('')

  const submit = () => {
    if (!body.trim()) return
    createStatusUpdate(project.id, status, body.trim())
    setBody('')
  }

  return (
    <div className="max-w-2xl space-y-4">
      <div className="border border-dark-border/60 rounded-lg p-3 space-y-2.5">
        <div className="flex gap-1.5">
          {STATUSES.map((s) => (
            <button
              key={s}
              onClick={() => setStatus(s)}
              className={cn('text-2xs px-2 py-1 rounded border transition-colors', status === s ? STATUS_BADGE[s] : 'border-dark-border text-dark-subtle')}
            >
              {STATUS_LABELS[s]}
            </button>
          ))}
        </div>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="What's the update?"
          rows={3}
          className="textarea-base"
        />
        <button onClick={submit} disabled={!body.trim()} className="btn-primary">Post update</button>
      </div>

      <div className="space-y-2.5">
        {updates.length === 0 && <p className="text-xs text-dark-muted">No status updates yet.</p>}
        {updates.map((u) => (
          <div key={u.id} className="border border-dark-border/60 rounded-lg p-3 group">
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <span className={cn('text-2xs px-1.5 py-0.5 rounded border', STATUS_BADGE[u.status])}>
                  {STATUS_LABELS[u.status] || u.status}
                </span>
                <span className="text-2xs text-dark-muted">{formatRelative(u.created_at)}</span>
              </div>
              <button
                onClick={() => { if (confirm('Delete this status update?')) deleteStatusUpdate(u.id) }}
                className="opacity-0 group-hover:opacity-100 text-dark-subtle hover:text-red-400 transition-opacity"
              >
                <Trash2 size={12} />
              </button>
            </div>
            <p className="text-sm text-dark-text whitespace-pre-wrap">{u.body}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
