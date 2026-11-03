import { Fragment, useMemo } from 'react'
import { countAt, funnelOf, PLANS, type Replay } from '../replay'

// The funnel at day t: one row per plan, one bar per step. A bar fills toward the bigger of the two
// plans at that step on the last day, so the rows compare A with B step by step.
export function Funnel({ replay, t }: { replay: Replay; t: number }) {
  const steps = funnelOf(replay)
  const end = useMemo(() => steps.map(s =>
    Math.max(1, ...PLANS.map(k => countAt(replay.people[k], s.key, replay.meta.days)))), [replay, steps])
  return (
    <div className="grid items-center gap-x-2 gap-y-2" style={{ gridTemplateColumns: `160px repeat(${steps.length}, 1fr)` }}>
      <div />
      {steps.map(s => <div key={s.key} className="label truncate">{s.label}</div>)}
      {PLANS.map(k => (
        <Fragment key={k}>
          <div className={`label ${k === 'a' ? 'text-plan-a' : 'text-plan-b'}`}>{replay.plans[k].name}</div>
          {steps.map((s, i) => {
            const n = countAt(replay.people[k], s.key, t)
            return (
              <div key={s.key} className={`relative h-10 overflow-hidden rounded-card ${k === 'a' ? 'bg-plan-a/10' : 'bg-plan-b/10'}`}>
                <div className={`absolute inset-y-0 left-0 ${k === 'a' ? 'bg-plan-a/30' : 'bg-plan-b/25'}`}
                  style={{ width: `${(n / end[i]) * 100}%` }} />
                <span className="relative px-3 text-body leading-10 font-medium text-strong tabular-nums">
                  {n.toLocaleString('en-US')}
                </span>
              </div>
            )
          })}
        </Fragment>
      ))}
    </div>
  )
}
