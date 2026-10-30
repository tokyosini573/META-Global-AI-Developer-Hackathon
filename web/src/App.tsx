import { useCallback, useEffect, useRef, useState } from 'react'
import { Backtest } from './components/Backtest'
import { Drawer } from './components/Drawer'
import { Funnel } from './components/Funnel'
import { Input } from './components/Input'
import { PlanMap } from './components/PlanMap'
import { Stage, STILL } from './components/Stage'
import { Timeline } from './components/Timeline'
import { metricsAt, PLANS, type PlanKey, type Replay } from './replay'

const PLAY_SECONDS = 30 // 90 days = 30 s

// In "Plan B wins.", color only the plan name with its plan color
function Headline({ text }: { text: string }) {
  const m = text.match(/^(.*Plan )([AB])(.*)$/)
  if (!m) return <>{text}</>
  return <>{m[1]}<span className={m[2] === 'A' ? 'text-plan-a' : 'text-plan-b'}>{m[2]}</span>{m[3]}</>
}

// Count a value like "+48%" up from 0 over 0.4 s
function CountUp({ value }: { value: string }) {
  const m = value.match(/^([^\d]*)([\d.]+)(.*)$/)
  const [shown, setShown] = useState(STILL && m ? Number(m[2]) : 0)
  useEffect(() => {
    if (!m || STILL) return
    const target = Number(m[2]), start = performance.now()
    let raf = 0
    const tick = (now: number) => {
      const k = Math.min(1, (now - start) / 400)
      setShown(target * (1 - (1 - k) ** 3))
      if (k < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [value]) // eslint-disable-line react-hooks/exhaustive-deps
  if (!m) return <>{value}</>
  const digits = m[2].includes('.') ? m[2].split('.')[1].length : 0
  return <>{m[1]}{shown.toFixed(digits)}{m[3]}</>
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
  // ?new opens "Try it yourself": the input screen, filled with the example
  const [input, setInput] = useState(new URLSearchParams(location.search).has('new'))
  // ?backtest opens the backtest screen
  const [backtest, setBacktest] = useState(new URLSearchParams(location.search).has('backtest'))

  // ?replay=demo plays the old hand-made placeholder instead of the engine output
  const name = new URLSearchParams(location.search).get('replay') ?? 'engine'
  useEffect(() => {
    fetch(`/replays/${encodeURIComponent(name)}.json`).then(r => r.json()).then(setReplay)
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
  if (backtest) {
    return (
      <Stage>
        <Backtest onHome={() => { history.replaceState(null, '', location.pathname); setBacktest(false) }} />
      </Stage>
    )
  }

  if (input) {
    return (
      <Stage>
        <div className="pointer-events-none absolute -right-[200px] -bottom-[300px] h-[900px] w-[1200px]"
          style={{ background: 'radial-gradient(closest-side, rgb(79 124 255 / .10), rgb(79 124 255 / 0))' }} />
        <Input replay={replay} onDone={() => { history.replaceState(null, '', location.pathname); setInput(false); setT(0); setPlaying(true) }} />
      </Stage>
    )
  }

  const toggle = () => {
    if (!playing && done) setT(0)
    setPlaying(!playing)
  }

  return (
    <Stage>
      <div className="pointer-events-none absolute -right-[200px] -bottom-[300px] h-[900px] w-[1200px]"
        style={{ background: 'radial-gradient(closest-side, rgb(79 124 255 / .10), rgb(79 124 255 / 0))' }} />

      <header className="label absolute top-12 right-16 left-16 flex justify-between">
        <span className="text-strong">Rehearsal</span>
        <span>
          Swipe dating app · {meta.market} · {meta.days} days · replay
          {meta.placeholder && ' · placeholder data'}
          {' · '}
          <button onClick={() => { setPlaying(false); setPicked(null); setBacktest(true) }}
            className="label cursor-pointer text-strong">Backtest</button>
          {' · '}
          <button onClick={() => { setPlaying(false); setPicked(null); setInput(true) }}
            className="label cursor-pointer text-strong">Try it yourself</button>
        </span>
      </header>

      <section className="absolute top-28 left-16 w-[900px]">
        <h1 className="text-headline font-semibold text-strong">
          {done ? <Headline text={verdict.headline} /> : 'Two launches.'}
        </h1>
        <p className="mt-6 max-w-[760px] text-body">
          {done
            ? verdict.reason
            : `Same $${meta.budget_usd.toLocaleString('en-US')} budget. ${replay.people.a.length.toLocaleString('en-US')} people each. ${meta.days} days in ${PLAY_SECONDS} seconds.`}
        </p>
      </section>

      <section className="absolute top-[120px] right-16 flex gap-16">
        {metricsAt(replay, t).map(m => (
          <div key={m.label}>
            <div className="text-number font-medium text-plan-b tabular-nums">
              {done ? <CountUp value={m.value} /> : <span className="text-dot-idle">—</span>}
            </div>
            <div className="label mt-4">{m.label}</div>
          </div>
        ))}
      </section>

      <section className="absolute top-80 right-16 left-16 grid grid-cols-2 gap-16">
        {PLANS.map(p => (
          <div key={p}>
            <div className="label flex items-baseline gap-4">
              <span className={p === 'a' ? 'text-plan-a' : 'text-plan-b'}>{plans[p].name}</span>
              <span>{plans[p].summary}</span>
              {p === 'b' && (
                <span className="ml-auto flex gap-6">
                  <span><i className="mr-2 inline-block size-2 rounded-full bg-strong" />Paying</span>
                  <span><i className="mr-2 inline-block size-2 rounded-full bg-text opacity-60" />Using</span>
                  <span><i className="mr-2 inline-block size-2 rounded-full bg-text opacity-20" />Quit</span>
                </span>
              )}
            </div>
            <PlanMap replay={replay} plan={p} t={t} selected={picked?.plan === p ? picked.id : undefined}
              onPick={id => { setPlaying(false); setPicked({ plan: p, id }) }} />
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

      {picked && person && <Drawer key={`${picked.plan}:${picked.id}`} replay={replay} replayName={name} plan={picked.plan} person={person} onClose={close} />}
    </Stage>
  )
}
