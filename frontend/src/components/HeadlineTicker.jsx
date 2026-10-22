import { isEnglish } from '../lib/english'

const REGION_LABEL = { india: 'India', global: 'Global' }
const SECONDS_PER_CHAR = 0.35   // bigger = slower. 0.35 s per character ~ 20 px/s (calm reading speed)
const MIN_SECONDS = 180

/** Scrolling English-only headline strip. Click a headline to analyse it. Pauses on hover. */
export default function HeadlineTicker({ items = [], feeds = {}, stale, loading, error, onAnalyze, showRegion = false }) {
  const rows = items.filter((h) => isEnglish(h.title))
  const feedTotal = Object.keys(feeds).length
  const feedOk = Object.values(feeds).filter((f) => f.ok).length

  // scroll time grows with the amount of text, so the speed stays slow even with many headlines
  const chars = rows.reduce((n, h) => n + h.title.length + h.source.length + 6, 0)
  const duration = Math.max(MIN_SECONDS, Math.round(chars * SECONDS_PER_CHAR))

  let body
  if (loading && rows.length === 0) body = <span className="text-xs text-white/60 px-3">Loading headlines…</span>
  else if (error && rows.length === 0) body = <span className="text-xs text-white/60 px-3">{error}</span>
  else if (rows.length === 0) body = <span className="text-xs text-white/60 px-3">No English headlines right now.</span>
  else {
    const list = (dup) => rows.map((h, i) => (
      <button key={`${dup}-${i}-${h.link || h.title}`} onClick={() => onAnalyze(h)} tabIndex={dup ? -1 : 0} aria-hidden={dup || undefined}
        title={`Analyse: ${h.title}`}
        className="inline-flex items-center gap-1.5 px-3 text-xs text-white/90 hover:text-white hover:underline whitespace-nowrap">
        {showRegion && h.region && <span className="rounded bg-white/15 px-1 text-[0.74rem] uppercase tracking-wide">{REGION_LABEL[h.region] ?? h.region}</span>}
        <span className="text-[#9db0ff]">{h.source}</span>
        <span>{h.title}</span>
      </button>
    ))
    body = <div className="ticker-track inline-flex" style={{ animationDuration: `${duration}s` }}>{list(0)}{list(1)}</div>
  }

  return (
    <div role="region" aria-label="Headlines" className="bg-night/95 border-t border-white/10 flex items-center h-8 text-white relative z-[5]">
      <span className="shrink-0 px-3 gap-1.5 text-[0.74rem] font-semibold uppercase tracking-wider text-white/70 border-r border-white/15 h-full inline-flex items-center">
        <span className="live-dot" aria-hidden="true" />
        Headlines
      </span>
      <div className="ticker-viewport flex-1 min-w-0 overflow-x-auto overflow-y-hidden whitespace-nowrap panel-scroll">{body}</div>
      <span className={`shrink-0 px-3 text-[0.74rem] ${stale ? 'text-[#f4c46b]' : 'text-white/55'}`}
        title={stale ? 'Feeds have not refreshed recently' : 'Feeds responding'}>
        {feedTotal ? `${feedOk}/${feedTotal} feeds${stale ? ' · stale' : ''}` : ''}
      </span>
    </div>
  )
}
