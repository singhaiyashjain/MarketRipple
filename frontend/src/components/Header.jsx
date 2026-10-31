import { useState } from 'react'
import { MODE_INFO } from '../lib/format'

export default function Header({ mode, warnings = [], hasData, onReset, user, onAdmin, onLogout }) {
  const [open, setOpen] = useState(false)
  const info = MODE_INFO[mode]
  return (
    <header className="bg-gradient-to-r from-night via-[#0a1033] to-[#16215a] text-white border-b border-line shadow-float relative z-10">
      <div className="flex items-center gap-3 px-4 h-14">
        <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="5" cy="12" r="2.4" fill="#fff" />
          <circle cx="19" cy="5" r="2.4" fill="#7ee0c8" />
          <circle cx="19" cy="19" r="2.4" fill="#f4a49a" />
          <path d="M7 12 L17 5.6 M7 12 L17 18.4" stroke="#fff" strokeWidth="1.5" fill="none" />
        </svg>
        <h1 className="font-semibold tracking-tight text-[1.1rem] whitespace-nowrap">Market<span className="text-[#9db0ff]">Ripple</span></h1>
        <span className="hidden md:inline text-sm text-white/55 border-l border-white/15 pl-3">Trace how one event spreads through sectors and assets</span>
        <div className="ml-auto flex items-center gap-2">
          {info && (
            <span title={info.hint} className={`text-xs font-medium px-2 py-0.5 rounded-full bg-white/10 border border-white/10 ${info.cls}`}><span className="mr-1">●</span>{info.text}</span>
          )}
          {warnings.length > 0 && (
            <button onClick={() => setOpen((o) => !o)} aria-expanded={open}
              className="text-xs px-2.5 py-1 rounded-full bg-white/10 hover:bg-white/20 transition">
              {warnings.length} {warnings.length === 1 ? 'note' : 'notes'}
            </button>
          )}
          {user && onAdmin && user.role === 'admin' && (
            <button onClick={onAdmin} className="text-xs px-3 py-1 rounded-full border border-white/30 hover:bg-white/15 transition font-medium">
              Admin
            </button>
          )}
          {user && onLogout && (
            <button onClick={onLogout} title={`Signed in as ${user.username}`} className="text-xs px-3 py-1 rounded-full border border-white/30 hover:bg-white/15 transition font-medium">
              Sign out
            </button>
          )}
          {hasData && (
            <button onClick={onReset} className="text-xs px-3 py-1 rounded-full border border-white/30 hover:bg-white/15 transition font-medium">
              New analysis
            </button>
          )}
        </div>
      </div>
      {open && warnings.length > 0 && (
        <ul className="px-4 py-2 text-xs bg-white/10 space-y-0.5 reveal">
          {warnings.map((w, i) => <li key={i}>{w}</li>)}
        </ul>
      )}
    </header>
  )
}
