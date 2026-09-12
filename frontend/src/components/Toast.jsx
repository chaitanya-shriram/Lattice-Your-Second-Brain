import { useAppStore } from '../stores/useAppStore'
import { cn } from '../lib/utils'
import { CheckCircle2, XCircle, Info, X } from 'lucide-react'
import { useEffect } from 'react'

const META = {
  success: { icon: CheckCircle2, color: 'text-green-400',  border: 'border-green-500/20',  bg: 'bg-green-500/8' },
  error:   { icon: XCircle,      color: 'text-red-400',    border: 'border-red-500/20',    bg: 'bg-red-500/8'   },
  info:    { icon: Info,         color: 'text-lattice-400',border: 'border-lattice-500/20',bg: 'bg-lattice-500/8'},
}

function Toast({ t }) {
  const { removeToast } = useAppStore()
  const m = META[t.type] ?? META.info
  const Icon = m.icon

  useEffect(() => {
    const id = setTimeout(() => removeToast(t.id), 4000)
    return () => clearTimeout(id)
  }, [t.id])

  return (
    <div
      className={cn(
        'flex items-start gap-2.5 px-3.5 py-2.5 rounded-lg text-sm animate-slide-up',
        'border shadow-lg shadow-black/40 min-w-[240px] max-w-[340px]',
        'bg-dark-card',
        m.border
      )}
    >
      <Icon size={14} className={cn('mt-0.5 shrink-0', m.color)} />
      <span className="text-dark-text flex-1 leading-snug text-[13px]">{t.message}</span>
      <button
        onClick={() => removeToast(t.id)}
        className="text-dark-muted hover:text-dark-subtle transition-colors mt-0.5 shrink-0"
      >
        <X size={12} />
      </button>
    </div>
  )
}

export default function ToastContainer() {
  const { toasts } = useAppStore()
  if (!toasts.length) return null

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2">
      {toasts.map((t) => <Toast key={t.id} t={t} />)}
    </div>
  )
}
