import { useEffect, useState } from 'react'
import { BookOpen, Search, RefreshCw, Tag, ChevronRight, X } from 'lucide-react'
import { Card } from '../components/Card'
import { useAppStore } from '../stores/useAppStore'
import { api } from '../lib/api'
import { formatRelative } from '../lib/utils'

function WikiPageModal({ pageId, onClose }) {
  const [page, setPage] = useState(null)
  const [loading, setLoading] = useState(true)
  const { addToast } = useAppStore()

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    api.wikiPage(pageId)
      .then((data) => { if (!cancelled) setPage(data) })
      .catch(() => { if (!cancelled) { addToast?.('Failed to load wiki page', 'error'); onClose() } })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [pageId])

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-dark-surface border border-dark-border rounded-xl w-full max-w-2xl max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b border-dark-border shrink-0">
          <h2 className="text-sm font-semibold text-dark-text">{page?.concept || 'Wiki page'}</h2>
          <button onClick={onClose} className="text-dark-subtle hover:text-dark-text">
            <X size={16} />
          </button>
        </div>
        <div className="p-4 overflow-y-auto">
          {loading ? (
            <p className="text-xs text-dark-subtle">Loading…</p>
          ) : page?.content ? (
            <pre className="text-xs text-dark-text whitespace-pre-wrap font-sans leading-relaxed">{page.content}</pre>
          ) : (
            <p className="text-xs text-dark-subtle">No content found — the note may have moved on disk.</p>
          )}
        </div>
      </div>
    </div>
  )
}

function WikiCard({ page, onOpen }) {
  return (
    <div
      onClick={() => onOpen(page.id)}
      className="p-3 rounded-xl border border-dark-border hover:border-lattice-700/40
                    bg-dark-surface transition-colors cursor-pointer group">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-dark-text group-hover:text-lattice-300 transition-colors">
            {page.concept}
          </p>
          <p className="text-[10px] text-dark-subtle mt-0.5">{page.folder}</p>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {page.has_contradictions ? (
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-yellow-900/20 text-yellow-500 border border-yellow-800/20">
              conflict
            </span>
          ) : null}
          <span className={`text-[9px] px-1.5 py-0.5 rounded border ${
            page.confidence === 'high'
              ? 'bg-green-900/20 text-green-400 border-green-800/20'
              : page.confidence === 'low'
              ? 'bg-red-900/20 text-red-400 border-red-800/20'
              : 'bg-dark-muted/20 text-dark-subtle border-dark-border'
          }`}>
            {page.confidence}
          </span>
        </div>
      </div>
      <div className="flex items-center justify-between mt-2">
        <span className="text-[9px] text-dark-muted">v{page.version} · {formatRelative(page.last_compiled)}</span>
        <ChevronRight size={12} className="text-dark-subtle opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    </div>
  )
}

export default function Wiki() {
  const [pages, setPages] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [openPageId, setOpenPageId] = useState(null)
  const { addToast } = useAppStore()

  const load = async () => {
    setLoading(true)
    try {
      const data = await api.wiki()
      setPages(data)
    } catch (e) {
      // Wiki API may not exist yet in phase 4
      setPages([])
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const byFolder = pages.reduce((acc, p) => {
    const folder = p.folder || 'general'
    if (!acc[folder]) acc[folder] = []
    acc[folder].push(p)
    return acc
  }, {})

  const filtered = search
    ? pages.filter(
        (p) =>
          p.concept?.toLowerCase().includes(search.toLowerCase()) ||
          p.folder?.toLowerCase().includes(search.toLowerCase())
      )
    : null

  return (
    <div className="p-4 lg:p-6 space-y-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-dark-text">Wiki</h1>
          <p className="text-xs text-dark-subtle">{pages.length} compiled pages</p>
        </div>
        <button
          onClick={load}
          className="p-2 rounded-lg border border-dark-border text-dark-subtle hover:text-dark-text transition-colors"
        >
          <RefreshCw size={14} />
        </button>
      </div>

      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-subtle" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search wiki…"
          className="w-full pl-9 pr-4 py-2 rounded-lg bg-dark-surface border border-dark-border
                     text-sm text-dark-text placeholder:text-dark-muted focus:outline-none focus:border-lattice-600"
        />
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-20 rounded-xl bg-dark-card animate-pulse" />
          ))}
        </div>
      ) : pages.length === 0 ? (
        <Card className="text-center py-12">
          <BookOpen size={32} className="text-dark-muted mx-auto mb-3" />
          <p className="text-sm text-dark-subtle">No wiki pages yet</p>
          <p className="text-xs text-dark-muted mt-1">Ingest a file and it will be compiled</p>
        </Card>
      ) : filtered ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.map((p) => <WikiCard key={p.id} page={p} onOpen={setOpenPageId} />)}
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(byFolder).map(([folder, folderPages]) => (
            <div key={folder}>
              <h2 className="text-xs font-semibold text-dark-subtle uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Tag size={10} />
                {folder}
                <span className="text-[9px] text-dark-muted">({folderPages.length})</span>
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {folderPages.map((p) => <WikiCard key={p.id} page={p} onOpen={setOpenPageId} />)}
              </div>
            </div>
          ))}
        </div>
      )}

      {openPageId && <WikiPageModal pageId={openPageId} onClose={() => setOpenPageId(null)} />}
    </div>
  )
}
