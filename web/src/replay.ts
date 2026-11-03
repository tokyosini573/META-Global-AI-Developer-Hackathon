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
  story?: Story
}

// What the one-person drawer shows (written by engine/world/output.py)
export type Story = {
  sex: 'm' | 'w'
  persona: string | null
  ad: string                  // screen they saw when reached (web/public/screens/<name>.png)
  last: string | null         // the last paywall they saw
  diary: [number, string, string | null][] // [day shown, what happened, their own words]
}

export type Replay = {
  version: 1
  meta: {
    app: string; market: string; days: number; budget_usd: number; placeholder: boolean
    people_types?: string[] // the kinds of people Muse Wonder designed for this market
    runs?: number           // Monte Carlo runs behind the verdict
    pack?: Pack             // the market's own words (engine/packs); dating when absent
  }
  plans: Record<PlanKey, {
    name: string; summary: string; events: { day: number; label: string }[]
    card?: { title: string; where: string; ads: string; price: string } // the plan in plain words (input screen)
  }>
  verdict: { winner: PlanKey; headline: string; reason: string }
  people: Record<PlanKey, Person[]>
  matches: Record<PlanKey, [number, number, number][]>
}

// The words a market pack uses on screen (engine/packs/<id>.py "labels")
export type Pack = {
  id: string; header: string; category?: string
  stages: string[]; numbers: string[]; legend: string[]; goal: string
  ask: { converted: string; quit: string; using: string }
  last_screen: string; since?: string
}

const DATING: Pack = {
  id: 'dating', header: 'Swipe dating app',
  stages: ['Installed', 'Got a match', 'Still using', 'Paying'],
  numbers: ['Paying users', 'Got a match', 'Quit in week one'], legend: ['Paying', 'Using', 'Quit'],
  goal: 'paying users',
  ask: { converted: 'Why did you pay?', quit: 'Why did you delete it?', using: 'What do you think of it so far?' },
  last_screen: 'Where {they} left', since: 'Paying since day {day}.',
}

export const packOf = (r: Replay): Pack => r.meta.pack ?? DATING
const swipe = (r: Replay) => packOf(r).id === 'dating'

export type State = 'hidden' | 'idle' | 'quit' | 'using' | 'paying'

const by = (day: number | null, t: number) => day !== null && day <= t

export function stateAt(p: Person, t: number): State {
  if (!by(p.reached, t)) return 'hidden'
  if (!by(p.installed, t)) return 'idle'
  if (by(p.paid, t)) return 'paying'
  if (by(p.quit, t)) return 'quit'
  return 'using'
}

// Starts at "Installed": only ~9% of people reached by an ad install, so a "Reached"
// stage would squeeze everything after it into a hairline. Dating ends at paying; the other
// markets end at people who traded and are still there.
export function funnelAt(people: Person[], t: number, dating = true): number[] {
  const f = [0, 0, 0, 0]
  for (const p of people) {
    if (!by(p.installed, t)) continue
    f[0]++
    if (by(p.matched, t)) f[1]++
    if (!by(p.quit, t)) f[2]++
    if (dating ? by(p.paid, t) : by(p.matched, t) && !by(p.quit, t)) f[3]++
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

const pts = (b: number, a: number) => {
  const v = Math.round((b - a) * 100)
  return `${v >= 0 ? '+' : '−'}${Math.abs(v)} pts`
}

// The three on-screen numbers. '—' when they can't be computed.
export function metricsAt(r: Replay, t: number) {
  const d = swipe(r), [goal, success, quit] = packOf(r).numbers
  const fa = funnelAt(r.people.a, t, d), fb = funnelAt(r.people.b, t, d)
  const qa = quitWeekOneShare(r.people.a, t), qb = quitWeekOneShare(r.people.b, t)
  // dating counts paying users; the other markets count completed sales or rides
  const done = (k: PlanKey) => d ? funnelAt(r.people[k], t, d)[3] : r.matches[k].filter(m => m[2] <= t).length
  const ga = done('a'), gb = done('b')
  return [
    { label: goal, value: ga ? pct(gb, ga) : gb ? 'only B' : '—' },
    // Percentage points of installers, so it still reads when Plan A has no match at all
    { label: success, value: fa[0] && fb[0] ? pts(fb[1] / fb[0], fa[1] / fa[0]) : '—' },
    { label: quit, value: qa && qb !== null ? pct(qb, qa) : '—' },
  ]
}
