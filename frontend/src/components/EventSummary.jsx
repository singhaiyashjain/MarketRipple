import { useState } from 'react'

const ROWS = [
  ['Type', 'event_type'], ['Entity', 'entity'], ['Indicator', 'indicator'], ['Direction', 'direction'],
  ['Change', 'change'], ['Driver', 'driver'], ['Country', 'country'], ['Date', 'event_date'],
]

export default function EventSummary({ event }) {
  const [raw, setRaw] = useState(false)
  if (!event) return null
  return (
    <section aria-label="Extracted event" className="card p-3.5 reveal">
      <div className="flex items-start justify-between gap-2">
        <h2 className="section-title pt-0.5">What the system read</h2>
        {event.is_simulated && (
          <span className="text-[0.74rem] font-semibold rounded-full bg-warn/10 text-warn px-2 py-0.5 whitespace-nowrap">Simulated demo event</span>
        )}
      </div>
      <dl className="mt-2.5 grid grid-cols-[84px_1fr] gap-x-2 gap-y-1 text-sm">
        {ROWS.map(([label, key]) => (
          <div key={key} className="contents">
            <dt className="text-mute text-xs pt-0.5">{label}</dt>
            <dd className={event[key] ? 'font-medium' : 'text-mute/60'}>{event[key] ?? 'not stated'}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-2 text-[0.8rem] text-mute">Values not in the source are left empty, never guessed.</p>
      <button onClick={() => setRaw((r) => !r)} className="mt-1 text-xs text-accent hover:underline" aria-expanded={raw}>
        {raw ? 'Hide' : 'Show'} structured output
      </button>
      {raw && <pre className="mt-1 text-[0.8rem] bg-paper rounded p-2 overflow-x-auto">{JSON.stringify(event, null, 2)}</pre>}
    </section>
  )
}
