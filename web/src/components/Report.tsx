import type { Replay } from '../replay'

// v2 stage screen "Where did people leave, and why?" (?report). To be built from plans[k].report
// (docs/replay-format.md "Version 2"); the approved mockup is the Report frame in the planning folder.
export function Report({ replay, onBack }: { replay: Replay; onBack: () => void }) {
  return (
    <div className="absolute inset-16">
      <button onClick={onBack} className="label cursor-pointer">Replay</button>
      <h1 className="mt-8 text-headline font-semibold text-strong">Where people left, and why.</h1>
      <p className="mt-4 text-lead text-dim">{replay.meta.app}</p>
    </div>
  )
}
