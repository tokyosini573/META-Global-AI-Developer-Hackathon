import { useEffect, useRef, useState } from 'react'
import { imageSlots, type Brief } from '../../brief'
import { finalBrief, requestBody } from './request'

// The admin's live run: POST /api/live with the brief and its images, then follow the run until its
// replay is ready (engine/live.py). Each run costs money, so the server asks for the admin key; it stays
// in this browser only.

const KEY = 'rehearsal-admin-key'
const POLL_MS = 2000

type Status = { state: 'running' | 'done' | 'error'; step: number; steps: string[]; done: number; total: number; error: string | null }

const plain = (status: number, error?: string) =>
  status === 401 || status === 403 ? 'The admin key is not right.'
    : status === 429 ? 'Today’s live runs are used up. Try again tomorrow.'
      : status === 413 ? 'The images are too large. Use smaller screenshots.'
        : error || 'The server could not start the run. Try again in a minute.'

export function LiveRun({ brief, files, check }: {
  brief: Brief; files: Record<string, File>
  check: () => boolean   // shows what is missing; true when the brief is ready
}) {
  const [key, setKey] = useState(() => { try { return localStorage.getItem(KEY) ?? '' } catch { return '' } })
  const [status, setStatus] = useState<Status | null>(null)
  const [error, setError] = useState('')
  const timer = useRef(0)
  useEffect(() => { try { localStorage.setItem(KEY, key) } catch { /* private window */ } }, [key])
  useEffect(() => () => clearTimeout(timer.current), [])

  const headers = () => ({ 'X-Admin-Key': key.trim() })

  const run = async () => {
    setError('')
    if (!check()) return
    if (!key.trim()) return setError('Type the admin key first.')
    const b = finalBrief(brief)
    if (import.meta.env.DEV) {
      console.debug('POST /api/live brief', b)
      console.debug('POST /api/live files', imageSlots(b.category, b.ads.length).map(n => `${n}: ${files[n]?.name} (${files[n]?.size} bytes)`))
    }
    setStatus({ state: 'running', step: 0, steps: [], done: 0, total: 0, error: null })
    try {
      const r = await fetch('/api/live', { method: 'POST', headers: headers(), body: requestBody(b, files) })
      const j = await r.json().catch(() => ({}))
      if (!r.ok || !j.id) { setStatus(null); return setError(plain(r.status, j.error)) }
      poll(j.id)
    } catch {
      setStatus(null)
      setError('The server is not reachable. Check the connection and try again.')
    }
  }

  const poll = async (id: string) => {
    try {
      const r = await fetch(`/api/live/${id}`, { headers: headers() })
      const s: Status = await r.json()
      if (!r.ok) { setStatus(null); return setError(r.status === 404 ? 'The run was lost. Start it again.' : plain(r.status, (s as { error?: string }).error)) }
      setStatus(s)
      if (s.state === 'running') { timer.current = window.setTimeout(() => poll(id), POLL_MS); return }
      if (s.state === 'error') { setStatus(null); return setError(s.error || 'The run stopped. Start it again.') }
      window.location.assign(`/?replay=live_${id}`)
    } catch {
      timer.current = window.setTimeout(() => poll(id), POLL_MS * 2)   // a dropped connection: keep following
    }
  }

  if (status) return <Progress status={status} />
  return (
    <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
      <p className="max-w-[560px] text-label text-dim">
        Your screens and text go to Muse Spark standard, which is not used for training. A run takes a few minutes
        and costs money, so it needs the admin key.
        {error && <span className="mt-2 block text-body font-medium text-strong">{error}</span>}
      </p>
      <div className="flex flex-none flex-wrap items-center gap-3">
        <input type="password" value={key} onChange={e => setKey(e.target.value)} placeholder="Admin key" autoComplete="off"
          aria-label="Admin key"
          className="w-56 rounded-card border border-line bg-bg px-4 py-3 text-body text-strong outline-none placeholder:text-dim focus:border-blue-600" />
        <button onClick={run} className="cursor-pointer rounded-card bg-blue-600 px-8 py-4 text-body font-medium text-white hover:bg-blue-900">
          Run both experiments
        </button>
      </div>
    </div>
  )
}

function Progress({ status }: { status: Status }) {
  const n = Math.max(1, status.steps.length)
  const part = status.total ? status.done / status.total : 0.5
  const width = status.steps.length ? ((status.step + part) / n) * 100 : 4
  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <div className="text-lead font-semibold text-strong">{status.steps[status.step] ?? 'Sending your app'}</div>
        {status.total > 0 && <div className="label">{status.done.toLocaleString('en-US')} of {status.total.toLocaleString('en-US')} answers</div>}
      </div>
      <div className="relative mt-4 h-1 overflow-hidden rounded-full bg-line">
        <i className="absolute inset-y-0 left-0 rounded-full bg-blue-600 transition-[width] duration-1000 ease-linear" style={{ width: `${width}%` }} />
      </div>
      <ol className="mt-6 grid gap-4 md:grid-cols-5">
        {status.steps.map((t, i) => (
          <li key={t} className="flex items-baseline gap-3">
            <span className={`size-2 flex-none -translate-y-0.5 rounded-full ${i < status.step ? 'bg-blue-600'
              : i === status.step ? 'border-[1.5px] border-blue-600' : 'border-[1.5px] border-dot-idle'}`} />
            <span className={`text-body ${i <= status.step ? 'text-strong' : 'text-dim'}`}>{t}</span>
          </li>
        ))}
      </ol>
      <p className="mt-6 text-label text-dim">Keep this page open. The results open by themselves when the run is done.</p>
    </div>
  )
}
