import { cn } from '../lib/utils'

export function Card({ className, children, glow = false, ...props }) {
  return (
    <div
      className={cn(
        'rounded-xl bg-dark-card border border-dark-border p-4',
        glow && 'glow-lattice',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({ className, children }) {
  return (
    <div className={cn('flex items-center justify-between mb-3', className)}>{children}</div>
  )
}

export function CardTitle({ className, children }) {
  return (
    <h3 className={cn('text-sm font-semibold text-dark-text uppercase tracking-wider', className)}>
      {children}
    </h3>
  )
}
