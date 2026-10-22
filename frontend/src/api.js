import mock from '@contracts/sample_response.json'

export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

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
