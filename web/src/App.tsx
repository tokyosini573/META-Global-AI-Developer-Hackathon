import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { Ads } from './components/Ads'
import { Backtest } from './components/Backtest'
import { Drawer } from './components/Drawer'
import { Funnel } from './components/Funnel'
import { PlanMap } from './components/PlanMap'
import { Report } from './components/Report'
import { Nav, type View } from './components/report/Nav'
import { Stage, STILL } from './components/Stage'
import { Timeline } from './components/Timeline'
import { noteOf, numbersAt, packOf, PLANS, type PlanKey, type Replay } from './replay'

const PLAY_SECONDS = 30 // 90 days = 30 s

// In "Plan B wins.", color only the plan name with its plan color
function Headline({ text }: { text: string }) {
  const m = text.match(/^(.*Plan )([AB])(.*)$/)
  if (!m) return <>{text}</>
  return <>{m[1]}<span className={m[2] === 'A' ? 'text-plan-a' : 'text-plan-b'}>{m[2]}</span>{m[3]}</>
}

const viewOf = (q: URLSearchParams): View =>
  q.has('backtest') ? 'backtest' : q.has('report') ? 'report' : q.has('ads') ? 'ads' : 'replay'

// Count a number up from 0 over 0.4 s
function CountUp({ value }: { value: number }) {
  const [shown, setShown] = useState(STILL ? value : 0)
  useEffect(() => {
    if (STILL) return
    const start = performance.now()
    let raf = 0
    const tick = (now: number) => {
      const k = Math.min(1, (now - start) / 400)
      setShown(value * (1 - (1 - k) ** 3))
      if (k < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [value])
  return <>{Math.round(shown).toLocaleString('en-US')}</>
}

export default function App() {
  const [replay, setReplay] = useState<Replay | null>(null)
  // ?day=90 freezes on that day (for screenshots); otherwise play on open.
  const fixedDay = new URLSearchParams(location.search).get('day')
  const [t, setT] = useState(fixedDay ? Number(fixedDay) : 0)
  const [playing, setPlaying] = useState(!fixedDay)
  const last = useRef<number | null>(null)
  // The person whose drawer is open. ?person=a:482 opens one on load (screenshots, video).
  const [picked, setPicked] = useState<{ plan: PlanKey; id: number } | null>(() => {
    const m = new URLSearchParams(location.search).get('person')?.match(/^([ab]):(\d+)$/)
    return m ? { plan: m[1] as PlanKey, id: Number(m[2]) } : null
  })
  const close = useCallback(() => setPicked(null), [])
  // ?backtest, ?report and ?ads open those screens; the top menu switches without reloading
  const [view, setView] = useState<View>(() => viewOf(new URLSearchParams(location.search)))
  useEffect(() => {
    const back = () => setView(viewOf(new URLSearchParams(location.search)))
    addEventListener('popstate', back)
    return () => removeEventListener('popstate', back)
  }, [])

  // ?replay=reloop plays another market's example; ?replay=live_<id> an admin's live run
  const [name] = useState(new URLSearchParams(location.search).get('replay') ?? 'engine')
  useEffect(() => {
    const live = name.match(/^live_([a-z0-9]{12})$/)
    let key = ''
    try { key = localStorage.getItem('rehearsal-admin-key') ?? '' } catch { /* private window */ }
    fetch(live ? `/api/live/${live[1]}/replay` : `/replays/${encodeURIComponent(name)}.json`,
      { headers: live ? { 'X-Admin-Key': key } : {} }).then(r => r.json()).then(setReplay)
  }, [name])

  useEffect(() => {
    if (!replay || !playing) return
    const days = replay.meta.days
    let raf = 0
    const tick = (now: number) => {
      const dt = last.current === null ? 0 : (now - last.current) / 1000
      last.current = now
      setT(prev => {
        const next = Math.min(days, prev + (dt * days) / PLAY_SECONDS)
        if (next >= days) setPlaying(false)
        return next
      })
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => { cancelAnimationFrame(raf); last.current = null }
  }, [replay, playing])

  if (!replay) return <Stage>{null}</Stage>

  const { meta, plans, verdict } = replay
  const person = picked && replay.people[picked.plan].find(p => p.id === picked.id)
  const done = t >= meta.days
  const go = (v: View) => {
    if (v === view) return
    setPlaying(false)
    setPicked(null)
    history.pushState(null, '', `/?replay=${encodeURIComponent(name)}${v === 'replay' ? '' : `&${v}`}${STILL ? '&still' : ''}`)
    setView(v)
  }
  const views: View[] = plans.a.report ? ['replay', 'report', 'ads', 'backtest'] : ['replay', 'backtest']
  const nav = (context: ReactNode) => (
    <Nav context={context} view={view} views={views} onView={go} tryHref={`/?new&replay=${encodeURIComponent(name)}`} />
  )
  const where = <>{meta.app} · {packOf(replay).header}{meta.placeholder && ' · placeholder data'}</>
  const drawer = picked && person &&
    <Drawer key={`${picked.plan}:${picked.id}`} replay={replay} replayName={name} plan={picked.plan} person={person} onClose={close} />
  const pick = (plan: PlanKey, id: number) => { setPlaying(false); setPicked({ plan, id }) }

  if (view === 'backtest') return <Stage><Backtest nav={nav} /></Stage>
  if (view === 'report') return <Stage>{nav(where)}<Report replay={replay} onPick={pick} />{drawer}</Stage>
  if (view === 'ads') return <Stage>{nav(where)}<Ads replay={replay} /></Stage>

  const toggle = () => {
    if (!playing && done) setT(0)
    setPlaying(!playing)
  }

  return (
    <Stage>
      <div className="pointer-events-none absolute -right-[200px] -bottom-[300px] h-[900px] w-[1200px]"
        style={{ background: 'radial-gradient(closest-side, rgb(27 91 245 / .07), rgb(27 91 245 / 0))' }} />

      {nav(<>{where} · {meta.market} · {meta.days} days</>)}

      <section className="absolute top-28 left-16 w-[1120px]">
        <h1 className="text-headline font-semibold text-strong">
          {done ? <Headline text={verdict.headline} /> : 'Two launches.'}
        </h1>
        <p className="mt-6 max-w-[1120px] text-body">
          {done
            ? verdict.reason
            : `Same $${meta.budget_usd.toLocaleString('en-US')} budget. ${(meta.agents ?? replay.people.a.length).toLocaleString('en-US')} simulated people each. ${meta.days} days in ${PLAY_SECONDS} seconds.`}
        </p>
      </section>

      <section className="absolute top-[120px] right-16 flex flex-col items-end text-right">
        <div className="flex gap-14">
          {numbersAt(replay, t).map(m => (
            <div key={m.label}>
              <div className={`text-number font-medium tabular-nums ${verdict.winner === 'a' ? 'text-plan-a' : 'text-plan-b'}`}>
                {done ? <CountUp value={m.value} /> : <span className="text-dot-idle">—</span>}
              </div>
              <div className="label mt-4">
                {m.label}{done && <> · <span className={m.otherPlan === 'a' ? 'text-plan-a' : 'text-plan-b'}>
                  {m.otherPlan.toUpperCase()} {m.other.toLocaleString('en-US')}</span></>}
              </div>
            </div>
          ))}
        </div>
        <p className="mt-4 max-w-[560px] text-body text-dim">{noteOf(replay)}</p>
      </section>

      <section className="absolute top-80 right-16 left-16 grid grid-cols-2 gap-16">
        {PLANS.map(p => (
          <div key={p}>
            <div className="label flex items-baseline gap-4">
              <span className={p === 'a' ? 'text-plan-a' : 'text-plan-b'}>{plans[p].name}</span>
              <span>{plans[p].summary}</span>
              {p === 'b' && (
                <span className="ml-auto flex gap-6">
                  <span><i className="mr-2 inline-block size-2 rounded-full bg-strong" />{packOf(replay).legend[0]}</span>
                  <span><i className="mr-2 inline-block size-2 rounded-full bg-text opacity-60" />{packOf(replay).legend[1]}</span>
                  <span><i className="mr-2 inline-block size-2 rounded-full bg-text opacity-20" />{packOf(replay).legend[2]}</span>
                </span>
              )}
            </div>
            <PlanMap replay={replay} plan={p} t={t} selected={picked?.plan === p ? picked.id : undefined}
              onPick={id => pick(p, id)} />
          </div>
        ))}
      </section>

      <section className="absolute top-[836px] right-16 left-16 text-dim">
        <Funnel replay={replay} t={t} />
      </section>

      <section className="absolute top-[988px] right-16 left-16">
        <Timeline replay={replay} t={t} playing={playing}
          onSeek={d => { setPlaying(false); setT(d) }} onToggle={toggle} />
      </section>

      {drawer}
    </Stage>
  )
}
