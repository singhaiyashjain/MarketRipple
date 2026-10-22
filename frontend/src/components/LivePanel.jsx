import { useEffect, useState } from 'react'

function rel(iso, now) {
  if (!iso) return '—'
  const s = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000))
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.round(s / 60)}m ago`
  return `${Math.round(s / 3600)}h ago`
}
function until(iso, now) {
  if (!iso) return '—'
  const s = Math.round((new Date(iso).getTime() - now) / 1000)
  if (s <= 0) return 'any moment'
  if (s < 60) return `${s}s`
  return `${Math.round(s / 60)}m`
}

const REGIONS = [
  { id: 'india', label: 'India' },
  { id: 'global', label: 'Global' },
  { id: 'all', label: 'All' },
]
const REGION_LABEL = { india: 'India', global: 'Global' }

export default function LivePanel({
  status, history = [], error, autoUpdate, onAutoUpdate, pending, onLoadPending,
  onLoadEvent, onPoll, onReplay, onFire, busy, activeVersion, notice,
  region = 'all', onRegion = () => {},
}) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => { const id = setInterval(() => setNow(Date.now()), 5000); return () => clearInterval(id) }, [])

  const feeds = status?.feeds ?? {}
  const feedTotal = Object.keys(feeds).length
  const feedOk = Object.values(feeds).filter((f) => f.ok).length
  const replay = !!status?.replay
  const apiText = !status ? '—'
    : status.api_provider === 'none' || !status.api_configured ? 'not configured'
    : status.api === 'ok' ? `${status.api_provider} · ok` : String(status.api)
  let pill = { text: 'Watching', cls: 'bg-loss/10 text-loss' }
  if (error) pill = { text: 'Offline', cls: 'bg-mute/10 text-mute' }
  else if (replay) pill = { text: 'Replay (simulated)', cls: 'bg-warn/10 text-warn' }
  else if (status && status.last_poll_ok === false) pill = { text: 'Issue', cls: 'bg-warn/10 text-warn' }

  return (
    <section aria-label="Live monitor" className="card p-3.5 space-y-2.5">
      <div className="flex items-center justify-between">
        <h2 className="section-title">Live monitor</h2>
        <span className={`text-[0.8rem] font-medium px-2 py-0.5 rounded-full ${pill.cls}`}><span className="mr-1">●</span>{pill.text}</span>
      </div>

      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-xs">
        <dt className="text-mute">Last check</dt><dd>{rel(status?.last_poll_at, now)}</dd>
        <dt className="text-mute">Next check</dt><dd>{until(status?.next_poll_at, now)}</dd>
        <dt className="text-mute">RSS feeds</dt><dd>{feedTotal ? `${feedOk}/${feedTotal} responding` : '—'}</dd>
        <dt className="text-mute">News API</dt><dd>{apiText}</dd>
      </dl>
      {status?.last_error && <p className="text-[0.8rem] text-warn">Last issue: {status.last_error}</p>}
      {error && <p className="text-[0.8rem] text-loss">{error}</p>}

      <div role="radiogroup" aria-label="News region" className="space-y-1">
        <div className="section-title">News region</div>
        <div className="grid grid-cols-3 gap-1 rounded-lg bg-paper p-0.5">
          {REGIONS.map((r) => (
            <button key={r.id} role="radio" aria-checked={region === r.id} onClick={() => onRegion(r.id)}
              className={`rounded-md py-1 text-xs font-medium transition ${region === r.id ? 'bg-white text-accent shadow-sm' : 'text-mute hover:text-ink'}`}>
              {r.label}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-1 text-xs">
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input type="checkbox" checked={autoUpdate} onChange={(e) => onAutoUpdate(e.target.checked)} />
          Auto-update when a new event is detected
        </label>
        <label className="flex items-center gap-1.5 cursor-pointer" title="Feeds saved, simulated events through the same pipeline (demo-safe)">
          <input type="checkbox" checked={replay} disabled={busy || !status} onChange={(e) => onReplay(e.target.checked)} />
          Replay demo mode (simulated events)
        </label>
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        <button className="btn" onClick={onPoll} disabled={busy || !!error}>{busy ? 'Working…' : 'Check news now'}</button>
        <button className="btn" onClick={onFire} disabled={busy || !!error}
          title="Show the next saved, simulated event immediately (demo)">Fire next saved event</button>
      </div>

      {pending && (
        <div role="status" className="rounded-lg border border-accent/40 bg-accent-soft p-2 text-xs reveal">
          <div className="font-semibold text-accent mb-0.5">New event detected</div>
          <div className="text-ink leading-snug mb-1.5">{pending.headline}</div>
          <button className="btn" onClick={onLoadPending}>Load it</button>
        </div>
      )}
      {notice && <p className="text-[0.8rem] text-mute">{notice}</p>}

      <div>
        <div className="section-title mb-1.5">Recent detected events · {region === 'all' ? 'All regions' : REGION_LABEL[region]}</div>
        {history.length === 0 ? (
          <p className="text-xs text-mute">
            Nothing detected yet{region !== 'all' ? ` for ${REGION_LABEL[region]}` : ''}. The monitor checks the news every few minutes
            {region !== 'all' ? ', or switch to All' : ''}, or turn on replay mode.
          </p>
        ) : (
          <ul className="space-y-1.5 max-h-56 overflow-y-auto panel-scroll">
            {history.map((e) => (
              <li key={e.version}>
                <button onClick={() => onLoadEvent(e)}
                  className={`w-full text-left rounded-lg border px-2.5 py-1.5 text-xs transition border-accent bg-accent-soft ${e.version === activeVersion ? 'ring-1 ring-accent/60' : ''}`}>
                  <div className="flex items-center gap-1.5 mb-0.5">
                    {/* region tag replaces the old "Live" label; red = detected from live news */}
                    <span className="chip !bg-loss/10 !text-loss">{REGION_LABEL[e.region] ?? 'Global'}</span>
                    {e.kind === 'replay' && <span className="chip !bg-warn/10 !text-warn">Simulated</span>}
                    {e.sources?.length > 1 && <span className="chip">{e.sources.length} outlets</span>}
                    <span className="ml-auto text-mute">{rel(e.detected_at, now)}</span>
                  </div>
                  <div className="text-ink leading-snug">{e.headline}</div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
