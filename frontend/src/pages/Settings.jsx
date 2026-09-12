import { useEffect, useState } from 'react'
import { Settings as SettingsIcon, Server, FolderOpen, Smartphone, Download, AlertTriangle } from 'lucide-react'
import { Card, CardHeader, CardTitle } from '../components/Card'
import { useAppStore } from '../stores/useAppStore'
import { api } from '../lib/api'

function Row({ label, value, status }) {
  const statusColor =
    status === 'ok' ? 'text-green-400' :
    status === 'error' ? 'text-red-400' :
    'text-dark-subtle'

  return (
    <div className="flex items-center justify-between py-2 border-b border-dark-border/40 text-sm">
      <span className="text-dark-subtle">{label}</span>
      <span className={`font-mono text-xs ${statusColor}`}>{value}</span>
    </div>
  )
}

export default function Settings() {
  const { health, checkHealth } = useAppStore()
  const [fullHealth, setFullHealth] = useState(null)
  const [backing, setBacking] = useState(false)
  const [backupMsg, setBackupMsg] = useState('')

  useEffect(() => {
    checkHealth()
    api.health().then(setFullHealth).catch(() => {})
  }, [])

  const h = fullHealth || health

  const pathRows = [
    ['Vault', h?.vault_path],
    ['Incoming', h?.incoming_path],
    ['Files', h?.vault_files_path],
    ['Database', h?.db_path],
    ['Logs', h?.logs_path],
  ]

  async function handleBackup() {
    setBacking(true)
    setBackupMsg('')
    try {
      const res = await api.backupCreate()
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const blob = await res.blob()
      const cd = res.headers.get('Content-Disposition') || ''
      const match = cd.match(/filename="?([^"]+)"?/)
      const name = match ? match[1] : 'lattice_backup.zip'
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = name
      a.click()
      URL.revokeObjectURL(a.href)
      setBackupMsg('Backup downloaded.')
    } catch (e) {
      setBackupMsg(`Backup failed: ${e.message}`)
    } finally {
      setBacking(false)
    }
  }

  const ollamaOk = h?.ollama === 'ok'
  const lanUrl = h?.lan_url

  return (
    <div className="p-4 lg:p-6 max-w-2xl space-y-4 animate-fade-in">
      <div>
        <h1 className="text-lg font-bold text-dark-text">Settings</h1>
        <p className="text-xs text-dark-subtle">System status and configuration</p>
      </div>

      {/* Ollama warning */}
      {h && !ollamaOk && (
        <div className="flex items-start gap-2 rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-3 py-2 text-xs text-yellow-300">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          <div>
            <span className="font-semibold">Ollama not detected.</span>{' '}
            AI features will fail. Start Ollama, then{' '}
            <button className="underline" onClick={() => api.health().then(setFullHealth)}>
              re-check
            </button>.
          </div>
        </div>
      )}

      {/* System health */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server size={14} />
            System Health
          </CardTitle>
        </CardHeader>
        <Row
          label="API Server"
          value={h?.status === 'ok' ? 'running' : h?.status ?? 'offline'}
          status={h?.status === 'ok' ? 'ok' : 'error'}
        />
        <Row
          label="Ollama LLM"
          value={h?.ollama ?? 'unknown'}
          status={ollamaOk ? 'ok' : 'error'}
        />
        <Row
          label="Database"
          value={h?.db ?? 'unknown'}
          status={h?.db === 'ok' ? 'ok' : 'error'}
        />
        <Row label="LLM Backend" value={h?.llm_backend ?? '—'} />
        <Row label="Model" value={h?.model ?? '—'} />
        <Row label="Version" value={h?.version ? `Lattice v${h.version}` : 'Lattice v2.0.0'} />
      </Card>

      {/* Paths */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FolderOpen size={14} />
            Paths
          </CardTitle>
        </CardHeader>
        <div className="space-y-0">
          {pathRows.map(([label, path]) => (
            <div key={label} className="flex items-start justify-between py-2 border-b border-dark-border/40 text-xs gap-4">
              <span className="text-dark-subtle shrink-0">{label}</span>
              <span className="text-dark-text font-mono bg-dark-surface px-2 py-0.5 rounded text-right break-all">
                {path ?? '—'}
              </span>
            </div>
          ))}
        </div>
      </Card>

      {/* LAN access / QR */}
      {lanUrl && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Smartphone size={14} />
              Mobile Access (same network)
            </CardTitle>
          </CardHeader>
          <div className="flex items-center gap-4 py-2">
            <img
              src={api.qrUrl()}
              alt="LAN QR code"
              className="w-28 h-28 rounded"
              onError={(e) => { e.target.style.display = 'none' }}
            />
            <div className="space-y-1">
              <p className="text-xs text-dark-subtle">Scan with your phone to open Lattice on mobile.</p>
              <p className="font-mono text-xs text-lattice-400 break-all">{lanUrl}</p>
            </div>
          </div>
        </Card>
      )}

      {/* Backup */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Download size={14} />
            Backup
          </CardTitle>
        </CardHeader>
        <div className="py-2 space-y-2">
          <p className="text-xs text-dark-subtle">
            Downloads a ZIP containing your entire vault and database.
          </p>
          <button
            onClick={handleBackup}
            disabled={backing}
            className="px-3 py-1.5 rounded bg-lattice-500/20 hover:bg-lattice-500/30 text-lattice-400 text-xs font-medium disabled:opacity-50 transition-colors cursor-pointer"
          >
            {backing ? 'Preparing backup…' : 'Download backup'}
          </button>
          {backupMsg && (
            <p className={`text-xs ${backupMsg.startsWith('Backup failed') ? 'text-red-400' : 'text-green-400'}`}>
              {backupMsg}
            </p>
          )}
        </div>
      </Card>
    </div>
  )
}
