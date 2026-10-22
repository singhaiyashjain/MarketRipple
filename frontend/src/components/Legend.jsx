import { useState } from 'react'

const Dot = ({ c, shape = 'rounded-full' }) => <span className={`inline-block w-2.5 h-2.5 ${shape}`} style={{ background: c }} />

export default function Legend() {
  const [open, setOpen] = useState(() => typeof window === 'undefined' || window.innerWidth >= 1024)
  return (
    <div className="pointer-events-auto glass text-xs w-[min(100%,290px)] shrink-0">
      <button onClick={() => setOpen((o) => !o)} aria-expanded={open} className="w-full text-left px-3 py-2 section-title">
        Reading the sky {open ? '–' : '+'}
      </button>
      {open && (
        <div className="px-3 pb-2.5 space-y-1.5 reveal">
          <div className="flex items-center gap-2"><Dot c="#8a9bff" /> The event you entered (ringed star)</div>
          <div className="flex items-center gap-2"><Dot c="#3be8b8" /> Possible benefit</div>
          <div className="flex items-center gap-2"><Dot c="#ff6b7a" /> Possible pressure</div>
          <div className="flex items-center gap-2"><Dot c="#b6a4ff" /> Mixed or unclear</div>
          <div className="flex items-center gap-2"><span className="inline-block w-5 border-t-2 border-[#8095ff]" /> Rule, news or data supported (blue)</div>
          <div className="flex items-center gap-2"><span className="inline-block w-5 border-t-2 border-dashed border-warn" /> Inferred by the LLM, unverified (amber)</div>
        </div>
      )}
    </div>
  )
}
