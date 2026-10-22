const STEPS = [
  ['1', 'Paste news', 'A headline or article about rates, commodities, FX or policy.'],
  ['2', 'Trace the spread', 'Events become a graph of sectors, assets and indicators.'],
  ['3', 'Inspect evidence', 'Click any link to see reasoning, sources and history.'],
]

export default function EmptyState({ loading }) {
  return (
    <div className="absolute inset-0 grid place-items-center p-6 text-center pointer-events-none">
      <div className="max-w-md">
        <svg width="96" height="96" viewBox="0 0 72 72" className={`mx-auto mb-4 ${loading ? 'animate-pulse' : ''}`} aria-hidden="true">
          <g stroke="#5668b8" strokeWidth="1.5" fill="none" strokeDasharray={loading ? '4 3' : '0'}>
            <path d="M14 36 L36 16 M14 36 L36 56 M36 16 L58 24 M36 56 L58 48 M36 16 L36 56" />
          </g>
          <circle cx="14" cy="36" r="6" fill="#8a9bff" />
          <circle cx="36" cy="16" r="5" fill="#3be8b8" /><circle cx="36" cy="56" r="5" fill="#ff6b7a" />
          <circle cx="58" cy="24" r="5" fill="#5668b8" /><circle cx="58" cy="48" r="5" fill="#5668b8" />
        </svg>
        <h2 className="font-serif text-2xl text-ink">{loading ? 'Building the impact graph…' : 'See how one event ripples outward'}</h2>
        <p className="text-sm text-mute mt-1.5">
          {loading ? 'Extracting entities, linking relationships and tracing paths.' : 'Pick a sample on the left or paste your own news, then choose Analyse event.'}
        </p>
        {!loading && (
          <ol className="mt-6 grid gap-2 text-left">
            {STEPS.map(([n, t, d]) => (
              <li key={n} className="glass flex items-start gap-3 px-3 py-2.5">
                <span className="grid place-items-center w-6 h-6 shrink-0 rounded-full bg-accent text-night text-xs font-semibold">{n}</span>
                <span><span className="block text-sm font-semibold">{t}</span><span className="text-xs text-mute">{d}</span></span>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  )
}
