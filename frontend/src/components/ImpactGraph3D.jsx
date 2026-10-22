import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react'
import ForceGraph3D from '3d-force-graph'
import * as THREE from 'three'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'
import { EFFECT_COLOR, EVIDENCE_LABEL, fmt, signWord } from '../lib/format'
import { makeAlertRing, makeOrb, makeSpace, signSprite, signSprites } from '../lib/space'
import OrbCard from './OrbCard'

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))
const LINK_COLOR = { normal: '#8095ff', inferred: '#ffbf47', quant: '#3be8b8', dim: '#151d45', hl: '#c9d4ff' }
const baseLinkColor = (l) => (l.evidence_type === 'llm_inferred' ? LINK_COLOR.inferred : l.evidence_type === 'quant_verified' ? LINK_COLOR.quant : LINK_COLOR.normal)
const ALERT_COLOR = new THREE.Color('#ff3b4e')
const WATCH_COLOR = new THREE.Color('#ffbf47')
const idOf = (x) => (typeof x === 'object' ? x.id : x)

/**
 * 3D "constellation" view. Same props + imperative handle (fit / relayout / exportPng) as the old 2D ImpactGraph,
 * so App.jsx only swaps the component.
 */
const ImpactGraph3D = forwardRef(function ImpactGraph3D({ data, selectedPath, selection, onSelect, filters, revealOrder = null, insetRight = 0, signals = {}, onHistory = () => {} }, ref) {
  const box = useRef(null)
  const fg = useRef(null)
  const extras = useRef({})
  const [pov, setPov] = useState(false)
  const [spin, setSpin] = useState(true)
  const [ready, setReady] = useState(false)

  const onSelectRef = useRef(onSelect); onSelectRef.current = onSelect
  const live = useRef({}) // latest values for use inside long-lived callbacks
  live.current = { pov, spin, selection, selectedPath, data, revealOrder, signals }
  const view = useRef({ hlN: null, hlL: null, selId: null, povId: null })
  const nodes = useRef([])
  const prevSel = useRef(null)
  const cardRef = useRef(null)
  const glideRef = useRef(null)            // running camera tween (own easing, see glide())
  const cardPos = useRef({ el: null, x: 0, y: 0 })
  // insetRight = px of the 3D area covered by the translucent right panel; the scene is shifted to stay centred in the clear part
  const insetRef = useRef({ cur: insetRight, target: insetRight, applied: null })
  insetRef.current.target = insetRight

  const analysis = data?.meta?.graph_analysis
  const selNode = selection?.kind === 'node' ? data.nodes.find((n) => n.id === selection.id) : null

  // ---------- helpers (read refs, safe to call from anywhere) ----------
  const posOf = (n) => ({ x: n?.x ?? 0, y: n?.y ?? 0, z: n?.z ?? 0 })
  const byId = (id) => nodes.current.find((n) => n.id === id)

  // ripple: hide stars further than `revealOrder` hops from the event; hide the star we are looking out from in POV
  const nodeShown = (n) => {
    const { revealOrder: ro, data: d } = live.current
    if (view.current.povId === n.id) return false
    const orders = d?.meta?.graph_analysis?.orders
    if (ro === null || ro === undefined || !orders) return true
    return (orders[n.id] ?? 0) <= ro
  }
  const refreshLinks = () => {
    const g = fg.current
    if (!g) return
    g.linkColor(g.linkColor()); g.linkWidth(g.linkWidth()); g.linkDirectionalParticles(g.linkDirectionalParticles())
  }
  const applyView = () => {
    const g = fg.current
    if (!g) return
    const { hlN, selId } = view.current
    nodes.current.forEach((n) => {
      const o = n.__orb
      if (!o) return
      const on = !hlN || hlN.has(n.id)
      // targets only: the render loop eases opacity towards them so selecting a star fades instead of snapping
      o.tgt = { core: on ? 0.9 : 0.2, halo: on ? 0.32 : 0.05, glint: on ? 0.28 : 0.05 }
      o.labelTarget = on ? 1 : 0.3
      o.scaleTo = n.id === selId ? 1.25 : 1
    })
    refreshLinks()
    g.nodeVisibility(g.nodeVisibility()); g.linkVisibility(g.linkVisibility())
  }

  /** Smooth camera move: ease-in-out on position, look-at target and (optionally) field of view. */
  const glide = (pos, look, ms = 1600, fov) => {
    const g = fg.current
    if (!g) return
    const cam = g.camera(); const c = g.controls()
    glideRef.current = {
      start: performance.now(), dur: Math.max(1, ms),
      fromP: cam.position.clone(), toP: new THREE.Vector3(pos.x, pos.y, pos.z),
      fromT: c.target.clone(), toT: new THREE.Vector3(look.x, look.y, look.z),
      fromF: cam.fov, toF: fov ?? cam.fov,
    }
  }

  const flyTo = (p, dist = 80, ms = 1600) => {
    const g = fg.current
    if (!g) return
    const len = Math.hypot(p.x, p.y, p.z)
    const k = 1 + dist / (len || 1)
    const to = len < 1 ? { x: 0, y: 0, z: dist } : { x: p.x * k, y: p.y * k, z: p.z * k }
    glide(to, p, ms, extras.current.fov)
  }
  // own fit (the library's zoomToFit also counts the starfield, which throws the camera far away)
  const fit = (ms = 1200, pad = 0.72, filter) => {
    const g = fg.current
    if (!g) return
    const list = nodes.current.filter((n) => !filter || filter(n))
    if (!list.length) return
    const box0 = fg.current?.renderer().domElement
    const box = new THREE.Box3()
    list.forEach((n) => box.expandByPoint(new THREE.Vector3(n.x ?? 0, n.y ?? 0, n.z ?? 0)))
    const center = box.getCenter(new THREE.Vector3())
    const radius = Math.max(40, ...list.map((n) => center.distanceTo(new THREE.Vector3(n.x ?? 0, n.y ?? 0, n.z ?? 0)) + n.r * 2))
    const cam = g.camera()
    const vfov = THREE.MathUtils.degToRad(extras.current.fov ?? cam.fov)
    // aspect of the part of the canvas not covered by the right panel
    const clearAspect = Math.max(0.3, ((box0.clientWidth || 1) - insetRef.current.target) / (box0.clientHeight || 1))
    const hfov = 2 * Math.atan(Math.tan(vfov / 2) * clearAspect)
    const dist = (radius / Math.sin(Math.min(vfov, hfov) / 2)) * pad
    const dir = cam.position.clone().sub(g.controls().target)
    if (dir.length() < 1e-3) dir.set(0.25, 0.18, 1)
    dir.normalize()
    glide({ x: center.x + dir.x * dist, y: center.y + dir.y * dist, z: center.z + dir.z * dist }, center, ms, extras.current.fov)
  }

  const setLook = (povOn) => {
    const g = fg.current
    if (!g) return
    const c = g.controls()
    c.enableZoom = !povOn; c.enablePan = !povOn   // the field of view itself is eased by glide()
  }

  const enterPov = (n, ms = 1800) => {
    const g = fg.current
    if (!g || !n) return
    const p = posOf(n)
    const nb = (live.current.data?.edges ?? []).flatMap((e) => (e.source === n.id ? [e.target] : e.target === n.id ? [e.source] : []))
      .map(byId).filter(Boolean)
    const tgt = nb.length ? nb.reduce((a, m) => ({ x: a.x + (m.x ?? 0) / nb.length, y: a.y + (m.y ?? 0) / nb.length, z: a.z + (m.z ?? 0) / nb.length }), { x: 0, y: 0, z: 0 }) : { x: 0, y: 0, z: 0 }
    let d = new THREE.Vector3(tgt.x - p.x, tgt.y - p.y, tgt.z - p.z)
    if (d.length() < 1) d = new THREE.Vector3(0, 0, -1)
    d.normalize()
    view.current.povId = n.id
    applyView()
    setLook(true)
    glide(p, { x: p.x + d.x * 1.5, y: p.y + d.y * 1.5, z: p.z + d.z * 1.5 }, ms, 78)
  }

  useImperativeHandle(ref, () => ({
    fit: () => fit(),
    relayout: () => {
      nodes.current.forEach((n) => { if (n.type !== 'event') { n.fx = undefined; n.fy = undefined; n.fz = undefined } })
      fg.current?.d3ReheatSimulation()
      setTimeout(() => !live.current.selection && fit(1000), 1800)
    },
    exportPng: () => {
      const cv = fg.current?.renderer().domElement
      if (!cv) return
      const a = document.createElement('a')
      a.href = cv.toDataURL('image/png')
      a.download = 'finpulse-impact-graph.png'
      a.click()
    },
  }))

  // ---------- mount: create renderer, space, bloom, loop ----------
  useEffect(() => {
    const el = box.current
    const g = new ForceGraph3D(el, { controlType: 'orbit', rendererConfig: { antialias: true, preserveDrawingBuffer: true, powerPreference: 'high-performance' } })
    fg.current = g
    if (import.meta.env.DEV) window.__fg = { g, nodes }
    g.backgroundColor('#01020a').showNavInfo(false).enableNodeDrag(false)
      .width(el.clientWidth).height(el.clientHeight)
      .nodeThreeObject((n) => n.__orb?.group ?? makeOrb(n))
      .nodeLabel((n) => `<div class="orb-tip"><b>${esc(n.label)}</b><span>${esc([n.sector, n.type].filter(Boolean).join(' · '))}</span></div>`)
      .linkLabel((l) => `<div class="orb-tip"><b>${esc(l.relationship.replaceAll('_', ' '))}</b><span>${esc(EVIDENCE_LABEL[l.evidence_type])} · weight ${fmt(l.weight)} · ${esc(signWord(l.sign))}</span></div>`)
      .linkColor((l) => {
        const v = view.current
        if (!v.hlL) return baseLinkColor(l)
        return v.hlL.has(l.id) ? LINK_COLOR.hl : LINK_COLOR.dim
      })
      .nodeVisibility((n) => nodeShown(n))
      .linkVisibility((l) => nodeShown(typeof l.source === 'object' ? l.source : { id: l.source }) && nodeShown(typeof l.target === 'object' ? l.target : { id: l.target }))
      .linkOpacity(0.7)
      .linkResolution(5)
      .linkWidth((l) => {
        if (view.current.povId) return 0.12 + l.weight * 0.25 // links start at the camera in POV: keep them hair-thin
        return view.current.hlL?.has(l.id) ? 0.35 + l.weight * 0.7 : 0.25 + l.weight * 1.3
      })
      .linkDirectionalArrowLength((l) => (view.current.hlL && !view.current.hlL.has(l.id) ? 0 : 3.2))
      .linkDirectionalArrowRelPos(0.86)
      .linkDirectionalArrowColor((l) => (view.current.hlL?.has(l.id) ? '#ffffff' : baseLinkColor(l)))
      .linkDirectionalParticles((l) => {
        const h = view.current.hlL
        return h ? (h.has(l.id) ? 5 : 0) : 1 + Math.round(l.weight * 2)
      })
      .linkDirectionalParticleWidth((l) => (view.current.hlL?.has(l.id) ? 2.4 : 1.5))
      .linkDirectionalParticleSpeed((l) => 0.0016 + l.weight * 0.0034) // ~45% slower than before: calmer flow
      .linkDirectionalParticleColor((l) => (view.current.hlL?.has(l.id) ? '#ffffff' : baseLinkColor(l)))
      .linkThreeObjectExtend(true)
      .linkThreeObject((l) => signSprite(l.sign))
      .linkPositionUpdate((sprite, { start, end }) => {
        sprite.position.set((start.x + end.x) / 2, (start.y + end.y) / 2, (start.z + end.z) / 2)
        // returning falsy keeps the default line update
      })
      .onNodeClick((n) => onSelectRef.current({ kind: 'node', id: n.id }))
      .onLinkClick((l) => onSelectRef.current({ kind: 'edge', id: l.id }))
      .onBackgroundClick(() => onSelectRef.current(null))
      .onNodeHover((n) => { el.style.cursor = n ? 'pointer' : 'grab' })
      .onLinkHover((l) => { el.style.cursor = l ? 'pointer' : 'grab' })
      .warmupTicks(60)
      .cooldownTicks(260)
      .onEngineStop(() => {
        if (!extras.current.fitted) { extras.current.fitted = true; fit(1400) }
      })
    g.d3Force('charge').strength(-280)
    g.d3Force('link').distance((l) => 38 + (1 - l.weight) * 60)

    const c = g.controls()
    c.enableDamping = true; c.dampingFactor = 0.08; c.rotateSpeed = 0.7; c.zoomSpeed = 0.9
    c.autoRotate = true; c.autoRotateSpeed = 0.55; c.minDistance = 0.5; c.maxDistance = 3000
    extras.current.fov = g.camera().fov
    const stopGlide = () => { glideRef.current = null }
    c.addEventListener('start', stopGlide)

    const space = makeSpace()
    g.scene().add(space.group)
    const bloom = new UnrealBloomPass(new THREE.Vector2(el.clientWidth, el.clientHeight), 0.22, 0.4, 0.6)
    g.postProcessingComposer().addPass(bloom)

    // per-frame: twinkle, ring spin, label fade, scale easing
    let raf = 0
    const camPos = new THREE.Vector3()
    const tmp = new THREE.Vector3()
    const loop = (ms) => {
      const t = ms / 1000
      space.tick(t)
      const cam = g.camera()

      // camera glide (ease-in-out cubic)
      const gl = glideRef.current
      if (gl) {
        const k0 = THREE.MathUtils.clamp((performance.now() - gl.start) / gl.dur, 0, 1)
        const k = k0 < 0.5 ? 4 * k0 * k0 * k0 : 1 - Math.pow(-2 * k0 + 2, 3) / 2
        cam.position.lerpVectors(gl.fromP, gl.toP, k)
        g.controls().target.lerpVectors(gl.fromT, gl.toT, k)
        if (Math.abs(gl.toF - gl.fromF) > 0.01) { cam.fov = gl.fromF + (gl.toF - gl.fromF) * k; cam.updateProjectionMatrix() }
        if (k0 >= 1) glideRef.current = null
      }

      // shift the render centre away from the area covered by the right panel (eased, so opening/closing the panel is smooth)
      const ins = insetRef.current
      ins.cur += (ins.target - ins.cur) * 0.14
      if (Math.abs(ins.target - ins.cur) < 0.4) ins.cur = ins.target
      if (ins.cur !== ins.applied) {
        ins.applied = ins.cur
        if (ins.cur < 0.5) cam.clearViewOffset()
        else cam.setViewOffset(el.clientWidth, el.clientHeight, ins.cur / 2, 0, el.clientWidth, el.clientHeight)
      }

      cam.getWorldPosition(camPos)
      // world units covered by one screen pixel at distance 1: lets labels keep a constant on-screen size
      const pxUnit = (2 * Math.tan(THREE.MathUtils.degToRad(cam.fov) / 2)) / Math.max(1, el.clientHeight)
      nodes.current.forEach((n) => {
        const o = n.__orb
        if (!o) return
        o.scale += (o.scaleTo - o.scale) * 0.1
        // ease highlight / dim instead of snapping
        o.cur = o.cur ?? { core: 0.9, halo: 0.32, glint: 0.28 }
        const tg = o.tgt ?? o.cur
        o.cur.core += (tg.core - o.cur.core) * 0.1; o.core.material.opacity = o.cur.core
        o.cur.halo += (tg.halo - o.cur.halo) * 0.1; o.halo.material.opacity = o.cur.halo
        o.cur.glint += (tg.glint - o.cur.glint) * 0.1; o.glint.material.opacity = o.cur.glint
        o.labelOn += ((o.labelTarget ?? 1) - o.labelOn) * 0.1
        o.group.scale.setScalar(o.scale)
        const d = camPos.distanceTo(tmp.set(n.x ?? 0, n.y ?? 0, n.z ?? 0))
        const pulse = 1 + Math.sin(t * 1.8 + o.phase) * 0.06
        const near = THREE.MathUtils.clamp(d / 70, 0.3, 1) // keep halos from flooding the screen up close
        // recurring-news alert: the star blinks red (alert) or breathes amber (watch) so it cannot be missed
        const lvl = live.current.signals?.[n.id]?.level
        const warn = lvl === 'alert' || lvl === 'watch'
        let blinkScale = 1
        if (warn) {
          const alert = lvl === 'alert'
          const k = 0.5 + 0.5 * Math.sin(t * (alert ? 6.0 : 2.4))          // 0..1, ~1 blink per second for alerts
          const col = alert ? ALERT_COLOR : WATCH_COLOR
          o.core.material.color.copy(o.coreTint0).lerp(col, 0.3 + 0.7 * k)
          o.halo.material.color.copy(o.haloTint0).lerp(col, 0.55 + 0.45 * k)
          o.core.material.opacity = Math.min(1, o.cur.core + 0.1 + 0.2 * k)
          o.halo.material.opacity = Math.min(1, o.cur.halo + (alert ? 0.15 + 0.6 * k : 0.1 + 0.3 * k))
          blinkScale = 1 + k * (alert ? 0.9 : 0.35)
          if (!o.alertRing) { o.alertRing = makeAlertRing(); o.group.add(o.alertRing) }
          const ph = (t * (alert ? 0.9 : 0.5) + o.phase) % 1               // sonar ping: ring grows and fades
          o.alertRing.visible = true
          o.alertRing.material.color.copy(col)
          o.alertRing.material.opacity = (1 - ph) * (alert ? 0.85 : 0.5)
          o.alertRing.scale.setScalar(n.r * (3 + ph * (alert ? 11 : 7)) * near)
          o.warn = true
        } else if (o.warn) {                                                // alert cleared: restore the normal look
          o.core.material.color.copy(o.coreTint0); o.halo.material.color.copy(o.haloTint0)
          if (o.alertRing) o.alertRing.visible = false
          o.warn = false
        }
        o.halo.scale.setScalar(n.r * 4.2 * pulse * near * blinkScale * (o.scaleTo > 1 ? 1.2 : 1))
        o.glint.scale.setScalar(n.r * 2.4 * near)
        if (o.ring) o.ring.rotation.z = t * 0.5
        // labels keep a constant on-screen height (26px, event 32px) however far the camera is, never smaller than the close-up size
        const lhNow = Math.max(o.lh, (n.type === 'event' ? 32 : 26) * pxUnit * d)
        o.label.scale.set(lhNow * o.aspect, lhNow, 1)
        o.label.position.y = -(n.r * o.scale + lhNow * 0.58)
        o.label.material.opacity = o.labelOn
      })
      // +/- link signs: same idea, so they stay readable from a distance
      signSprites.forEach((sp) => {
        if (!sp.parent) { if (sp.userData.seen) signSprites.delete(sp); return }
        sp.userData.seen = true
        const sz = Math.max(4.5, 26 * pxUnit * camPos.distanceTo(sp.position))
        sp.scale.set(sz, sz, 1)
      })
      // popup: stays next to the clicked sphere while the camera moves (side panel in POV / on phones)
      const card = cardRef.current
      if (card) {
        const sid = view.current.selId
        const n = sid && !live.current.pov && el.clientWidth >= 640 ? nodes.current.find((x) => x.id === sid) : null
        if (n && n.x !== undefined) {
          const c = g.graph2ScreenCoords(n.x, n.y, n.z)
          const W = el.clientWidth - ins.cur, H = el.clientHeight, cw = card.offsetWidth, ch = card.offsetHeight
          let x = c.x + 30
          if (x + cw > W - 8) x = c.x - cw - 30
          const tx = THREE.MathUtils.clamp(x, 8, Math.max(8, W - cw - 8))
          const ty = THREE.MathUtils.clamp(c.y - 28, 56, Math.max(56, H - ch - 8))
          const cp = cardPos.current
          if (cp.el !== card) { cp.el = card; cp.x = tx; cp.y = ty }   // first frame: appear in place
          else { cp.x += (tx - cp.x) * 0.2; cp.y += (ty - cp.y) * 0.2 } // afterwards: glide, also when it flips sides
          card.style.left = `${cp.x}px`
          card.style.top = `${cp.y}px`
          card.style.right = 'auto'
        } else if (card.style.left) { card.style.left = ''; card.style.top = ''; card.style.right = ''; cardPos.current.el = null }
      }
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)

    // scroll = field-of-view zoom while looking from inside a star
    const onWheel = (e) => {
      if (!live.current.pov) return
      e.preventDefault()
      const cam = g.camera()
      cam.fov = THREE.MathUtils.clamp(cam.fov + e.deltaY * 0.04, 18, 100)
      cam.updateProjectionMatrix()
    }
    el.addEventListener('wheel', onWheel, { passive: false, capture: true })

    const ro = new ResizeObserver(() => { g.width(el.clientWidth).height(el.clientHeight); bloom.setSize(el.clientWidth, el.clientHeight); insetRef.current.applied = null })
    ro.observe(el)
    setReady(true)

    return () => {
      cancelAnimationFrame(raf); ro.disconnect(); c.removeEventListener('start', stopGlide); el.removeEventListener('wheel', onWheel, { capture: true })
      space.dispose()
      g.pauseAnimation(); g._destructor?.()
      while (el.firstChild) el.removeChild(el.firstChild)
      fg.current = null; nodes.current = []
      setReady(false)
    }
  }, [])

  // ---------- data -> nodes (built once per response) ----------
  const base = useMemo(() => {
    if (!data) return []
    const infl = Object.fromEntries((data.meta?.graph_analysis?.influence ?? []).map((x) => [x.id, x.score]))
    return data.nodes.map((n) => {
      const ev = n.type === 'event'
      const r = ev ? 6.5 : 2.6 + (infl[n.id] ?? 0.2) * 2.6 + (n.type === 'sector' ? 0.6 : 0)
      const node = { id: n.id, label: n.label, type: n.type, sector: n.sector, effect: n.effect, r, color: ev ? '#8a9bff' : EFFECT_COLOR[n.effect] ?? EFFECT_COLOR.unknown }
      if (ev) { node.fx = 0; node.fy = 0; node.fz = 0 }
      return node
    })
  }, [data])

  // ---------- data + filters -> graphData ----------
  useEffect(() => {
    const g = fg.current
    if (!g || !ready || !data) return
    const keepE = data.edges.filter((e) => e.weight >= filters.minWeight && (filters.showInferred || e.evidence_type !== 'llm_inferred'))
    const used = new Set(keepE.flatMap((e) => [e.source, e.target]))
    const ns = base.filter((n) => n.type === 'event' || used.has(n.id))
    const ids = new Set(ns.map((n) => n.id))
    nodes.current = ns
    if (extras.current.lastData !== data) { extras.current.lastData = data; extras.current.fitted = false }
    const links = keepE.filter((e) => ids.has(e.source) && ids.has(e.target)).map((e) => ({ ...e }))
    g.graphData({ nodes: ns, links })
    g.d3ReheatSimulation()
    applyView()
  }, [ready, base, filters, data])

  // ---------- selection -> highlight ----------
  useEffect(() => {
    if (!ready || !data) return
    const path = data.paths.find((p) => p.id === selectedPath)
    let hlN = null, hlL = null, selId = null
    if (path) { hlN = new Set(path.node_ids); hlL = new Set(path.edge_ids) }
    else if (selection?.kind === 'node') {
      const es = data.edges.filter((e) => e.source === selection.id || e.target === selection.id)
      hlL = new Set(es.map((e) => e.id)); hlN = new Set([selection.id, ...es.flatMap((e) => [e.source, e.target])]); selId = selection.id
    } else if (selection?.kind === 'edge') {
      const e = data.edges.find((x) => x.id === selection.id)
      if (e) { hlL = new Set([e.id]); hlN = new Set([e.source, e.target]) }
    }
    view.current = { hlN, hlL, selId, povId: pov && selId ? selId : null }
    applyView()
  }, [ready, data, selectedPath, selection, filters, pov])

  // ---------- selection -> camera ----------
  useEffect(() => {
    const g = fg.current
    if (!g || !ready || !data) return
    const path = data.paths.find((p) => p.id === selectedPath)
    const had = prevSel.current
    prevSel.current = selection || selectedPath
    const c = g.controls()
    if (selNode) {
      const n = byId(selNode.id)
      if (!n) return
      if (pov) enterPov(n)
      else { setLook(false); flyTo(posOf(n), 135) }
    } else {
      if (pov) setPov(false)
      setLook(false)
      if (selection?.kind === 'edge') {
        const e = data.edges.find((x) => x.id === selection.id)
        const a = byId(e?.source), b = byId(e?.target)
        if (a && b) flyTo({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, z: (a.z + b.z) / 2 }, 85)
      } else if (path) fit(1200, 1.25, (n) => path.node_ids.includes(n.id))
      else if (had) fit(1200)
    }
    if (!selNode && !pov && !glideRef.current && Math.abs(g.camera().fov - (extras.current.fov ?? 40)) > 0.1) {
      glide(g.camera().position, c.target, 700, extras.current.fov)   // ease the field of view back after leaving a star's POV
    }
    c.autoRotate = spin && !selection && !selectedPath
  }, [ready, selection, selectedPath, pov])

  useEffect(() => {
    const c = fg.current?.controls()
    if (c) c.autoRotate = spin && !selection && !selectedPath && !pov
  }, [spin, selection, selectedPath, pov, ready])

  // ripple step changed -> show/hide stars (positions stay fixed)
  useEffect(() => { if (ready) applyView() }, [ready, revealOrder])

  // leaving POV while a node is still selected -> return to orbit camera
  const exitPov = () => setPov(false)
  const zoomBy = (f) => {
    const g = fg.current
    if (!g) return
    if (pov) { const cam = g.camera(); cam.fov = THREE.MathUtils.clamp(cam.fov * f, 18, 100); cam.updateProjectionMatrix(); return }
    const c = g.controls(); const cam = g.camera()
    const v = cam.position.clone().sub(c.target).multiplyScalar(f)
    glide({ x: c.target.x + v.x, y: c.target.y + v.y, z: c.target.z + v.z }, c.target, 450, cam.fov)
  }

  const btn = 'btn !px-2.5 !py-1.5'
  return (
    <div className="relative h-full w-full overflow-hidden">
      <div ref={box} className="absolute inset-0 cursor-grab" role="img"
        aria-label="Interactive 3D constellation of the analysed event. Click a star for details." />

      {pov && (
        <div className="pointer-events-none absolute inset-0 z-10"
          style={{ background: 'radial-gradient(ellipse at center, transparent 55%, rgba(0,0,12,.75) 100%)' }} />
      )}

      {/* everything that floats over the 3D area lives in this frame, which stops where the translucent right panel starts */}
      <div className="pointer-events-none absolute inset-y-0 left-0 z-20 transition-[right] duration-500 ease-in-out" style={{ right: insetRight }}>
        {pov && (
          <>
            <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-14 h-14 rounded-full border border-white/25">
              <span className="absolute left-1/2 top-1/2 w-1 h-1 -ml-0.5 -mt-0.5 rounded-full bg-white/80" />
            </div>
            <div className="absolute top-16 left-3 glass px-4 py-1.5 text-xs whitespace-nowrap">
              Viewing from <b className="text-accent">{selNode?.label}</b> · drag to look · scroll to zoom
            </div>
          </>
        )}

        <OrbCard cardRef={cardRef} node={selNode} data={data} analysis={analysis} pov={pov} signal={selNode ? signals[selNode.id] : null} onHistory={onHistory}
          onPov={() => setPov(true)} onExitPov={exitPov}
          onSelectNode={(id) => onSelect({ kind: 'node', id })} onClose={() => onSelect(null)} />

        <div className="pointer-events-auto absolute bottom-3 right-3 z-20 flex items-center gap-1.5">
          <button className={btn} onClick={() => zoomBy(0.78)} aria-label="Zoom in">＋</button>
          <button className={btn} onClick={() => zoomBy(1.28)} aria-label="Zoom out">－</button>
          <button className={btn} onClick={() => setSpin((s) => !s)} aria-pressed={spin}>{spin ? '⏸ Orbit' : '▶ Orbit'}</button>
        </div>
        {insetRight === 0 && (
          <p className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 text-[0.78rem] text-mute hidden xl:block">
            drag to rotate · scroll to zoom · right-drag to pan · click a star
          </p>
        )}
      </div>
    </div>
  )
})

export default ImpactGraph3D
