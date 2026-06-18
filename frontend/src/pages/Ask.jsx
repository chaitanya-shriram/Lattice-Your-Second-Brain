import { useState, useRef } from 'react'
import { Search, Send, Loader, BookOpen, GitBranch, Clock } from 'lucide-react'
import { api } from '../lib/api'
import { useAppStore } from '../stores/useAppStore'
import { cn } from '../lib/utils'

function SourceTag({ label }) {
  return (
    <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-lattice-900/40 text-lattice-400 border border-lattice-800/30">
      <BookOpen size={8} />
      {label}
    </span>
  )
}

function AnswerCard({ result }) {
  return (
    <div className="bg-dark-surface border border-dark-border rounded-lg overflow-hidden">
      {/* Answer */}
      <div className="p-4">
        <p className="text-xs text-dark-subtle mb-2 font-medium">Q: {result.question}</p>
        <div className="text-sm text-dark-text leading-relaxed whitespace-pre-wrap">
          {result.answer}
        </div>
      </div>

      {/* Meta */}
      <div className="px-4 py-2 border-t border-dark-border/60 bg-dark-card/40 flex flex-wrap items-center gap-3">
        <span className="text-[10px] text-dark-subtle flex items-center gap-1">
          <GitBranch size={9} />
          {result.sources_used} sources · {result.graph_expanded} graph hops
        </span>
        {result.wiki_pages_used?.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {result.wiki_pages_used.map((p) => (
              <SourceTag key={p} label={p} />
            ))}
          </div>
        )}
        {result.timestamp && (
          <span className="text-[10px] text-dark-muted ml-auto flex items-center gap-1">
            <Clock size={9} />
            {new Date(result.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>
    </div>
  )
}

const EXAMPLE_QUESTIONS = [
  'What is entropy in information theory?',
  'Summarize my notes on probability theory',
  'What tasks are most urgent right now?',
  'What have I been studying this week?',
]

export default function Ask() {
  const { addToast } = useAppStore()
  const [question, setQuestion] = useState('')
  const [useGraph, setUseGraph] = useState(true)
  const [topK, setTopK] = useState(5)
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState([])
  const inputRef = useRef(null)

  const ask = async (q = question) => {
    const text = q.trim()
    if (!text) return
    setLoading(true)
    try {
      const result = await api.ragQuery(text, topK, useGraph)
      setHistory((h) => [result, ...h])
      setQuestion('')
    } catch (e) {
      addToast(e.message, 'error')
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  return (
    <div className="p-4 space-y-4 max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Search size={18} className="text-lattice-400" />
        <h1 className="text-base font-semibold text-dark-text">Ask Your Vault</h1>
      </div>

      {/* Input */}
      <div className="bg-dark-surface border border-dark-border rounded-lg p-3 space-y-2">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            placeholder="Ask anything in your vault..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && ask()}
            className="flex-1 bg-transparent text-sm text-dark-text placeholder-dark-subtle outline-none"
            autoFocus
          />
          <button
            onClick={() => ask()}
            disabled={loading || !question.trim()}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors shrink-0',
              'bg-lattice-600 hover:bg-lattice-500 text-white',
              'disabled:opacity-40 disabled:cursor-not-allowed'
            )}
          >
            {loading ? <Loader size={12} className="animate-spin" /> : <Send size={12} />}
            Ask
          </button>
        </div>

        {/* Options */}
        <div className="flex items-center gap-4 pt-1 border-t border-dark-border/60 text-[10px] text-dark-subtle">
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={useGraph}
              onChange={(e) => setUseGraph(e.target.checked)}
              className="accent-lattice-500"
            />
            <GitBranch size={9} className="text-lattice-400" />
            Graph expand
          </label>
          <label className="flex items-center gap-1.5 cursor-pointer">
            Sources:
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="bg-dark-card border border-dark-border rounded px-1 text-[10px] text-dark-text outline-none"
            >
              <option value={3}>3</option>
              <option value={5}>5</option>
              <option value={10}>10</option>
            </select>
          </label>
        </div>
      </div>

      {/* Examples (shown when no history) */}
      {history.length === 0 && !loading && (
        <div className="space-y-1.5">
          <p className="text-[10px] text-dark-subtle uppercase tracking-wide font-medium">Try asking</p>
          <div className="grid gap-1.5 sm:grid-cols-2">
            {EXAMPLE_QUESTIONS.map((q) => (
              <button
                key={q}
                onClick={() => ask(q)}
                className="text-left text-xs text-dark-subtle bg-dark-card border border-dark-border rounded-lg px-3 py-2 hover:border-lattice-700/40 hover:text-dark-text transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="flex items-center gap-2 text-sm text-dark-subtle py-4">
          <Loader size={14} className="animate-spin text-lattice-400" />
          Searching vault and synthesizing answer...
        </div>
      )}

      {/* Answer history */}
      <div className="space-y-3">
        {history.map((result, i) => (
          <AnswerCard key={i} result={result} />
        ))}
      </div>
    </div>
  )
}
