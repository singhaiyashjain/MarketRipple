import { useCallback, useRef, useState } from 'react'
import { USE_MOCK, analyze } from '../api'

/** Request lifecycle for /analyze: data, loading, error; newer runs abort older ones. */
export default function useAnalysis() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const ctrl = useRef(null)

  const run = useCallback(async (news, simulated) => {
    ctrl.current?.abort()
    ctrl.current = new AbortController()
    setLoading(true)
    setError(null)
    try {
      const res = await analyze(news, simulated, ctrl.current.signal)
      // The backend answers with a canned "Sample data" graph when it cannot map a REAL story. Never show that
      // as if it were the story's analysis: keep the current graph and explain why instead.
      // Real story the graph can't map: never show it, even when "simulated" is ticked.
      if (res.meta?.unmapped && !USE_MOCK) {
        setError(null)
        return res
      }
      if (res.mode === 'mock' && !simulated && !USE_MOCK) {
        const why = (res.warnings?.[0] ?? '').replace(/^Mock data:\s*/i, '').trim()
        setError("Couldn't map this story to the impact graph, so no sample graph is shown. "
          + 'Pick a story about oil, RBI/Fed rates or the rupee, or add an LLM key in .env to analyse any headline.'
          + (why ? ` (${why.slice(0, 160)})` : ''))
        return null
      }
      setData(res)
      return res
    } catch (e) {
      if (e.name !== 'AbortError') {
        setError(
          e instanceof TypeError
            ? 'Cannot reach the API. Start the backend (uvicorn app.main:app --reload) or run with VITE_USE_MOCK=true.'
            : e.message,
        )
      }
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  /** Show an already-computed analysis (e.g. an auto-detected live event) without calling the API. */
  const load = useCallback((res) => { ctrl.current?.abort(); setData(res); setError(null); setLoading(false) }, [])

  const reset = useCallback(() => { ctrl.current?.abort(); setData(null); setError(null); setLoading(false) }, [])

  return { data, loading, error, run, reset, load }
}
