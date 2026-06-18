import { useEffect, useState } from 'react'
import {
  Brain,
  CheckSquare,
  FileText,
  BookOpen,
  Zap,
  Upload,
  Send,
  TrendingUp,
} from 'lucide-react'
import { Card, CardHeader, CardTitle } from '../components/Card'
import { useTaskStore } from '../stores/useTaskStore'
import { useAppStore } from '../stores/useAppStore'
import { api } from '../lib/api'
import { formatRelative, truncate } from '../lib/utils'

function StatCard({ icon: Icon, label, value, color = 'lattice' }) {
  const colors = {
    lattice: 'text-lattice-400 bg-lattice-900/20',
    green: 'text-green-400 bg-green-900/20',
    yellow: 'text-yellow-400 bg-yellow-900/20',
    purple: 'text-purple-400 bg-purple-900/20',
  }
  return (
    <Card className="flex items-center gap-3">
      <div className={`p-2 rounded-lg ${colors[color]}`}>
        <Icon size={18} className={colors[color].split(' ')[0]} />
      </div>
      <div>
        <div className="text-xl font-bold text-dark-text">{value ?? '—'}</div>
        <div className="text-xs text-dark-subtle">{label}</div>
      </div>
    </Card>
  )
}

function BrainDumpBox() {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const { addToast, fetchDumpHistory } = useAppStore()

  const submit = async () => {
    if (!text.trim()) return
    setLoading(true)
    try {
      const result = await api.dump(text.trim(), 'web')
      setText('')
      const { tasks_created = 0, questions = 0, ideas = 0 } = result
      addToast(
        `Extracted: ${tasks_created} tasks, ${questions} questions, ${ideas} ideas`,
        'success'
      )
      fetchDumpHistory()
    } catch (e) {
      addToast(e.message, 'error')
    }
    setLoading(false)
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit()
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Brain Dump</CardTitle>
        <span className="text-xs text-dark-subtle">Ctrl+Enter to process</span>
      </CardHeader>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKey}
        placeholder="Dump everything here — tasks, ideas, questions, links, thoughts..."
        className="w-full bg-dark-surface border border-dark-border rounded-lg p-3 text-sm text-dark-text
                   placeholder:text-dark-muted resize-none focus:outline-none focus:border-lattice-600
                   transition-colors min-h-[120px] font-mono"
      />
      <div className="flex justify-end mt-2">
        <button
          onClick={submit}
          disabled={loading || !text.trim()}
          className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-sm
                     bg-lattice-600 hover:bg-lattice-500 text-white font-medium
                     disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <Send size={14} />
          {loading ? 'Processing…' : 'Process'}
        </button>
      </div>
    </Card>
  )
}

function FileDropZone() {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const { addToast } = useAppStore()

  const handleDrop = async (e) => {
    e.preventDefault()
    setDragging(false)
    const files = Array.from(e.dataTransfer?.files || [])
    if (!files.length) return
    setUploading(true)
    for (const file of files) {
      try {
        await api.fileUpload(file)
        addToast(`Queued: ${file.name}`, 'success')
      } catch (err) {
        addToast(`Failed: ${file.name}`, 'error')
      }
    }
    setUploading(false)
  }

  const handleInput = async (e) => {
    const files = Array.from(e.target.files || [])
    if (!files.length) return
    setUploading(true)
    for (const file of files) {
      try {
        await api.fileUpload(file)
        addToast(`Queued: ${file.name}`, 'success')
      } catch (err) {
        addToast(`Failed: ${file.name}`, 'error')
      }
    }
    setUploading(false)
    e.target.value = ''
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Drop Files</CardTitle>
        <span className="text-xs text-dark-subtle">PDF, EPUB, DOCX, TXT, MD</span>
      </CardHeader>
      <label
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`flex flex-col items-center justify-center gap-2 border-2 border-dashed rounded-xl
                   p-6 cursor-pointer transition-all
                   ${dragging
                     ? 'border-lattice-500 bg-lattice-900/20'
                     : 'border-dark-muted hover:border-lattice-700'
                   }`}
      >
        <Upload size={24} className={dragging ? 'text-lattice-400' : 'text-dark-subtle'} />
        <span className="text-xs text-dark-subtle text-center">
          {uploading ? 'Uploading…' : 'Drop files or click to browse'}
        </span>
        <input
          type="file"
          className="hidden"
          multiple
          accept=".pdf,.epub,.docx,.txt,.md"
          onChange={handleInput}
        />
      </label>
    </Card>
  )
}

function RecentDumps() {
  const { dumpHistory, fetchDumpHistory } = useAppStore()

  useEffect(() => {
    fetchDumpHistory()
  }, [])

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Dumps</CardTitle>
      </CardHeader>
      <div className="space-y-2 max-h-48 overflow-y-auto">
        {dumpHistory.length === 0 && (
          <p className="text-xs text-dark-muted">No dumps yet</p>
        )}
        {dumpHistory.slice(0, 8).map((d) => (
          <div key={d.id} className="flex items-start gap-2 text-xs border-b border-dark-border/40 pb-2">
            <Brain size={12} className="text-lattice-500 mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-dark-text truncate">{truncate(d.preview, 60)}</p>
              <p className="text-dark-subtle">
                {d.items_extracted} items · {formatRelative(d.created_at)}
              </p>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

function TodayTasks() {
  const { tasks, fetch } = useTaskStore()

  useEffect(() => {
    fetch({ bucket: 'daily', status: 'pending' })
  }, [])

  const pending = tasks.filter((t) => t.status !== 'done').slice(0, 8)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Today</CardTitle>
        <span className="text-xs text-dark-subtle">{pending.length} pending</span>
      </CardHeader>
      <div className="space-y-1.5">
        {pending.length === 0 && <p className="text-xs text-dark-muted">All clear 🎉</p>}
        {pending.map((t) => (
          <div key={t.id} className="flex items-center gap-2 group">
            <div className="w-1.5 h-1.5 rounded-full bg-lattice-500 shrink-0" />
            <span className="text-sm text-dark-text flex-1 truncate">{t.title}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded ${
              t.priority === 'urgent'
                ? 'bg-red-900/30 text-red-400'
                : t.priority === 'high'
                ? 'bg-yellow-900/30 text-yellow-400'
                : 'bg-dark-muted/30 text-dark-subtle'
            }`}>{t.priority}</span>
          </div>
        ))}
      </div>
    </Card>
  )
}

export default function Dashboard() {
  const { stats, fetchStats } = useTaskStore()

  useEffect(() => {
    fetchStats()
  }, [])

  return (
    <div className="p-4 lg:p-6 space-y-4 lg:space-y-6 max-w-6xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gradient">Lattice</h1>
          <p className="text-xs text-dark-subtle mt-0.5">
            {new Date().toLocaleDateString('en-US', {
              weekday: 'long',
              month: 'long',
              day: 'numeric',
            })}
          </p>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-lattice-700/20 border border-lattice-700/30">
          <Zap size={12} className="text-lattice-400" />
          <span className="text-xs text-lattice-300 font-medium">v2.0.0</span>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard icon={CheckSquare} label="Pending tasks" value={stats?.pending} color="Lattice" />
        <StatCard icon={Zap} label="Completed today" value={stats?.completed_today} color="green" />
        <StatCard icon={FileText} label="Files ingested" value={stats?.files} color="yellow" />
        <StatCard icon={BookOpen} label="Wiki pages" value={stats?.wiki_pages} color="purple" />
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <BrainDumpBox />
          <FileDropZone />
        </div>
        <div className="space-y-4">
          <TodayTasks />
          <RecentDumps />
        </div>
      </div>
    </div>
  )
}
