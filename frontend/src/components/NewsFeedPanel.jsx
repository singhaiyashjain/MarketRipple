import { useEffect, useState } from 'react'

const REGION_LABEL = { india: 'India', global: 'Global', all: 'All regions' }

function rel(iso, now) {
  if (!iso) return ''
  const s = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000))
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.round(s / 60)}m ago`
  if (s < 86400) return `${Math.round(s / 3600)}h ago`
  return `${Math.round(s / 86400)}d ago`
}

/**
 * Current FINANCIAL news for the selected region (India | Global | All). The backend already drops everything
 * that is not financial / project-related; this panel also refuses such items as a second safety net.
 * - "Project-related" = touches what the impact graph models (oil, RBI/rates, rupee, inflation, banks...).
 * - Every card always shows its description (the story summary) in this left panel.
 * - Click = analyse it (or open the impact graph if it was already analysed automatically); the description is
 *   also copied into the "Financial event" box below.
 */
export default function NewsFeedPanel({
  items = [], region = 'all', loading, error, stale, counts, onAnalyze, onLoadEvent, onRefresh, activeVersion,
}) {
  const [now, setNow] = useState(Date.now())
  const [onlyProject, setOnlyProject] = useState(false)
  useEffect(() => { const id = setInterval(() => setNow(Date.now()), 30000); return () => clearInterval(id) }, [])

  const financial = items.filter((h) => h.relevant !== false)          // never show non-financial news
  const rows = onlyProject ? financial.filter((h) => h.project || h.event_version) : financial
  const analysed = financial.filter((h) => h.event_version).length

  return (
    <section aria-label="Latest news" className="card p-3.5 space-y-2.5">
      <div className="flex items-center justify-between gap-2">
        <h2 className="section-title">Latest news · {REGION_LABEL[region] ?? region}</h2>
        <button className="text-[0.8rem] text-accent hover:underline" onClick={onRefresh} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      <div className="flex items-center justify-between text-[0.8rem] text-mute">
        <span>
          {financial.length} stories{analysed ? ` · ${analysed} auto-analysed` : ''}
          {counts ? ` · India ${counts.india ?? 0} / Global ${counts.global ?? 0}` : ''}
        </span>
        <label className="flex items-center gap-1 cursor-pointer">
          <input type="checkbox" checked={onlyProject} onChange={(e) => setOnlyProject(e.target.checked)} />
          Project-related only
        </label>
      </div>
      {stale && <p className="text-[0.8rem] text-warn">Feeds have not refreshed recently, showing the last known news.</p>}

      {rows.length === 0 ? (
        <p className="text-xs text-mute">
          {loading ? 'Loading live news…'
            : error ? `${error}. Start the backend to see live news.`
            : onlyProject ? 'No project-related stories right now. Untick the filter to see all financial news.'
            : `No ${region === 'all' ? '' : REGION_LABEL[region] + ' '}financial news yet. The monitor checks every few minutes, or press Check news now.`}
        </p>
      ) : (
        <ul className="space-y-1.5 max-h-96 overflow-y-auto panel-scroll">
          {rows.map((h, i) => {
            const open = () => (h.event_version ? onLoadEvent({ version: h.event_version }) : onAnalyze(h))
            const desc = (h.summary || '').trim()
            const showDesc = desc && desc.toLowerCase() !== h.title.trim().toLowerCase()
            return (
              <li key={`${h.link || h.title}-${i}`}>
                <div className={`rounded-lg border px-2.5 py-1.5 text-xs transition ${h.event_version && h.event_version === activeVersion ? 'ring-1 ring-accent/60' : ''} border-accent bg-accent-soft`}>
                  <div className="flex items-center gap-1.5 mb-0.5 flex-wrap">
                    {region === 'all' && h.region && <span className="chip">{REGION_LABEL[h.region] ?? h.region}</span>}
                    {h.event_version
                      ? <span className="chip !bg-loss/10 !text-loss">Impact ready</span>
                      : h.project
                        ? <span className="chip !bg-warn/10 !text-warn">Project-related</span>
                        : <span className="chip">Financial</span>}
                    <span className="text-mute truncate max-w-[45%]" title={h.source}>{h.source}</span>
                    <span className="ml-auto text-mute">{rel(h.published, now)}</span>
                  </div>
                  <button onClick={open} className="text-left text-ink leading-snug hover:text-accent w-full"
                    title={h.event_version ? 'Open the impact graph' : 'Analyse this story'}>
                    {h.title}
                  </button>
                  {/* description: always shown in the left panel */}
                  <p className="mt-1 text-[0.8rem] leading-snug text-mute line-clamp-3">
                    {showDesc ? desc : 'No description provided by the source. Open the story for details.'}
                  </p>
                  <div className="mt-1 flex items-center gap-3 text-[0.8rem]">
                    <button onClick={open} className="text-accent hover:underline">
                      {h.event_version ? 'View impact graph' : 'Analyse impact'}
                    </button>
                    {h.link && <a href={h.link} target="_blank" rel="noreferrer" className="text-mute hover:text-accent hover:underline">Read story ↗</a>}
                  </div>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
