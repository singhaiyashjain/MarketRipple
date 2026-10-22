export default function GraphToolbar({ filters, setFilters, onFit, onRelayout, onExport, disabled }) {
  const btn = 'btn'
  return (
    <div className="w-full flex flex-wrap items-center justify-end gap-2 pointer-events-none">
      <div className="pointer-events-auto flex flex-wrap items-center gap-3 glass px-3 py-1.5 text-xs">
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input type="checkbox" checked={filters.showInferred} disabled={disabled}
            onChange={(e) => setFilters({ ...filters, showInferred: e.target.checked })} />
          Show LLM-inferred links
        </label>
        <label className="flex items-center gap-1.5">
          Min weight
          <input type="range" min="0" max="0.9" step="0.1" value={filters.minWeight} disabled={disabled}
            onChange={(e) => setFilters({ ...filters, minWeight: Number(e.target.value) })} aria-label="Minimum edge weight" />
          <span className="w-6 text-right">{filters.minWeight.toFixed(1)}</span>
        </label>
      </div>
      <div className="pointer-events-auto ml-auto flex gap-1.5">
        <button className={btn} onClick={onFit} disabled={disabled}>Fit</button>
        <button className={btn} onClick={onRelayout} disabled={disabled}>Re-layout</button>
        <button className={btn} onClick={onExport} disabled={disabled}>Snapshot</button>
      </div>
    </div>
  )
}
