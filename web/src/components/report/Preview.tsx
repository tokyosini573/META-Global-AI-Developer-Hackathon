import { useEffect, useState } from 'react'
import { countAt, funnelOf, leftWords, noteOf, type Replay } from '../../replay'

const STEP_SECONDS = 3

// The front page's report preview: the winner's funnel on the last day, one step lit at a time
// with the words of the people who left there. Every number is counted from the replay.
export function ReportPreview({ replay }: { replay: Replay }) {
  const w = replay.verdict.winner
  const steps = funnelOf(replay)
  const counts = steps.map(s => countAt(replay.people[w], s.key, replay.meta.days))
  const report = replay.plans[w].report ?? []
  // Only the steps people left with a reason to quote
  const lit = steps.map((s, i) => ({ i, r: report.find(r => r.from === s.key && r.themes.length) }))
    .filter((x): x is { i: number; r: NonNullable<typeof x.r> } => !!x.r)
  const [n, setN] = useState(0)
  useEffect(() => {
    if (lit.length < 2) return
    const id = setInterval(() => setN(k => (k + 1) % lit.length), STEP_SECONDS * 1000)
    return () => clearInterval(id)
  }, [lit.length])
  const on = lit[n % Math.max(1, lit.length)]
  const top = counts[0] || 1

  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <span className="label">
          Example · {replay.meta.app}, a {replay.meta.pack?.header.toLowerCase() ?? 'dating app'} ·{' '}
          {(replay.meta.agents ?? replay.people[w].length).toLocaleString('en-US')} simulated people · {replay.meta.days} days
          {replay.meta.placeholder && ' · placeholder data'}
        </span>
        <span className="label text-strong">{replay.plans[w].card?.title ?? replay.plans[w].name}</span>
      </div>
      <h2 className="mt-4 mb-8 text-title font-semibold text-strong">Where people leave, and why.</h2>
      {steps.map((s, i) => (
        <div key={s.key} className="grid grid-cols-[112px_1fr_56px] items-center gap-4 py-2 md:grid-cols-[220px_1fr_96px] md:gap-6">
          <div className="text-body text-strong">{s.label}</div>
          <div className="h-10 overflow-hidden rounded-card bg-surface">
            {/* Square-root widths, so the later steps stay visible next to everyone who saw an ad */}
            <div className={`h-full rounded-card transition-colors duration-300 ${on?.i === i ? 'bg-blue-600' : 'bg-blue-200'}`}
              style={{ width: `${Math.max(1.5, Math.sqrt(counts[i] / top) * 100)}%` }} />
          </div>
          <div className="text-right text-body font-medium text-strong tabular-nums">{counts[i].toLocaleString('en-US')}</div>
        </div>
      ))}
      {on && (
        <div className="mt-6 min-h-[136px] rounded-card bg-blue-50 px-8 py-6">
          <div className="text-body text-blue-900">{on.r.left.toLocaleString('en-US')} {leftWords(on.r.to, steps.find(s => s.key === on.r.to)?.label ?? '')}</div>
          <div key={n} className="mt-2 text-lead text-strong">“{on.r.themes[0].quote}”</div>
        </div>
      )}
      <p className="mt-4 text-body text-dim">{noteOf(replay)}</p>
    </div>
  )
}

// "What you get" pictures for the two report screens, drawn from the same replay
export function MiniReport({ replay }: { replay: Replay }) {
  const w = replay.verdict.winner
  const step = [...(replay.plans[w].report ?? [])].sort((x, y) => y.left - x.left)[0]
  if (!step) return null
  return (
    <div className="flex size-full flex-col justify-center bg-blue-50 px-8">
      {step.themes.map(th => (
        <div key={th.name} className="border-t border-blue-200 py-3 first:border-t-0">
          <div className="truncate text-body font-medium text-strong">{th.name}</div>
          <div className="truncate text-body text-dim">“{th.quote}”</div>
        </div>
      ))}
    </div>
  )
}

export function MiniAds({ replay }: { replay: Replay }) {
  const w = replay.verdict.winner
  const ads = replay.meta.ads ?? [], kinds = (replay.meta.kinds ?? []).slice(0, 5), cells = replay.plans[w].ads?.cells
  const rate = (k: string, a: string) => { const c = cells?.[k]?.[a]; return c && c[0] ? c[1] / c[0] : 0 }
  const all = kinds.flatMap(k => ads.map(a => rate(k.id, a.id))), lo = Math.min(...all), hi = Math.max(...all)
  return (
    <div className="grid size-full content-center gap-2 bg-blue-50 px-8" style={{ gridTemplateColumns: `1fr repeat(${ads.length}, 48px)` }}>
      {kinds.map(k => [
        <div key={k.id} className="truncate text-body text-strong">{k.name}</div>,
        ...ads.map(a => (
          <div key={a.id} className="h-7 rounded-card"
            style={{ background: `color-mix(in srgb, var(--color-blue-600) ${Math.round(10 + (hi > lo ? (rate(k.id, a.id) - lo) / (hi - lo) : 1) * 80)}%, var(--color-bg))` }} />
        )),
      ])}
    </div>
  )
}
