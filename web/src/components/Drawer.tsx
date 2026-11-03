import { useEffect, useRef, useState } from 'react'
import { packOf, screenSrc, type Pack, type PlanKey, type Person, type Replay } from '../replay'
import { record, type Recording } from '../voice'
import { STILL } from './Stage'

const day = (d: number) => Math.floor(d) + 1 // day 0.4 of the run is "Day 1" on screen

function outcome(p: Person, days: number, pack: Pack) {
  if (p.installed === null) return `Did not install the app on day ${day(p.reached!)}.`
  if (p.signed_up === null) return `Installed the app on day ${day(p.installed)} and left at sign-up.`
  const since = (pack.since ?? 'Paying since day {day}.').replace('{day}', String(day(p.paid ?? 0)))
  if (p.paid !== null && p.quit !== null && pack.id !== 'dating') return `${since} Deleted the app on day ${day(p.quit)}.`
  if (p.paid !== null) return since
  if (p.quit !== null) return `Deleted the app on day ${day(p.quit)}.`
  return `Still using the app on day ${days}.`
}

// The real screens the person (and the model deciding for them) looked at
function Phone({ label, screen }: { label: string; screen: string }) {
  return (
    <div>
      <div className="label mb-2">{label}</div>
      <div className="h-[240px] overflow-hidden rounded-card border border-line bg-bg">
        <img src={screenSrc(screen)} alt="" className="size-full object-cover"
          style={{ objectPosition: /_m[01]_/.test(screen) ? 'center bottom' : 'center 40%' }} />
      </div>
    </div>
  )
}

// The diary with the person's reason for stopping (v2 story.quit_reason) on the day they stopped,
// when that day's line has no words of its own; otherwise as a line of its own
function diaryOf(p: Person): [number, string, string | null][] {
  const s = p.story!, why = s.quit_reason
  if (!why || p.quit === null || s.diary.some(e => e[2] === why)) return s.diary
  const i = s.diary.findLastIndex(e => e[0] === day(p.quit!) && !e[2])
  if (i >= 0) return s.diary.map((e, j) => (j === i ? [e[0], e[1], why] : e))
  return [...s.diary, [day(p.quit), 'Stopped using the app.', why]]
}

function suggestion(p: Person, pack: Pack) {
  if (p.installed === null) return "Why didn't you install it?"
  if (p.signed_up === null) return 'Why did you stop at sign-up?'
  if (p.paid !== null && p.quit !== null && pack.id !== 'dating') return pack.ask.quit
  if (p.paid !== null) return pack.ask.converted
  if (p.quit !== null) return pack.ask.quit
  return pack.ask.using
}

// Ask the person a question, spoken or typed. Live calls: Muse Voice Transcribe, then Muse Spark
// answering from this person's record (engine/interview.py, served by engine/serve.py).
function Ask({ replayName, plan, p, pack }: { replayName: string; plan: PlanKey; p: Person; pack: Pack }) {
  const [question, setQuestion] = useState(suggestion(p, pack))
  const [reply, setReply] = useState<{ text: string; ok: boolean } | null>(null)
  const [state, setState] = useState<'idle' | 'listening' | 'thinking'>('idle')
  const rec = useRef<Recording | null>(null)

  const ask = async (q: string) => {
    if (!q.trim()) return
    setState('thinking')
    setReply(null)
    try {
      const r = await fetch('/api/interview', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ replay: replayName, plan, id: p.id, question: q }),
      })
      const j = await r.json()
      setReply(r.ok ? { text: j.answer, ok: true } : { text: j.error, ok: false })
    } catch {
      setReply({ text: `${p.name} can't be reached right now.`, ok: false })
    }
    setState('idle')
  }

  const mic = async () => {
    if (state === 'listening' && rec.current) {
      const audio = await rec.current.stop()
      rec.current = null
      setState('thinking')
      try {
        const r = await fetch('/api/transcribe', { method: 'POST', headers: { 'Content-Type': 'audio/wav' }, body: audio })
        const j = await r.json()
        if (!r.ok || !j.text) throw new Error()
        setQuestion(j.text)
        await ask(j.text)
      } catch {
        setReply({ text: "Couldn't catch that. Try again, or type the question.", ok: false })
        setState('idle')
      }
      return
    }
    try {
      rec.current = await record()
      setState('listening')
    } catch {
      setReply({ text: 'No microphone. Type the question instead.', ok: false })
    }
  }

  // ?ask asks the suggested question as soon as the drawer opens (video). Once: each ask is a paid call.
  const asked = useRef(false)
  useEffect(() => {
    if (asked.current || !new URLSearchParams(location.search).has('ask')) return
    asked.current = true
    ask(question)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="absolute right-12 bottom-12 left-12">
      <form onSubmit={e => { e.preventDefault(); ask(question) }}
        className="flex items-center gap-4 rounded-card border border-line p-4">
        <button type="button" onClick={mic} aria-label={state === 'listening' ? 'Stop recording' : 'Ask by voice'}
          className="flex-none cursor-pointer">
          <svg width="18" height="18" viewBox="0 0 18 18" className={state === 'listening' ? 'animate-pulse' : ''}>
            <rect x="6" y="1.5" width="6" height="10" rx="3" stroke="currentColor" strokeWidth="1.5"
              fill={state === 'listening' ? 'currentColor' : 'none'} className="text-strong" />
            <path d="M3 8.5 a6 6 0 0 0 12 0 M9 14.5 V17" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-strong" />
          </svg>
        </button>
        <input value={question} onChange={e => setQuestion(e.target.value)} maxLength={300}
          className="min-w-0 flex-1 bg-transparent text-body text-text outline-none" />
      </form>
      <div className="mt-6 min-h-[81px] text-body">
        {state === 'listening' && <span className="label">Listening · press the microphone again to stop</span>}
        {state === 'thinking' && <span className="label">{p.name} is answering</span>}
        {state === 'idle' && reply && (reply.ok
          ? <blockquote className="text-strong">“{reply.text}”</blockquote>
          : <span className="text-dim">{reply.text}</span>)}
      </div>
    </div>
  )
}

export function Drawer({ replay, replayName, plan, person: p, onClose }: {
  replay: Replay; replayName: string; plan: PlanKey; person: Person; onClose: () => void
}) {
  const [open, setOpen] = useState(STILL)
  useEffect(() => {
    const id = requestAnimationFrame(() => setOpen(true))
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    addEventListener('keydown', esc)
    return () => { cancelAnimationFrame(id); removeEventListener('keydown', esc) }
  }, [onClose])

  const s = p.story
  const pack = packOf(replay)
  const she = pack.id !== 'dating' ? 'they' : s?.sex === 'w' ? 'she' : 'he'
  // v2: the ad they saw (meta.ads) and the kind of person they are (meta.kinds)
  const ads = replay.meta.ads ?? [], n = ads.findIndex(a => a.id === p.ad_id)
  const kind = replay.meta.kinds?.find(k => k.id === p.kind)
  const left = pack.id !== 'dating' ? pack.last_screen.replace('{they}', she)
    : p.paid !== null ? `Where ${she} paid` : p.quit !== null ? `Where ${she} left` : `Last paywall ${she} saw`
  return (
    <>
      <div className="absolute inset-0 bg-blue-900/20" onClick={onClose} />
      <aside className="absolute top-0 right-0 h-[1080px] w-[640px] rounded-l-card border-l border-line bg-surface p-12
        transition-transform duration-[250ms] ease-out" style={{ transform: open ? 'none' : 'translateX(100%)' }}>
        <button onClick={onClose} aria-label="Close" className="absolute top-10 right-10 cursor-pointer">
          <svg width="16" height="16" viewBox="0 0 16 16"><path d="M2 2 L14 14 M14 2 L2 14" stroke="currentColor" strokeWidth="1.5" className="text-dim" /></svg>
        </button>
        <div className={`label ${plan === 'a' ? 'text-plan-a' : 'text-plan-b'}`}>{replay.plans[plan].name} · {kind?.name ?? `Person ${p.id}`}</div>
        <h2 className="mt-6 text-number font-medium text-strong">{p.name}, {p.age}</h2>
        <p className="mt-4 text-body text-dim">{p.place}. {outcome(p, replay.meta.days, pack)}</p>
        {s && (
          <>
            <div className="mt-12 grid grid-cols-2 gap-6">
              {n >= 0
                ? <Phone label={`Ad ${n + 1} ${she} saw · ${ads[n].angle}`} screen={ads[n].screen} />
                : <Phone label={`The ${/(^|_|\/)ad$/.test(s.ad) ? 'ad' : 'page'} ${she} saw`} screen={s.ad} />}
              {s.last && <Phone label={left} screen={s.last} />}
            </div>
            <div className="mt-12 grid grid-cols-[72px_1fr] gap-y-4">
              {diaryOf(p).map(([d, what, words], i) => (
                <div key={i} className="contents">
                  <span className="label pt-1">Day {d}</span>
                  <span className="text-body">
                    {what}
                    {words && <span className="block text-strong">“{words}”</span>}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
        {s && <Ask replayName={replayName} plan={plan} p={p} pack={pack} />}
      </aside>
    </>
  )
}
