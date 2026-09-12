import { useEffect } from 'react'
import { useAppStore } from '../stores/useAppStore'

export default function StatusBar() {
  const { health, checkHealth } = useAppStore()

  useEffect(() => {
    checkHealth()
    const id = setInterval(checkHealth, 30_000)
    return () => clearInterval(id)
  }, [])

  const online   = health?.status === 'ok'
  const ollamaOk = health?.ollama === 'ok' || health?.ollama === true
  const model    = health?.model ? health.model.split(':')[0] : null

  return (
    <div className="flex items-center gap-3 font-mono text-[10px] text-dark-subtle select-none">
      {/* Server */}
      <span className="flex items-center gap-1.5">
        <span className={`w-1.5 h-1.5 rounded-full ${online ? 'bg-green-500' : 'bg-red-500'}`} />
        <span className={online ? 'text-green-400' : 'text-red-400'}>
          {online ? 'online' : 'offline'}
        </span>
      </span>

      <span className="text-dark-border">·</span>

      {/* LLM */}
      <span className="flex items-center gap-1.5">
        <span className={`w-1.5 h-1.5 rounded-full ${ollamaOk ? 'bg-lattice-400' : 'bg-yellow-500'}`} />
        <span className={ollamaOk ? 'text-lattice-400' : 'text-yellow-400'}>
          {ollamaOk ? (model ?? 'ollama') : 'no llm'}
        </span>
      </span>

      {health?.version && (
        <>
          <span className="text-dark-border">·</span>
          <span className="text-dark-muted">v{health.version}</span>
        </>
      )}
    </div>
  )
}
