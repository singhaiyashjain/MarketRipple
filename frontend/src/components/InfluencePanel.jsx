/** Which intermediate variables carry the most impact (betweenness + PageRank on the reachable graph). */
export default function InfluencePanel({ analysis, onSelectNode, visibleIds }) {
  const rows = analysis?.influence
  if (!rows?.length) return null
  const best = analysis.best_paths?.[0]
  return (
    <section aria-label="Key transmission nodes" className="space-y-2 reveal">
      <h2 className="section-title">Key transmission nodes</h2>
      <ul className="card p-2.5 space-y-2">
        {rows.map((r) => {
          const clickable = visibleIds.has(r.id)
          return (
            <li key={r.id}>
              <button disabled={!clickable} onClick={() => onSelectNode(r.id)}
                className="w-full text-left disabled:cursor-default" title={`betweenness ${r.betweenness} · PageRank ${r.pagerank}`}>
                <div className="flex items-baseline gap-2 text-xs">
                  <span className={`font-medium ${clickable ? 'hover:text-accent' : ''}`}>{r.label}</span>
                  <span className="text-mute">{r.sector}</span>
                  <span className="ml-auto text-mute">{r.score.toFixed(2)}</span>
                </div>
                <div className="mt-1 h-1.5 rounded-full bg-line overflow-hidden">
                  <div className="h-full rounded-full bg-accent shadow-[0_0_8px_#8a9bff]" style={{ width: `${Math.max(4, r.score * 100)}%` }} />
                </div>
              </button>
            </li>
          )
        })}
        {best && <p className="text-[0.8rem] text-mute pt-1">Strongest single chain: {best.label} (relative strength {best.strength.toFixed(2)}, found with Dijkstra).</p>}
      </ul>
    </section>
  )
}
