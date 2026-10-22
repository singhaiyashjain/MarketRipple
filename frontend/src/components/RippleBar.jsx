import { useEffect, useRef, useState } from 'react'

const STEP_MS = 900

/**
 * Ripple controls: step the graph outward hop by hop from the event.
 * order === null means the whole graph is shown. `playKey` changing replays from the start.
 */
export default function RippleBar({ orders, order, setOrder, playKey }) {
  const max = orders ? Math.max(0, ...Object.values(orders)) : 0
  const [playing, setPlaying] = useState(false)
  const orderRef = useRef(order)
  orderRef.current = order

  // a new live event => replay the ripple from the event node
  useEffect(() => { if (playKey !== null && playKey !== undefined && max > 0) { setOrder(0); setPlaying(true) } }, [playKey]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!playing) return undefined
    const id = setInterval(() => {
      const cur = orderRef.current ?? 0
      if (cur >= max) { setPlaying(false); setOrder(null); return }
      setOrder(cur + 1)
    }, STEP_MS)
    return () => clearInterval(id)
  }, [playing, max, setOrder])

  if (!orders || max < 1) return null
  const shown = order === null || order === undefined ? max : order

  const play = () => { setOrder(0); setPlaying(true) }
  const stop = () => { setPlaying(false); setOrder(null) }

  return (
    <div className="pointer-events-auto glass absolute left-3 bottom-14 z-10 flex flex-wrap items-center gap-2 px-2.5 py-1.5 text-xs max-w-[calc(100%-1.5rem)]" role="group" aria-label="Ripple playback">
      <span className="section-title">Ripple</span>
      <button className="btn" onClick={playing ? () => setPlaying(false) : play}>{playing ? 'Pause' : 'Play'}</button>
      <input type="range" min={0} max={max} value={shown} aria-label="Hops from the event"
        onChange={(e) => { setPlaying(false); const v = Number(e.target.value); setOrder(v >= max ? null : v) }} />
      <span className="text-mute w-14 tabular-nums">{shown === 0 ? 'Event' : `${shown} hop${shown > 1 ? 's' : ''}`}</span>
      <button className="btn" onClick={stop} disabled={order === null || order === undefined}>Show all</button>
    </div>
  )
}
