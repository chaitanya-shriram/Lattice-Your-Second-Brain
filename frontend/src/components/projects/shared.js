export const PRIORITY_DOT = {
  Low: 'bg-gray-400',
  Medium: 'bg-blue-400',
  High: 'bg-orange-400',
  Urgent: 'bg-red-500',
}

export const PRIORITY_BADGE = {
  Low: 'bg-dark-muted/20 text-dark-subtle border-dark-border',
  Medium: 'bg-blue-900/30 text-blue-400 border-blue-800/30',
  High: 'bg-orange-900/30 text-orange-400 border-orange-800/30',
  Urgent: 'bg-red-900/30 text-red-400 border-red-800/30',
}

export const STATUS_BADGE = {
  on_track: 'bg-emerald-900/30 text-emerald-400 border-emerald-800/30',
  at_risk: 'bg-amber-900/30 text-amber-400 border-amber-800/30',
  off_track: 'bg-red-900/30 text-red-400 border-red-800/30',
  complete: 'bg-blue-900/30 text-blue-400 border-blue-800/30',
}

export function isOverdue(dueDate, completed) {
  if (!dueDate || completed) return false
  return new Date(dueDate) < new Date(new Date().toDateString())
}

export function tagList(tags) {
  return (tags || '').split(',').map((t) => t.trim()).filter(Boolean)
}
