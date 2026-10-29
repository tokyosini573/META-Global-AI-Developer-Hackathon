import { useRef } from 'react'
import type { Replay } from '../replay'

const W = 1792, X0 = 64, LEN = W - X0

// Plan A events above the line, Plan B below. Click or drag the line to jump to that day.
export function Timeline({ replay, t, playing, onSeek, onToggle }: {
  replay: Replay
  t: number
  playing: boolean
  onSeek: (day: number) => void
  onToggle: () => void
}) {
  const svg = useRef<SVGSVGElement>(null)
  const days = replay.meta.days
  const x = (d: number) => X0 + (d / days) * LEN
  const seek = (e: React.PointerEvent) => {
    const box = svg.current!.getBoundingClientRect()
    const local = ((e.clientX - box.left) / box.width) * W
    onSeek(Math.min(days, Math.max(0, ((local - X0) / LEN) * days)))
  }

  return (
    <div className="relative h-16">
      <button onClick={onToggle} aria-label={playing ? 'Pause' : 'Play'}
        className="absolute left-0 top-2 z-10 grid size-10 place-items-center rounded-card border border-line">
        <svg width="14" height="14" viewBox="0 0 14 14" className="fill-strong">
          {playing ? <path d="M3 2 H6 V12 H3 Z M8 2 H11 V12 H8 Z" /> : <path d="M3 1.5 L12 7 L3 12.5 Z" />}
        </svg>
      </button>
      <svg ref={svg} width={W} height={64} viewBox={`0 0 ${W} 64`} className="absolute left-0 top-0 cursor-pointer"
        onPointerDown={e => { e.currentTarget.setPointerCapture(e.pointerId); seek(e) }}
        onPointerMove={e => { if (e.buttons) seek(e) }}>
        <rect x={X0} y={8} width={LEN} height={40} fill="transparent" />
        <line x1={X0} y1={28} x2={X0 + LEN} y2={28} className="stroke-line" strokeWidth={2} />
        <line x1={X0} y1={28} x2={x(t)} y2={28} className="stroke-strong" strokeWidth={2} />
        <circle cx={x(t)} cy={28} r={6} className="fill-strong" />
        {replay.plans.a.events.map(ev => (
          <g key={`a${ev.day}`} className="fill-plan-a stroke-plan-a">
            <line x1={x(ev.day)} y1={18} x2={x(ev.day)} y2={28} strokeWidth={2} />
            <text x={x(ev.day) + 8} y={13} className="label fill-plan-a stroke-none">{ev.label}</text>
          </g>
        ))}
        {replay.plans.b.events.map(ev => (
          <g key={`b${ev.day}`} className="fill-plan-b stroke-plan-b">
            <line x1={x(ev.day)} y1={28} x2={x(ev.day)} y2={38} strokeWidth={2} />
            <text x={x(ev.day) + 8} y={56} className="label fill-plan-b stroke-none">{ev.label}</text>
          </g>
        ))}
        <text x={X0 + LEN} y={56} textAnchor="end" className="label" fill="currentColor">Day {Math.floor(t)}</text>
      </svg>
    </div>
  )
}
