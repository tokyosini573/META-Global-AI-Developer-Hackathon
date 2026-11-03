import { noteOf, screenSrc, type Replay } from '../replay'
import { Tabs, usePlan } from './report/Tabs'

const HEAD = 320, ROWS = 600, BOTTOM = 984

// "Which people answered which ad?" (?ads): one column per ad, one row per kind of person, each cell
// the share of the people who saw that ad and installed (plans[k].ads.cells). Darker = higher, the best
// ad in each row in bold.
export function Ads({ replay }: { replay: Replay }) {
  const [plan, setPlan] = usePlan(replay)
  const ads = replay.meta.ads ?? [], kinds = replay.meta.kinds ?? []
  const data = replay.plans[plan].ads
  const rate = (kind: string, ad: string) => {
    const c = data?.cells[kind]?.[ad]
    return c && c[0] ? c[1] / c[0] : null
  }
  // Shade from the lowest cell to the highest, so small differences still read
  const all = kinds.flatMap(k => ads.map(a => rate(k.id, a.id))).filter((r): r is number => r !== null)
  const lo = Math.min(...all), hi = Math.max(...all)
  const rowH = Math.min(72, (BOTTOM - ROWS) / Math.max(1, kinds.length))
  const color = plan === 'a' ? 'var(--color-plan-a)' : 'var(--color-plan-b)'
  const cols = { gridTemplateColumns: `400px repeat(${ads.length}, 1fr)` }

  return (
    <>
      <section className="absolute top-28 right-16 left-16 flex items-start justify-between gap-16">
        <h1 className={`max-w-[1300px] font-semibold text-strong ${(data?.line ?? '').length > 60 ? 'text-title' : 'text-headline'}`}>
          {data?.line ?? 'Which people answered which ad?'}</h1>
        <div className="flex-none"><Tabs replay={replay} plan={plan} onPlan={setPlan} /></div>
      </section>

      <section className="absolute right-16 left-16 grid gap-x-2" style={{ top: HEAD, height: ROWS - HEAD, ...cols }}>
        <div />
        {ads.map((a, i) => (
          <div key={a.id} className="flex flex-col items-center text-center">
            <img src={screenSrc(a.screen)} alt="" className="h-[180px] rounded-card border border-line" />
            <div className="label mt-3">Ad {i + 1} · {a.angle}</div>
            <div className="mt-1 max-w-[440px] truncate text-body text-strong">“{a.line}”</div>
          </div>
        ))}
      </section>

      <section className="absolute right-16 left-16 grid gap-2" style={{ top: ROWS, gridAutoRows: rowH - 8, ...cols }}>
        {kinds.map(k => {
          const rates = ads.map(a => rate(k.id, a.id))
          const best = Math.max(...rates.map(r => r ?? -1))
          return [
            <div key={k.id} className="flex items-center gap-3 truncate">
              <span className="text-body text-strong">{k.name}</span>
              <span className="label">· {Math.round(k.share * 100)}%</span>
            </div>,
            ...rates.map((r, i) => {
              const level = r === null ? 0 : hi > lo ? (r - lo) / (hi - lo) : 1
              return (
                <div key={`${k.id}:${ads[i].id}`}
                  className={`grid place-items-center rounded-card text-lead tabular-nums ${plan === 'b' && level > 0.6 ? 'text-white' : 'text-strong'}
                    ${r !== null && r === best ? 'font-semibold' : 'font-normal'}`}
                  style={{ background: `color-mix(in srgb, ${color} ${Math.round(8 + level * 80)}%, var(--color-bg))` }}>
                  {r === null ? '—' : `${Math.round(r * 100)}%`}
                </div>
              )
            }),
          ]
        })}
      </section>

      <p className="absolute bottom-10 left-16 text-body text-dim">
        Share of the people who saw that ad and installed. {noteOf(replay)}
      </p>
    </>
  )
}
