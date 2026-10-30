import { useEffect, useState } from 'react'
import { type PlanKey, type Person, type Replay } from '../replay'
import { STILL } from './Stage'

const day = (d: number) => Math.floor(d) + 1 // day 0.4 of the run is "Day 1" on screen

function outcome(p: Person, days: number) {
  if (p.installed === null) return `Did not install the app on day ${day(p.reached!)}.`
  if (p.paid !== null) return `Paying since day ${day(p.paid)}.`
  if (p.quit !== null) return `Deleted the app on day ${day(p.quit)}.`
  return `Still using the app on day ${days}.`
}

// The real screens the person (and the model deciding for them) looked at
function Phone({ label, screen }: { label: string; screen: string }) {
  return (
    <div>
      <div className="label mb-2">{label}</div>
      <div className="h-[300px] overflow-hidden rounded-card border border-line bg-bg">
        <img src={`/screens/${screen}.png`} alt="" className="size-full object-cover"
          style={{ objectPosition: screen.startsWith('paywall') ? 'center bottom' : 'center 40%' }} />
      </div>
    </div>
  )
}

export function Drawer({ replay, plan, person: p, onClose }: {
  replay: Replay; plan: PlanKey; person: Person; onClose: () => void
}) {
  const [open, setOpen] = useState(STILL)
  useEffect(() => {
    const id = requestAnimationFrame(() => setOpen(true))
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    addEventListener('keydown', esc)
    return () => { cancelAnimationFrame(id); removeEventListener('keydown', esc) }
  }, [onClose])

  const s = p.story
  const she = s?.sex === 'w' ? 'she' : 'he'
  const left = p.paid !== null ? `Where ${she} paid` : p.quit !== null ? `Where ${she} left` : `Last paywall ${she} saw`
  return (
    <>
      <div className="absolute inset-0 bg-bg/55" onClick={onClose} />
      <aside className="absolute top-0 right-0 h-[1080px] w-[560px] rounded-l-card border-l border-line bg-surface p-12
        transition-transform duration-[250ms] ease-out" style={{ transform: open ? 'none' : 'translateX(100%)' }}>
        <button onClick={onClose} aria-label="Close" className="absolute top-10 right-10 cursor-pointer">
          <svg width="16" height="16" viewBox="0 0 16 16"><path d="M2 2 L14 14 M14 2 L2 14" stroke="currentColor" strokeWidth="1.5" className="text-dim" /></svg>
        </button>
        <div className={`label ${plan === 'a' ? 'text-plan-a' : 'text-plan-b'}`}>{replay.plans[plan].name} · Person {p.id}</div>
        <h2 className="mt-6 text-number font-medium text-strong">{p.name}, {p.age}</h2>
        <p className="mt-4 text-body text-dim">{p.place}. {outcome(p, replay.meta.days)}</p>
        {s && (
          <>
            <div className="mt-12 grid grid-cols-2 gap-6">
              <Phone label={`The ${s.ad === 'ad' ? 'ad' : 'page'} ${she} saw`} screen={s.ad} />
              {s.last && <Phone label={left} screen={s.last} />}
            </div>
            <div className="mt-12 grid grid-cols-[72px_1fr] gap-y-4">
              {s.diary.map(([d, what, words], i) => (
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
      </aside>
    </>
  )
}
