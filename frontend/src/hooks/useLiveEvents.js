import { useCallback, useEffect, useRef, useState } from 'react'
import { USE_MOCK, getEventByVersion, getLiveEvents, getLiveStatus } from '../api'

const EVERY_MS = 8_000

/**
 * Polls the live monitor. region: 'india' | 'global' | 'all'.
 * `history` is filtered by region; `latest` is set only when a NEW event (newer than anything
 * seen so far) arrives in the selected region, so switching region never auto-loads an old event.
 */
export default function useLiveEvents(region = 'all') {
  const [status, setStatus] = useState(null)
  const [history, setHistory] = useState([])
  const [latest, setLatest] = useState(null)
  const [error, setError] = useState(null)
  const lastSeen = useRef(null)
  const alive = useRef(true)

  const refresh = useCallback(async () => {
    if (USE_MOCK) return
    try {
      const [st, hist] = await Promise.all([getLiveStatus(), getLiveEvents(region)])
      if (!alive.current) return
      setStatus(st)
      setHistory(hist)
      setError(null)
      if (lastSeen.current === null) {
        lastSeen.current = st.version                       // baseline: don't auto-load what already existed
      } else if (st.version > lastSeen.current) {
        lastSeen.current = st.version
        if (region === 'all' || st.latest_region === region) {
          const ev = await getEventByVersion(st.version)
          if (alive.current) setLatest(ev)
        }
      }
    } catch {
      if (alive.current) setError('Live monitor is offline. Start the backend to enable it.')
    }
  }, [region])

  useEffect(() => {
    alive.current = true
    refresh()
    const id = setInterval(refresh, EVERY_MS)
    return () => { alive.current = false; clearInterval(id) }
  }, [refresh])

  return { status, history, latest, error, refresh }
}
