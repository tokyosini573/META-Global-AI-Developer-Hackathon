import type { Replay } from '../replay'

// v2 stage screen "Which people answered which ad?" (?ads). To be built from plans[k].ads and
// meta.ads/meta.kinds (docs/replay-format.md "Version 2").
export function Ads({ replay, onBack }: { replay: Replay; onBack: () => void }) {
  return (
    <div className="absolute inset-16">
      <button onClick={onBack} className="label cursor-pointer">Replay</button>
      <h1 className="mt-8 text-headline font-semibold text-strong">Which people answered which ad?</h1>
      <p className="mt-4 text-lead text-dim">{replay.meta.app}</p>
    </div>
  )
}
