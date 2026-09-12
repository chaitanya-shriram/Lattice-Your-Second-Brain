import { useState } from 'react'
import { Folder, FolderOpen, RefreshCw, ArrowRight, Check } from 'lucide-react'
import { api } from '../lib/api'
import { cn } from '../lib/utils'

const DERIVED = (root) => [
  { label: 'Vault',    path: `${root}/vault` },
  { label: 'Files',   path: `${root}/vault-files` },
  { label: 'Incoming',path: `${root}/incoming` },
  { label: 'Database',path: `${root}/data/lattice.db` },
  { label: 'Logs',    path: `${root}/logs` },
]

async function waitForServer(maxMs = 20000) {
  const deadline = Date.now() + maxMs
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 800))
    try { await api.health(); return true } catch {}
  }
  return false
}

export default function Setup() {
  const [rootPath, setRootPath]   = useState('')
  const [browsing, setBrowsing]   = useState(false)
  const [saving, setSaving]       = useState(false)
  const [restarting, setRestarting] = useState(false)
  const [error, setError]         = useState('')
  const [done, setDone]           = useState(false)

  const browse = async () => {
    setBrowsing(true)
    setError('')
    try {
      const res = await api.setupBrowse('Select your Lattice root folder')
      if (res.path) setRootPath(res.path)
      else if (res.error) setError(`Folder picker: ${res.error}`)
    } catch (e) { setError(e.message) }
    setBrowsing(false)
  }

  const save = async () => {
    if (!rootPath) return
    setSaving(true)
    setError('')
    try {
      await api.setupSave(rootPath)
      setSaving(false)
      setDone(true)
      setRestarting(true)
      await api.setupRestart().catch(() => {})
      const ok = await waitForServer(20000)
      if (ok) {
        window.location.reload()
      } else {
        setRestarting(false)
        setError('Server did not restart in time — refresh the page manually.')
      }
    } catch (e) {
      setError(e.message)
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-dark-bg flex items-center justify-center p-6">
      <div className="w-full max-w-[420px] space-y-6">

        {/* Brand */}
        <div className="space-y-1">
          <div className="grid grid-cols-3 gap-[4px] w-fit">
            {Array(9).fill(0).map((_, i) => (
              <div key={i} className={`w-2 h-2 rounded-full ${[0,2,4,6,8].includes(i) ? 'bg-lattice-400' : 'bg-lattice-900'}`} />
            ))}
          </div>
          <h1 className="text-lg font-semibold text-dark-text mt-3">Set up Lattice</h1>
          <p className="text-sm text-dark-subtle">
            Choose a folder — vault, database, and logs will be created inside it.
          </p>
        </div>

        {/* Folder picker */}
        <div className="space-y-3">
          <button
            onClick={browse}
            disabled={browsing || done}
            className={cn(
              'w-full flex items-center gap-3 px-4 py-3 rounded-lg border text-left transition-colors',
              'border-dark-border/60 bg-dark-card hover:border-lattice-700/50 disabled:opacity-50'
            )}
          >
            {browsing
              ? <RefreshCw size={15} className="text-lattice-400 animate-spin shrink-0" />
              : <FolderOpen size={15} className={rootPath ? 'text-lattice-400' : 'text-dark-muted'} />
            }
            <span className={cn('text-sm font-mono truncate flex-1', rootPath ? 'text-dark-text' : 'text-dark-subtle/50')}>
              {rootPath || 'Click to browse…'}
            </span>
          </button>

          {/* Preview */}
          {rootPath && (
            <div className="rounded-lg border border-dark-border/60 bg-dark-surface/60 p-3 space-y-1 animate-fade-in">
              <p className="section-label mb-2">Will create</p>
              {DERIVED(rootPath).map(({ label, path }) => (
                <div key={label} className="flex items-center gap-2.5 text-xs">
                  <Folder size={11} className="text-dark-muted shrink-0" />
                  <span className="text-dark-subtle w-16 shrink-0">{label}</span>
                  <span className="text-dark-text font-mono text-2xs truncate">{path}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 text-xs text-red-400 bg-red-500/8 border border-red-500/20 rounded-lg px-3 py-2">
            <span className="w-1 h-1 rounded-full bg-red-400 shrink-0" />
            {error}
          </div>
        )}

        {/* Save */}
        <button
          onClick={save}
          disabled={!rootPath || saving || done}
          className={cn(
            'w-full flex items-center justify-center gap-2 py-2.5 rounded-lg font-medium text-sm transition-colors',
            'bg-lattice-600 hover:bg-lattice-500 text-white disabled:opacity-30'
          )}
        >
          {restarting ? (
            <><RefreshCw size={14} className="animate-spin" /> Restarting…</>
          ) : done ? (
            <><Check size={14} /> Saved — restarting server…</>
          ) : saving ? (
            <><RefreshCw size={14} className="animate-spin" /> Saving…</>
          ) : (
            <><ArrowRight size={14} /> Save &amp; continue</>
          )}
        </button>

      </div>
    </div>
  )
}
