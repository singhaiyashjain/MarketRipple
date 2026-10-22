const TREND = { rising: '↗', steady: '→', easing: '↘' }
const WINDOWS = [3, 7, 14, 30]

/** Stars that keep getting negative news. Alerts blink in the 3D graph; this is the list behind them. */
export default function RecurrencePanel({ rec, settings, onSettings, visibleIds, onSelectStar, onHistory, onClear }) {
  const { nodes = {}, alerts = [], watch = [], thresholds = {}, events_in_window: events = 0, window_days: win = 7, error } = rec
  const all = [...alerts, ...watch].map((id) => nodes[id]).filter(Boolean)
  const rows = all.slice(0, 8)
  const open = (s) => (visibleIds.has(s.node_id) ? onSelectStar(s.node_id) : onHistory(s.node_id))
  return (
    <section aria-label="Recurring news alerts" className="card p-3.5 space-y-2.5">
      <div className="flex items-center justify-between gap-2">
        <h2 className="section-title">Recurring news</h2>
        <span className={`text-[0.8rem] font-medium px-2 py-0.5 rounded-full ${alerts.length ? 'bg-loss/10 text-loss' : 'bg-mute/10 text-mute'}`}>
          {alerts.length ? <><span className="live-dot mr-1.5 align-middle" />{alerts.length} blinking</> : 'all quiet'}
        </span>
      </div>

      {rows.length === 0 ? (
        <p className="text-xs text-mute leading-snug">
          No star has had {thresholds.alert_hits ?? 3} separate negative stories in the last {win} days yet
          ({events} analysed event{events === 1 ? '' : 's'} in that window). A star starts blinking when it does.
        </p>
      ) : (
        <ul className="space-y-1.5">
          {rows.map((s) => (
            <li key={s.node_id}>
              <button onClick={() => open(s)}
                className={`w-full text-left rounded-lg border p-2 transition hover:-translate-y-px ${s.level === 'alert' ? 'border-loss/50 bg-loss/5' : 'border-warn/40 bg-warn/5'}`}>
                <div className="flex items-center gap-2 text-sm font-medium">
                  <span className={`inline-block w-2.5 h-2.5 rounded-full ${s.level === 'alert' ? 'bg-loss animate-pulse' : 'bg-warn'}`} />
                  <span className="truncate">{s.label}</span>
                  <span className="ml-auto text-xs text-mute">{s.negative} negative {s.trend ? TREND[s.trend] : ''}</span>
                </div>
                <div className="mt-0.5 text-[0.8rem] text-mute leading-snug truncate">{s.stories?.[0]?.headline}</div>
                <div className="mt-0.5 flex flex-wrap gap-1">
                  {!visibleIds.has(s.node_id) && <span className="chip">not in this graph · opens history</span>}
                  {s.simulated_hits > 0 && <span className="chip !text-warn">{s.simulated_hits} simulated</span>}
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}

      {all.length > rows.length && <p className="text-[0.8rem] text-mute">+ {all.length - rows.length} more stars on watch or alert (strongest 8 shown)</p>}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[0.8rem] text-mute">
        <label className="flex items-center gap-1">Window
          <select className="bg-paper border border-line rounded px-1 py-0.5 text-ink" value={settings.windowDays}
            onChange={(e) => onSettings({ ...settings, windowDays: Number(e.target.value) })}>
            {WINDOWS.map((d) => <option key={d} value={d}>{d} days</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1 cursor-pointer" title="Replay / sample events are labelled simulated">
          <input type="checkbox" checked={settings.includeSimulated} onChange={(e) => onSettings({ ...settings, includeSimulated: e.target.checked })} /> include simulated
        </label>
        <label className="flex items-center gap-1 cursor-pointer" title="Fly to the blinking star and open its card when a new event arrives">
          <input type="checkbox" checked={settings.autoOpen} onChange={(e) => onSettings({ ...settings, autoOpen: e.target.checked })} /> auto-open star
        </label>
      </div>
      <div className="flex items-center justify-between text-[0.8rem] text-mute">
        <span>Alert at {thresholds.alert_hits ?? 3}+ negative stories · watch at {thresholds.watch_hits ?? 2}</span>
        <button className="underline hover:text-ink" onClick={onClear}>clear history</button>
      </div>
      {error && <p className="text-[0.8rem] text-warn">{error}</p>}
    </section>
  )
}
