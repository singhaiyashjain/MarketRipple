import { useEffect, useMemo, useState } from 'react'
import { getBacktest, getStarBacktest } from '../api'

const GAIN = '#3be8b8'
const LOSS = '#ff6b7a'
const WINDOWS = ['1', '5', '20']
const pct = (v, d = 1) => (v === null || v === undefined ? '—' : `${v > 0 ? '+' : ''}${Number(v).toFixed(d)}%`)
const tone = (v) => (v > 0 ? 'text-gain' : v < 0 ? 'text-loss' : 'text-mute')
const dateFmt = (iso, yr = '2-digit') => new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { year: yr, month: 'short', day: 'numeric' })

function Verdict({ t }) {
  if (t.n < 3) return <span className="chip !bg-mute/10">Insufficient history</span>
  if (t.agrees === true) return <span className="chip !bg-gain/15 !text-gain">History agrees with the graph</span>
  if (t.agrees === false) return <span className="chip !bg-loss/15 !text-loss">History disagrees with the graph</span>
  if (t.leans) return <span className="chip !bg-warn/10 !text-warn">Leans {t.leans} the graph · not significant</span>
  return <span className="chip !bg-mute/10">Inconclusive</span>
}

/** Per window (+1/+5/+20 days): one bar per past episode (newest first) and a white tick at the average. Pure SVG. */
function Bars({ t, adjusted }) {
  const key = adjusted ? 'abnormal_pct' : 'return_pct'
  const eps = t.last_episodes
  const vals = eps.flatMap((e) => WINDOWS.map((w) => e.returns[w][key] ?? e.returns[w].return_pct))
  const max = Math.max(1, ...vals.map((v) => Math.abs(v)))
  const W = 252, H = 92, mid = 40, gw = W / 3, bw = Math.min(11, (gw - 14) / Math.max(1, eps.length))
  const mean = (w) => (t.stats ? ((adjusted && t.stats.mean_abnormal_pct) || t.stats.mean_return_pct)[w] : null)
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img"
      aria-label={`Returns after the last ${eps.length} episodes at +1, +5 and +20 trading days`}>
      <line x1="0" x2={W} y1={mid} y2={mid} stroke="#2a376e" strokeWidth="1" />
      {WINDOWS.map((w, gi) => {
        const x0 = gi * gw + (gw - bw * eps.length) / 2
        const m = mean(w)
        return (
          <g key={w}>
            {eps.map((e, i) => {
              const v = e.returns[w][key] ?? e.returns[w].return_pct
              const h = Math.max(1, (Math.abs(v) / max) * (mid - 6))
              return (
                <rect key={e.date} x={x0 + i * bw} y={v >= 0 ? mid - h : mid} width={bw - 2} height={h} rx="1.5"
                  fill={v >= 0 ? GAIN : LOSS} opacity={0.35 + 0.65 * (1 - i / Math.max(1, eps.length))}>
                  <title>{`${dateFmt(e.date)} · +${w}d ${pct(v, 2)}`}</title>
                </rect>
              )
            })}
            {m !== null && m !== undefined && (() => {
              const y = mid - (m / max) * (mid - 6)
              return <line x1={gi * gw + 6} x2={(gi + 1) * gw - 6} y1={y} y2={y} stroke="#fff" strokeWidth="1.6" strokeDasharray="3 2"><title>{`average +${w}d ${pct(m, 2)}`}</title></line>
            })()}
            <text x={gi * gw + gw / 2} y={H - 4} textAnchor="middle" fontSize="9.5" fill="#a9b6dd">+{w} day{w === '1' ? '' : 's'}</text>
          </g>
        )
      })}
    </svg>
  )
}

function TargetCard({ t, adjusted }) {
  const key = adjusted ? 'abnormal_pct' : 'return_pct'
  const hit = t.hit_rate?.['5']
  const mean = t.stats ? ((adjusted && t.stats.mean_abnormal_pct) || t.stats.mean_return_pct)['5'] : null
  const tstat = t.stats?.t_stat?.['5']
  return (
    <li className="card p-2.5 space-y-2">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="font-medium text-sm">{t.label}</span>
        <span className="chip">{t.ticker}</span>
        <span className="chip" title="What the graph expects for this node">graph expects {t.predicted === 'up' ? '↑' : t.predicted === 'down' ? '↓' : '?'}</span>
      </div>
      <Verdict t={t} />
      <p className="text-[0.85rem] leading-snug text-ink/90">{t.summary}</p>
      {t.note && <p className="text-[0.8rem] text-warn">{t.note}</p>}
      {t.last_episodes.length > 0 && (
        <>
          {t.stats && (
            <dl className="grid grid-cols-3 gap-2 text-center text-[0.8rem]">
              <div className="rounded bg-paper/60 p-1"><dt className="text-mute">Episodes</dt><dd className="font-semibold">{t.n}</dd></div>
              <div className="rounded bg-paper/60 p-1"><dt className="text-mute">Hit-rate +5d</dt><dd className="font-semibold">{hit === null || hit === undefined ? '—' : `${Math.round(hit * 100)}%`}</dd></div>
              <div className="rounded bg-paper/60 p-1" title={tstat !== undefined ? `t-stat ${tstat}` : ''}>
                <dt className="text-mute">Avg +5d</dt><dd className={`font-semibold ${tone(mean)}`}>{pct(mean, 2)}</dd>
              </div>
            </dl>
          )}
          <Bars t={t} adjusted={adjusted} />
          <div className="overflow-x-auto">
            <table className="w-full text-[0.8rem] tabular-nums">
              <thead><tr className="text-mute text-left">
                <th className="font-medium py-0.5">Date</th><th className="font-medium text-right">Driver</th>
                {WINDOWS.map((w) => <th key={w} className="font-medium text-right">+{w}d</th>)}
              </tr></thead>
              <tbody>
                {t.last_episodes.map((e) => (
                  <tr key={e.date} className="border-t border-line/60">
                    <td className="py-0.5">{dateFmt(e.date)}</td>
                    <td className={`text-right ${tone(e.driver_move_pct)}`}>{pct(e.driver_move_pct)}</td>
                    {WINDOWS.map((w) => {
                      const v = e.returns[w][key] ?? e.returns[w].return_pct
                      return <td key={w} className={`text-right ${tone(v)}`}>{pct(v)}</td>
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </li>
  )
}

function Result({ bt, adjusted }) {
  if (!bt) return null
  if (!bt.available) {
    return (
      <div className="rounded-lg border border-line bg-paper/50 p-2.5 text-xs space-y-1" role="status">
        <p className="font-medium">No historical test for this one</p>
        <p className="text-mute leading-snug">{bt.reason}</p>
      </div>
    )
  }
  const sc = bt.size_comparison
  return (
    <div className="space-y-2.5">
      <p className="text-[0.85rem] leading-snug">
        Past times <b>{bt.driver.label}</b> ({bt.driver.ticker}) moved <b>{bt.driver.direction}</b> by ≥{bt.driver.shock_sigma}σ,
        {' '}from {dateFmt(bt.date_range.start, 'numeric')} to {dateFmt(bt.date_range.end, 'numeric')}.
        {bt.simulated_event && <span className="ml-1 text-warn">(the event itself is simulated)</span>}
      </p>
      {sc && (
        <p className="text-[0.8rem] text-mute leading-snug">
          The news says {pct(sc.stated_pct, 1)}; historical shocks of this kind moved {pct(sc.median_historical_move_pct, 1)} in a day (median, largest {pct(sc.largest_historical_move_pct, 1)}). {sc.note}
        </p>
      )}
      <ul className="space-y-2">{bt.targets.map((t) => <TargetCard key={t.node_id} t={t} adjusted={adjusted} />)}</ul>
      {bt.skipped?.length > 0 && (
        <details className="text-[0.8rem] text-mute">
          <summary className="cursor-pointer">{bt.skipped.length} affected node(s) not tested</summary>
          <ul className="mt-1 list-disc pl-4">{bt.skipped.map((s) => <li key={s.node_id}>{s.node_id}: {s.reason}</li>)}</ul>
        </details>
      )}
      <details className="text-[0.8rem] text-mute"><summary className="cursor-pointer">How this is computed</summary><p className="mt-1 leading-snug">{bt.method}</p></details>
      <p className="text-[0.8rem] text-warn/90 leading-snug">{bt.caveat}</p>
    </div>
  )
}

/** "The last 5 times this happened, here is what moved" - for the current event, or for a blinking star. */
export default function BacktestPanel({ data, focusStar, focusLabel, onClearFocus, windowDays, includeSimulated }) {
  const [tab, setTab] = useState('event')
  const [adjusted, setAdjusted] = useState(true)
  const [ev, setEv] = useState({ loading: false, bt: null, error: null })
  const [st, setSt] = useState({ loading: false, bt: null, error: null })

  useEffect(() => { if (focusStar) setTab('star') }, [focusStar])
  useEffect(() => { if (!focusStar && tab === 'star') setTab('event') }, [focusStar, tab])

  useEffect(() => {
    if (!data) { setEv({ loading: false, bt: null, error: null }); return undefined }
    const ctl = new AbortController()
    setEv({ loading: true, bt: null, error: null })
    getBacktest(data, ctl.signal)
      .then((bt) => setEv({ loading: false, bt, error: null }))
      .catch((e) => { if (e.name !== 'AbortError') setEv({ loading: false, bt: null, error: 'Could not reach the backtest service.' }) })
    return () => ctl.abort()
  }, [data])

  useEffect(() => {
    if (!focusStar) return undefined
    let live = true
    setSt({ loading: true, bt: null, error: null })
    getStarBacktest(focusStar, { windowDays, includeSimulated })
      .then((bt) => live && setSt({ loading: false, bt, error: null }))
      .catch(() => live && setSt({ loading: false, bt: null, error: 'Could not reach the backtest service.' }))
    return () => { live = false }
  }, [focusStar, windowDays, includeSimulated])

  const cur = useMemo(() => (tab === 'star' && focusStar ? st : ev), [tab, focusStar, st, ev])
  if (!data && !focusStar) return null

  const tabBtn = (id, label) => (
    <button key={id} onClick={() => setTab(id)} aria-pressed={tab === id}
      className={`rounded-full px-2.5 py-0.5 text-[0.8rem] border transition ${tab === id ? 'border-accent bg-accent-soft text-ink' : 'border-line text-mute hover:text-ink'}`}>{label}</button>
  )
  return (
    <section aria-label="Historical backtest" id="backtest-panel" className="space-y-2">
      <div className="flex items-baseline justify-between">
        <h2 className="section-title">Has this happened before?</h2>
        <label className="text-[0.8rem] text-mute flex items-center gap-1 cursor-pointer" title="Abnormal = return minus what the Nifty 50 explains">
          <input type="checkbox" checked={adjusted} onChange={(e) => setAdjusted(e.target.checked)} /> market-adjusted
        </label>
      </div>
      <div className="flex flex-wrap gap-1.5 items-center">
        {tabBtn('event', 'This event')}
        {focusStar && tabBtn('star', `Recurring: ${focusLabel || focusStar}`)}
        {focusStar && tab === 'star' && <button className="text-[0.8rem] text-mute hover:text-ink" onClick={onClearFocus} aria-label="Close recurring-star history">×</button>}
      </div>
      {cur.loading && <p className="text-xs text-mute animate-pulse">Looking up past episodes in 10 years of prices…</p>}
      {cur.error && <p role="alert" className="text-xs text-loss">{cur.error}</p>}
      {!cur.loading && <Result bt={cur.bt} adjusted={adjusted} />}
    </section>
  )
}
