import { useState } from 'react'
import { EFFECT_COLOR, fmt } from '../lib/format'

const Dot = ({ effect }) => (
  <span className="inline-block w-2 h-2 rounded-full shrink-0" style={{ background: EFFECT_COLOR[effect] ?? EFFECT_COLOR.unknown }} />
)

/** Two views of the same graph: roll-up through the sector hierarchy, and BFS impact order. */
export default function HierarchyPanel({ analysis, onSelectNode, visibleIds }) {
  const [tab, setTab] = useState('tree')
  if (!analysis?.hierarchy?.length && !analysis?.layers?.length) return null
  const tabBtn = (id, text) => (
    <button key={id} onClick={() => setTab(id)} aria-pressed={tab === id}
      className={`px-2.5 py-1 text-xs rounded-md transition ${tab === id ? 'bg-accent text-night' : 'text-mute hover:text-ink'}`}>{text}</button>
  )
  return (
    <section aria-label="Hierarchy" className="space-y-2 reveal">
      <div className="flex items-center justify-between">
        <h2 className="section-title">Hierarchy</h2>
        <div className="flex gap-1 rounded-lg bg-paper border border-line p-0.5">{tabBtn('tree', 'Sector tree')}{tabBtn('order', 'Impact order')}</div>
      </div>

      {tab === 'tree' && (
        <ul className="card p-2.5 space-y-2">
          {analysis.hierarchy.map((g) => (
            <li key={g.group}>
              <div className="flex items-center gap-2 text-sm font-semibold">
                <Dot effect={g.effect} /><span>{g.group}</span>
                <span className="ml-auto text-[0.8rem] font-normal text-mute">{fmt(g.strength)}</span>
              </div>
              <ul className="ml-1.5 mt-1 border-l border-line pl-3 space-y-1">
                {g.sectors.map((s) => (
                  <li key={s.sector} className="text-xs">
                    <div className="flex items-center gap-2"><Dot effect={s.effect} /><span className="font-medium">{s.sector}</span>
                      <span className="ml-auto text-mute">{fmt(s.strength)}</span></div>
                    <div className="ml-4 text-[0.8rem] text-mute">{s.nodes.join(' · ')}</div>
                  </li>
                ))}
              </ul>
            </li>
          ))}
          <p className="text-[0.8rem] text-mute">Economy → group → sector. Strength = strongest path reaching it (relative score).</p>
        </ul>
      )}

      {tab === 'order' && (
        <ol className="card p-2.5 space-y-2">
          {analysis.layers.map((l) => (
            <li key={l.order} className="flex gap-2.5">
              <span className="grid place-items-center w-5 h-5 shrink-0 rounded-full bg-accent-soft text-accent text-[0.8rem] font-semibold">{l.order}</span>
              <div className="min-w-0">
                <div className="text-xs font-semibold">{l.name}</div>
                <div className="flex flex-wrap gap-1 mt-1">
                  {l.nodes.map((n) => visibleIds.has(n.id)
                    ? <button key={n.id} onClick={() => onSelectNode(n.id)} className="chip hover:bg-accent-soft hover:text-accent">{n.label}</button>
                    : <span key={n.id} className="chip opacity-60">{n.label}</span>)}
                </div>
              </div>
            </li>
          ))}
          <p className="text-[0.8rem] text-mute">Hops from the event found by breadth-first search.</p>
        </ol>
      )}
    </section>
  )
}
