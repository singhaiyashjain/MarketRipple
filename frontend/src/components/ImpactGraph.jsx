import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import cytoscape from 'cytoscape'
import dagre from 'cytoscape-dagre'
import { toElements } from '../lib/graphElements'
import { graphStyle } from '../lib/graphStyle'
import { EVIDENCE_LABEL, fmt, signWord } from '../lib/format'

let dagreRegistered = false
if (!dagreRegistered) {
  cytoscape.use(dagre)
  dagreRegistered = true
}

const LAYOUT = { name: 'dagre', rankDir: 'LR', nodeSep: 28, rankSep: 90, animate: false, padding: 40 }

/** Imperative handle: fit(), relayout(), exportPng(). Highlight priority: path > node neighbourhood > edge. */
const ImpactGraph = forwardRef(function ImpactGraph({ data, selectedPath, selection, onSelect, filters, revealOrder = null }, ref) {
  const box = useRef(null)
  const cyRef = useRef(null)
  const [tip, setTip] = useState(null)
  const onSelectRef = useRef(onSelect)
  onSelectRef.current = onSelect

  useImperativeHandle(ref, () => ({
    fit: () => cyRef.current?.fit(undefined, 40),
    relayout: () => { cyRef.current?.elements().not('.hide').layout(LAYOUT).run(); cyRef.current?.fit(undefined, 40) },
    exportPng: () => {
      const cy = cyRef.current
      if (!cy) return
      const a = document.createElement('a')
      a.href = cy.png({ full: true, scale: 2, bg: '#f7f9fb' })
      a.download = 'finpulse-impact-graph.png'
      a.click()
    },
  }))

  // build graph when data changes
  useEffect(() => {
    if (!data || !box.current) return undefined
    const cy = cytoscape({
      container: box.current,
      elements: toElements(data),
      style: graphStyle,
      layout: LAYOUT,
      minZoom: 0.3,
      maxZoom: 2.5,
      wheelSensitivity: 0.25,
    })
    cy.on('tap', 'node', (e) => onSelectRef.current({ kind: 'node', id: e.target.id() }))
    cy.on('tap', 'edge', (e) => onSelectRef.current({ kind: 'edge', id: e.target.id() }))
    cy.on('tap', (e) => { if (e.target === cy) onSelectRef.current(null) })
    cy.on('mouseover', 'node, edge', (e) => {
      const t = e.target
      const p = e.renderedPosition || t.renderedPosition()
      if (t.isNode()) {
        const n = data.nodes.find((x) => x.id === t.id())
        setTip({ x: p.x, y: p.y, title: n.label, body: [n.sector, n.type].filter(Boolean).join(' · ') })
      } else {
        const ed = data.edges.find((x) => x.id === t.id())
        setTip({ x: p.x, y: p.y, title: ed.relationship.replaceAll('_', ' '),
          body: `${EVIDENCE_LABEL[ed.evidence_type]} · weight ${fmt(ed.weight)} · ${signWord(ed.sign)}` })
      }
    })
    cy.on('mouseout', 'node, edge', () => setTip(null))
    cy.on('viewport', () => setTip(null))
    cyRef.current = cy

    const ro = new ResizeObserver(() => { cy.resize(); cy.fit(undefined, 40) })
    ro.observe(box.current)
    return () => { ro.disconnect(); cy.destroy(); cyRef.current = null }
  }, [data])

  // filters -> hide edges/nodes, re-layout visible part
  useEffect(() => {
    const cy = cyRef.current
    if (!cy || !data) return
    cy.batch(() => {
      cy.elements().removeClass('hide')
      cy.edges().forEach((e) => {
        if (e.data('weight') < filters.minWeight || (!filters.showInferred && e.data('inferred') === 1)) e.addClass('hide')
      })
      cy.nodes().forEach((n) => {
        if (n.data('type') !== 'event' && n.connectedEdges().not('.hide').length === 0) n.addClass('hide')
      })
    })
    cy.elements().not('.hide').layout(LAYOUT).run()
    cy.fit(undefined, 40)
  }, [data, filters])

  // ripple: show only nodes/edges up to `revealOrder` hops from the event (null = whole graph).
  // Layout positions stay fixed (nodes are only hidden), so the graph doesn't jump while it plays.
  useEffect(() => {
    const cy = cyRef.current
    const orders = data?.meta?.graph_analysis?.orders
    if (!cy || !data) return
    cy.batch(() => {
      cy.elements().removeClass('future')
      if (revealOrder === null || revealOrder === undefined || !orders) return
      const ord = (id) => orders[id] ?? 0
      cy.nodes().forEach((n) => { if (ord(n.id()) > revealOrder) n.addClass('future') })
      cy.edges().forEach((e) => { if (ord(e.target().id()) > revealOrder || ord(e.source().id()) > revealOrder) e.addClass('future') })
    })
  }, [data, revealOrder, filters])

  // highlight
  useEffect(() => {
    const cy = cyRef.current
    if (!cy || !data) return
    cy.batch(() => {
      cy.elements().removeClass('dim hl sel')
      let keep = null
      const path = data.paths.find((p) => p.id === selectedPath)
      if (path) {
        keep = cy.collection()
        path.node_ids.forEach((id) => { keep = keep.union(cy.getElementById(id)) })
        path.edge_ids.forEach((id) => { keep = keep.union(cy.getElementById(id)) })
        keep.addClass('hl')
      } else if (selection?.kind === 'node') {
        const n = cy.getElementById(selection.id)
        keep = n.closedNeighborhood()
        n.connectedEdges().addClass('hl')
      } else if (selection?.kind === 'edge') {
        const e = cy.getElementById(selection.id)
        keep = e.union(e.connectedNodes())
        e.addClass('hl')
      }
      if (keep) cy.elements().not(keep).addClass('dim')
      if (selection) cy.getElementById(selection.id).addClass('sel')
    })
  }, [data, selectedPath, selection, filters])

  return (
    <div className="relative h-full w-full">
      <div ref={box} className="absolute inset-0" role="img" aria-label="Impact graph of the analysed event" />
      {tip && (
        <div className="absolute z-10 pointer-events-none rounded-md bg-ink text-white text-xs px-2 py-1 shadow-lg max-w-[260px]"
          style={{ left: Math.min(tip.x + 12, (box.current?.clientWidth ?? 600) - 270), top: tip.y + 12 }}>
          <div className="font-semibold">{tip.title}</div>
          <div className="text-white/70">{tip.body}</div>
        </div>
      )}
    </div>
  )
})

export default ImpactGraph
