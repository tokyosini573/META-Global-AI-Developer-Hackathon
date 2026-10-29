// Replay format and derived numbers. The format is defined in docs/replay-format.md.

export type PlanKey = 'a' | 'b'
export const PLANS: PlanKey[] = ['a', 'b']

export type Person = {
  id: number
  name: string
  age: number
  place: string
  lon: number
  lat: number
  reached: number | null
  installed: number | null
  matched: number | null
  quit: number | null
  paid: number | null
}

export type Replay = {
  version: 1
  meta: { app: string; market: string; days: number; budget_usd: number; placeholder: boolean }
  plans: Record<PlanKey, { name: string; summary: string; events: { day: number; label: string }[] }>
  verdict: { winner: PlanKey; headline: string; reason: string }
  people: Record<PlanKey, Person[]>
  matches: Record<PlanKey, [number, number, number][]>
}

export type State = 'hidden' | 'idle' | 'quit' | 'using' | 'paying'

const by = (day: number | null, t: number) => day !== null && day <= t

export function stateAt(p: Person, t: number): State {
  if (!by(p.reached, t)) return 'hidden'
  if (!by(p.installed, t)) return 'idle'
  if (by(p.paid, t)) return 'paying'
  if (by(p.quit, t)) return 'quit'
  return 'using'
}

export const FUNNEL_STAGES = ['Reached', 'Installed', 'Got a match', 'Still using', 'Paying']

export function funnelAt(people: Person[], t: number): number[] {
  const f = [0, 0, 0, 0, 0]
  for (const p of people) {
    if (!by(p.reached, t)) continue
    f[0]++
    if (!by(p.installed, t)) continue
    f[1]++
    if (by(p.matched, t)) f[2]++
    if (!by(p.quit, t)) f[3]++
    if (by(p.paid, t)) f[4]++
  }
  return f
}

function quitWeekOneShare(people: Person[], t: number): number | null {
  let installed = 0, quit = 0
  for (const p of people) {
    if (!by(p.installed, t)) continue
    installed++
    if (by(p.quit, t) && p.quit! - p.installed! <= 7) quit++
  }
  return installed ? quit / installed : null
}

const pct = (b: number, a: number) => {
  const v = Math.round((b / a - 1) * 100)
  return `${v >= 0 ? '+' : '−'}${Math.abs(v)}%`
}

// The three on-screen numbers. '—' when they can't be computed.
export function metricsAt(r: Replay, t: number) {
  const fa = funnelAt(r.people.a, t), fb = funnelAt(r.people.b, t)
  const qa = quitWeekOneShare(r.people.a, t), qb = quitWeekOneShare(r.people.b, t)
  return [
    { label: 'Paying users', value: fa[4] ? pct(fb[4], fa[4]) : '—' },
    { label: 'Got a match', value: fa[2] ? `${(fb[2] / fa[2]).toFixed(1)}×` : '—' },
    { label: 'Quit in week one', value: qa && qb !== null ? pct(qb, qa) : '—' },
  ]
}
