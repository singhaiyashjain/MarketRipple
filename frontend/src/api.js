import mock from '@contracts/sample_response.json'

export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

// Backend address. Empty = same site (local dev uses the Vite proxy). On GitHub Pages set VITE_API_URL to the Render URL.
const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')

// ---------------------------------------------------------------- login session (token kept for this browser tab only)
const TOKEN_KEY = 'mr_token'
let memToken = ''
export const getToken = () => { try { return sessionStorage.getItem(TOKEN_KEY) || memToken } catch { return memToken } }
export const setToken = (t) => {
  memToken = t || ''
  try { t ? sessionStorage.setItem(TOKEN_KEY, t) : sessionStorage.removeItem(TOKEN_KEY) } catch { /* storage blocked: memory only */ }
}

// every call goes through here, so the login token is attached in one place
let onUnauthorized = null
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn }
const fetch = async (url, opts = {}) => {
  const token = getToken()
  const headers = token ? { ...(opts.headers || {}), Authorization: `Bearer ${token}` } : opts.headers
  const r = await window.fetch(API_BASE + url, { ...opts, headers })
  if (r.status === 401 && token && !url.startsWith('/api/auth/login')) onUnauthorized?.()   // token expired or account disabled
  return r
}

async function authJson(url, method, body) {
  const r = await fetch(url, { method, headers: body ? { 'Content-Type': 'application/json' } : undefined, body: body ? JSON.stringify(body) : undefined })
  let data = null
  try { data = await r.json() } catch { /* no body */ }
  if (!r.ok) {
    const d = data?.detail
    throw new Error(typeof d === 'string' ? d : Array.isArray(d) ? d.map((x) => x.msg).join(' ') : `Server error ${r.status}`)
  }
  return data
}

// Mock mode (VITE_USE_MOCK=true, no backend) keeps a demo account so the UI can still be previewed.
const MOCK_USER = { username: 'demo', role: 'admin', active: true }
export async function login(username, password) {
  if (USE_MOCK) {
    if (username !== 'demo' || password !== 'marketripple') throw new Error('Wrong username or password.')
    return { token: '', user: MOCK_USER }
  }
  const out = await authJson('/api/auth/login', 'POST', { username, password })
  setToken(out.token)
  return out
}
export const logout = () => setToken('')
export const getMe = () => (USE_MOCK ? Promise.resolve(MOCK_USER) : authJson('/api/auth/me', 'GET'))
export const changePassword = (current_password, new_password) =>
  authJson('/api/auth/change-password', 'POST', { current_password, new_password })

// ---------------------------------------------------------------- admin panel
export const adminListUsers = () => authJson('/api/admin/users', 'GET')
export const adminCreateUser = (username, password, role) => authJson('/api/admin/users', 'POST', { username, password, role })
export const adminUpdateUser = (username, patch) => authJson(`/api/admin/users/${encodeURIComponent(username)}`, 'PATCH', patch)
export const adminDeleteUser = (username) => authJson(`/api/admin/users/${encodeURIComponent(username)}`, 'DELETE')

const MOCK_SAMPLES = [
  { id: 'oil_shock', title: 'Crude oil +12% (simulated)', simulated: true,
    news: 'Crude oil prices surge by 12% amid escalating geopolitical tensions in the Middle East, raising concerns about supply disruptions.' },
  { id: 'rate_hike', title: 'RBI rate hike (simulated)', simulated: true,
    news: 'The Reserve Bank of India raises its policy repo rate by 25 basis points to curb persistent inflation, citing elevated food and fuel prices.' },
  { id: 'inr_depreciation', title: 'Rupee depreciation (simulated)', simulated: true,
    news: 'The Indian rupee falls sharply to a record low against the US dollar as foreign investors pull money out of domestic equities.' },
]

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

export async function analyze(news, simulated = false, signal) {
  if (USE_MOCK) {
    await sleep(500)
    return structuredClone(mock)
  }
  const r = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ news, simulated }),
    signal,
  })
  if (!r.ok) {
    let detail = ''
    try { detail = (await r.json()).detail } catch { /* ignore */ }
    throw new Error(detail ? `Server error ${r.status}: ${JSON.stringify(detail)}` : `Server error ${r.status}`)
  }
  return r.json()
}

export async function getSamples() {
  if (USE_MOCK) return MOCK_SAMPLES
  try {
    const r = await fetch('/api/samples')
    return r.ok ? await r.json() : MOCK_SAMPLES
  } catch {
    return MOCK_SAMPLES
  }
}

// ---------------------------------------------------------------- live monitor
async function jget(url) {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`Server error ${r.status}`)
  return r.json()
}
async function jpost(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!r.ok) throw new Error(`Server error ${r.status}`)
  return r.json()
}

/** region: 'india' | 'global' | 'all' */
export const getHeadlines = (region = 'all') => jget(`/api/headlines?region=${region}`)
export const getLiveStatus = () => jget('/api/live/status')
export const getLiveEvents = (region = 'all') => jget(`/api/live/events?region=${region}`)
export const getEventByVersion = (version) => jget(`/api/live/events/${version}`)
export const pollNow = () => jpost('/api/live/poll')
export const fireNext = () => jpost('/api/live/fire')
export const setReplay = (enabled) => jpost('/api/live/replay', { enabled })

// ---------------------------------------------------------------- recurring-news alerts + historical backtest
const EMPTY_RECURRENCE = { nodes: {}, alerts: [], watch: [], thresholds: { alert_hits: 3, watch_hits: 2 }, window_days: 7, events_in_window: 0 }

/** Per-star recurrence signals. level: 'alert' (blinks) | 'watch' | 'none'. */
export async function getRecurrence({ windowDays, includeSimulated = true } = {}) {
  if (USE_MOCK) return EMPTY_RECURRENCE
  const q = new URLSearchParams({ include_simulated: String(includeSimulated) })
  if (windowDays) q.set('window_days', String(windowDays))
  return jget(`/api/recurrence?${q}`)
}
export const clearRecurrence = (simulatedOnly = false) =>
  fetch(`/api/recurrence?simulated_only=${simulatedOnly}`, { method: 'DELETE' }).then((r) => r.json())

/** "The last 5 times this happened" for the shock that keeps hitting one star. */
export const getStarBacktest = (nodeId, { windowDays, includeSimulated = true } = {}) => {
  const q = new URLSearchParams({ include_simulated: String(includeSimulated) })
  if (windowDays) q.set('window_days', String(windowDays))
  return jget(`/api/recurrence/${encodeURIComponent(nodeId)}/backtest?${q}`)
}

/** Backtest for the current analysis. Prefers the saved id, falls back to sending the whole analysis. */
export async function getBacktest(analysis, signal) {
  if (USE_MOCK) return { available: false, reason: 'Backtest needs the backend (mock mode is on).' }
  const post = (body) => fetch('/api/backtest', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal })
  const id = analysis?.meta?.analysis_id
  let r = id != null ? await post({ analysis_id: id }) : null
  if (!r || r.status === 404) r = await post({ analysis })
  if (!r.ok) throw new Error(`Server error ${r.status}`)
  return r.json()
}
