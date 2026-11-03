import { useEffect, useRef, useState } from 'react'
import { PLANS, type PlanKey, type Replay } from '../replay'

// The admin's live run (engine/live.py): upload what people see, set two plans, and run them with
// Muse Wonder and Muse Spark. Opened with ?new&admin. Each run costs money, so the server asks for the
// admin key; it stays in this browser only.

const KEY = 'rehearsal-admin-key'
const MARKETS = [['dating', 'Dating'], ['resale', 'Resale'], ['rides', 'Rides']] as const
const KINDS = ['feed', 'search', 'event', 'outdoor', 'referral'] as const
const KIND_WORDS: Record<string, string> = {
  feed: 'Feed ads', search: 'Search ads', event: 'Offline', outdoor: 'Outdoor', referral: 'Referrals',
}

type Channel = { kind: string; budget_share: number; start_day: number; end_day: number; side?: string; where?: string }
type PlanSpec = {
  summary: string; budget_usd: number; cities: { name: string; open_day: number }[]; channels: Channel[]
  trial_days?: number; free_swipes_per_day?: number
}
type Spec = {
  pack: string; app: string; days: number; plans: Record<PlanKey, PlanSpec>
  slots: { name: string; label: string; example: string }[]; sides: string[]; metros: string[]
}
type Status = { state: 'running' | 'done' | 'error'; step: number; steps: string[]; done: number; total: number; error: string | null }

const short = (metro: string) => metro.split(',')[0]

// "Austin 0, Denver 30" <-> [{name: "Austin, Texas", open_day: 0}, ...]
const citiesText = (cs: PlanSpec['cities']) => cs.map(c => `${short(c.name)} ${c.open_day}`).join(', ')
function parseCities(text: string, metros: string[]) {
  const out: PlanSpec['cities'] = [], unknown: string[] = []
  for (const part of text.split(',').map(s => s.trim()).filter(Boolean)) {
    const m = part.match(/^(.*?)\s*(\d+)?$/)!
    const metro = metros.find(x => short(x).toLowerCase() === m[1].toLowerCase())
    if (metro) out.push({ name: metro, open_day: Number(m[2] ?? 0) })
    else unknown.push(m[1])
  }
  return { cities: out, unknown }
}

const field = 'min-w-0 border-b border-line bg-transparent text-text outline-none focus:border-dim'

function Num({ value, onChange, className = '' }: { value: number; onChange: (v: number) => void; className?: string }) {
  return <input inputMode="numeric" value={Number.isFinite(value) ? value : ''} className={`${field} label text-text ${className}`}
    onChange={e => onChange(Number(e.target.value.replace(/[^\d.]/g, '')))} />
}

function Row({ name, children }: { name: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[96px_1fr] items-baseline gap-4 border-t border-line py-3">
      <span className="label">{name}</span>
      <div className="min-w-0">{children}</div>
    </div>
  )
}

function PlanCard({ k, spec, setPlan }: { k: PlanKey; spec: Spec; setPlan: (p: PlanSpec) => void }) {
  const p = spec.plans[k]
  const [text, setText] = useState(citiesText(p.cities))   // the card is keyed by market, so this resets with it
  const { unknown } = parseCities(text, spec.metros)
  const set = (patch: Partial<PlanSpec>) => setPlan({ ...p, ...patch })
  const setChannel = (i: number, patch: Partial<Channel>) =>
    set({ channels: p.channels.map((c, j) => (j === i ? { ...c, ...patch } : c)) })
  const toggle = (kind: string) => {
    const on = p.channels.some(c => c.kind === kind)
    set({ channels: on ? p.channels.filter(c => c.kind !== kind)
      : [...p.channels, { kind, budget_share: 0.2, start_day: 0, end_day: spec.days }] })
  }
  const total = p.channels.reduce((s, c) => s + c.budget_share, 0) || 1
  return (
    <div>
      <div className={`label ${k === 'a' ? 'text-plan-a' : 'text-plan-b'}`}>Plan {k.toUpperCase()}</div>
      <div className="mt-4 h-[584px] rounded-card bg-surface px-8 py-6">
        <input value={p.summary} onChange={e => set({ summary: e.target.value })} maxLength={60}
          className="w-full bg-transparent pb-3 text-body text-strong outline-none" />
        <div className="mt-4">
          <Row name="where">
            <input value={text} placeholder="Nationwide" className={`${field} w-full text-body`}
              onChange={e => { setText(e.target.value); set({ cities: parseCities(e.target.value, spec.metros).cities }) }} />
            <div className="label mt-2 normal-case tracking-normal">
              {unknown.length ? `Not a listed city: ${unknown.join(', ')}` : 'City and opening day · empty is nationwide'}
            </div>
          </Row>
          <Row name="budget">
            <span className="label text-text">$ </span>
            <Num value={p.budget_usd} onChange={v => set({ budget_usd: v })} className="w-24" />
            {p.trial_days !== undefined && (
              <span className="ml-8">
                <span className="label">free days </span>
                <Num value={p.trial_days} onChange={v => set({ trial_days: v })} className="w-10" />
              </span>
            )}
          </Row>
          <Row name="ads">
            <div className="flex flex-wrap gap-x-4 gap-y-2">
              {KINDS.map(kind => {
                const on = p.channels.some(c => c.kind === kind)
                return (
                  <button key={kind} onClick={() => toggle(kind)}
                    className={`label flex cursor-pointer items-center gap-2 ${on ? 'text-strong' : ''}`}>
                    <i className={`size-2 rounded-full ${on ? 'bg-strong' : 'border-[1.5px] border-dot-idle'}`} />
                    {KIND_WORDS[kind]}
                  </button>
                )
              })}
            </div>
          </Row>
        </div>
        <div className="mt-2">
          {p.channels.map((c, i) => (
            <div key={i} className="grid grid-cols-[104px_56px_1fr_104px] items-baseline gap-4 py-2">
              <span className="label text-text">{KIND_WORDS[c.kind]}</span>
              <span className="label">
                <Num value={Math.round((c.budget_share / total) * 100)} className="w-8"
                  onChange={v => setChannel(i, { budget_share: (v / 100) * total })} />%
              </span>
              <span className="label">
                day <Num value={c.start_day} onChange={v => setChannel(i, { start_day: v })} className="w-7" />
                {'–'}<Num value={c.end_day} onChange={v => setChannel(i, { end_day: v })} className="w-7" />
              </span>
              {spec.sides.length ? (
                <select value={c.side ?? ''} onChange={e => setChannel(i, { side: e.target.value || undefined })}
                  className="label cursor-pointer appearance-none bg-transparent text-text outline-none">
                  <option value="">both sides</option>
                  {spec.sides.map(s => <option key={s} value={s}>{s}s</option>)}
                </select>
              ) : <span />}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function Step({ state, text }: { state: 'done' | 'now' | 'todo'; text: string }) {
  return (
    <div className="flex items-baseline gap-4">
      <span className={`size-2 flex-none -translate-y-0.5 rounded-full ${state === 'done' ? 'bg-strong'
        : state === 'now' ? 'border-[1.5px] border-strong' : 'border-[1.5px] border-dot-idle'}`} />
      <span className={`text-body ${state === 'todo' ? 'text-dim' : ''}`}>{text}</span>
    </div>
  )
}

export function AdminInput({ onReplay }: { onReplay: (r: Replay, id: string) => void }) {
  const [key, setKey] = useState(() => { try { return localStorage.getItem(KEY) ?? '' } catch { return '' } })
  const [pack, setPack] = useState('resale')
  const [spec, setSpec] = useState<Spec | null>(null)
  const [files, setFiles] = useState<Record<string, Blob>>({})
  const [shown, setShown] = useState<Record<string, string>>({})
  const [status, setStatus] = useState<Status | null>(null)
  const [error, setError] = useState('')
  const picking = useRef<string>('')
  const fileInput = useRef<HTMLInputElement>(null)

  useEffect(() => { try { localStorage.setItem(KEY, key) } catch { /* private window */ } }, [key])

  // The market's example plans and screens, so the form starts filled in
  useEffect(() => {
    let live = true
    fetch(`/api/live/example/${pack}`).then(r => r.json()).then(async (s: Spec) => {
      if (!live) return
      setSpec(s)
      setShown(Object.fromEntries(s.slots.map(x => [x.name, x.example])))
      const blobs = await Promise.all(s.slots.map(x => fetch(x.example).then(r => r.blob())))
      if (live) setFiles(Object.fromEntries(s.slots.map((x, i) => [x.name, blobs[i]])))
    }).catch(() => live && setError('The server is not reachable.'))
    return () => { live = false }
  }, [pack])

  const pick = (name: string) => { picking.current = name; fileInput.current?.click() }
  const picked = (f: File | undefined) => {
    if (!f) return
    const name = picking.current
    setFiles(x => ({ ...x, [name]: f }))
    setShown(x => ({ ...x, [name]: URL.createObjectURL(f) }))
  }

  const headers = { 'X-Admin-Key': key.trim() }
  const run = async () => {
    if (!spec) return
    setError('')
    const body = new FormData()
    const plans = Object.fromEntries(PLANS.map(k => [k, {
      ...spec.plans[k], channels: spec.plans[k].channels.map(c => ({ ...c, where: 'cities' })),
    }]))
    body.append('spec', JSON.stringify({ pack: spec.pack, app: spec.app, days: spec.days, plans }))
    for (const s of spec.slots) body.append(s.name, files[s.name], `${s.name}.png`)
    const r = await fetch('/api/live', { method: 'POST', headers, body })
    const j = await r.json().catch(() => ({ error: 'The server did not answer.' }))
    if (!r.ok) return setError(j.error)
    setStatus({ state: 'running', step: 0, steps: [], done: 0, total: 0, error: null })
    poll(j.id)
  }

  const poll = async (id: string) => {
    const r = await fetch(`/api/live/${id}`, { headers })
    const s: Status = await r.json()
    if (!r.ok) { setStatus(null); return setError('The run was lost. Start it again.') }
    setStatus(s)
    if (s.state === 'running') return void setTimeout(() => poll(id), 2000)
    if (s.state === 'error') return setError(s.error ?? 'The run failed.')
    const rep = await fetch(`/api/live/${id}/replay`, { headers }).then(x => x.json())
    onReplay(rep, id)
  }

  const setPlan = (k: PlanKey) => (p: PlanSpec) => spec && setSpec({ ...spec, plans: { ...spec.plans, [k]: p } })
  const ready = spec && key && spec.slots.every(s => files[s.name])

  return (
    <>
      <header className="label absolute top-12 right-16 left-16 flex justify-between">
        <a href="/" className="text-strong">Rehearsal</a>
        <span>Live rehearsal · admin · {spec?.days ?? 90} days</span>
      </header>

      <section className="absolute top-28 left-16 w-[1100px]">
        <h1 className="text-headline font-semibold text-strong">Rehearse your launch.</h1>
        <p className="mt-6 max-w-[760px] text-body">
          Upload what people see and set two plans. Muse Wonder designs the people, Muse Spark decides for them.
          A run takes a few minutes.
        </p>
      </section>

      <section className="absolute top-[328px] left-16 w-[740px]">
        <div className="label flex gap-4">
          {MARKETS.map(([id, words]) => (
            <button key={id} onClick={() => {
              if (status || id === pack) return
              setSpec(null); setFiles({}); setShown({}); setError(''); setPack(id)
            }}
              className={`label cursor-pointer ${pack === id ? 'text-strong' : ''}`}>{words}</button>
          ))}
          <span>·</span>
          {spec && <input value={spec.app} maxLength={24} onChange={e => setSpec({ ...spec, app: e.target.value })}
            className={`${field} label w-32 text-strong`} />}
        </div>
        <div className="mt-4 flex gap-4">
          {spec?.slots.map(s => (
            <button key={s.name} onClick={() => pick(s.name)} className="w-[173px] cursor-pointer text-left">
              <div className="h-[374px] overflow-hidden rounded-card border border-line bg-surface">
                {shown[s.name] && <img src={shown[s.name]} alt="" className="size-full object-cover object-top" />}
              </div>
              <div className="label mt-2">{s.label}</div>
            </button>
          ))}
        </div>
        <input ref={fileInput} type="file" accept="image/png,image/jpeg" className="hidden"
          onChange={e => { picked(e.target.files?.[0]); e.target.value = '' }} />
        <div className="label mt-8">Click a screen to replace it with your own</div>
      </section>

      {spec && (
        <section className="absolute top-[328px] right-16 left-[836px] grid grid-cols-2 gap-6">
          {PLANS.map(k => <PlanCard key={`${spec.pack}${k}`} k={k} spec={spec} setPlan={setPlan(k)} />)}
        </section>
      )}

      {!status || status.state === 'error' ? (
        <section className="absolute top-[952px] right-16 left-16 flex items-center gap-6">
          <button onClick={run} disabled={!ready}
            className="cursor-pointer rounded-card bg-blue-600 px-8 py-5 text-body font-medium text-white disabled:cursor-default disabled:opacity-40">
            Run both plans
          </button>
          <input type="password" value={key} onChange={e => setKey(e.target.value)} placeholder="Admin key"
            autoComplete="off" className={`${field} label w-48 text-text`} />
          <span className={`label ${error ? 'text-text' : ''}`}>
            {error || 'Live runs call Meta models and cost money. Ten a day.'}
          </span>
        </section>
      ) : (
        <section className="absolute top-[920px] right-16 left-16">
          <div className="label">
            {status.steps[status.step] ?? 'Starting'}
            {status.step === 2 && status.total > 0 && ` · ${status.done} of ${status.total} answers`}
          </div>
          <div className="relative mt-4 h-0.5 bg-line">
            <i className="absolute inset-y-0 left-0 bg-strong transition-[width] duration-1000 ease-linear"
              style={{ width: `${((status.step + (status.step === 2 && status.total ? status.done / status.total : 0.5))
                / Math.max(1, status.steps.length)) * 100}%` }} />
          </div>
          <div className="mt-6 grid grid-cols-5 gap-6">
            {status.steps.map((t, i) => <Step key={t} text={t} state={i < status.step ? 'done' : i === status.step ? 'now' : 'todo'} />)}
          </div>
        </section>
      )}
    </>
  )
}
