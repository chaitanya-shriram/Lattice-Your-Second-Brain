import { useEffect, useState } from 'react'
import { Settings as SettingsIcon, Server, Database, FolderOpen } from 'lucide-react'
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

  useEffect(() => {
    checkHealth()
  }, [])

  return (
    <div className="p-4 lg:p-6 max-w-2xl space-y-4 animate-fade-in">
      <div>
        <h1 className="text-lg font-bold text-dark-text">Settings</h1>
        <p className="text-xs text-dark-subtle">System status and configuration</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server size={14} />
            System Health
          </CardTitle>
        </CardHeader>
        <Row
          label="API Server"
          value={health?.status === 'ok' ? 'running' : 'offline'}
          status={health?.status === 'ok' ? 'ok' : 'error'}
        />
        <Row
          label="Ollama LLM"
          value={health?.ollama ? 'connected' : 'not available'}
          status={health?.ollama ? 'ok' : 'error'}
        />
        <Row
          label="Database"
          value={health?.db || 'sqlite'}
          status="ok"
        />
        <Row label="Version" value="Lattice v2.0.0" />
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FolderOpen size={14} />
            Paths
          </CardTitle>
        </CardHeader>
        <div className="space-y-2 text-xs font-mono">
          {[
            ['Vault', 'vault/'],
            ['Incoming', 'incoming/'],
            ['Files', 'vault-files/'],
            ['Database', 'lattice/data/lattice.db'],
            ['Logs', 'logs/'],
          ].map(([label, path]) => (
            <div key={label} className="flex items-center justify-between py-1.5 border-b border-dark-border/40">
              <span className="text-dark-subtle">{label}</span>
              <span className="text-dark-text bg-dark-surface px-2 py-0.5 rounded">{path}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>LLM Config</CardTitle>
        </CardHeader>
        <Row label="Backend" value="Ollama (local)" status="ok" />
        <Row label="Primary model" value="qwen2.5:14b" />
        <Row label="Fallback model" value="qwen2.5:7b" />
        <Row label="Embed model" value="nomic-embed-text" />
      </Card>
    </div>
  )
}
