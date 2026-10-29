import { useEffect, useRef, useState } from 'react'
import { Funnel } from './components/Funnel'
import { PlanMap } from './components/PlanMap'
import { Stage, STILL } from './components/Stage'
import { Timeline } from './components/Timeline'
import { metricsAt, PLANS, type Replay } from './replay'

const PLAY_SECONDS = 30 // 90일 = 30초

// "Plan B wins." 에서 계획 글자만 계획 색으로
function Headline({ text }: { text: string }) {
  const m = text.match(/^(.*Plan )([AB])(.*)$/)
  if (!m) return <>{text}</>
  return <>{m[1]}<span className={m[2] === 'A' ? 'text-plan-a' : 'text-plan-b'}>{m[2]}</span>{m[3]}</>
}

// "+48%" 같은 값을 0에서부터 0.4초 동안 굴려 올린다
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
  // ?day=90 으로 열면 그날에 멈춘 화면 (스크린샷용). 아니면 열자마자 재생.
  const fixedDay = new URLSearchParams(location.search).get('day')
  const [t, setT] = useState(fixedDay ? Number(fixedDay) : 0)
  const [playing, setPlaying] = useState(!fixedDay)
  const last = useRef<number | null>(null)

  useEffect(() => {
    fetch('/replays/demo.json').then(r => r.json()).then(setReplay)
  }, [])

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
  const done = t >= meta.days
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
            <PlanMap replay={replay} plan={p} t={t} />
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
    </Stage>
  )
}
