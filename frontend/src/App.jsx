import { useCallback, useEffect, useRef, useState } from 'react'
import { clearRecurrence, fireNext, getEventByVersion, getSamples, pollNow, setReplay } from './api'
import useAnalysis from './hooks/useAnalysis'
import useHeadlines from './hooks/useHeadlines'
import useLiveEvents from './hooks/useLiveEvents'
import useRecurrence from './hooks/useRecurrence'
import Header from './components/Header'
import HeadlineTicker from './components/HeadlineTicker'
import LivePanel from './components/LivePanel'
import NewsFeedPanel from './components/NewsFeedPanel'
import NewsInput from './components/NewsInput'
import EventSummary from './components/EventSummary'
import PathList from './components/PathList'
import ImpactGraph from './components/ImpactGraph3D'
import GraphToolbar from './components/GraphToolbar'
import RippleBar from './components/RippleBar'
import EvidencePanel from './components/EvidencePanel'
import SectorTable from './components/SectorTable'
import Legend from './components/Legend'
import HierarchyPanel from './components/HierarchyPanel'
import InfluencePanel from './components/InfluencePanel'
import EmptyState from './components/EmptyState'
import RecurrencePanel from './components/RecurrencePanel'
import BacktestPanel from './components/BacktestPanel'
import Landing from './components/Landing'

const DEFAULT_FILTERS = { showInferred: true, minWeight: 0 }

function Dashboard() {
  const { data, loading, error, run, reset, load } = useAnalysis()
  const [region, setRegion] = useState('all')              // 'india' | 'global' | 'all'
  const headlines = useHeadlines(region)
  const live = useLiveEvents(region)

  // recurring-news alerts: stars with repeated negative news blink; their history is the "last 5 times" backtest
  const [recSettings, setRecSettings] = useState({ windowDays: 7, includeSimulated: true, autoOpen: false })
  const [focusStar, setFocusStar] = useState(null)         // star whose recurring-news backtest is shown
  const announced = useRef(new Set())                      // `${analysis}:${star}` already auto-opened

  const [samples, setSamples] = useState([])
  const [selectedPath, setSelectedPath] = useState(null)   // path id
  const [selection, setSelection] = useState(null)         // {kind:'node'|'edge', id}
  const [filters, setFilters] = useState(DEFAULT_FILTERS)
  const graph = useRef(null)

  // right panel: translucent overlay on the 3D area (~27% of the screen); `inset` = px of the canvas it covers
  const [panelOpen, setPanelOpen] = useState(true)
  const [inset, setInset] = useState(0)
  const rightRef = useRef(null)
  useEffect(() => {
    const el = rightRef.current
    if (!el) return undefined
    const measure = () => setInset(panelOpen && getComputedStyle(el).position === 'absolute' ? el.offsetWidth : 0)
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    window.addEventListener('resize', measure)
    return () => { ro.disconnect(); window.removeEventListener('resize', measure) }
  }, [panelOpen])

  // live monitor state
  const [autoUpdate, setAutoUpdate] = useState(true)
  const [pending, setPending] = useState(null)             // new event waiting when auto-update is off
  const [injected, setInjected] = useState(null)           // text pushed into the input box
  const [activeVersion, setActiveVersion] = useState(null)
  const [revealOrder, setRevealOrder] = useState(null)     // ripple: null = whole graph
  const [rippleKey, setRippleKey] = useState(null)         // changes => ripple replays
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [unmapped, setUnmapped] = useState(null)         // real story the graph has no path for (never show the sample)
  const bootLoaded = useRef(false)                        // first live event shown automatically on startup
  const regionPending = useRef(false)                     // after a region switch, show that region's latest event
  const appliedVersion = useRef(0)

  useEffect(() => { getSamples().then(setSamples) }, [])
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') { setSelection(null); setSelectedPath(null) } }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const rec = useRecurrence({ windowDays: recSettings.windowDays, includeSimulated: recSettings.includeSimulated, refreshKey: live.status?.version })
  const analysis = data?.meta?.graph_analysis
  const visibleIds = new Set((data?.nodes ?? []).map((n) => n.id))
  const selectNode = (id) => { setSelectedPath(null); setSelection({ kind: 'node', id }) }
  const clear = () => { setSelection(null); setSelectedPath(null) }

  const showHistory = (id) => {
    setFocusStar(id)
    setPanelOpen(true)
    setTimeout(() => document.getElementById('backtest-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 350)
  }
  const clearRecurring = async () => {
    if (!window.confirm('Clear the recurring-news history (all stored events used for the blinking alerts)?')) return
    try { await clearRecurrence() } catch { setNotice('Could not clear the history.') }
    setFocusStar(null)
    rec.refresh()
  }

  // a star that is blinking opens by itself: fly to it and show its card (once per analysis and star)
  useEffect(() => {
    if (!recSettings.autoOpen || !data || loading || selection || selectedPath) return undefined
    const aid = data.meta?.analysis_id ?? `${data.event?.entity}|${data.event?.change}`
    const orders = data.meta?.graph_analysis?.orders
    const ids = new Set(data.nodes.map((n) => n.id))
    const cand = rec.alerts.find((id) => ids.has(id) && !announced.current.has(`${aid}:${id}`)
      && (revealOrder === null || revealOrder === undefined || (orders?.[id] ?? 0) <= revealOrder))
    if (!cand) return undefined
    const tm = setTimeout(() => { announced.current.add(`${aid}:${cand}`); selectNode(cand) }, 1800)
    return () => clearTimeout(tm)
  }, [recSettings.autoOpen, data, loading, selection, selectedPath, rec.alerts, revealOrder]) // eslint-disable-line react-hooks/exhaustive-deps

  /** Show an auto-detected event: fill the input, swap the graph, replay the ripple. */
  const applyEvent = useCallback((ev) => {
    appliedVersion.current = ev.version
    setSelection(null)
    setSelectedPath(null)
    setFilters(DEFAULT_FILTERS)
    load(ev.analysis)
    setInjected({ key: `live-${ev.version}`, text: ev.text, simulated: !!ev.simulated,
      label: ev.simulated ? 'Replay (simulated)' : (ev.sources ?? []).join(', ') })
    setActiveVersion(ev.version)
    setPending(null)
    setNotice('')
    setUnmapped(null)
    setRevealOrder(0)
    setRippleKey(ev.version)
  }, [load])

  // a new event arrived from the server
  useEffect(() => {
    const ev = live.latest
    if (!ev || ev.version === appliedVersion.current) return
    if (autoUpdate) applyEvent(ev)
    else setPending(ev)
  }, [live.latest, autoUpdate, applyEvent])

  // manual analysis (button, sample, or a clicked headline) = normal full-graph view
  const onRun = async (news, simulated) => {
    clear()
    setFilters(DEFAULT_FILTERS)
    setRevealOrder(null)
    setRippleKey(null)
    setActiveVersion(null)
    setUnmapped(null)
    const res = await run(news, simulated)
    if (res?.meta?.unmapped) {                           // real story, but no path in the graph: don't show the canned sample
      reset()
      setUnmapped({ text: news.slice(0, 180) })
    }
  }
  const onReset = () => { clear(); setRevealOrder(null); setRippleKey(null); setActiveVersion(null); setUnmapped(null); reset() }

  const onAnalyzeHeadline = (h) => {
    const text = [h.title, h.summary].filter(Boolean).join('. ').slice(0, 1500)
    setInjected({ key: `hl-${Date.now()}`, text, simulated: false, label: h.source })
    onRun(text, false)
  }

  const onLoadEvent = async (item) => {
    try {
      const ev = item.analysis ? item : await getEventByVersion(item.version)
      applyEvent(ev)
    } catch {
      setNotice('That event has aged out of the history.')
    }
  }

  // startup: show the latest REAL detected event instead of an empty/sample screen
  useEffect(() => {
    if (bootLoaded.current || data || loading || live.history.length === 0) return
    const first = live.history.find((e) => e.kind === 'live')
    if (!first) return
    bootLoaded.current = true
    onLoadEvent(first)
  }, [live.history, data, loading]) // eslint-disable-line react-hooks/exhaustive-deps

  // switching India / Global / All: show the newest event of that region
  const changeRegion = (r) => { if (r !== region) { regionPending.current = true; setRegion(r) } }
  useEffect(() => {
    if (!regionPending.current) return
    regionPending.current = false
    const first = live.history.find((e) => e.kind === 'live') ?? live.history[0]
    if (first) onLoadEvent(first)
  }, [live.history]) // eslint-disable-line react-hooks/exhaustive-deps

  const onPoll = async () => {
    setBusy(true)
    try { await pollNow() } catch { setNotice('Could not reach the live monitor.') }
    await Promise.all([live.refresh(), headlines.refresh()])
    setBusy(false)
  }

  const onFire = async () => {
    setBusy(true)
    try { await fireNext() } catch { setNotice('Could not reach the live monitor.') }
    await live.refresh()
    setBusy(false)
  }

  const onReplay = async (enabled) => {
    setBusy(true)
    try {
      await setReplay(enabled)
      setTimeout(live.refresh, 1500)       // first replayed event arrives right after the loop wakes
    } catch { setNotice('Could not switch replay mode.') }
    setBusy(false)
  }

  return (
    <div className="h-full flex flex-col">
      <Header mode={data?.mode} warnings={data?.warnings ?? []} hasData={!!data} onReset={onReset} />
      <HeadlineTicker items={headlines.items} feeds={headlines.feeds} stale={headlines.stale}
        loading={headlines.loading} error={headlines.error} onAnalyze={onAnalyzeHeadline}
        showRegion={region === 'all'} />
      <main className="rp-vars relative flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-[var(--lp-w)_minmax(0,1fr)] overflow-y-auto lg:overflow-hidden">
        <aside className="lg:border-r border-line p-4 space-y-5 lg:overflow-y-auto panel-scroll bg-paper text-[1.02em]">
          <LivePanel status={live.status} history={live.history} error={live.error}
            autoUpdate={autoUpdate} onAutoUpdate={setAutoUpdate}
            pending={pending} onLoadPending={() => pending && applyEvent(pending)}
            onLoadEvent={onLoadEvent} onPoll={onPoll} onReplay={onReplay} onFire={onFire}
            busy={busy} activeVersion={activeVersion} notice={notice}
            region={region} onRegion={changeRegion} />
          <RecurrencePanel rec={rec} settings={recSettings} onSettings={setRecSettings} visibleIds={visibleIds}
            onSelectStar={selectNode} onHistory={showHistory} onClear={clearRecurring} />
          <NewsFeedPanel items={headlines.items} region={region} loading={headlines.loading} error={headlines.error}
            stale={headlines.stale} counts={headlines.counts} onAnalyze={onAnalyzeHeadline} onLoadEvent={onLoadEvent}
            onRefresh={headlines.refresh} activeVersion={activeVersion} />
          <NewsInput samples={samples} onRun={onRun} loading={loading} injected={injected} />
          {error && (
            <div role="alert" className="rounded-lg border border-loss/30 bg-loss/5 text-loss text-sm p-2">{error}</div>
          )}
          {unmapped && (
            <div role="status" className="rounded-lg border border-warn/40 bg-warn/5 text-sm p-2.5 space-y-1 reveal">
              <div className="font-semibold text-warn">This story is not mapped to the impact graph</div>
              <p className="text-ink/80 text-xs leading-snug">“{unmapped.text}”</p>
              <p className="text-mute text-xs leading-snug">
                The graph covers oil, interest-rate, rupee/FX and related moves. Showing no graph rather than a sample.
                Pick a story marked “Impact ready”, or add an LLM key in <code>.env</code> so more stories can be analysed.
              </p>
            </div>
          )}
          <EventSummary event={data?.event} />
          <PathList data={data} selected={selectedPath}
            onSelect={(id) => { setSelectedPath(id); setSelection(null) }} />
        </aside>

        <section className="relative canvas-grid h-[62vh] lg:h-auto min-h-[360px]" aria-label="Impact graph">
          {data && !loading ? (
            <>
              <ImpactGraph ref={graph} data={data} selectedPath={selectedPath} selection={selection}
                onSelect={setSelection} filters={filters} revealOrder={revealOrder} insetRight={inset}
                signals={rec.nodes} onHistory={showHistory} />
              {/* controls sit in the clear part of the 3D area, left of the translucent right panel */}
              <div className="pointer-events-none absolute inset-y-0 left-0 z-10 transition-[right] duration-500 ease-in-out" style={{ right: inset }}>
                <div className="absolute top-3 left-3 right-3 flex flex-col items-end gap-2">
                  <GraphToolbar filters={filters} setFilters={setFilters}
                    onFit={() => graph.current?.fit()} onRelayout={() => graph.current?.relayout()}
                    onExport={() => graph.current?.exportPng()} />
                  <Legend />
                </div>
                <RippleBar orders={analysis?.orders} order={revealOrder} setOrder={setRevealOrder} playKey={rippleKey} />
              </div>
            </>
          ) : <EmptyState loading={loading} />}
        </section>

        <button type="button" onClick={() => setPanelOpen((o) => !o)} aria-expanded={panelOpen}
          aria-label={panelOpen ? 'Hide details panel' : 'Show details panel'}
          className="hidden lg:flex absolute z-40 top-1/2 -translate-y-1/2 glass !rounded-r-none items-center gap-1 px-2 py-4 text-xs font-semibold text-accent hover:text-white transition-[right] duration-500 ease-in-out [writing-mode:vertical-rl]"
          style={{ right: panelOpen ? 'var(--rp-w)' : 0 }}>
          {panelOpen ? 'Hide details ›' : '‹ Details'}
        </button>

        <aside ref={rightRef} aria-label="Details"
          className={`rp panel-scroll p-4 lg:absolute lg:inset-y-0 lg:right-0 lg:z-30 lg:w-[var(--rp-w)] lg:overflow-y-auto lg:transition-transform lg:duration-500 lg:ease-in-out ${panelOpen ? '' : 'lg:translate-x-full'}`}>
          <div className="rp-cols">
          <EvidencePanel data={data} selection={selection} selectedPath={selectedPath}
            onSelect={setSelection} onSelectPath={(id) => { setSelectedPath(id); setSelection(null) }} />
          <SectorTable sectors={data?.sectors} />
          <BacktestPanel data={data} focusStar={focusStar} focusLabel={rec.nodes?.[focusStar]?.label} onClearFocus={() => setFocusStar(null)}
            windowDays={recSettings.windowDays} includeSimulated={recSettings.includeSimulated} />
          <HierarchyPanel analysis={analysis} onSelectNode={selectNode} visibleIds={visibleIds} />
          <InfluencePanel analysis={analysis} onSelectNode={selectNode} visibleIds={visibleIds} />
          {!data && <p className="text-xs text-mute">Scores here are relative path strengths under defined scoring rules. They are not probabilities or predictions.</p>}
          </div>
        </aside>
      </main>
    </div>
  )
}

// Landing page first; "Launch app" / "Analyze an event" opens the dashboard above.
export default function App() {
  const [showLanding, setShowLanding] = useState(true)
  return showLanding ? <Landing onLaunch={() => setShowLanding(false)} /> : <Dashboard />
}
