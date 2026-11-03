import { useState } from 'react'
import { funnelOf, leftWords, noteOf, type PlanKey, type Replay } from '../replay'
import { ThemeList } from './report/ThemeList'
import { Tabs, usePlan } from './report/Tabs'

const TOP = 320, BOTTOM = 984, GAP = 16

// "Where did people leave, and why?" (?report): for each step, the people who never reached the next
// one and up to three reasons in their own words. Counts come from plans[k].report (docs/replay-format.md).
export function Report({ replay, onPick }: { replay: Replay; onPick: (plan: PlanKey, id: number) => void }) {
  const [plan, setPlan] = usePlan(replay)
  // ?theme=<step>:<theme> opens one reason's people on load (screenshots)
  const [open, setOpen] = useState<[number, number] | null>(() => {
    const m = new URLSearchParams(location.search).get('theme')?.match(/^(\d+):(\d+)$/)
    return m ? [Number(m[1]), Number(m[2])] : null
  })
  const label = new Map(funnelOf(replay).map(s => [s.key, s.label]))
  const steps = replay.plans[plan].report ?? []
  const rowH = (BOTTOM - TOP - GAP * (steps.length - 1)) / Math.max(1, steps.length)
  const tint = plan === 'a' ? 'text-plan-a' : 'text-plan-b'
  const name = (i: number) => `${label.get(steps[i].from)} → ${label.get(steps[i].to)?.toLowerCase()}`
  const theme = open && steps[open[0]]?.themes[open[1]]

  return (
    <>
      <section className="absolute top-28 right-16 left-16 flex items-end justify-between">
        <div>
          <h1 className="text-headline font-semibold text-strong">Where people left, and why.</h1>
          <p className="mt-6 text-lead">In their own words. Grouped by Muse Wonder, counted by the engine.</p>
        </div>
        <Tabs replay={replay} plan={plan} onPlan={p => { setPlan(p); setOpen(null) }} />
      </section>

      <section className="absolute right-16 left-16 grid" style={{ top: TOP, rowGap: GAP }}>
        {steps.map((s, i) => (
          <div key={`${s.from}-${s.to}`} className="grid grid-cols-[320px_1fr_1fr_1fr] gap-4" style={{ height: rowH }}>
            <div className="flex flex-col justify-center">
              <div className="label">{name(i)}</div>
              <div className="mt-2 flex items-baseline gap-3">
                <span className="text-number font-medium text-strong tabular-nums">{s.left.toLocaleString('en-US')}</span>
                <span className="text-body text-dim">{leftWords(s.to, label.get(s.to) ?? s.to)}</span>
              </div>
            </div>
            {s.themes.slice(0, 3).map((th, j) => (
              <button key={th.name} onClick={() => setOpen([i, j])}
                className="cursor-pointer overflow-hidden rounded-card bg-surface px-6 py-4 text-left hover:bg-blue-50">
                <div className="truncate text-body font-medium text-strong">
                  {th.name} <span className={`tabular-nums ${tint}`}>· {th.count.toLocaleString('en-US')}</span>
                </div>
                <div className="mt-1 line-clamp-2 text-body text-text">“{th.quote}”</div>
              </button>
            ))}
            {!s.themes.length && (
              <div className="col-span-3 flex items-center text-body text-dim">
                {s.left ? 'Nobody said why.' : 'Nobody left here.'}
              </div>
            )}
          </div>
        ))}
      </section>

      <p className="absolute bottom-10 left-16 text-body text-dim">
        {noteOf(replay)} When people quit follows public retention curves; why they quit is in their own words.
      </p>

      {theme && open && (
        <ThemeList key={`${plan}:${open}`} replay={replay} plan={plan} step={name(open[0])} theme={theme}
          onPick={id => onPick(plan, id)} onClose={() => setOpen(null)} />
      )}
    </>
  )
}
