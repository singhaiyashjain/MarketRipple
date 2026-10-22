import StatsBadge from './StatsBadge'
import {
  EFFECT_COLOR, EFFECT_LABEL, EVIDENCE_LABEL, HORIZON_LABEL, VERIFY_LABEL, fmt, labelOf, signSymbol, signWord,
} from '../lib/format'

const Chip = ({ children, tone = 'bg-paper text-mute border border-line/70' }) => (
  <span className={`inline-block rounded-full px-2 py-0.5 text-[0.8rem] font-medium ${tone}`}>{children}</span>
)
const Card = ({ title, children }) => (
  <section className="card p-3.5 reveal space-y-2.5">
    {title && <h3 className="font-semibold text-[0.98rem] leading-snug">{title}</h3>}
    {children}
  </section>
)
const evTone = (t) => (t === 'llm_inferred' ? 'bg-warn/10 text-warn' : t === 'quant_verified' ? 'bg-gain/10 text-gain' : 'bg-paper text-mute')

function EdgeDetail({ edge, data, onSelectPath, onSelect }) {
  const inPaths = data.paths.filter((p) => p.edge_ids.includes(edge.id))
  return (
    <Card title={`${labelOf(data.nodes, edge.source)} → ${labelOf(data.nodes, edge.target)}`}>
      <div className="flex flex-wrap gap-1.5">
        <Chip tone={evTone(edge.evidence_type)}>{EVIDENCE_LABEL[edge.evidence_type]}</Chip>
        <Chip>{VERIFY_LABEL[edge.verification_status] ?? edge.verification_status}</Chip>
        <Chip>{HORIZON_LABEL[edge.horizon]}</Chip>
        <Chip>{signSymbol(edge.sign)} {signWord(edge.sign)}</Chip>
        <Chip>weight {fmt(edge.weight)}</Chip>
      </div>
      <p className="font-serif text-[0.98rem] leading-snug">{edge.explanation || 'No explanation recorded for this link yet.'}</p>
      {edge.evidence_type === 'llm_inferred' && (
        <p className="text-xs rounded bg-warn/10 text-warn p-2">This link was proposed by the language model and has no supporting source or data yet. It is excluded from verified conclusions.</p>
      )}
      {edge.assumptions?.length > 0 && (
        <div>
          <div className="text-xs font-medium">Holds only if</div>
          <ul className="list-disc ml-4 text-xs text-mute space-y-0.5">{edge.assumptions.map((a) => <li key={a}>{a}</li>)}</ul>
        </div>
      )}
      <div>
        <div className="text-xs font-medium mb-1">Evidence</div>
        {edge.evidence?.length ? (
          <ul className="space-y-1">
            {edge.evidence.map((ev, i) => (
              <li key={i} className="text-xs border-l-2 border-line pl-2">
                <span className="text-mute">{ev.source_type.replace('_', ' ')}: </span>
                {ev.text}
                {ev.url && <> <a className="text-accent underline" href={ev.url} target="_blank" rel="noreferrer">source</a></>}
              </li>
            ))}
          </ul>
        ) : <p className="text-xs text-mute">No source attached yet.</p>}
      </div>
      <div>
        <div className="text-xs font-medium mb-1">Historical data</div>
        <StatsBadge stats={edge.stats} />
      </div>
      {inPaths.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <span className="text-mute">Used in</span>
          {inPaths.map((p) => (
            <button key={p.id} onClick={() => onSelectPath(p.id)} className="rounded-full border border-line px-2 py-0.5 hover:border-accent hover:text-accent">
              {labelOf(data.nodes, p.node_ids[p.node_ids.length - 1])}
            </button>
          ))}
        </div>
      )}
    </Card>
  )
}

function NodeDetail({ node, data, onSelect }) {
  const out = data.edges.filter((e) => e.source === node.id)
  const inc = data.edges.filter((e) => e.target === node.id)
  const Row = ({ e, other }) => (
    <li>
      <button onClick={() => onSelect({ kind: 'edge', id: e.id })} className="text-left text-xs hover:text-accent">
        <span className="font-semibold">{signSymbol(e.sign)}</span> {labelOf(data.nodes, other)}
      </button>
    </li>
  )
  return (
    <Card title={node.label}>
      <div className="flex flex-wrap gap-1.5">
        <Chip>{node.type}</Chip>
        {node.sector && <Chip>{node.sector}</Chip>}
        <Chip tone="bg-paper"><span style={{ color: EFFECT_COLOR[node.effect] }}>●</span> {EFFECT_LABEL[node.effect]}</Chip>
      </div>
      {inc.length > 0 && <div><div className="text-xs font-medium">Driven by</div><ul className="space-y-0.5">{inc.map((e) => <Row key={e.id} e={e} other={e.source} />)}</ul></div>}
      {out.length > 0 && <div><div className="text-xs font-medium">Affects</div><ul className="space-y-0.5">{out.map((e) => <Row key={e.id} e={e} other={e.target} />)}</ul></div>}
    </Card>
  )
}

function PathDetail({ path, data, onSelect }) {
  return (
    <Card title="Selected path">
      <div className="flex flex-wrap gap-1.5">
        <Chip><span style={{ color: EFFECT_COLOR[path.terminal_effect] }}>●</span> {EFFECT_LABEL[path.terminal_effect]}</Chip>
        <Chip>{HORIZON_LABEL[path.horizon]}</Chip>
        <Chip>relative strength {fmt(path.strength)}</Chip>
      </div>
      <p className="font-serif text-[0.98rem] leading-snug">{path.explanation}</p>
      {path.uncertainty && <p className="text-xs rounded bg-warn/10 text-warn p-2">Uncertainty: {path.uncertainty}</p>}
      <ol className="space-y-1">
        {path.edge_ids.map((id) => {
          const e = data.edges.find((x) => x.id === id)
          if (!e) return null
          return (
            <li key={id}>
              <button onClick={() => onSelect({ kind: 'edge', id })} className="w-full text-left text-xs rounded border border-line px-2 py-1 hover:border-accent">
                {labelOf(data.nodes, e.source)} <span className="font-semibold text-accent">{signSymbol(e.sign)}</span> {labelOf(data.nodes, e.target)}
                <span className="block text-[0.8rem] text-mute">{EVIDENCE_LABEL[e.evidence_type]}{e.stats ? ' · tested on history' : ''}</span>
              </button>
            </li>
          )
        })}
      </ol>
    </Card>
  )
}

export default function EvidencePanel({ data, selection, selectedPath, onSelect, onSelectPath }) {
  if (!data) return null
  const edge = selection?.kind === 'edge' ? data.edges.find((e) => e.id === selection.id) : null
  const node = selection?.kind === 'node' ? data.nodes.find((n) => n.id === selection.id) : null
  const path = data.paths.find((p) => p.id === selectedPath)
  return (
    <div className="space-y-3">
      {edge && <EdgeDetail key={`e-${edge.id}`} edge={edge} data={data} onSelect={onSelect} onSelectPath={onSelectPath} />}
      {node && <NodeDetail key={`n-${node.id}`} node={node} data={data} onSelect={onSelect} />}
      {path && <PathDetail key={`p-${path.id}`} path={path} data={data} onSelect={onSelect} />}
      {!edge && !node && !path && (
        <Card title="Why does each link exist?">
          <p className="text-sm text-mute">Select a path on the left, or click any node or arrow in the graph. You will see the reasoning, the evidence, what must hold true, and what history says.</p>
        </Card>
      )}
    </div>
  )
}
