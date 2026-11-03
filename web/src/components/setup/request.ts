import { imageSlots, type Brief, type Channel } from '../../brief'
import { changeWords } from './words'

// What POST /api/live receives: field `brief` (JSON, docs/brief-format.md) and one file per image name

// The brief exactly as it is sent: text trimmed, budget shares scaled to 100%, every experiment described
export function finalBrief(b: Brief): Brief {
  const x = structuredClone(b)
  const trim = (o: unknown): unknown => typeof o === 'string' ? o.trim()
    : Array.isArray(o) ? o.map(trim).filter(v => v !== '')
      : o && typeof o === 'object' ? Object.fromEntries(Object.entries(o).map(([k, v]) => [k, trim(v)]).filter(([, v]) => v !== '')) : o
  const y = trim(x) as Brief
  const scale = (cs: Channel[]) => {
    const s = cs.reduce((t, c) => t + c.budget_share, 0) || 1
    return cs.map(c => ({ ...c, budget_share: Math.round((c.budget_share / s) * 1000) / 1000 }))
  }
  if (y.setup.campaign) y.setup.campaign.channels = scale(y.setup.campaign.channels)
  for (const k of ['a', 'b'] as const) {
    const ex = y.setup.experiments[k]
    if (ex.channels) ex.channels = scale(ex.channels)
    if (!ex.changes) ex.changes = changeWords(y, ex)
  }
  if (y.category === 'resale' && y.money.per === 'percent') y.extra = { ...y.extra, fee_share: y.money.price }
  // Optional pairs: dropped when both are empty, otherwise both present
  if (y.competition) y.competition = { now: y.competition.now ?? '', switch: y.competition.switch ?? '' }
  if (y.competition && !y.competition.now && !y.competition.switch) delete y.competition
  if (y.retention) y.retention = { back: y.retention.back ?? '', leave: y.retention.leave ?? '' }
  if (y.retention && !y.retention.back && !y.retention.leave) delete y.retention
  return y
}

export function requestBody(b: Brief, files: Record<string, File>) {
  const body = new FormData()
  body.append('brief', JSON.stringify(b))
  for (const name of imageSlots(b.category, b.ads.length)) {
    const f = files[name]
    body.append(name, f, `${name}.${f.type === 'image/jpeg' ? 'jpg' : 'png'}`)
  }
  return body
}
