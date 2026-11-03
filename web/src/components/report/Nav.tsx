import type { ReactNode } from 'react'

export type View = 'replay' | 'report' | 'ads' | 'backtest'

const NAMES: Record<View, string> = { replay: 'Replay', report: 'Report', ads: 'Ads', backtest: 'Backtest' }

// The stage's top line: where you are on the left, the screens on the right. Report and Ads only
// appear for replays that carry them (v2).
export function Nav({ context, view, views, onView, tryHref }: {
  context: ReactNode; view: View; views: View[]; onView: (v: View) => void; tryHref: string
}) {
  return (
    <header className="label absolute top-12 right-16 left-16 flex justify-between">
      <span><a href="/" className="text-strong">Rehearsal</a> · {context}</span>
      <nav className="flex gap-6">
        {views.map(v => (
          <button key={v} onClick={() => onView(v)}
            className={`label cursor-pointer ${v === view ? 'text-strong' : 'hover:text-strong'}`}>
            {NAMES[v]}
          </button>
        ))}
        <a href={tryHref} className="label hover:text-strong">Try it yourself</a>
      </nav>
    </header>
  )
}
