import React, { useMemo } from 'react'
import './landing.css'

// Change the product name here (one place).
const BRAND = 'MarketRipple'

const HUB = { x: 640, y: 330 }
// label, position, colour, drift (dx, dy in px) and drift period (s) of each floating node
const NODES = [
  { label: 'Crude Oil', x: 190, y: 190, c: '#3be8b8', dx: 16, dy: 12, dur: 11 },
  { label: 'Inflation', x: 1090, y: 170, c: '#ff6b7a', dx: -14, dy: 16, dur: 13 },
  { label: 'Policy Rate', x: 110, y: 470, c: '#8a9bff', dx: 18, dy: -12, dur: 12 },
  { label: 'Banks', x: 1170, y: 430, c: '#3be8b8', dx: -16, dy: -14, dur: 10 },
  { label: 'USD/INR', x: 330, y: 620, c: '#ffbf47', dx: 14, dy: -16, dur: 14 },
  { label: 'Nifty 50', x: 950, y: 640, c: '#8a9bff', dx: -18, dy: -10, dur: 12 },
  { label: 'Real Estate', x: 640, y: 105, c: '#8d9cc8', dx: 20, dy: 6, dur: 15 },
]
const INFERRED = [[0, 2], [1, 3], [4, 5], [2, 4]] // dashed amber = model-suggested links
const CONSTELLATIONS = [
  [[60, 60], [150, 112], [244, 70], [318, 142]],
  [[1000, 722], [1092, 680], [1182, 732], [1244, 664]],
  [[900, 52], [982, 104], [1064, 60], [1130, 118]],
]
const WORDS = [['One', 0.45], ['event.', 0.6], ['Thousands', 0.78], ['of', 0.92], ['connections.', 1.05, true]]
const CARDS = [
  ['Every link explained', '#3be8b8', 'Each connection shows its reason, assumptions and evidence.'],
  ['Facts vs guesses', '#ffbf47', 'Model suggestions are dashed, unverified and kept weak.'],
  ['Works offline too', '#8a9bff', 'A rule-based fallback keeps the demo running without the model.'],
]

const vals = (a, d) => `${a};${a + d};${(a - d * 0.6).toFixed(1)};${a}`

function stars(n, color, seed) {
  let s = seed
  const rnd = () => { s = (s * 16807) % 2147483647; return s / 2147483647 }
  return Array.from({ length: n }, () =>
    `${(rnd() * 100).toFixed(1)}vw ${(rnd() * 100).toFixed(1)}vh 0 ${rnd() > 0.5 ? 1 : 0}px ${color}`).join(',')
}

export default function Landing({ onLaunch }) {
  const starsA = useMemo(() => stars(46, '#c3cdf0', 7), [])
  const starsB = useMemo(() => stars(34, '#8a9bff', 11), [])
  const scrollToWhy = () => document.getElementById('lp-why')?.scrollIntoView({ behavior: 'smooth' })

  return (
    <div className="lp">
      <div aria-hidden="true" className="lp-star" style={{ boxShadow: starsA }} />
      <div aria-hidden="true" className="lp-star" style={{ boxShadow: starsB, animationDelay: '-2.5s', animationDuration: '7s' }} />

      <svg aria-hidden="true" className="lp-bg" viewBox="0 0 1280 780" preserveAspectRatio="xMidYMid slice">
        {CONSTELLATIONS.map((pts, i) => (
          <g key={i}>
            <polyline points={pts.map((p) => p.join(',')).join(' ')} fill="none" stroke="#3a4a80" strokeWidth="1" opacity=".8" />
            {pts.map(([x, y], j) => (
              <circle key={j} cx={x} cy={y} r="2.6" fill="#c3cdf0">
                <animate attributeName="opacity" values=".3;1;.3" dur={`${3 + j}s`} repeatCount="indefinite" />
              </circle>
            ))}
          </g>
        ))}
        {[0.2, 2, 3.8].map((b) => (
          <circle key={b} cx={HUB.x} cy={HUB.y} r="20" fill="none" stroke="#8a9bff" strokeWidth="1.5">
            <animate attributeName="r" from="20" to="360" dur="5.5s" begin={`${b}s`} repeatCount="indefinite" />
            <animate attributeName="opacity" from=".45" to="0" dur="5.5s" begin={`${b}s`} repeatCount="indefinite" />
          </circle>
        ))}
        {NODES.map((n) => (
          <line key={n.label} x1={HUB.x} y1={HUB.y} x2={n.x} y2={n.y} stroke="#3a4a80" strokeWidth="1.6">
            <animate attributeName="x2" values={vals(n.x, n.dx)} dur={`${n.dur}s`} repeatCount="indefinite" />
            <animate attributeName="y2" values={vals(n.y, n.dy)} dur={`${n.dur}s`} repeatCount="indefinite" />
          </line>
        ))}
        {INFERRED.map(([a, b]) => {
          const A = NODES[a], B = NODES[b]
          return (
            <line key={`${a}-${b}`} x1={A.x} y1={A.y} x2={B.x} y2={B.y} stroke="#ffbf47" strokeOpacity=".45" strokeWidth="1.3" strokeDasharray="6 6">
              <animate attributeName="x1" values={vals(A.x, A.dx)} dur={`${A.dur}s`} repeatCount="indefinite" />
              <animate attributeName="y1" values={vals(A.y, A.dy)} dur={`${A.dur}s`} repeatCount="indefinite" />
              <animate attributeName="x2" values={vals(B.x, B.dx)} dur={`${B.dur}s`} repeatCount="indefinite" />
              <animate attributeName="y2" values={vals(B.y, B.dy)} dur={`${B.dur}s`} repeatCount="indefinite" />
            </line>
          )
        })}
        {NODES.map((n, i) => (
          <circle key={`p-${n.label}`} r="3.5" fill="#3be8b8">
            <animateMotion dur="3.6s" begin={`${(2.2 + i * 0.55).toFixed(2)}s`} repeatCount="indefinite" path={`M${HUB.x} ${HUB.y} L${n.x} ${n.y}`} />
            <animate attributeName="opacity" values="0;1;1;0" dur="3.6s" begin={`${(2.2 + i * 0.55).toFixed(2)}s`} repeatCount="indefinite" />
          </circle>
        ))}
        {NODES.map((n) => (
          <g key={n.label}>
            <animateTransform attributeName="transform" type="translate" values={`0 0;${n.dx} ${n.dy};${-n.dx * 0.6} ${n.dy * 0.6};0 0`} dur={`${n.dur}s`} repeatCount="indefinite" />
            <circle cx={n.x} cy={n.y} r="26" fill={n.c} opacity=".13" />
            <circle cx={n.x} cy={n.y} r="8" fill={n.c} />
            <text x={n.x} y={n.y + 30} textAnchor="middle" fontSize="13" fill="#8d9cc8" fontFamily="Manrope, sans-serif">{n.label}</text>
          </g>
        ))}
        <circle cx={HUB.x} cy={HUB.y} r="70" fill="#8a9bff" opacity=".1">
          <animate attributeName="r" values="60;82;60" dur="4s" repeatCount="indefinite" />
        </circle>
        <circle cx={HUB.x} cy={HUB.y} r="13" fill="#8a9bff" />
      </svg>

      <header className="lp-nav lp-rise">
        <span className="lp-brand">{BRAND}</span>
        <button type="button" className="lp-btn lp-btn-sm" onClick={onLaunch}>Launch app</button>
      </header>

      <main className="lp-hero">
        <span className="lp-rise lp-eyebrow" style={{ animationDelay: '.2s' }}>Hackwave 3.0 · Market impact graph</span>
        <h1 className="lp-h1">
          {WORDS.map(([w, d, em]) => (
            <span key={w} className={`lp-rise lp-word${em ? ' lp-em' : ''}`} style={{ animationDelay: `${d}s` }}>{w}</span>
          ))}
        </h1>
        <p className="lp-rise lp-sub" style={{ animationDelay: '1.35s' }}>
          Paste a financial headline and watch it spread through sectors and assets, with a reason behind every link.
        </p>
        <div className="lp-rise lp-cta" style={{ animationDelay: '1.65s' }}>
          <button type="button" className="lp-btn" onClick={onLaunch}>Analyze an event</button>
          <button type="button" className="lp-btn lp-btn-ghost" onClick={scrollToWhy}>Why trust it</button>
        </div>
        <div className="lp-typewrap"><span className="lp-type">Crude oil +12% → Inflation → Policy rate → Banks</span></div>
      </main>

      <section id="lp-why" className="lp-cards">
        {CARDS.map(([t, c, d], i) => (
          <div key={t} className="lp-rise lp-card" style={{ animationDelay: `${2.5 + i * 0.15}s` }}>
            <b style={{ color: c }}>{t}</b>
            <div>{d}</div>
          </div>
        ))}
      </section>
    </div>
  )
}
