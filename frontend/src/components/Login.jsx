import React, { useId, useMemo, useState } from 'react'
import './landing.css' // reuse the landing page's look (fonts, starfield, pill buttons)

/**
 * Login.jsx: standalone username + password screen for MarketRipple.
 * Drop into: frontend/src/components/Login.jsx  (next to Landing.jsx and landing.css)
 *
 * Look: same night-sky background, twinkling stars, constellations, Sora/Manrope fonts,
 * teal accent and pill button as the landing page and its launch hero.
 *
 * Props
 *   onLogin({ username, password })  async function that performs the real sign-in.
 *                                    Resolve = success. Throw an Error to show its message.
 *   onSuccess(result)                called with what onLogin resolved to (e.g. open the dashboard).
 *   onBack()                         optional; shows a "Back" button (e.g. return to the landing page).
 *
 * Nothing is stored or checked here. Until onLogin is wired to a backend, signing in shows
 * "Login is not connected yet", so a placeholder can never pass as real authentication.
 */

const BRAND = 'MarketRipple'

const CONSTELLATIONS = [
  [[60, 60], [150, 112], [244, 70], [318, 142]],
  [[1000, 722], [1092, 680], [1182, 732], [1244, 664]],
  [[900, 52], [982, 104], [1064, 60], [1130, 118]],
]

function stars(n, color, seed) {
  let s = seed
  const rnd = () => { s = (s * 16807) % 2147483647; return s / 2147483647 }
  return Array.from({ length: n }, () =>
    `${(rnd() * 100).toFixed(1)}vw ${(rnd() * 100).toFixed(1)}vh 0 ${rnd() > 0.5 ? 1 : 0}px ${color}`).join(',')
}

const notConnected = async () => { throw new Error('Login is not connected yet.') }

const CSS = `
.lg-wrap { position: relative; flex: 1; display: flex; align-items: center; justify-content: center; padding: 24px; }
.lg-box { width: 100%; max-width: 420px; background: #0f1838cc; border: 1px solid #2a3878; border-radius: 16px; padding: 34px 32px 30px; backdrop-filter: blur(6px); }
.lg-h1 { margin: 0; font: 700 32px/1.15 Sora, sans-serif; }
.lg-sub { margin: 10px 0 0; color: #c3cdf0; font-size: 16px; line-height: 1.5; }
.lg-label { display: block; margin: 22px 0 8px; font-size: 15px; font-weight: 600; color: #c3cdf0; }
.lg-field { position: relative; }
.lg-input { width: 100%; box-sizing: border-box; background: #070b1f; color: #e8edff; border: 1.5px solid #2a3878; border-radius: 12px;
  padding: 14px 16px; font: 400 16px Manrope, system-ui, sans-serif; }
.lg-input::placeholder { color: #6f7fb3; }
.lg-input:focus-visible { outline: 3px solid #3be8b8; outline-offset: 2px; border-radius: 12px; }
.lg-input[aria-invalid="true"] { border-color: #ff6b7a; }
.lg-input:disabled { opacity: .6; }
.lg-pw { padding-right: 76px; }
.lg-toggle { position: absolute; top: 0; right: 0; bottom: 0; padding: 0 16px; background: none; border: 0; color: #8a9bff; font: 600 15px Manrope, sans-serif; cursor: pointer; }
.lg-toggle:hover { color: #a3b1ff; }
.lg-toggle:focus-visible { outline: 3px solid #3be8b8; outline-offset: -3px; border-radius: 12px; }
.lg-err { min-height: 22px; margin: 16px 0 0; font-size: 15px; color: #ff6b7a; }
.lg-submit { width: 100%; margin-top: 8px; }
.lg-submit:disabled { opacity: .55; cursor: default; }
`

export default function Login({ onLogin = notConnected, onSuccess, onBack }) {
  const uid = useId()
  const userId = `${uid}-username`
  const passId = `${uid}-password`
  const errId = `${uid}-error`

  const starsA = useMemo(() => stars(46, '#c3cdf0', 7), [])
  const starsB = useMemo(() => stars(34, '#8a9bff', 11), [])

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [touched, setTouched] = useState({ username: false, password: false })

  const missingUser = touched.username && !username.trim()
  const missingPass = touched.password && !password

  async function submit(e) {
    e.preventDefault()
    if (busy) return
    setTouched({ username: true, password: true })
    if (!username.trim() || !password) {
      setError('Enter your username and password.')
      return
    }
    setError('')
    setBusy(true)
    try {
      const result = await onLogin({ username: username.trim(), password })
      onSuccess?.(result)
    } catch (err) {
      setError(err?.message || 'Could not sign in. Try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="lp">
      <style>{CSS}</style>

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
      </svg>

      <nav className="lp-nav">
        <div className="lp-brand">{BRAND}</div>
        {onBack && <button type="button" className="lp-btn lp-btn-sm lp-btn-ghost" onClick={onBack}>Back</button>}
      </nav>

      <main className="lg-wrap">
        <div className="lg-box lp-rise">
          <h1 className="lg-h1">Sign in</h1>
          <p className="lg-sub">Use your username and password to open the dashboard.</p>

          <form onSubmit={submit} noValidate>
            <label htmlFor={userId} className="lg-label">Username</label>
            <input
              id={userId}
              className="lg-input"
              type="text"
              name="username"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onBlur={() => setTouched((t) => ({ ...t, username: true }))}
              aria-invalid={missingUser}
              aria-describedby={error ? errId : undefined}
              disabled={busy}
            />

            <label htmlFor={passId} className="lg-label">Password</label>
            <div className="lg-field">
              <input
                id={passId}
                className="lg-input lg-pw"
                type={show ? 'text' : 'password'}
                name="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onBlur={() => setTouched((t) => ({ ...t, password: true }))}
                aria-invalid={missingPass}
                aria-describedby={error ? errId : undefined}
                disabled={busy}
              />
              <button type="button" className="lg-toggle" onClick={() => setShow((s) => !s)} aria-pressed={show}>
                {show ? 'Hide' : 'Show'}
              </button>
            </div>

            <p id={errId} className="lg-err" role="alert">{error}</p>

            <button type="submit" className="lp-btn lg-submit" disabled={busy}>
              {busy ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>
      </main>
    </div>
  )
}
