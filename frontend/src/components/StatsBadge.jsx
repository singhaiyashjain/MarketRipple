import { fmt } from '../lib/format'

const STAB = { high: 'Stable across periods', medium: 'Moderately stable', low: 'Unstable across periods' }

/** Historical evidence for one link. Co-movement, not causation. */
export default function StatsBadge({ stats }) {
  if (!stats) {
    return <p className="text-xs text-mute rounded bg-paper p-2">No historical data tested for this link yet. Treat it as a reasoned relationship, not a measured one.</p>
  }
  const sig = stats.t_stat !== null && stats.t_stat !== undefined && Math.abs(stats.t_stat) >= 2
  const cell = (k, v) => (
    <div className="rounded bg-paper px-2 py-1"><div className="text-[0.8rem] text-mute">{k}</div><div className="text-sm font-semibold">{v}</div></div>
  )
  return (
    <div className="space-y-1.5">
      <div className="grid grid-cols-4 gap-1.5">
        {cell('Beta', fmt(stats.beta))}
        {cell('t-stat', fmt(stats.t_stat, 1))}
        {cell('Events', stats.n ?? '—')}
        {cell('Lag', stats.lag_days != null ? `${stats.lag_days}d` : '—')}
      </div>
      <div className="text-xs text-mute">
        {stats.ci_low != null && <>95% interval {fmt(stats.ci_low)} to {fmt(stats.ci_high)}. </>}
        {sig ? 'Statistically distinguishable from zero.' : 'Not clearly different from zero.'}
        {stats.stability && <> {STAB[stats.stability]}.</>}
      </div>
      <p className="text-[0.8rem] text-mute italic">{stats.note ?? 'Historical co-movement, not proof of causation.'}</p>
    </div>
  )
}
