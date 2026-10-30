import { useEffect, useState } from 'react'

// web/public/backtest.json, written by `python -m engine.backtest.run export`
type Marker = { id: string; month: number; called: boolean; p: number; answer: boolean; question: string; note: string; source: string }
type Case = { id: string; name: string; what: string; never_seen: boolean; markers: Marker[] }
type Data = {
  called: { world: number; always_success: number; markers: number }
  cases: Case[]
  commits: { time: string; what: string; hash: string }[]
}

const X0 = 720, X1 = 1840, MAX = 50 // months 0-50 across the stage (the last marker is month 49)
const x = (m: number) => X0 + (m / MAX) * (X1 - X0)
const ROW = 54
const CARD_W = 440

function Axis({ top }: { top: number }) {
  return (
    <>
      {[0, 12, 24, 36, 48].map(m => (
        <span key={m} className="label absolute" style={{ top, left: x(m), transform: m ? 'translateX(-50%)' : undefined }}>
          {m === 48 ? 'Month 48' : m}
        </span>
      ))}
    </>
  )
}

function Row({ c, top, onPoint, pointed }: {
  c: Case; top: number; onPoint: (k: string | null) => void; pointed: string | null
}) {
  const fg = c.never_seen ? 'var(--color-strong)' : 'var(--color-dim)'
  const seen: Record<number, number> = {}
  return (
    <>
      <span className={`absolute left-16 text-body ${c.never_seen ? 'text-strong' : 'text-dim'}`} style={{ top: top + 8 }}>{c.name}</span>
      <span className="label absolute left-[224px]" style={{ top: top + 20 }}>{c.what}</span>
      <svg className="absolute left-0" style={{ top }} width={1920} height={ROW}>
        <line x1={X0} x2={X1} y1={30} y2={30} stroke="var(--color-line)" />
        {c.markers.map(m => {
          const k = (seen[m.month] = (seen[m.month] ?? -1) + 1)
          const cx = x(m.month) + k * 16, key = `${c.id}:${m.id}`
          return (
            <g key={m.id} className="cursor-pointer" onMouseEnter={() => onPoint(key)} onMouseLeave={() => onPoint(null)}>
              <circle cx={cx} cy={30} r={14} fill="transparent" />
              {m.called
                ? <circle cx={cx} cy={30} r={6} fill={fg} />
                : <circle cx={cx} cy={30} r={5.25} fill="var(--color-bg)" stroke={fg} strokeWidth={1.5} />}
              {pointed === key && <circle cx={cx} cy={30} r={12} fill="none" stroke="var(--color-strong)" strokeWidth={1.5} />}
            </g>
          )
        })}
      </svg>
    </>
  )
}

// What one turning point asked, what really happened, and what the runs said
function Card({ c, m, left, top, above }: { c: Case; m: Marker; left: number; top: number; above: boolean }) {
  const said = m.p === 0.5 ? 'half the runs said yes' : `${Math.round(m.p * 100)}% of runs said yes`
  return (
    <div className="pointer-events-none absolute rounded-card border border-line bg-surface p-6" style={{ left, top, width: CARD_W, transform: above ? 'translateY(-100%)' : undefined }}>
      <div className="label">{c.name} · month {m.month} · {m.called ? 'called' : 'missed'}</div>
      <div className="mt-3 text-body text-strong">{m.question}</div>
      <div className="mt-3 text-body">Real: {m.answer ? 'yes' : 'no'}. {m.note}</div>
      <div className="mt-1 text-body text-dim">Rehearsal: {said}.</div>
      <div className="label mt-4">Source · {m.source}</div>
    </div>
  )
}

export function Backtest({ onHome }: { onHome: () => void }) {
  const [data, setData] = useState<Data | null>(null)
  // ?backtest&point=case_5:m2 shows one card (screenshots)
  const [pointed, setPointed] = useState<string | null>(new URLSearchParams(location.search).get('point'))
  useEffect(() => { fetch('/backtest.json').then(r => r.json()).then(setData) }, [])
  if (!data) return null

  const never = data.cases.filter(c => c.never_seen), seen = data.cases.filter(c => !c.never_seen)
  const tops: Record<string, number> = {}
  let top = 352 + 32
  never.forEach(c => { tops[c.id] = top; top += ROW })
  top += 28
  const seenLabel = top
  top += 32
  seen.forEach(c => { tops[c.id] = top; top += ROW })

  let card = null
  if (pointed) {
    const [cid, mid] = pointed.split(':')
    const c = data.cases.find(c => c.id === cid), m = c?.markers.find(m => m.id === mid)
    if (c && m) {
      const k = c.markers.filter(o => o.month === m.month).indexOf(m)
      const cx = x(m.month) + k * 16, cy = tops[cid] + 30
      const left = Math.min(cx - 24, 1856 - CARD_W)
      card = <Card c={c} m={m} left={left} top={cy > 640 ? cy - 28 : cy + 28} above={cy > 640} />
    }
  }

  const { world, always_success, markers } = data.called
  return (
    <>
      <header className="label absolute top-12 right-16 left-16 flex justify-between">
        <button onClick={onHome} className="label cursor-pointer text-strong">Rehearsal</button>
        <span>Backtest · {data.cases.length === 9 ? 'nine' : data.cases.length} real launches · up to four years</span>
      </header>

      <section className="absolute top-28 left-16 w-[1100px]">
        <h1 className="text-headline font-semibold text-strong">Would it have called it?</h1>
        <p className="mt-6 max-w-[800px] text-body">
          Nine real launches of two-sided apps, names hidden. The rules were frozen first, the predictions committed
          next, the real outcomes added last. Spark still recognized most names, so we reran with plain descriptions:
          the calls held.
        </p>
      </section>

      <section className="absolute top-[120px] right-16 flex gap-16 text-right">
        <div>
          <div className="text-number font-medium text-strong tabular-nums">{world} of {markers}</div>
          <div className="label mt-4">Turning points called<br />in launches it never saw</div>
        </div>
        <div>
          <div className="text-number font-medium text-dim tabular-nums">{always_success} of {markers}</div>
          <div className="label mt-4">A model that always<br />says "it grows"</div>
        </div>
      </section>

      <span className="label absolute top-[352px] left-16 text-strong">Never seen</span>
      <Axis top={352} />
      {never.map(c => <Row key={c.id} c={c} top={tops[c.id]} onPoint={setPointed} pointed={pointed} />)}
      <span className="label absolute left-16" style={{ top: seenLabel }}>Seen while choosing the method</span>
      {seen.map(c => <Row key={c.id} c={c} top={tops[c.id]} onPoint={setPointed} pointed={pointed} />)}

      <div className="absolute top-[988px] right-16 left-16 border-t border-line" />
      <div className="label absolute top-[1012px] right-16 left-16 flex gap-6">
        <span><span className="text-strong">●</span> called &nbsp; ○ missed</span>
        <span className="ml-auto" />
        {data.commits.map((c, i) => (
          <span key={c.hash}>
            {i > 0 && <span className="mr-6">→</span>}
            {c.time} {c.what} <span className="text-strong">{c.hash}</span>
          </span>
        ))}
      </div>
      {card}
    </>
  )
}
