import { useEffect, useMemo, useRef } from 'react'
import { stateAt, type PlanKey, type Replay } from '../replay'
import { color } from '../tokens'
import { halftone, MAP_H, MAP_W, project } from '../usMap'

// 점이 켜지는 데 걸리는 날 수 (90일 = 30초에서 약 0.3초)
const FADE_DAYS = 0.9
const fade = (since: number | null, t: number) => (since === null ? 1 : Math.min(1, Math.max(0, (t - since) / FADE_DAYS)))

export function PlanMap({ replay, plan, t }: { replay: Replay; plan: PlanKey; t: number }) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const people = replay.people[plan]
  const xy = useMemo(() => people.map(p => project(p.lon, p.lat)), [people])
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

    // 뒤에서 앞으로: 설치 안 함 → 떠남 → 사용 중 → 결제
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
    ctx.globalAlpha = 1
  }, [replay, plan, t, people, xy, index])

  return <canvas ref={canvas} style={{ width: MAP_W, height: MAP_H }} className="mt-4 block" />
}
