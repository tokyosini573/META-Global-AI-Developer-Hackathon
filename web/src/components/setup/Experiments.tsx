import { CHANNEL_KINDS, CITIES, DAYS, LIMITS, PEOPLE, SIDES, type Brief, type Channel, type City, type Experiment } from '../../brief'
import type { PlanKey, Replay } from '../../replay'
import { Chips, Field, Grid, Link, Num, Section, Text } from './fields'
import type { Edit } from './Sections'
import { CHANNEL_WORDS, changeWords, channelWords, cityWords, shortCity, sideWords, usd } from './words'

// Section 08: how many people, how long, the campaign both experiments share, and what A and B change

type Change = 'budget' | 'channels' | 'ads' | 'price'
const CHANGES: [Change, string][] = [['budget', 'Budget'], ['channels', 'Channels and cities'], ['ads', 'Ads shown'], ['price', 'Price or trial']]

const changed = (x: Experiment): Change[] => [
  ...(x.budget_usd !== undefined ? ['budget' as const] : []),
  ...(x.channels || x.cities ? ['channels' as const] : []),
  ...(x.ads ? ['ads' as const] : []),
  ...(x.price !== undefined || x.trial_days !== undefined ? ['price' as const] : []),
]

export function ExperimentSetup({ b, e, replay, footer }: { b: Brief; e: Edit; replay?: Replay; footer: React.ReactNode }) {
  const c = b.setup.campaign
  return (
    <Section n="08" title="Experiment setup" required band>
      <Grid>
        <Field label="People" hint="Simulated people reached in each experiment">
          <Chips edit={e.edit} options={PEOPLE.map(n => [n, n.toLocaleString('en-US')])} value={[b.setup.people]}
            onChange={([v]) => e.up(x => { x.setup.people = v })} />
        </Field>
        <Field label="Days">
          <Chips edit={e.edit} options={DAYS.map(n => [n, String(n)])} value={[b.setup.days]}
            onChange={([v]) => e.up(x => {
              x.setup.days = v
              const fit = (ch: Channel) => ({ ...ch, start_day: Math.min(ch.start_day, v), end_day: Math.min(ch.end_day, v) })
              if (x.setup.campaign) x.setup.campaign.channels = x.setup.campaign.channels.map(fit)
              for (const k of ['a', 'b'] as const) {
                const ex = x.setup.experiments[k]
                if (ex.channels) ex.channels = ex.channels.map(fit)
              }
            })} />
        </Field>
      </Grid>

      <div className="mt-12">
        <div className="label">Shared campaign</div>
        {c && e.edit ? <Campaign b={b} e={e} /> : (
          <div className="mt-4 rounded-card border border-line bg-bg px-4 py-3 text-body text-strong">
            {c ? [usd(c.budget_usd), ...c.channels.map(channelWords), c.cities?.length ? cityWords(c.cities) : 'nationwide',
              c.ads.length === b.ads.length ? 'every ad' : c.ads.map(a => `ad ${a.slice(3)}`).join(', ')].join(' · ')
              : `${usd(replay?.meta.budget_usd ?? 0)} for each experiment · ${b.setup.days} days · every ad`}
          </div>
        )}
      </div>

      <div className="mt-12 grid gap-12 md:grid-cols-2">
        {(['a', 'b'] as const).map(k => <ExperimentColumn key={k} k={k} b={b} e={e} replay={replay} />)}
      </div>
      {e.errors.experiments && <div className="mt-6 text-label font-medium text-strong">{e.errors.experiments}</div>}

      <div className="mt-12">{footer}</div>
    </Section>
  )
}

function Campaign({ b, e }: { b: Brief; e: Edit }) {
  const c = b.setup.campaign!
  const set = (f: (c: NonNullable<Brief['setup']['campaign']>) => void) => e.up(x => f(x.setup.campaign!))
  return (
    <div className="mt-4 grid gap-8 md:grid-cols-2">
      <Field label="Budget" error={e.errors['campaign.budget']}>
        <Num edit min={0} step={1000} before="$" value={c.budget_usd} width="w-40" onChange={v => set(c => { c.budget_usd = v })} />
      </Field>
      <Field label="Ads shown" error={e.errors['campaign.ads']}>
        <Chips multi edit options={b.ads.map((a, i) => [a.id, `Ad ${i + 1}`])} value={c.ads} onChange={v => set(c => { c.ads = v })} />
      </Field>
      <Field label="Channels" error={e.errors['campaign.channels']}>
        <Channels value={c.channels} days={b.setup.days} sides={SIDES[b.category]} onChange={v => set(c => { c.channels = v })} />
      </Field>
      <Field label="Cities" error={e.errors['campaign.cities']} hint="Used by channels set to run in the cities.">
        <Cities value={c.cities ?? []} days={b.setup.days} onChange={v => set(c => { c.cities = v })} />
      </Field>
    </div>
  )
}

function ExperimentColumn({ k, b, e, replay }: { k: PlanKey; b: Brief; e: Edit; replay?: Replay }) {
  const x = b.setup.experiments[k], c = b.setup.campaign
  const color = k === 'a' ? 'text-plan-a' : 'text-plan-b'
  const rule = k === 'a' ? 'border-plan-a' : 'border-plan-b'
  const plan = replay?.plans[k]
  const set = (f: (x: Experiment) => void) => e.up(y => f(y.setup.experiments[k]))

  // Read-only: the experiment in plain words (the example's own plan card when it has one)
  if (!e.edit || !c) {
    const card = plan?.card
    return (
      <div className={`border-t-2 pt-6 ${rule}`}>
        <div className={`label ${color}`}>Experiment {k.toUpperCase()} · changes</div>
        <div className="mt-4 text-lead text-strong">{x.changes || plan?.changes || plan?.summary}</div>
        {card && (['where', 'ads', 'price'] as const).map(f => (
          <div key={f} className="mt-4 grid grid-cols-[96px_1fr] gap-4 border-t border-line pt-4">
            <span className="label pt-[3px]">{f}</span>
            <span className="text-body">{card[f]}</span>
          </div>
        ))}
        {!card && <div className="mt-4"><Chips edit={false} options={CHANGES} value={changed(x)} /></div>}
      </div>
    )
  }

  const toggle = (ch: Change[]) => set(y => {
    const on = (w: Change) => ch.includes(w)
    if (on('budget') && y.budget_usd === undefined) y.budget_usd = c.budget_usd
    if (!on('budget')) delete y.budget_usd
    if (on('channels') && !y.channels) { y.channels = structuredClone(c.channels); y.cities = structuredClone(c.cities ?? []) }
    if (!on('channels')) { delete y.channels; delete y.cities }
    if (on('ads') && !y.ads) y.ads = [...c.ads]
    if (!on('ads')) delete y.ads
    if (on('price') && y.price === undefined && y.trial_days === undefined) { y.price = b.money.price; y.trial_days = b.money.trial_days ?? 0 }
    if (!on('price')) { delete y.price; delete y.trial_days }
  })
  const now = changed(x), pct = b.money.per === 'percent'
  return (
    <div className={`min-w-0 border-t-2 pt-6 ${rule}`}>
      <div className={`label ${color}`}>Experiment {k.toUpperCase()} · changes</div>
      <div className="mt-4"><Chips multi edit options={CHANGES} value={now} onChange={toggle} /></div>
      <div className="mt-6 space-y-6">
        {now.includes('budget') && (
          <Field label="Budget" error={e.errors[`${k}.budget`]}>
            <Num edit min={0} step={1000} before="$" value={x.budget_usd} width="w-40" onChange={v => set(y => { y.budget_usd = v })} />
          </Field>
        )}
        {now.includes('channels') && <>
          <Field label="Channels" error={e.errors[`${k}.channels`]}>
            <Channels value={x.channels ?? []} days={b.setup.days} sides={SIDES[b.category]} onChange={v => set(y => { y.channels = v })} />
          </Field>
          <Field label="Cities">
            <Cities value={x.cities ?? []} days={b.setup.days} onChange={v => set(y => { y.cities = v })} />
          </Field>
        </>}
        {now.includes('ads') && (
          <Field label="Ads shown" error={e.errors[`${k}.ads`]}>
            <Chips multi edit options={b.ads.map((a, i) => [a.id, `Ad ${i + 1}`])} value={x.ads ?? []} onChange={v => set(y => { y.ads = v })} />
          </Field>
        )}
        {now.includes('price') && (
          <div className="flex flex-wrap gap-6">
            <Field label="Price">
              <Num edit min={0} step={pct ? 1 : 0.01} before={pct ? undefined : '$'} after={pct ? '%' : undefined}
                value={pct ? (x.price ?? b.money.price) * 100 : x.price ?? b.money.price} onChange={v => set(y => { y.price = pct ? v / 100 : v })} />
            </Field>
            <Field label="Free trial">
              <Num edit min={0} after="days" width="w-24" value={x.trial_days ?? b.money.trial_days ?? 0} onChange={v => set(y => { y.trial_days = v })} />
            </Field>
          </div>
        )}
        <Field label="In a few words" hint="Shown on the results. Empty: written from the changes above.">
          <Text edit max={LIMITS.changes} value={x.changes} placeholder={changeWords(b, x)} onChange={v => set(y => { y.changes = v })} />
        </Field>
      </div>
    </div>
  )
}

// Five channel kinds, each with its share of the budget, its days, where it runs and which side it aims at
function Channels({ value, onChange, days, sides }: { value: Channel[]; onChange: (v: Channel[]) => void; days: number; sides: string[] }) {
  const kinds = value.map(c => c.kind)
  const toggle = (next: Channel['kind'][]) => {
    const kept = value.filter(c => next.includes(c.kind))
    const added = next.filter(k => !kinds.includes(k)).map(kind => ({ kind, where: 'nationwide' as const, budget_share: 0.2, start_day: 0, end_day: days }))
    onChange([...kept, ...added])
  }
  const setOne = (i: number, patch: Partial<Channel>) => onChange(value.map((c, j) => (j === i ? { ...c, ...patch } : c)))
  const total = Math.round(value.reduce((s, c) => s + c.budget_share, 0) * 100)
  const select = 'min-w-0 cursor-pointer rounded-card border border-line bg-bg px-3 py-2 text-body text-strong outline-none focus:border-blue-600'
  return (
    <div>
      <Chips multi edit options={CHANNEL_KINDS.map(k => [k, CHANNEL_WORDS[k]])} value={kinds} onChange={toggle} />
      <div className="mt-4 space-y-4">
        {value.map((c, i) => (
          <div key={`${c.kind}${i}`} className="border-t border-line pt-4">
            <div className="text-body font-medium text-strong">{CHANNEL_WORDS[c.kind]}</div>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <Num edit min={0} max={100} value={Math.round(c.budget_share * 100)} after="% of budget" width="w-20"
                onChange={v => setOne(i, { budget_share: v / 100 })} />
              <Num edit min={0} max={days} before="day" value={c.start_day} width="w-20" onChange={v => setOne(i, { start_day: v })} />
              <Num edit min={0} max={days} before="to" value={c.end_day} width="w-20" onChange={v => setOne(i, { end_day: v })} />
              <select value={c.where} onChange={ev => setOne(i, { where: ev.target.value as Channel['where'] })} className={select}>
                <option value="nationwide">Nationwide</option>
                <option value="cities">In the cities</option>
              </select>
              {sides.length > 0 && (
                <select value={c.side ?? ''} onChange={ev => setOne(i, { side: ev.target.value || undefined })} className={select}>
                  <option value="">Both sides</option>
                  {sides.map(s => <option key={s} value={s}>{sideWords(s)[0].toUpperCase() + sideWords(s).slice(1)}</option>)}
                </select>
              )}
            </div>
          </div>
        ))}
      </div>
      {value.length > 0 && total !== 100 && (
        <div className="mt-4 text-label text-dim">The shares add up to {total}%; the run scales them to 100%.</div>
      )}
    </div>
  )
}

function Cities({ value, onChange, days }: { value: City[]; onChange: (v: City[]) => void; days: number }) {
  const left = CITIES.filter(n => !value.some(c => c.name === n))
  return (
    <div className="space-y-3">
      {value.map((c, i) => (
        <div key={c.name} className="flex flex-wrap items-center gap-3">
          <span className="min-w-[140px] text-body text-strong">{shortCity(c.name)}</span>
          <Num edit min={0} max={days} before="opens on day" value={c.open_day} width="w-20"
            onChange={v => onChange(value.map((x, j) => (j === i ? { ...x, open_day: v } : x)))} />
          <Link onClick={() => onChange(value.filter((_, j) => j !== i))}>Remove</Link>
        </div>
      ))}
      {!value.length && <div className="text-body text-dim">None yet</div>}
      <select value="" onChange={ev => ev.target.value && onChange([...value, { name: ev.target.value, open_day: 0 }])}
        className="w-full cursor-pointer rounded-card border border-line bg-bg px-4 py-3 text-body text-strong outline-none focus:border-blue-600">
        <option value="">Add a city</option>
        {left.map(n => <option key={n} value={n}>{n}</option>)}
      </select>
    </div>
  )
}
