export const EFFECT_COLOR = {
  positive: '#3be8b8', negative: '#ff6b7a', mixed: '#b6a4ff', neutral: '#a9b6dc', unknown: '#a9b6dc',
}
export const EFFECT_LABEL = {
  positive: 'Possible benefit', negative: 'Possible pressure', mixed: 'Mixed', neutral: 'Neutral', unknown: 'Unclear',
}
export const EVIDENCE_LABEL = {
  domain_rule: 'Domain rule', news_evidence: 'News evidence', llm_inferred: 'LLM-inferred', quant_verified: 'Quant-verified',
}
export const VERIFY_LABEL = {
  reviewed: 'Reviewed', supported: 'Supported by source', unverified: 'Unverified', conflicting: 'Conflicting evidence',
}
export const HORIZON_LABEL = {
  immediate: 'Immediate', short: 'Days to weeks', medium: 'Weeks to months', long: 'Months or longer',
}
export const MODE_INFO = {
  live: { text: 'Live analysis', cls: 'bg-gain/10 text-gain', hint: 'Every stage ran on real code.' },
  fallback: { text: 'Fallback mode', cls: 'bg-warn/10 text-warn', hint: 'LLM unavailable; rule-based extraction used.' },
  mock: { text: 'Current data', cls: 'bg-accent/10 text-accent', hint: 'Backend stages not finished yet — showing the canned example.' },
}

export const signSymbol = (s) => (s > 0 ? '+' : s < 0 ? '−' : '±')
export const signWord = (s) => (s > 0 ? 'moves the same way' : s < 0 ? 'moves the opposite way' : 'effect is mixed')
export const fmt = (n, d = 2) => (n === null || n === undefined || Number.isNaN(n) ? '—' : Number(n).toFixed(d))
export const labelOf = (nodes, id) => nodes.find((n) => n.id === id)?.label ?? id

export function exposureTone(text = '') {
  const t = text.toLowerCase()
  if (/(pressure|cost|risk|negative|loss)/.test(t)) return 'loss'
  if (/(benefit|positive|gain)/.test(t)) return 'gain'
  return 'mixed'
}
