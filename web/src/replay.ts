// Replay format and derived numbers. The format is defined in docs/replay-format.md.

import type { Brief } from './brief'

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
  // v2 (docs/replay-format.md "Version 2")
  kind?: string               // id in meta.kinds
  ad_id?: string | null       // the ad they saw, or null
  signed_up?: number | null   // day they finished sign-up
}

// What the one-person drawer shows (written by engine/world/output.py)
export type Story = {
  sex: 'm' | 'w'
  persona: string | null
  ad: string                  // screen they saw when reached (web/public/screens/<name>.png)
  last: string | null         // the last paywall they saw
  diary: [number, string, string | null][] // [day shown, what happened, their own words]
  quit_reason?: string | null // v2: why they stopped, in their own words
  stop?: { to: FunnelKey; words: string | null } // v2: the first step they never reached, and why
}

// v2: one step of the funnel, one ad, one kind of person, one row of the report
export type FunnelKey = 'saw' | 'installed' | 'signed_up' | 'first' | 'active' | 'paid'
export type Ad = { id: string; angle: string; line: string; screen: string }
export type Kind = { id: string; name: string; share: number; side?: string }
export type Theme = { name: string; count: number; quote: string; ids: number[] }
export type ReportStep = { from: FunnelKey; to: FunnelKey; left: number; themes: Theme[] }

export type Replay = {
  version: 1 | 2
  meta: {
    app: string; market: string; days: number; budget_usd: number; placeholder: boolean
    people_types?: string[] // the kinds of people Muse Wonder designed for this market
    runs?: number           // Monte Carlo runs behind the verdict
    pack?: Pack             // the market's own words (engine/packs); dating when absent
    live?: boolean          // an admin's live run from uploaded screens (engine/live.py)
    // v2
    brief?: Brief           // the brief this run used (docs/brief-format.md)
    note?: string           // "Simulated, calibrated to public benchmarks. Not observed."
    agents?: number         // simulated people reached in each experiment
    funnel?: { key: FunnelKey; label: string }[]
    ads?: Ad[]
    kinds?: Kind[]
  }
  plans: Record<PlanKey, {
    name: string; summary: string; events: { day: number; label: string }[]
    card?: { title: string; where: string; ads: string; price: string } // the plan in plain words (input screen)
    // v2
    changes?: string                                  // what this experiment changes
    range?: Partial<Record<FunnelKey, [number, number]>> // 10th-90th percentile across runs
    report?: ReportStep[]                             // where people left and why
    ads?: { line: string; cells: Record<string, Record<string, [number, number]>> } // kind -> ad -> [saw, installed]
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
  screens?: string[]          // what people see, for the input screen (names in web/public/screens, or live paths)
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

// v2: the funnel steps, in order. v1 files have no meta.funnel: their steps come from the pack,
// without sign-up (v1 people have no sign-up day).
export function funnelOf(r: Replay): { key: FunnelKey; label: string }[] {
  if (r.meta.funnel) return r.meta.funnel
  const pack = packOf(r)
  return [
    { key: 'saw', label: 'Saw an ad' }, { key: 'installed', label: 'Installed' },
    { key: 'first', label: pack.stages[1] }, { key: 'active', label: `Using on day ${r.meta.days}` },
    ...(pack.id === 'dating' ? [{ key: 'paid' as const, label: 'Paid' }] : []),
  ]
}

// Whether a person counts toward a step at day t (docs/replay-format.md "Version 2")
export function atStep(p: Person, key: FunnelKey, t: number): boolean {
  switch (key) {
    case 'saw': return by(p.reached, t)
    case 'installed': return by(p.installed, t)
    case 'signed_up': return by(p.signed_up ?? null, t)
    case 'first': return by(p.matched, t)
    case 'active': return by(p.signed_up === undefined ? p.installed : p.signed_up, t) && !by(p.quit, t)
    case 'paid': return by(p.paid, t)
  }
}

export const countAt = (people: Person[], key: FunnelKey, t: number) =>
  people.reduce((n, p) => n + (atStep(p, key, t) ? 1 : 0), 0)

// The three numbers on the main screen: the winner's count at day t and the other plan's.
// Dating counts payers; the other markets count completed sales or rides (matches by day t).
export function numbersAt(r: Replay, t: number) {
  const steps = funnelOf(r), label = (k: FunnelKey) => steps.find(s => s.key === k)?.label ?? k
  const goal = swipe(r)
    ? { label: label('paid'), of: (k: PlanKey) => countAt(r.people[k], 'paid', t) }
    : { label: packOf(r).numbers[0], of: (k: PlanKey) => r.matches[k].filter(m => m[2] <= t).length }
  const w = r.verdict.winner, l: PlanKey = w === 'a' ? 'b' : 'a'
  return [goal, ...(['first', 'active'] as const).map(k => ({ label: label(k), of: (p: PlanKey) => countAt(r.people[p], k, t) }))]
    .map(n => ({ label: n.label, value: n.of(w), other: n.of(l), otherPlan: l }))
}

// v2: the words under a step's count in the report ("864 did not install")
export function leftWords(to: FunnelKey, label: string): string {
  if (to === 'installed') return 'did not install'
  if (to === 'signed_up') return 'left at sign-up'
  if (to === 'active') return 'quit'
  if (to === 'paid') return 'did not pay'
  return `never ${label.charAt(0).toLowerCase()}${label.slice(1)}`
}

// P7: the line next to every number. v1 files have none, so they get the same words.
export const noteOf = (r: Replay) => r.meta.note ?? 'Simulated, calibrated to public benchmarks. Not observed.'

// A screen name as an image address: web/public/screens/<name>.png, or a live run's path
export const screenSrc = (s: string) => (s.startsWith('/') ? s : `/screens/${s}.png`)
