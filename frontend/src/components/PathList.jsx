import { EFFECT_COLOR, EFFECT_LABEL, HORIZON_LABEL, fmt, labelOf } from '../lib/format'

export default function PathList({ data, selected, onSelect }) {
  const paths = data?.paths
  if (!paths?.length) return null
  const sorted = [...paths].sort((a, b) => b.strength - a.strength)
  return (
    <section aria-label="Impact paths" className="space-y-1.5">
      <div className="flex items-baseline justify-between">
        <h2 className="section-title">Impact paths</h2>
        <span className="text-[0.8rem] text-mute" title="Product of edge weights. A relative score, not a probability.">relative strength</span>
      </div>
      {sorted.map((p) => {
        const active = selected === p.id
        const end = labelOf(data.nodes, p.node_ids[p.node_ids.length - 1])
        return (
          <button key={p.id} onClick={() => onSelect(active ? null : p.id)} aria-pressed={active}
            className={`w-full text-left rounded-xl border p-2.5 transition shadow-card border-accent bg-accent-soft ${active ? 'ring-1 ring-accent/60' : 'hover:-translate-y-px'}`}>
            <div className="flex items-center gap-2 text-sm font-medium">
              <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: EFFECT_COLOR[p.terminal_effect] }} />
              <span className="truncate">{end}</span>
              <span className="ml-auto text-xs text-mute">{fmt(p.strength, 2)}</span>
            </div>
            <div className="mt-1.5 h-1.5 rounded-full bg-line overflow-hidden">
              <div className="h-full rounded-full" style={{ width: `${Math.max(4, Math.min(1, p.strength) * 100)}%`, background: EFFECT_COLOR[p.terminal_effect] }} />
            </div>
            <div className="mt-1 text-[0.8rem] text-mute">
              {EFFECT_LABEL[p.terminal_effect]} · {HORIZON_LABEL[p.horizon]} · {p.node_ids.length - 1} steps
            </div>
          </button>
        )
      })}
    </section>
  )
}
