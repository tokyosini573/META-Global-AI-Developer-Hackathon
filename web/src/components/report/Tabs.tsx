import { useState } from 'react'
import { PLANS, type PlanKey, type Replay } from '../../replay'

// Which plan a report screen shows: ?plan=a on load (screenshots), else the winner
export function usePlan(replay: Replay) {
  return useState<PlanKey>(() => {
    const q = new URLSearchParams(location.search).get('plan')
    return q === 'a' || q === 'b' ? q : replay.verdict.winner
  })
}

export function Tabs({ replay, plan, onPlan }: { replay: Replay; plan: PlanKey; onPlan: (p: PlanKey) => void }) {
  return (
    <div className="flex gap-2">
      {PLANS.map(k => (
        <button key={k} onClick={() => onPlan(k)}
          className={`cursor-pointer rounded-card border px-6 py-2 text-body ${k === plan
            ? 'border-strong bg-strong text-white' : 'border-line text-text hover:border-blue-200'}`}>
          <span className={`mr-3 inline-block size-2 rounded-full align-middle ${k === 'a' ? 'bg-plan-a' : 'bg-plan-b'}`} />
          {replay.plans[k].name}
        </button>
      ))}
    </div>
  )
}
