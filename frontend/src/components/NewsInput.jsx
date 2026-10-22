import { useEffect, useState } from 'react'

const MIN = 10
const MAX = 10000

export default function NewsInput({ samples = [], onRun, loading, injected = null }) {
  const [text, setText] = useState('')
  const [simulated, setSimulated] = useState(false)
  const [source, setSource] = useState('')

  // text pushed in from outside (auto-detected live event or a clicked headline)
  useEffect(() => {
    if (!injected) return
    setText((injected.text ?? '').slice(0, MAX))
    setSimulated(!!injected.simulated)
    setSource(injected.label ?? '')
  }, [injected?.key]) // eslint-disable-line react-hooks/exhaustive-deps
  const valid = text.trim().length >= MIN && text.length <= MAX

  const submit = () => { if (valid && !loading) onRun(text.trim(), simulated) }
  const pick = (s) => { setText(s.news); setSimulated(!!s.simulated); setSource('') }

  return (
    <section aria-label="Event input" className="card p-3.5 space-y-2.5">
      <div className="flex items-center justify-between gap-2">
        <h2 className="section-title">Financial event</h2>
        {source && <span className="chip truncate max-w-[60%]" title={source}>From: {source}</span>}
      </div>
      <textarea
        value={text}
        onChange={(e) => { setText(e.target.value); setSimulated(false); setSource('') }}
        onKeyDown={(e) => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') submit() }}
        rows={6}
        maxLength={MAX}
        placeholder="Paste a news article or headline about a rate decision, commodity move, currency shock, or policy change…"
        className="w-full rounded-lg border border-line bg-paper/60 p-2.5 text-sm leading-relaxed resize-y focus:border-accent focus:bg-panel transition"
      />
      <div className="flex items-center justify-between text-xs text-mute">
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input type="checkbox" checked={simulated} onChange={(e) => setSimulated(e.target.checked)} />
          Simulated event (numbers are made up)
        </label>
        <span>{text.length}/{MAX}</span>
      </div>
      {samples.length > 0 && (
        <div>
          <div className="section-title mb-1.5">Try a sample</div>
          <div className="flex flex-wrap gap-1.5">
            {samples.map((s) => (
              <button key={s.id} onClick={() => pick(s)}
                className="text-xs rounded-full border border-line bg-panel px-2.5 py-1 hover:border-accent hover:text-accent hover:bg-accent-soft transition">
                {s.title}
              </button>
            ))}
          </div>
        </div>
      )}
      <button onClick={submit} disabled={!valid || loading}
        className="btn-primary">
        {loading ? 'Analysing event…' : 'Analyse event →'}
      </button>
      <p className="text-[0.8rem] text-mute">Tip: Ctrl+Enter runs the analysis.</p>
    </section>
  )
}
