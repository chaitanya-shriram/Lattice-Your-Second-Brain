import { useAppStore } from '../stores/useAppStore'
import { cn } from '../lib/utils'
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react'

const ICONS = {
  success: <CheckCircle size={14} className="text-green-400" />,
  error: <AlertCircle size={14} className="text-red-400" />,
  info: <Info size={14} className="text-lattice-400" />,
}

export default function ToastContainer() {
  const { toasts } = useAppStore()

  if (!toasts.length) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={cn(
            'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm',
            'bg-dark-card border border-dark-border shadow-xl animate-fade-in',
            'max-w-xs'
          )}
        >
          {ICONS[t.type] || ICONS.info}
          <span className="text-dark-text">{t.message}</span>
        </div>
      ))}
    </div>
  )
}
