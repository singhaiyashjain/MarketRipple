import React, { useCallback, useEffect, useState } from 'react'
import { adminCreateUser, adminDeleteUser, adminListUsers, adminUpdateUser } from '../api'
import './landing.css' // same night-sky look as the landing and login pages

/**
 * Admin.jsx: admin panel for MarketRipple accounts.
 * Drop into: frontend/src/components/Admin.jsx
 *
 * Lists every account and lets an admin add users, enable/disable them, change role,
 * reset a password, or delete. All checks are enforced by the backend (/api/admin/*);
 * this screen only shows what the server allows.
 *
 * Props: me ({username, role}), onBack(), onLogout()
 */

const CSS = `
.ad-wrap { position: relative; flex: 1; width: 100%; max-width: 980px; margin: 0 auto; padding: 8px 24px 48px; box-sizing: border-box; }
.ad-h1 { margin: 0 0 6px; font: 700 30px/1.15 Sora, sans-serif; }
.ad-sub { margin: 0 0 24px; color: #c3cdf0; font-size: 15px; }
.ad-stats { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 22px; }
.ad-stat { background: #0f1838cc; border: 1px solid #2a3878; border-radius: 12px; padding: 12px 18px; min-width: 110px; }
.ad-stat b { display: block; font: 700 24px Sora, sans-serif; }
.ad-stat span { color: #c3cdf0; font-size: 13px; }
.ad-card { background: #0f1838cc; border: 1px solid #2a3878; border-radius: 16px; padding: 20px; margin-bottom: 22px; backdrop-filter: blur(6px); }
.ad-card h2 { margin: 0 0 14px; font: 600 18px Sora, sans-serif; }
.ad-form { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; align-items: end; }
.ad-form label { display: block; font-size: 13px; font-weight: 600; color: #c3cdf0; margin-bottom: 6px; }
.ad-in, .ad-sel { width: 100%; box-sizing: border-box; background: #070b1f; color: #e8edff; border: 1.5px solid #2a3878; border-radius: 10px; padding: 11px 12px; font: 400 15px Manrope, system-ui, sans-serif; }
.ad-in:focus-visible, .ad-sel:focus-visible { outline: 3px solid #3be8b8; outline-offset: 2px; }
.ad-msg { min-height: 20px; margin: 12px 0 0; font-size: 14px; }
.ad-msg.err { color: #ff6b7a; } .ad-msg.ok { color: #3be8b8; }
.ad-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.ad-table th { text-align: left; color: #8a9bff; font-weight: 600; padding: 8px 10px; border-bottom: 1px solid #2a3878; white-space: nowrap; }
.ad-table td { padding: 10px; border-bottom: 1px solid #1a2552; vertical-align: middle; }
.ad-scroll { overflow-x: auto; }
.ad-pill { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; border: 1px solid #2a3878; }
.ad-pill.admin { color: #8a9bff; border-color: #8a9bff; } .ad-pill.on { color: #3be8b8; border-color: #3be8b8; } .ad-pill.off { color: #ff6b7a; border-color: #ff6b7a; }
.ad-acts { display: flex; gap: 6px; flex-wrap: wrap; }
.ad-act { background: transparent; color: #e8edff; border: 1px solid #2a3878; border-radius: 8px; padding: 6px 10px; font: 600 13px Manrope, sans-serif; cursor: pointer; }
.ad-act:hover:not(:disabled) { background: #1a2552; }
.ad-act:disabled { opacity: .4; cursor: default; }
.ad-act.danger { color: #ff6b7a; border-color: #5a2a3a; }
.ad-act:focus-visible { outline: 3px solid #3be8b8; outline-offset: 2px; }
.ad-nav { display: flex; gap: 10px; }
@media (max-width: 700px) { .lp-nav.ad-top { padding: 20px 16px; } .ad-wrap { padding: 8px 16px 40px; } }
`

const fmt = (iso) => (iso ? new Date(iso).toLocaleString() : 'never')

export default function Admin({ me, onBack, onLogout }) {
  const [rows, setRows] = useState([])
  const [counts, setCounts] = useState({ total: 0, admins: 0, active: 0 })
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState({ type: '', text: '' })
  const [form, setForm] = useState({ username: '', password: '', role: 'user' })
  const [busy, setBusy] = useState(false)

  const say = (type, text) => setMsg({ type, text })

  const refresh = useCallback(async () => {
    try {
      const d = await adminListUsers()
      setRows(d.users)
      setCounts({ total: d.total, admins: d.admins, active: d.active })
    } catch (e) {
      say('err', e.message)
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => { refresh() }, [refresh])

  async function run(fn, okText) {
    if (busy) return
    setBusy(true)
    try {
      await fn()
      say('ok', okText)
      await refresh()
    } catch (e) {
      say('err', e.message)
    } finally {
      setBusy(false)
    }
  }

  const add = (e) => {
    e.preventDefault()
    run(async () => {
      await adminCreateUser(form.username.trim(), form.password, form.role)
      setForm({ username: '', password: '', role: 'user' })
    }, `User "${form.username.trim()}" created.`)
  }
  const resetPw = (u) => {
    const pw = window.prompt(`New password for ${u.username} (8-128 characters):`)
    if (pw) run(() => adminUpdateUser(u.username, { password: pw }), `Password changed for ${u.username}.`)
  }
  const del = (u) => {
    if (window.confirm(`Delete ${u.username}? This cannot be undone.`)) run(() => adminDeleteUser(u.username), `${u.username} deleted.`)
  }

  return (
    <div className="lp">
      <style>{CSS}</style>
      <nav className="lp-nav ad-top">
        <div className="lp-brand">MarketRipple · Admin</div>
        <div className="ad-nav">
          <button type="button" className="lp-btn lp-btn-sm lp-btn-ghost" onClick={onBack}>Dashboard</button>
          <button type="button" className="lp-btn lp-btn-sm lp-btn-ghost" onClick={onLogout}>Sign out</button>
        </div>
      </nav>

      <main className="ad-wrap">
        <h1 className="ad-h1">Users</h1>
        <p className="ad-sub">Signed in as {me.username}. Accounts are stored in the database; passwords are saved only as hashes.</p>

        <div className="ad-stats">
          <div className="ad-stat"><b>{counts.total}</b><span>Total users</span></div>
          <div className="ad-stat"><b>{counts.active}</b><span>Active</span></div>
          <div className="ad-stat"><b>{counts.admins}</b><span>Admins</span></div>
        </div>

        <section className="ad-card" aria-labelledby="ad-add">
          <h2 id="ad-add">Add a user</h2>
          <form className="ad-form" onSubmit={add}>
            <div>
              <label htmlFor="ad-u">Username</label>
              <input id="ad-u" className="ad-in" autoComplete="off" autoCapitalize="none" spellCheck={false} required
                value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
            </div>
            <div>
              <label htmlFor="ad-p">Password (min 8)</label>
              <input id="ad-p" className="ad-in" type="password" autoComplete="new-password" required minLength={8}
                value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            </div>
            <div>
              <label htmlFor="ad-r">Role</label>
              <select id="ad-r" className="ad-sel" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <button type="submit" className="lp-btn lp-btn-sm" disabled={busy}>Create</button>
          </form>
          <p className={`ad-msg ${msg.type}`} role={msg.type === 'err' ? 'alert' : 'status'}>{msg.text}</p>
        </section>

        <section className="ad-card" aria-labelledby="ad-list">
          <h2 id="ad-list">All users</h2>
          {loading ? <p className="ad-sub">Loading…</p> : (
            <div className="ad-scroll">
              <table className="ad-table">
                <thead>
                  <tr><th>Username</th><th>Role</th><th>Status</th><th>Last login</th><th>Logins</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  {rows.map((u) => {
                    const self = u.username.toLowerCase() === me.username.toLowerCase()
                    return (
                      <tr key={u.username}>
                        <td>{u.username}{self ? ' (you)' : ''}</td>
                        <td><span className={`ad-pill ${u.role === 'admin' ? 'admin' : ''}`}>{u.role}</span></td>
                        <td><span className={`ad-pill ${u.active ? 'on' : 'off'}`}>{u.active ? 'active' : 'disabled'}</span></td>
                        <td>{fmt(u.last_login)}</td>
                        <td>{u.login_count}</td>
                        <td>
                          <div className="ad-acts">
                            <button className="ad-act" disabled={busy || self}
                              onClick={() => run(() => adminUpdateUser(u.username, { active: !u.active }), `${u.username} ${u.active ? 'disabled' : 'enabled'}.`)}>
                              {u.active ? 'Disable' : 'Enable'}
                            </button>
                            <button className="ad-act" disabled={busy || self}
                              onClick={() => run(() => adminUpdateUser(u.username, { role: u.role === 'admin' ? 'user' : 'admin' }), `${u.username} is now ${u.role === 'admin' ? 'a user' : 'an admin'}.`)}>
                              {u.role === 'admin' ? 'Make user' : 'Make admin'}
                            </button>
                            <button className="ad-act" disabled={busy} onClick={() => resetPw(u)}>Reset password</button>
                            <button className="ad-act danger" disabled={busy || self} onClick={() => del(u)}>Delete</button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                  {rows.length === 0 && <tr><td colSpan={6}>No users yet.</td></tr>}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
