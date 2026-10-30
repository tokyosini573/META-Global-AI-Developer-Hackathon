import { useEffect, useMemo, useRef, type MouseEvent } from 'react'
import { stateAt, type PlanKey, type Replay } from '../replay'
import { color } from '../tokens'
import { halftone, MAP_H, MAP_W, project } from '../usMap'

// Days a dot takes to fade in (about 0.3 s when 90 days = 30 s)
const FADE_DAYS = 0.9
const fade = (since: number | null, t: number) => (since === null ? 1 : Math.min(1, Math.max(0, (t - since) / FADE_DAYS)))
const CELL = 4.5 // px: one person per cell, so a crowded city reads as a patch instead of one blob

// Move each dot to the nearest free cell, earliest arrivals first, so area grows with headcount.
function settle(points: [number, number][], order: number[]): [number, number][] {
  const taken = new Set<string>()
  const out: [number, number][] = points.map(p => [...p] as [number, number])
  for (const i of order) {
    const [x, y] = points[i]
    const gx = Math.round(x / CELL), gy = Math.round(y / CELL)
    for (let r = 0; r < 60; r++) {
      let best: [number, number] | null = null, bestD = Infinity
      for (let dx = -r; dx <= r; dx++)
        for (let dy = -r; dy <= r; dy++) {
          if (Math.max(Math.abs(dx), Math.abs(dy)) !== r || taken.has(`${gx + dx},${gy + dy}`)) continue
          const d = ((gx + dx) * CELL - x) ** 2 + ((gy + dy) * CELL - y) ** 2
          if (d < bestD) { bestD = d; best = [gx + dx, gy + dy] }
        }
      if (best) {
        taken.add(`${best[0]},${best[1]}`)
        out[i] = [best[0] * CELL, best[1] * CELL]
        break
      }
    }
  }
  return out
}

const PICK_PX = 8 // a click this close to a dot opens that person

export function PlanMap({ replay, plan, t, selected, onPick }: {
  replay: Replay; plan: PlanKey; t: number; selected?: number; onPick?: (id: number) => void
}) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const people = replay.people[plan]
  const xy = useMemo(() => {
    const order = people.map((_, i) => i).sort((i, j) => (people[i].reached ?? 1e9) - (people[j].reached ?? 1e9))
    return settle(people.map(p => project(p.lon, p.lat)), order)
  }, [people])
  const index = useMemo(() => new Map(people.map((p, i) => [p.id, i])), [people])

  useEffect(() => {
    const el = canvas.current!
    const dpr = window.devicePixelRatio || 1
    el.width = MAP_W * dpr
    el.height = MAP_H * dpr
    const ctx = el.getContext('2d')!
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, MAP_W, MAP_H)
    const tint = plan === 'a' ? color.a : color.b

    ctx.fillStyle = color.dotIdle
    for (const [x, y] of halftone) {
      ctx.beginPath()
      ctx.arc(x, y, 1.6, 0, Math.PI * 2)
      ctx.fill()
    }

    ctx.strokeStyle = tint
    ctx.lineWidth = 1
    for (const [i, j, day] of replay.matches[plan]) {
      if (day > t) continue
      const [x1, y1] = xy[index.get(i)!], [x2, y2] = xy[index.get(j)!]
      ctx.globalAlpha = 0.22 * fade(day, t)
      ctx.beginPath()
      ctx.moveTo(x1, y1)
      ctx.lineTo(x2, y2)
      ctx.stroke()
    }

    // Back to front: not installed -> quit -> active -> paid
    const layers = { idle: [] as number[], quit: [] as number[], using: [] as number[], paying: [] as number[] }
    people.forEach((p, i) => {
      const s = stateAt(p, t)
      if (s !== 'hidden') layers[s].push(i)
    })
    const dot = (i: number, r: number, fill: string, alpha: number) => {
      const [x, y] = xy[i]
      ctx.globalAlpha = alpha * fade(people[i].reached, t)
      ctx.fillStyle = fill
      ctx.beginPath()
      ctx.arc(x, y, r, 0, Math.PI * 2)
      ctx.fill()
    }
    for (const i of layers.idle) dot(i, 1.8, color.dim, 0.7)
    for (const i of layers.quit) dot(i, 2, tint, 0.25)
    for (const i of layers.using) dot(i, 2.2, tint, 0.85)
    for (const i of layers.paying) {
      dot(i, 3.6, tint, 1)
      const [x, y] = xy[i]
      ctx.globalAlpha = 0.5
      ctx.strokeStyle = tint
      ctx.beginPath()
      ctx.arc(x, y, 7, 0, Math.PI * 2)
      ctx.stroke()
    }
    if (selected !== undefined && index.has(selected)) {
      const [x, y] = xy[index.get(selected)!]
      ctx.globalAlpha = 1
      ctx.fillStyle = color.strong
      ctx.strokeStyle = color.strong
      ctx.lineWidth = 1.5
      ctx.beginPath()
      ctx.arc(x, y, 3, 0, Math.PI * 2)
      ctx.fill()
      ctx.beginPath()
      ctx.arc(x, y, 12, 0, Math.PI * 2)
      ctx.stroke()
    }
    ctx.globalAlpha = 1
  }, [replay, plan, t, people, xy, index, selected])

  // The stage is scaled to the window, so map the click back to canvas pixels first.
  const pick = (e: MouseEvent<HTMLCanvasElement>) => {
    const r = e.currentTarget.getBoundingClientRect()
    const k = MAP_W / r.width
    const cx = (e.clientX - r.left) * k, cy = (e.clientY - r.top) * k
    let best = -1, bestD = PICK_PX ** 2
    people.forEach((p, i) => {
      if (stateAt(p, t) === 'hidden') return
      const d = (xy[i][0] - cx) ** 2 + (xy[i][1] - cy) ** 2
      if (d < bestD) { bestD = d; best = i }
    })
    if (best >= 0) onPick?.(people[best].id)
  }

  return <canvas ref={canvas} style={{ width: MAP_W, height: MAP_H }} onClick={pick}
    className={`mt-4 block ${onPick ? 'cursor-pointer' : ''}`} />
}
