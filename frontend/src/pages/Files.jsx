import { useEffect, useState } from 'react'
import { FileText, Upload, Search, BookOpen, FileCode, File } from 'lucide-react'
import { Card } from '../components/Card'
import { useAppStore } from '../stores/useAppStore'
import { api } from '../lib/api'
import { formatRelative } from '../lib/utils'
import { cn } from '../lib/utils'
import { useFileUpload } from '../lib/hooks'

const TYPE_ICONS = {
  book: BookOpen,
  textbook: BookOpen,
  paper: FileCode,
  lecture: FileCode,
  notes: FileText,
}

function FileCard({ file }) {
  const Icon = TYPE_ICONS[file.file_type] || File
  const topics = (() => {
    try { return JSON.parse(file.topics || '[]') }
    catch { return [] }
  })()

  return (
    <div className="p-3 rounded-xl border border-dark-border hover:border-lattice-700/40
                    bg-dark-surface transition-colors group">
      <div className="flex items-start gap-2.5">
        <div className="p-1.5 rounded-lg bg-lattice-900/30 shrink-0">
          <Icon size={14} className="text-lattice-400" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-dark-text truncate">{file.canonical_filename}</p>
          <p className="text-xs text-dark-subtle mt-0.5">{file.file_type || 'unknown'}</p>
        </div>
        {file.compiled ? (
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-green-900/30 text-green-400 border border-green-800/30 shrink-0">
            compiled
          </span>
        ) : (
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-yellow-900/20 text-yellow-500 border border-yellow-800/20 shrink-0">
            pending
          </span>
        )}
      </div>
      <div className="flex flex-wrap gap-1 mt-2">
        {topics.slice(0, 3).map((t) => (
          <span key={t} className="text-[9px] px-1.5 py-0.5 rounded-full bg-dark-muted/30 text-dark-subtle border border-dark-border">
            {t}
          </span>
        ))}
      </div>
      <div className="flex items-center justify-between mt-2">
        <span className="text-[10px] text-dark-muted">{formatRelative(file.ingested_at)}</span>
        {file.year && <span className="text-[10px] text-dark-subtle">{file.year}</span>}
      </div>
    </div>
  )
}

export default function Files() {
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [dragging, setDragging] = useState(false)
  const { addToast } = useAppStore()

  const load = async () => {
    setLoading(true)
    try {
      const data = await api.files()
      setFiles(data)
    } catch (e) {
      addToast(e.message, 'error')
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const { uploading, upload: handleUpload } = useFileUpload(() => setTimeout(load, 1000))

  const filtered = files.filter((f) =>
    !search ||
    f.canonical_filename?.toLowerCase().includes(search.toLowerCase()) ||
    f.file_type?.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="p-4 lg:p-6 space-y-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-dark-text">Files</h1>
          <p className="text-xs text-dark-subtle">{files.length} ingested</p>
        </div>
      </div>

      {/* Upload zone */}
      <label
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); handleUpload(e.dataTransfer.files) }}
        className={cn(
          'flex items-center justify-center gap-3 border-2 border-dashed rounded-xl p-5 cursor-pointer transition-all',
          dragging ? 'border-lattice-500 bg-lattice-900/20' : 'border-dark-muted hover:border-lattice-700'
        )}
      >
        <Upload size={20} className={dragging ? 'text-lattice-400' : 'text-dark-subtle'} />
        <span className="text-sm text-dark-subtle">
          {uploading ? 'Uploading…' : 'Drop files or click · PDF, EPUB, DOCX, TXT, MD'}
        </span>
        <input
          type="file"
          className="hidden"
          multiple
          accept=".pdf,.epub,.docx,.txt,.md"
          onChange={(e) => handleUpload(e.target.files)}
        />
      </label>

      {/* Search */}
      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-subtle" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search files…"
          className="w-full pl-9 pr-4 py-2 rounded-lg bg-dark-surface border border-dark-border
                     text-sm text-dark-text placeholder:text-dark-muted focus:outline-none focus:border-lattice-600"
        />
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-24 rounded-xl bg-dark-card animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <Card className="text-center py-12">
          <FileText size={32} className="text-dark-muted mx-auto mb-3" />
          <p className="text-sm text-dark-subtle">
            {search ? 'No files match' : 'No files ingested yet'}
          </p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.map((f) => (
            <FileCard key={f.id} file={f} />
          ))}
        </div>
      )}
    </div>
  )
}
