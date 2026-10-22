import { EFFECT_COLOR, EFFECT_LABEL, HORIZON_LABEL, fmt, labelOf, signSymbol } from '../lib/format'

const ORDER = ['The event itself', '1st-order impact', '2nd-order impact', '3rd-order impact']
const orderText = (n) => (n === undefined ? null : ORDER[n] ?? `${n}th-order impact`)

/** Floating "star info" card shown when an orb is clicked. */
const LEVEL = {
  alert: { text: 'Alert', cls: 'bg-loss/15 text-loss border-loss/50', dot: 'bg-loss' },
  watch: { text: 'Watch', cls: 'bg-warn/10 text-warn border-warn/40', dot: 'bg-warn' },
}
const TREND = { rising: '↗ rising', steady: '→ steady', easing: '↘ easing' }
/** Same headline repeated (replay) -> one line with a count. */
const grouped = (stories) => {
  const m = new Map()
  stories.forEach((x) => { const g = m.get(x.headline); if (g) g.n += 1; else m.set(x.headline, { ...x, n: 1 }) })
  return [...m.values()]
}
const day = (iso) => new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

export default function OrbCard({ cardRef, node, data, analysis, pov, signal, onHistory = () => {}, onPov, onExitPov, onSelectNode, onClose }) {
  if (!node) return null
  const inc = data.edges.filter((e) => e.target === node.id)
  const out = data.edges.filter((e) => e.source === node.id)
  const infl = analysis?.influence?.find((x) => x.id === node.id)
  const order = orderText(analysis?.orders?.[node.id])
  const col = EFFECT_COLOR[node.effect] ?? '#fff'

  // plain-language impact: strongest path ending here, else the sector exposure, else the first link it drives
  const endPath = [...(data.paths ?? [])].filter((p) => p.node_ids[p.node_ids.length - 1] === node.id).sort((a, b) => b.strength - a.strength)[0]
  const sectorHit = (data.sectors ?? []).find((s) => node.sector && s.sector?.toLowerCase().startsWith(node.sector.toLowerCase()))
  const firstOut = out[0]
  const impact = endPath
    ? { text: endPath.explanation, meta: `${HORIZON_LABEL[endPath.horizon] ?? endPath.horizon} · relative strength ${fmt(endPath.strength)}` }
    : sectorHit ? { text: sectorHit.reason, meta: `${sectorHit.exposure} · ${sectorHit.confidence} confidence` }
    : firstOut?.explanation ? { text: firstOut.explanation, meta: `${labelOf(data.nodes, firstOut.source)} ${signSymbol(firstOut.sign)} ${labelOf(data.nodes, firstOut.target)}` }
    : null

  const Link = ({ e, other }) => (
    <button onClick={() => onSelectNode(other)}
      className="group flex items-center gap-1.5 rounded-full border border-line bg-paper/60 px-2 py-0.5 text-[0.8rem] hover:border-accent hover:text-accent hover:shadow-float transition">
      <span className="font-bold text-accent">{signSymbol(e.sign)}</span>{labelOf(data.nodes, other)}
    </button>
  )

  return (
    <div ref={cardRef} className="pointer-events-auto absolute z-20 max-sm:left-3 max-sm:right-3 max-sm:bottom-14 max-sm:top-auto max-sm:max-h-[46%] sm:top-14 sm:right-3 sm:w-[290px] sm:max-h-[calc(100%-7rem)] overflow-y-auto panel-scroll glass p-3.5 text-sm reveal space-y-3">
      <div className="flex items-start gap-3">
        <span className="mt-1 relative inline-block w-4 h-4 shrink-0 rounded-full bg-white"
          style={{ boxShadow: `0 0 10px 3px ${col}, 0 0 22px 6px ${col}66` }} />
        <div className="min-w-0 flex-1">
          <div className="text-[0.74rem] uppercase tracking-[.18em] text-mute">{node.type}{node.sector ? ` · ${node.sector}` : ''}</div>
          <h3 className="font-semibold text-[1.05rem] leading-tight text-ink">{node.label}</h3>
        </div>
        <button onClick={onClose} aria-label="Close" className="text-mute hover:text-ink text-lg leading-none -mt-1">×</button>
      </div>

      <div className="flex flex-wrap gap-1.5 text-[0.8rem]">
        <span className="chip"><span style={{ color: col }}>●</span>&nbsp;{EFFECT_LABEL[node.effect]}</span>
        {order && <span className="chip">{order}</span>}
        <span className="chip">{inc.length} in · {out.length} out</span>
      </div>

      {signal && LEVEL[signal.level] && (
        <div className={`rounded-lg border p-2.5 space-y-1.5 ${LEVEL[signal.level].cls}`} role="status">
          <div className="flex items-center gap-2">
            <span className={`inline-block w-2 h-2 rounded-full animate-pulse ${LEVEL[signal.level].dot}`} />
            <span className="section-title !text-inherit whitespace-nowrap">Recurring news · {LEVEL[signal.level].text}</span>
            {signal.trend && <span className="ml-auto text-[0.8rem] whitespace-nowrap">{TREND[signal.trend]}</span>}
          </div>
          <p className="text-[0.85rem] leading-snug text-ink">{signal.reason}</p>
          <ul className="space-y-0.5">
            {grouped(signal.stories.filter((x) => x.effect === 'negative' || signal.negative === 0)).slice(0, 3).map((x, i) => (
              <li key={i} className="text-[0.8rem] leading-snug text-ink/80">
                <span className="text-mute">{day(x.ts)}</span> {x.headline.length > 80 ? `${x.headline.slice(0, 78)}…` : x.headline}
                {x.n > 1 && <span className="ml-1 text-ink">×{x.n}</span>}
                {x.simulated && <span className="ml-1 text-warn">(simulated)</span>}
              </li>
            ))}
          </ul>
          {signal.drivers?.length > 0 && (
            <button onClick={() => onHistory(node.id)} className="btn !w-full !justify-center">Last 5 times this happened ›</button>
          )}
        </div>
      )}

      {impact?.text && (
        <div className="rounded-lg border border-line bg-paper/60 p-2.5 space-y-1">
          <div className="section-title">Impact</div>
          <p className="font-serif text-[0.92rem] leading-snug text-ink">{impact.text}</p>
          <div className="text-[0.8rem] text-mute">{impact.meta}</div>
        </div>
      )}

      {infl && (
        <div>
          <div className="flex justify-between text-[0.8rem] text-mute"><span>Influence in this graph</span><span>{Math.round(infl.score * 100)}%</span></div>
          <div className="mt-1 h-1.5 rounded-full bg-line overflow-hidden">
            <div className="h-full rounded-full bg-accent shadow-[0_0_8px_#8a9bff]" style={{ width: `${Math.max(4, infl.score * 100)}%` }} />
          </div>
        </div>
      )}

      {inc.length > 0 && (
        <div>
          <div className="section-title mb-1">Driven by</div>
          <div className="flex flex-wrap gap-1.5">{inc.map((e) => <Link key={e.id} e={e} other={e.source} />)}</div>
        </div>
      )}
      {out.length > 0 && (
        <div>
          <div className="section-title mb-1">Affects</div>
          <div className="flex flex-wrap gap-1.5">{out.map((e) => <Link key={e.id} e={e} other={e.target} />)}</div>
        </div>
      )}

      <button onClick={pov ? onExitPov : onPov} className="btn-primary !py-2">
        {pov ? '← Back to orbit view' : '◉ See the graph from this star'}
      </button>
      <p className="text-[0.8rem] text-mute leading-snug">
        {pov ? 'Drag to look around · scroll to zoom · click a star to travel to it.' : 'Click any linked star to fly there. Full reasoning is in the right-hand panel.'}
      </p>
    </div>
  )
}
