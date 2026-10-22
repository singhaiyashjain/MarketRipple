import * as THREE from 'three'

/** Everything that makes the graph look like a night sky: textures, starfield, nebula, orbs, labels. */

const texCache = new Map()

/** Soft radial glow texture, white centre fading to transparent. */
export function glowTexture(stops = [[0, 'rgba(255,255,255,1)'], [0.25, 'rgba(255,255,255,.55)'], [0.6, 'rgba(255,255,255,.12)'], [1, 'rgba(255,255,255,0)']]) {
  const key = JSON.stringify(stops)
  if (texCache.has(key)) return texCache.get(key)
  const c = document.createElement('canvas')
  c.width = c.height = 128
  const g = c.getContext('2d')
  const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64)
  stops.forEach(([o, col]) => grad.addColorStop(o, col))
  g.fillStyle = grad
  g.fillRect(0, 0, 128, 128)
  const t = new THREE.CanvasTexture(c)
  t.colorSpace = THREE.SRGBColorSpace
  texCache.set(key, t)
  return t
}

/** Background stars + a few faint nebula clouds. Returns {group, tick(t)}. */
export function makeSpace() {
  const group = new THREE.Group()
  const N = 2200
  const pos = new Float32Array(N * 3)
  const col = new Float32Array(N * 3)
  const tint = [new THREE.Color('#ffffff'), new THREE.Color('#aebcff'), new THREE.Color('#ffd9b8'), new THREE.Color('#b8f3ff')]
  for (let i = 0; i < N; i++) {
    const r = 900 + Math.random() * 1700
    const th = Math.random() * Math.PI * 2
    const ph = Math.acos(2 * Math.random() - 1)
    pos[i * 3] = r * Math.sin(ph) * Math.cos(th)
    pos[i * 3 + 1] = r * Math.sin(ph) * Math.sin(th)
    pos[i * 3 + 2] = r * Math.cos(ph)
    const c = tint[(Math.random() * tint.length) | 0].clone().multiplyScalar(0.35 + Math.random() * 0.65)
    col.set([c.r, c.g, c.b], i * 3)
  }
  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3))
  const mat = new THREE.PointsMaterial({
    size: 2.4, sizeAttenuation: false, vertexColors: true, map: glowTexture(), transparent: true,
    depthWrite: false, blending: THREE.AdditiveBlending,
  })
  const stars = new THREE.Points(geo, mat)
  group.add(stars)

  const nebula = [['rgba(90,70,255,.55)', -900, 300, -1400, 1900], ['rgba(0,160,255,.4)', 1100, -400, -1300, 1700], ['rgba(190,60,255,.35)', 200, 700, 1500, 1800]]
  nebula.forEach(([color, x, y, z, s]) => {
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({
      map: glowTexture([[0, color], [0.5, color.replace(/[\d.]+\)$/, '.08)')], [1, 'rgba(0,0,0,0)']]),
      transparent: true, depthWrite: false, opacity: 0.55, blending: THREE.AdditiveBlending,
    }))
    sp.position.set(x, y, z)
    sp.scale.setScalar(s)
    sp.raycast = () => {}
    group.add(sp)
  })
  return {
    group,
    tick: (t) => { stars.rotation.y = t * 0.004; stars.rotation.x = t * 0.0013; mat.opacity = 0.82 + Math.sin(t * 1.3) * 0.1 },
    dispose: () => { geo.dispose(); mat.dispose() },
  }
}

function labelTexture(text) {
  const H = 96 // texture height in px: ~2.5x the on-screen size so text stays crisp
  const font = '700 46px "Hanken Grotesk", system-ui, sans-serif'
  const probe = document.createElement('canvas').getContext('2d')
  probe.font = font
  const w = Math.ceil(probe.measureText(text).width) + 56
  const c = document.createElement('canvas')
  c.width = w
  c.height = H
  const g = c.getContext('2d')
  g.font = font
  g.textAlign = 'center'
  g.textBaseline = 'middle'
  g.lineJoin = 'round'
  // dark outline keeps the text readable over bright halos and other stars
  g.lineWidth = 9
  g.strokeStyle = 'rgba(2,4,18,.95)'
  g.strokeText(text, w / 2, H / 2 + 2)
  g.shadowColor = 'rgba(120,140,255,.85)'
  g.shadowBlur = 8
  g.fillStyle = '#ffffff'
  g.fillText(text, w / 2, H / 2 + 2)
  const t = new THREE.CanvasTexture(c)
  t.colorSpace = THREE.SRGBColorSpace
  t.anisotropy = 8
  return { t, aspect: w / H }
}

const noRay = () => {}

/** One glowing orb: white core, coloured halo, floating label. Event nodes also get a spinning ring. */
export function makeOrb(node) {
  const r = node.r
  const color = new THREE.Color(node.color)
  const group = new THREE.Group()

  const core = new THREE.Mesh(
    new THREE.SphereGeometry(r, 24, 24),
    new THREE.MeshBasicMaterial({ color: new THREE.Color('#ffffff').lerp(color, 0.42).multiplyScalar(0.8), transparent: true, opacity: 0.9 }),
  )
  group.add(core)  // the only raycastable part => easy, accurate clicking

  const halo = new THREE.Sprite(new THREE.SpriteMaterial({
    map: glowTexture(), color, transparent: true, opacity: 0.32, depthWrite: false, blending: THREE.AdditiveBlending,
  }))
  halo.scale.setScalar(r * 4.2)
  halo.raycast = noRay
  group.add(halo)

  const glint = new THREE.Sprite(new THREE.SpriteMaterial({
    map: glowTexture(), color: 0xffffff, transparent: true, opacity: 0.28, depthWrite: false, blending: THREE.AdditiveBlending,
  }))
  glint.scale.setScalar(r * 2.4)
  glint.raycast = noRay
  group.add(glint)

  const { t, aspect } = labelTexture(node.label)
  const label = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, transparent: true, depthWrite: false, depthTest: false }))
  const lh = node.type === 'event' ? 3.1 : 2.5
  label.scale.set(lh * aspect, lh, 1)
  label.position.y = -(r + lh * 0.9)
  label.renderOrder = 20
  label.raycast = noRay
  group.add(label)

  let ring = null
  if (node.type === 'event') {
    ring = new THREE.Mesh(
      new THREE.TorusGeometry(r * 1.9, 0.18, 8, 80),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending, depthWrite: false }),
    )
    ring.rotation.x = Math.PI / 2.6
    ring.raycast = noRay
    group.add(ring)
  }
  node.__orb = { group, core, halo, glint, label, ring, coreTint0: core.material.color.clone(), haloTint0: halo.material.color.clone(), scale: 1, scaleTo: 1, labelOn: 1, lw: lh * aspect, aspect, lh, labelTarget: 1, haloBase: 0.32, phase: Math.random() * 6.28 }
  return group
}

const signTex = {}
/** Every sign sprite ever made; the render loop rescales them so they stay readable from far away. */
export const signSprites = new Set()
export function signSprite(sign) {
  const ch = sign > 0 ? '+' : sign < 0 ? '\u2212' : '\u00b1'
  if (!signTex[ch]) {
    const c = document.createElement('canvas')
    c.width = c.height = 128
    const g = c.getContext('2d')
    g.font = '800 96px "Hanken Grotesk", system-ui, sans-serif'
    g.textAlign = 'center'
    g.textBaseline = 'middle'
    g.lineJoin = 'round'
    g.lineWidth = 14
    g.strokeStyle = 'rgba(2,4,18,.95)'
    g.strokeText(ch, 64, 68)
    g.shadowColor = 'rgba(138,155,255,1)'
    g.shadowBlur = 10
    g.fillStyle = '#ffffff'
    g.fillText(ch, 64, 68)
    const t = new THREE.CanvasTexture(c)
    t.colorSpace = THREE.SRGBColorSpace
    t.anisotropy = 8
    signTex[ch] = t
  }
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: signTex[ch], transparent: true, depthWrite: false, depthTest: false, opacity: 0.95 }))
  s.scale.set(5, 5, 1)
  s.raycast = noRay
  signSprites.add(s)
  return s
}

/** Thin expanding ring used by stars that are in "alert": the render loop grows and fades it in a loop (sonar ping). */
export function makeAlertRing() {
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({
    map: glowTexture([[0, 'rgba(255,255,255,0)'], [0.62, 'rgba(255,255,255,0)'], [0.8, 'rgba(255,255,255,.95)'], [0.92, 'rgba(255,255,255,.25)'], [1, 'rgba(255,255,255,0)']]),
    color: 0xff4d5e, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending,
  }))
  sp.raycast = noRay
  sp.visible = false
  return sp
}
