import { useEffect, useState } from 'react'
import { Send, BookOpen, Loader, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import { useAppStore } from '../stores/useAppStore'
import { cn } from '../lib/utils'

function EntryCard({ entry }) {
  return (
    <div className="bg-dark-surface border border-dark-border rounded-lg p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-dark-subtle">
          {entry.created_at ? new Date(entry.created_at).toLocaleString() : 'today'}
        </span>
        {entry.source && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-lattice-900/40 text-lattice-400 border border-lattice-800/30">
            {entry.source}
          </span>
        )}
      </div>
      <p className="text-sm text-dark-text leading-relaxed whitespace-pre-wrap">{entry.raw_text}</p>
      {entry.reflection && (
        <div className="mt-2 pt-2 border-t border-dark-border/60">
          <div className="flex items-center gap-1 mb-1">
            <Sparkles size={10} className="text-lattice-400" />
            <span className="text-[10px] text-lattice-400 font-medium">Reflection</span>
          </div>
          <p className="text-xs text-dark-subtle leading-relaxed">{entry.reflection}</p>
        </div>
      )}
    </div>
  )
}

export default function Journal() {
  const { addToast } = useAppStore()
  const [text, setText] = useState('')
  const [reflect, setReflect] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [entries, setEntries] = useState([])
  const [todaySummary, setTodaySummary] = useState(null)
  const [loadingToday, setLoadingToday] = useState(false)

  const loadEntries = async () => {
    try {
      const data = await api.journalEntries(20)
      setEntries(data)
    } catch (e) {
      // silent
    }
  }

  useEffect(() => {
    loadEntries()
  }, [])

  const submit = async () => {
    if (!text.trim()) return
    setSubmitting(true)
    try {
      await api.journalAdd(text.trim(), reflect)
      setText('')
      addToast('Journal entry saved', 'success')
      loadEntries()
    } catch (e) {
      addToast(e.message, 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const fetchTodaySummary = async () => {
    setLoadingToday(true)
    try {
      const data = await api.journalToday()
      setTodaySummary(data.summary || data.message || JSON.stringify(data))
    } catch (e) {
      addToast(e.message, 'error')
    } finally {
      setLoadingToday(false)
    }
  }

  return (
    <div className="p-4 space-y-4 max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-2">
        <BookOpen size={18} className="text-lattice-400" />
        <h1 className="text-base font-semibold text-dark-text">Journal</h1>
      </div>

      {/* Entry form */}
      <div className="bg-dark-surface border border-dark-border rounded-lg p-3 space-y-2">
        <textarea
          className={cn(
            'w-full bg-transparent text-sm text-dark-text placeholder-dark-subtle resize-none outline-none',
            'min-h-[100px] leading-relaxed'
          )}
          placeholder="What's on your mind today? Write freely..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && e.ctrlKey) submit()
          }}
        />
        <div className="flex items-center justify-between pt-1 border-t border-dark-border/60">
          <label className="flex items-center gap-1.5 text-xs text-dark-subtle cursor-pointer">
            <input
              type="checkbox"
              checked={reflect}
              onChange={(e) => setReflect(e.target.checked)}
              className="rounded border-dark-border bg-transparent accent-lattice-500"
            />
            <Sparkles size={11} className="text-lattice-400" />
            AI reflection
          </label>
          <button
            onClick={submit}
            disabled={submitting || !text.trim()}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
              'bg-lattice-600 hover:bg-lattice-500 text-white',
              'disabled:opacity-40 disabled:cursor-not-allowed'
            )}
          >
            {submitting ? <Loader size={12} className="animate-spin" /> : <Send size={12} />}
            Save
          </button>
        </div>
      </div>

      {/* Today's summary */}
      <div className="bg-dark-card border border-dark-border/60 rounded-lg p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-dark-subtle font-medium">Today's Summary</span>
          <button
            onClick={fetchTodaySummary}
            disabled={loadingToday}
            className="text-[10px] text-lattice-400 hover:text-lattice-300 flex items-center gap-1"
          >
            {loadingToday ? <Loader size={10} className="animate-spin" /> : <Sparkles size={10} />}
            Generate
          </button>
        </div>
        {todaySummary ? (
          <p className="text-sm text-dark-text leading-relaxed">{todaySummary}</p>
        ) : (
          <p className="text-xs text-dark-subtle">Click Generate to get an AI summary of today.</p>
        )}
      </div>

      {/* Entries list */}
      <div className="space-y-2">
        <p className="text-xs text-dark-subtle font-medium">Recent entries ({entries.length})</p>
        {entries.length === 0 ? (
          <p className="text-xs text-dark-muted text-center py-6">No entries yet. Start writing.</p>
        ) : (
          entries.map((e, i) => <EntryCard key={i} entry={e} />)
        )}
      </div>
    </div>
  )
}
