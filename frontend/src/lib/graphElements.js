import { EFFECT_COLOR, signSymbol } from './format'

const SHAPE = {
  event: 'diamond', commodity: 'hexagon', sector: 'round-rectangle', company: 'round-rectangle',
  index: 'octagon', currency: 'ellipse', policy: 'round-tag', indicator: 'ellipse', country: 'ellipse',
}

/** API response -> Cytoscape elements. */
export function toElements(data) {
  const nodes = data.nodes.map((n) => ({
    data: {
      id: n.id,
      label: n.label,
      type: n.type,
      sector: n.sector ?? '',
      color: n.type === 'event' ? '#3b4bdb' : EFFECT_COLOR[n.effect] ?? EFFECT_COLOR.unknown,
      shape: SHAPE[n.type] ?? 'ellipse',
      size: n.type === 'event' ? 46 : n.type === 'sector' ? 40 : 32,
    },
  }))
  const edges = data.edges.map((e) => ({
    data: {
      id: e.id,
      source: e.source,
      target: e.target,
      sign: signSymbol(e.sign),
      weight: e.weight,
      width: 1.2 + e.weight * 3.2,
      inferred: e.evidence_type === 'llm_inferred' ? 1 : 0,
      quant: e.evidence_type === 'quant_verified' ? 1 : 0,
    },
  }))
  return [...nodes, ...edges]
}
