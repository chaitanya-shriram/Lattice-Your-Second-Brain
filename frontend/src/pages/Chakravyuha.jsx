import { useEffect, useState, useMemo } from 'react'
import { Check, ChevronsDown, Loader } from 'lucide-react'
import { api } from '../lib/api'
import { useAppStore } from '../stores/useAppStore'
import { cn } from '../lib/utils'

// Chakravyuha: the 7-layer spiral formation from the Mahabharata. You don't see
// the whole battlefield at once — you break one ring, the next reveals itself.
// Same idea for parallel work: instead of one long list, show only the ring
// that matters right now. Rings are computed from existing task fields —
// no new backend state.
const RINGS = [
  { label: 'Outer Ring', sub: 'Overdue & urgent' },
  { label: 'Second Ring', sub: 'Urgent' },
  { label: 'Third Ring', sub: 'High priority, due now' },
  { label: 'Fourth Ring', sub: 'High priority' },
  { label: 'Fifth Ring', sub: 'This week' },
  { label: 'Sixth Ring', sub: 'Recurring & waiting' },
  { label: 'Core', sub: 'Someday & long-term' },
]

const PRIORITY_DOWNGRADE = { urgent: 'high', high: 'medium', medium: 'low', low: 'low' }

function ringOf(task, today) {
  const overdue = task.deadline && task.deadline < today
  const dueToday = task.deadline && task.deadline === today
  const p = task.priority
  const b = task.bucket
  if (p === 'urgent' && overdue) return 0
  if (p === 'urgent') return 1
  if (p === 'high' && (overdue || dueToday)) return 2
  if (p === 'high' && b === 'daily') return 2
  if (p === 'high') return 3
  if (p === 'medium' && (b === 'daily' || dueToday)) return 3
  if (p === 'medium' && b === 'weekly') return 4
  if (b === 'recurring' || b === 'waiting') return 5
  return 6
}

export default function Chakravyuha() {
  const { addToast } = useAppStore()
  const [tasks, setTasks] = useState(null)
  const [busyId, setBusyId] = useState(null)

  const load = () => api.tasks().then(setTasks).catch((e) => addToast(e.message, 'error'))
  useEffect(load, [])

  const active = useMemo(
    () => (tasks || []).filter((t) => t.status !== 'done' && t.status !== 'dropped'),
    [tasks]
  )

  const rings = useMemo(() => {
    const today = new Date().toISOString().slice(0, 10)
    const buckets = Array.from({ length: 7 }, () => [])
    for (const t of active) buckets[ringOf(t, today)].push(t)
    return buckets
  }, [active])

  const currentRing = rings.findIndex((r) => r.length > 0)

  const complete = async (id) => {
    setBusyId(id)
    try { await api.taskComplete(id); await load() }
    catch (e) { addToast(e.message, 'error') }
    finally { setBusyId(null) }
  }

  const pushDeeper = async (task) => {
    setBusyId(task.id)
    try { await api.taskUpdate(task.id, { priority: PRIORITY_DOWNGRADE[task.priority] || 'low' }); await load() }
    catch (e) { addToast(e.message, 'error') }
    finally { setBusyId(null) }
  }

  if (tasks === null) {
    return (
      <div className="p-8 flex items-center gap-2 text-xs text-dark-subtle">
        <Loader size={12} className="animate-spin" /> Forming the vyuha…
      </div>
    )
  }

  return (
    <div className="p-5 lg:p-8 max-w-2xl animate-fade-in">
      <div className="mb-5">
        <h1 className="text-base font-semibold text-dark-text">Chakravyuha</h1>
        <p className="text-xs text-dark-subtle mt-0.5">Break one ring at a time. Everything else stays hidden.</p>
      </div>

      {/* Ring progress dots */}
      <div className="flex items-center gap-1.5 mb-6">
        {RINGS.map((r, i) => (
          <div
            key={r.label}
            title={`${r.label} — ${rings[i].length} task(s)`}
            className={cn(
              'h-1.5 flex-1 rounded-full transition-colors',
              i === currentRing ? 'bg-lattice-500' :
              rings[i].length > 0 ? 'bg-dark-border' :
              i < currentRing || currentRing === -1 ? 'bg-lattice-900/50' : 'bg-dark-border/40'
            )}
          />
        ))}
      </div>

      {currentRing === -1 ? (
        <div className="bg-dark-card border border-lattice-800/40 rounded-lg p-6 text-center">
          <p className="text-sm text-dark-text font-medium">Vyuha cleared.</p>
          <p className="text-xs text-dark-subtle mt-1">No active tasks in any ring — pull from Brain Dump or Tasks.</p>
        </div>
      ) : (
        <>
          <div className="mb-3">
            <p className="text-sm font-medium text-dark-text">{RINGS[currentRing].label}</p>
            <p className="text-2xs text-dark-subtle">{RINGS[currentRing].sub} · {rings[currentRing].length} to break through</p>
          </div>

          <div className="space-y-2">
            {rings[currentRing].map((task) => (
              <div
                key={task.id}
                className="bg-dark-surface border border-dark-border/60 rounded-lg p-2.5 flex items-start gap-2.5"
              >
                <button
                  onClick={() => complete(task.id)}
                  disabled={busyId === task.id}
                  className="mt-0.5 w-4 h-4 rounded-full border border-dark-muted hover:border-lattice-500
                             hover:bg-lattice-900/30 flex items-center justify-center shrink-0 transition-colors"
                >
                  <Check size={10} className="text-lattice-400" />
                </button>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-dark-text leading-tight">{task.title}</p>
                  <span className="text-[10px] text-dark-subtle">{task.bucket} · {task.priority}</span>
                </div>
                <button
                  onClick={() => pushDeeper(task)}
                  disabled={busyId === task.id}
                  title="Not now — push to a deeper ring"
                  className="p-1 rounded hover:bg-white/5 text-dark-subtle hover:text-dark-text transition-colors shrink-0"
                >
                  <ChevronsDown size={12} />
                </button>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Rings still waiting, collapsed */}
      {currentRing !== -1 && (
        <div className="mt-6 space-y-1">
          {RINGS.map((r, i) => i > currentRing && rings[i].length > 0 && (
            <p key={r.label} className="text-2xs text-dark-muted">{r.label} — {rings[i].length} waiting</p>
          ))}
        </div>
      )}
    </div>
  )
}
