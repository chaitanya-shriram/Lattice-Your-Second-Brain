import { useEffect, useState } from 'react'
import { Send, Brain, Clock, Tag } from 'lucide-react'
import { Card, CardHeader, CardTitle } from '../components/Card'
import { useAppStore } from '../stores/useAppStore'
import { api } from '../lib/api'
import { formatRelative, truncate } from '../lib/utils'

export default function BrainDump() {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [lastResult, setLastResult] = useState(null)
  const { addToast, dumpHistory, fetchDumpHistory } = useAppStore()

  useEffect(() => {
    fetchDumpHistory()
  }, [])

  const submit = async () => {
    if (!text.trim()) return
    setLoading(true)
    setLastResult(null)
    try {
      const result = await api.dump(text.trim(), 'web')
      setText('')
      setLastResult(result)
      addToast('Brain dump processed', 'success')
      fetchDumpHistory()
    } catch (e) {
      addToast(e.message, 'error')
    }
    setLoading(false)
  }

  return (
    <div className="p-4 lg:p-6 max-w-4xl mx-auto space-y-4 animate-fade-in">
      <div>
        <h1 className="text-lg font-bold text-dark-text">Brain Dump</h1>
        <p className="text-xs text-dark-subtle mt-0.5">
          Raw thoughts → structured tasks, questions, ideas, references
        </p>
      </div>

      <Card>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit()
          }}
          placeholder={`Examples:\n• Read the Karpathy neural net series — important for the Q3 paper\n• ? How does attention mechanism compare to RNNs in long sequences\n• Idea: build a tool that tracks reading velocity per book\n• https://arxiv.org/abs/2301.00000 — interesting paper on RAG systems`}
          className="w-full bg-dark-surface border border-dark-border rounded-xl p-4 text-sm text-dark-text
                     placeholder:text-dark-muted resize-none focus:outline-none focus:border-lattice-600
                     transition-colors font-mono min-h-[200px]"
        />
        <div className="flex items-center justify-between mt-3">
          <span className="text-xs text-dark-subtle">Ctrl+Enter to process</span>
          <button
            onClick={submit}
            disabled={loading || !text.trim()}
            className="flex items-center gap-2 px-5 py-2 rounded-lg text-sm
                       bg-lattice-600 hover:bg-lattice-500 text-white font-medium
                       disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Send size={14} />
            {loading ? 'Processing…' : 'Process Dump'}
          </button>
        </div>
      </Card>

      {/* Result card */}
      {lastResult && (
        <Card className="border-green-800/30 bg-green-900/5">
          <CardHeader>
            <CardTitle className="text-green-400">Extracted</CardTitle>
          </CardHeader>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Tasks', val: lastResult.tasks_created },
              { label: 'Questions', val: lastResult.questions },
              { label: 'Ideas', val: lastResult.ideas },
              { label: 'References', val: lastResult.references },
            ].map(({ label, val }) => (
              <div key={label} className="text-center">
                <div className="text-2xl font-bold text-green-300">{val ?? 0}</div>
                <div className="text-xs text-dark-subtle">{label}</div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* History */}
      <Card>
        <CardHeader>
          <CardTitle>History</CardTitle>
          <span className="text-xs text-dark-subtle">{dumpHistory.length} dumps</span>
        </CardHeader>
        <div className="space-y-2 max-h-80 overflow-y-auto">
          {dumpHistory.length === 0 && (
            <p className="text-xs text-dark-muted py-4 text-center">No dumps yet</p>
          )}
          {dumpHistory.map((d) => (
            <div
              key={d.id}
              className="p-2.5 rounded-lg border border-dark-border/40 hover:border-dark-border
                         transition-colors group"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm text-dark-text leading-snug">{truncate(d.preview, 80)}</p>
                <div className="flex items-center gap-1 text-dark-subtle shrink-0">
                  <Brain size={11} />
                  <span className="text-[10px]">{d.items_extracted}</span>
                </div>
              </div>
              <div className="flex items-center gap-2 mt-1.5">
                <Clock size={10} className="text-dark-muted" />
                <span className="text-[10px] text-dark-muted">{formatRelative(d.created_at)}</span>
                <span className="text-[10px] text-dark-muted">·</span>
                <span className="text-[10px] text-dark-subtle">{d.source}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
