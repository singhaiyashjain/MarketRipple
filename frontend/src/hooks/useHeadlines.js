import { useCallback, useEffect, useRef, useState } from 'react'
import { USE_MOCK, getHeadlines } from '../api'
import { isEnglish } from '../lib/english'

const EVERY_MS = 60_000

/** Headlines for the ticker. region: 'india' | 'global' | 'all'. English only. */
export default function useHeadlines(region = 'all') {
  const [state, setState] = useState({ items: [], feeds: {}, counts: null, stale: false, loading: true, error: null })
  const alive = useRef(true)

  const refresh = useCallback(async () => {
    if (USE_MOCK) { setState((s) => ({ ...s, loading: false })); return }
    try {
      const res = await getHeadlines(region)
      if (!alive.current) return
      setState({
        items: (res.items ?? []).filter((h) => isEnglish(h.title) && h.relevant !== false),
        feeds: res.feeds ?? {}, counts: res.counts ?? null, stale: !!res.stale, loading: false, error: null,
      })
    } catch {
      if (alive.current) setState((s) => ({ ...s, loading: false, error: 'Headlines unavailable' }))
    }
  }, [region])

  useEffect(() => {
    alive.current = true
    setState((s) => ({ ...s, loading: true }))
    refresh()
    const id = setInterval(refresh, EVERY_MS)
    return () => { alive.current = false; clearInterval(id) }
  }, [refresh])

  return { ...state, refresh }
}
