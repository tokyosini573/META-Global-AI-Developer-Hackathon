import { useEffect, useState } from 'react'
import type { PlanKey, Replay, Theme } from '../../replay'
import { STILL } from '../Stage'

// The people behind one reason, sliding in from the right like the one-person drawer.
// Clicking a person opens their drawer on top of this list.
export function ThemeList({ replay, plan, step, theme, onPick, onClose }: {
  replay: Replay; plan: PlanKey; step: string; theme: Theme
  onPick: (id: number) => void; onClose: () => void
}) {
  const [open, setOpen] = useState(STILL)
  useEffect(() => {
    const id = requestAnimationFrame(() => setOpen(true))
    return () => cancelAnimationFrame(id)
  }, [])
  const byId = new Map(replay.people[plan].map(p => [p.id, p]))
  const words = (id: number) => byId.get(id)?.story?.stop?.words ?? byId.get(id)?.story?.quit_reason ?? null
  // People who said something first, in the file's order
  const ids = theme.ids.filter(id => byId.has(id)).sort((x, y) => Number(!words(x)) - Number(!words(y)))
  return (
    <>
      <div className="absolute inset-0 bg-blue-900/20" onClick={onClose} />
      <aside className="absolute top-0 right-0 flex h-[1080px] w-[640px] flex-col rounded-l-card border-l border-line bg-surface p-12
        transition-transform duration-[250ms] ease-out" style={{ transform: open ? 'none' : 'translateX(100%)' }}>
        <button onClick={onClose} aria-label="Close" className="absolute top-10 right-10 cursor-pointer">
          <svg width="16" height="16" viewBox="0 0 16 16"><path d="M2 2 L14 14 M14 2 L2 14" stroke="currentColor" strokeWidth="1.5" className="text-dim" /></svg>
        </button>
        <div className={`label ${plan === 'a' ? 'text-plan-a' : 'text-plan-b'}`}>{replay.plans[plan].name} · {step}</div>
        <h2 className="mt-6 text-title font-semibold text-strong">{theme.name}</h2>
        <p className="mt-4 text-body text-dim">{theme.count.toLocaleString('en-US')} people. “{theme.quote}”</p>
        <div className="mt-8 min-h-0 flex-1 overflow-y-auto">
          {ids.map(id => {
            const p = byId.get(id)!, w = words(id)
            return (
              <button key={id} onClick={() => onPick(id)}
                className="block w-full cursor-pointer border-t border-line py-4 text-left hover:bg-blue-50">
                <span className="text-body text-strong">{p.name}, {p.age}</span>
                <span className="text-body text-dim"> · {p.place}</span>
                {w && <span className="block truncate text-body text-text">“{w}”</span>}
              </button>
            )
          })}
        </div>
      </aside>
    </>
  )
}
