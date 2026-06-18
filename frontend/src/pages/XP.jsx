import { useEffect, useState } from 'react'
import { Zap, Trophy, TrendingUp, Star, Clock, RefreshCw } from 'lucide-react'
import { api } from '../lib/api'
import { useAppStore } from '../stores/useAppStore'
import { cn } from '../lib/utils'

function StatCard({ label, value, sub, icon: Icon, color = 'text-lattice-400' }) {
  return (
    <div className="bg-dark-surface border border-dark-border rounded-lg p-3 flex items-center gap-3">
      <div className={cn('p-2 rounded-lg bg-dark-card', color.replace('text-', 'text-'))}>
        <Icon size={16} className={color} />
      </div>
      <div>
        <p className="text-lg font-bold text-dark-text leading-none">{value ?? '—'}</p>
        <p className="text-[10px] text-dark-subtle mt-0.5">{label}</p>
        {sub && <p className="text-[10px] text-dark-muted">{sub}</p>}
      </div>
    </div>
  )
}

function XPBar({ current, required, level }) {
  const pct = required > 0 ? Math.min(100, Math.round((current / required) * 100)) : 0
  return (
    <div className="bg-dark-surface border border-dark-border rounded-lg p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-lattice-700/40 border border-lattice-600/40 flex items-center justify-center">
            <span className="text-xs font-bold text-lattice-300">{level}</span>
          </div>
          <div>
            <p className="text-sm font-semibold text-dark-text">Level {level}</p>
            <p className="text-[10px] text-dark-subtle">{current} / {required} XP to next level</p>
          </div>
        </div>
        <span className="text-xs text-lattice-400 font-medium">{pct}%</span>
      </div>
      <div className="w-full h-1.5 bg-dark-card rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-lattice-600 to-lattice-400 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

function AchievementBadge({ badge }) {
  return (
    <div className={cn(
      'bg-dark-card border rounded-lg p-2.5 flex items-start gap-2',
      badge.unlocked_at ? 'border-yellow-700/40' : 'border-dark-border opacity-40'
    )}>
      <div className={cn(
        'p-1.5 rounded-md',
        badge.unlocked_at ? 'bg-yellow-900/40' : 'bg-dark-border/20'
      )}>
        <Trophy size={14} className={badge.unlocked_at ? 'text-yellow-400' : 'text-dark-muted'} />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-dark-text truncate">{badge.badge_name || badge.name}</p>
        {badge.xp_awarded != null && (
          <p className="text-[10px] text-lattice-400">+{badge.xp_awarded} XP</p>
        )}
        {badge.unlocked_at && (
          <p className="text-[10px] text-dark-subtle">
            {new Date(badge.unlocked_at).toLocaleDateString()}
          </p>
        )}
      </div>
    </div>
  )
}

function XPLogRow({ entry }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-dark-border/40 last:border-0">
      <div className="flex items-center gap-2">
        <Zap size={11} className="text-lattice-400 shrink-0" />
        <span className="text-xs text-dark-text">{entry.description || entry.action_type}</span>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <span className="text-xs font-medium text-lattice-400">+{entry.xp_earned ?? entry.xp_amount ?? '?'}</span>
        {entry.earned_at && (
          <span className="text-[10px] text-dark-subtle">
            {new Date(entry.earned_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>
    </div>
  )
}

export default function XP() {
  const { addToast } = useAppStore()
  const [stats, setStats] = useState(null)
  const [log, setLog] = useState([])
  const [achievements, setAchievements] = useState([])
  const [weeklyReport, setWeeklyReport] = useState(null)
  const [loadingReport, setLoadingReport] = useState(false)

  const loadAll = async () => {
    try {
      const [s, l, a] = await Promise.all([
        api.xpStats(),
        api.xpLog(20),
        api.xpAchievements(),
      ])
      setStats(s)
      setLog(Array.isArray(l) ? l : [])
      setAchievements(Array.isArray(a) ? a : [])
    } catch (e) {
      // silent
    }
  }

  const fetchWeeklyReport = async () => {
    setLoadingReport(true)
    try {
      const data = await api.xpWeeklyReport()
      setWeeklyReport(data)
    } catch (e) {
      addToast(e.message, 'error')
    } finally {
      setLoadingReport(false)
    }
  }

  useEffect(() => {
    loadAll()
  }, [])

  const level = stats?.level ?? 1
  const totalXP = stats?.total_xp ?? 0
  const currentLevelXP = stats?.current_level_xp ?? totalXP
  const nextLevelXP = stats?.next_level_xp ?? 100
  const streak = stats?.streak_days ?? 0

  return (
    <div className="p-4 space-y-4 max-w-2xl mx-auto">
      <div className="flex items-center gap-2">
        <Zap size={18} className="text-lattice-400" />
        <h1 className="text-base font-semibold text-dark-text">XP Dashboard</h1>
      </div>

      {/* Level bar */}
      <XPBar current={currentLevelXP} required={nextLevelXP} level={level} />

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <StatCard label="Total XP" value={totalXP} icon={Zap} color="text-lattice-400" />
        <StatCard label="Level" value={level} icon={Star} color="text-yellow-400" />
        <StatCard label="Streak" value={`${streak}d`} icon={TrendingUp} color="text-green-400" />
        <StatCard
          label="Achievements"
          value={achievements.filter((a) => a.unlocked_at).length}
          sub={`/ ${achievements.length}`}
          icon={Trophy}
          color="text-purple-400"
        />
      </div>

      {/* Weekly report */}
      <div className="bg-dark-surface border border-dark-border rounded-lg p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-dark-subtle">Weekly Report</span>
          <button
            onClick={fetchWeeklyReport}
            disabled={loadingReport}
            className="text-[10px] text-lattice-400 hover:text-lattice-300 flex items-center gap-1"
          >
            <RefreshCw size={10} className={loadingReport ? 'animate-spin' : ''} />
            Generate
          </button>
        </div>
        {weeklyReport ? (
          <div className="space-y-1 text-xs text-dark-text">
            {Object.entries(weeklyReport).map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <span className="text-dark-subtle capitalize">{k.replace(/_/g, ' ')}</span>
                <span className="font-medium">{String(v)}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-dark-muted">Click Generate to see this week's summary.</p>
        )}
      </div>

      {/* Achievements grid */}
      {achievements.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-dark-subtle font-medium">Achievements</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {achievements.map((a, i) => (
              <AchievementBadge key={a.id || i} badge={a} />
            ))}
          </div>
        </div>
      )}

      {/* XP log */}
      {log.length > 0 && (
        <div className="bg-dark-surface border border-dark-border rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <Clock size={12} className="text-dark-subtle" />
            <span className="text-xs text-dark-subtle font-medium">Recent XP</span>
          </div>
          <div>
            {log.map((e, i) => (
              <XPLogRow key={i} entry={e} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
