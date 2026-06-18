import { useEffect } from 'react'
import { Cpu, Database, Wifi, WifiOff } from 'lucide-react'
import { useAppStore } from '../stores/useAppStore'

export default function StatusBar() {
  const { health, checkHealth } = useAppStore()

  useEffect(() => {
    checkHealth()
    const id = setInterval(checkHealth, 30000)
    return () => clearInterval(id)
  }, [])

  const online = health?.status === 'ok'
  const ollamaOk = health?.ollama === true || health?.ollama === 'ok'

  return (
    <div className="flex items-center gap-3 text-xs text-dark-subtle font-mono">
      <span className="flex items-center gap-1">
        {online ? (
          <Wifi size={12} className="text-green-500" />
        ) : (
          <WifiOff size={12} className="text-red-500" />
        )}
        <span className={online ? 'text-green-400' : 'text-red-400'}>
          {online ? 'online' : 'offline'}
        </span>
      </span>

      <span className="text-dark-muted">|</span>

      <span className="flex items-center gap-1">
        <Cpu size={12} className={ollamaOk ? 'text-lattice-400' : 'text-yellow-500'} />
        <span className={ollamaOk ? 'text-lattice-300' : 'text-yellow-400'}>
          {ollamaOk ? 'ollama' : 'no-llm'}
        </span>
      </span>

      <span className="text-dark-muted">|</span>

      <span className="flex items-center gap-1">
        <Database size={12} className="text-dark-subtle" />
        <span>sqlite</span>
      </span>
    </div>
  )
}
