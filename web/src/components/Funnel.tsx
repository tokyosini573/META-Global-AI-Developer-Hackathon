import { useMemo } from 'react'
import { FUNNEL_STAGES, funnelAt, PLANS, type Replay } from '../replay'

const W = 1792, H = 136, TOP = 32, ROW = 44, GAP = 8

// One river per plan. Thickness = people still in at that step, on one scale for both plans.
function river(f: number[], total: number, cy: number) {
  const step = W / (f.length - 1)
  const hw = (v: number) => Math.max(1.5, (v / total) * ROW / 2)
  let d = `M 0 ${cy - hw(f[0])}`
  for (let i = 1; i < f.length; i++) {
    const xa = (i - 1) * step, xb = i * step, xm = (xa + xb) / 2
    d += ` C ${xm} ${cy - hw(f[i - 1])}, ${xm} ${cy - hw(f[i])}, ${xb} ${cy - hw(f[i])}`
  }
  d += ` L ${W} ${cy + hw(f[f.length - 1])}`
  for (let i = f.length - 1; i > 0; i--) {
    const xa = (i - 1) * step, xb = i * step, xm = (xa + xb) / 2
    d += ` C ${xm} ${cy + hw(f[i])}, ${xm} ${cy + hw(f[i - 1])}, ${xa} ${cy + hw(f[i - 1])}`
  }
  return d + ' Z'
}

export function Funnel({ replay, t }: { replay: Replay; t: number }) {
  const step = W / (FUNNEL_STAGES.length - 1)
  const total = useMemo(
    () => Math.max(1, ...PLANS.map(k => funnelAt(replay.people[k], replay.meta.days)[0])), [replay])
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
      {FUNNEL_STAGES.map((name, i) => (
        <g key={name}>
          <text x={i * step} y={13} textAnchor={i === 0 ? 'start' : i === FUNNEL_STAGES.length - 1 ? 'end' : 'middle'}
            className="label" fill="currentColor">{name}</text>
          <line x1={i * step} y1={TOP - 4} x2={i * step} y2={H} className="stroke-line" />
        </g>
      ))}
      {PLANS.map((plan, row) => {
        const people = replay.people[plan]
        return (
          <path key={plan} d={river(funnelAt(people, t), total, TOP + row * (ROW + GAP) + ROW / 2)}
            className={plan === 'a' ? 'fill-plan-a' : 'fill-plan-b'} fillOpacity={plan === 'b' ? 0.9 : 0.75} />
        )
      })}
    </svg>
  )
}
