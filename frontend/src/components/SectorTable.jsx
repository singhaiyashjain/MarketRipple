import { exposureTone } from '../lib/format'

const TONE = { loss: 'bg-loss/10 text-loss', gain: 'bg-gain/10 text-gain', mixed: 'bg-mixed/15 text-mute' }
const CONF = { low: 1, medium: 2, high: 3 }

export default function SectorTable({ sectors = [] }) {
  if (!sectors?.length) return null
  return (
    <section aria-label="Sector exposure" className="space-y-1.5">
      <h2 className="section-title">Sector exposure</h2>
      <ul className="space-y-1.5">
        {sectors.map((s) => (
          <li key={s.sector} className="card p-2.5">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm">{s.sector}</span>
              <span className={`ml-auto rounded-full px-2 py-0.5 text-[0.8rem] font-medium ${TONE[exposureTone(s.exposure)]}`}>{s.exposure}</span>
            </div>
            <p className="text-xs text-mute mt-0.5">{s.reason}</p>
            <div className="mt-1 flex items-center gap-1 text-[0.8rem] text-mute" title={`Confidence: ${s.confidence}`}>
              {[1, 2, 3].map((i) => (
                <span key={i} className={`inline-block w-3 h-1 rounded ${i <= CONF[s.confidence] ? 'bg-ink' : 'bg-line'}`} />
              ))}
              <span className="ml-1">{s.confidence} confidence</span>
            </div>
          </li>
        ))}
      </ul>
      <p className="text-[0.8rem] text-mute">Illustrative exposure analysis, not investment advice.</p>
    </section>
  )
}
