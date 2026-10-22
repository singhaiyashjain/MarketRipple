import { useCallback, useEffect, useRef, useState } from 'react'
import { USE_MOCK, getRecurrence } from '../api'

const EVERY_MS = 8_000

/** Polls /api/recurrence. `nodes[id].level` is 'alert' | 'watch' | 'none' for every star that was in the news recently. */
export default function useRecurrence({ windowDays, includeSimulated = true, refreshKey } = {}) {
  const [state, setState] = useState({ nodes: {}, alerts: [], watch: [], thresholds: { alert_hits: 3, watch_hits: 2 }, window_days: 7, events_in_window: 0 })
  const [error, setError] = useState(null)
  const alive = useRef(true)

  const refresh = useCallback(async () => {
    if (USE_MOCK) return
    try {
      const res = await getRecurrence({ windowDays, includeSimulated })
      if (alive.current) { setState(res); setError(null) }
    } catch {
      if (alive.current) setError('Recurring-news alerts are offline.')
    }
  }, [windowDays, includeSimulated])

  useEffect(() => {
    alive.current = true
    refresh()
    const id = setInterval(refresh, EVERY_MS)
    return () => { alive.current = false; clearInterval(id) }
  }, [refresh, refreshKey])

  return { ...state, error, refresh }
}
