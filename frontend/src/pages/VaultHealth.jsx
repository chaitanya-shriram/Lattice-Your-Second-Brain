import { useState } from 'react'
import { ShieldCheck, Link2, AlertTriangle, FileQuestion, HelpCircle, RefreshCw } from 'lucide-react'
import { Card, CardHeader, CardTitle } from '../components/Card'
import { useAppStore } from '../stores/useAppStore'
import { api } from '../lib/api'

const CHECKS = [
  { key: 'broken_links', label: 'Broken links', icon: Link2, empty: 'No broken [[links]] found.' },
  { key: 'contradictions', label: 'Contradictions', icon: AlertTriangle, empty: 'No flagged contradictions.' },
  { key: 'orphaned_notes', label: 'Orphaned notes', icon: FileQuestion, empty: 'No orphaned notes.' },
  { key: 'gap_detection', label: 'Knowledge gaps', icon: HelpCircle, empty: 'No unanswered questions detected.' },
]

function ReportItem({ checkKey, item }) {
  if (checkKey === 'broken_links') {
    return <span>{item.source} → <span className="text-red-400">{item.target}</span></span>
  }
  if (checkKey === 'contradictions') {
    return <span>{item.concept} <span className="text-dark-muted">({item.folder})</span></span>
  }
  if (checkKey === 'orphaned_notes') {
    return <span className="font-mono text-2xs">{item}</span>
  }
  return <span>{item.file} — {item.count} unanswered</span>
}

export default function VaultHealth() {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const { addToast } = useAppStore()

  const run = async () => {
    setLoading(true)
    try {
      const r = await api.vaultHealthRun()
      setReport(r)
    } catch (e) {
      addToast(e.message, 'error')
    }
    setLoading(false)
  }

  return (
    <div className="p-4 lg:p-6 max-w-2xl space-y-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-dark-text flex items-center gap-2">
            <ShieldCheck size={18} className="text-lattice-400" />
            Vault Health
          </h1>
          <p className="text-xs text-dark-subtle">Broken links, orphaned notes, contradictions, knowledge gaps.</p>
        </div>
        <button
          onClick={run}
          disabled={loading}
          className="btn-primary disabled:opacity-50"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          {loading ? 'Checking…' : report ? 'Re-check' : 'Run check'}
        </button>
      </div>

      {!report ? (
        <Card className="text-center py-10">
          <p className="text-sm text-dark-subtle">Runs automatically every night at your configured maintenance time.</p>
          <p className="text-xs text-dark-muted mt-1">Click "Run check" to check right now instead of waiting.</p>
        </Card>
      ) : (
        <>
          <p className="text-xs text-dark-subtle">
            {report.total_issues === 0 ? 'No issues found.' : `${report.total_issues} issue${report.total_issues === 1 ? '' : 's'} found.`}
          </p>
          {CHECKS.map(({ key, label, icon: Icon, empty }) => {
            const check = report.checks[key]
            return (
              <Card key={key}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 normal-case tracking-normal text-dark-text text-sm font-semibold">
                    <Icon size={14} className="text-dark-subtle" />
                    {label}
                  </CardTitle>
                  <span className="text-xs font-mono text-dark-subtle">{check.count}</span>
                </CardHeader>
                {check.items.length === 0 ? (
                  <p className="text-xs text-dark-muted py-1">{empty}</p>
                ) : (
                  <div className="space-y-1">
                    {check.items.map((item, i) => (
                      <p key={i} className="text-xs text-dark-text py-0.5">
                        <ReportItem checkKey={key} item={item} />
                      </p>
                    ))}
                    {check.count > check.items.length && (
                      <p className="text-2xs text-dark-muted pt-1">+ {check.count - check.items.length} more</p>
                    )}
                  </div>
                )}
              </Card>
            )
          })}
        </>
      )}
    </div>
  )
}
