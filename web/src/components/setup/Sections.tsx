import { AGE, LIMITS, SIDES, imageSlots, type Brief } from '../../brief'
import { Chips, Field, Grid, Link, More, Num, Section, Select, Shot, Text } from './fields'
import {
  ANGLES, INCOME, MODELS, MODEL_WORDS, NEW_APPS, PAYWALL, PERMISSIONS, SIGNUP, SLOT_WORDS, priceWords, sideWords,
} from './words'

// Sections 01-07 of the brief: what the app is (docs/brief-format.md)

export type Edit = {
  edit: boolean
  up: (f: (b: Brief) => void) => void       // change a copy of the brief
  images: Record<string, string>            // image name -> preview address
  pick: (name: string) => void              // ask for a file for this image
  errors: Record<string, string>
  addAd: () => void
  removeAd: (i: number) => void
}

export function AppSections({ b, e }: { b: Brief; e: Edit }) {
  return (
    <>
      <Profile b={b} e={e} />
      <Audience b={b} e={e} />
      <Product b={b} e={e} />
      <Money b={b} e={e} />
      <Ads b={b} e={e} />
      <Section n="06" title="Competition" collapsed summary="What people use now, why they would switch">
        <Grid>
          <Field label="What people use now">
            <Text multiline edit={e.edit} max={LIMITS.competition} value={b.competition?.now}
              onChange={v => e.up(x => { x.competition = { now: v, switch: x.competition?.switch ?? '' } })} />
          </Field>
          <Field label="Why they would switch to yours">
            <Text multiline edit={e.edit} max={LIMITS.competition} value={b.competition?.switch}
              onChange={v => e.up(x => { x.competition = { now: x.competition?.now ?? '', switch: v } })} />
          </Field>
        </Grid>
      </Section>
      <Section n="07" title="Retention" collapsed summary="What brings people back, what could make them leave">
        <Grid>
          <Field label="What brings people back">
            <Text multiline edit={e.edit} max={LIMITS.retention} value={b.retention?.back}
              onChange={v => e.up(x => { x.retention = { back: v, leave: x.retention?.leave ?? '' } })} />
          </Field>
          <Field label="What could make them leave">
            <Text multiline edit={e.edit} max={LIMITS.retention} value={b.retention?.leave}
              onChange={v => e.up(x => { x.retention = { back: x.retention?.back ?? '', leave: v } })} />
          </Field>
        </Grid>
        <p className="mt-6 max-w-[760px] text-body text-dim">
          No usage guess needed: when people stop, they say why in their own words.
        </p>
      </Section>
    </>
  )
}

function Profile({ b, e }: { b: Brief; e: Edit }) {
  const features = b.profile.features ?? []
  const setFeature = (i: number, v: string | null) => e.up(x => {
    const f = [...(x.profile.features ?? [])]
    if (v === null) f.splice(i, 1); else f[i] = v
    x.profile.features = f
  })
  return (
    <Section n="01" title="App profile" required>
      <Grid>
        <Field label="App name" error={e.errors.app}>
          <Text edit={e.edit} max={LIMITS.app} value={b.app} onChange={v => e.up(x => { x.app = v.replace(/[^A-Za-z0-9 ]/g, '') })} />
        </Field>
        <Field label="Market" hint={e.edit ? 'The only market with map, census and ad-cost data.' : undefined}>
          <div className="w-full rounded-card border border-line bg-bg px-4 py-3 text-body text-dim">{b.market}</div>
        </Field>
        <Field label="What it does" error={e.errors['profile.does']}>
          <Text multiline edit={e.edit} max={LIMITS.does} value={b.profile.does} onChange={v => e.up(x => { x.profile.does = v })} />
        </Field>
        <Field label="Why people would pick it" error={e.errors['profile.why']}>
          <Text multiline edit={e.edit} max={LIMITS.why} value={b.profile.why} onChange={v => e.up(x => { x.profile.why = v })}
            placeholder="Over what they use now" />
        </Field>
        <Field label="Key features" wide>
          {e.edit ? (
            <div className="grid gap-3 md:grid-cols-3">
              {features.map((f, i) => (
                <div key={i} className="flex items-center gap-3">
                  <Text edit max={LIMITS.feature} value={f} onChange={v => setFeature(i, v)} />
                  <Link onClick={() => setFeature(i, null)}>Remove</Link>
                </div>
              ))}
              {features.length < LIMITS.features && <div className="flex items-center"><Link onClick={() => setFeature(features.length, '')}>Add a feature</Link></div>}
            </div>
          ) : features.length ? <Chips edit={false} options={features.map(f => [f, f])} value={features} />
            : <div className="text-body text-dim">Not given</div>}
        </Field>
      </Grid>
    </Section>
  )
}

function Audience({ b, e }: { b: Brief; e: Edit }) {
  const [lo, hi] = AGE[b.category], [a0, a1] = b.audience.age
  const sides = SIDES[b.category]
  const share = b.category === 'resale' ? 'seller_share' : 'driver_share'
  return (
    <Section n="02" title="Target audience" required>
      <Grid>
        <Field label="Age range" error={e.errors['audience.age']} hint={e.edit ? `Between ${lo} and ${hi} in this market.` : undefined}>
          {e.edit ? (
            <span className="flex items-center gap-3">
              <Num edit min={lo} max={hi} value={a0} width="w-24" onChange={v => e.up(x => { x.audience.age = [v, x.audience.age[1]] })} />
              <span className="text-body">to</span>
              <Num edit min={lo} max={hi} value={a1} width="w-24" onChange={v => e.up(x => { x.audience.age = [x.audience.age[0], v] })} />
            </span>
          ) : <div className="w-full rounded-card border border-line bg-bg px-4 py-3 text-body text-strong">{a0} – {a1}</div>}
        </Field>
        {b.category === 'dating' ? (
          <Ratio label="Women / men" edit={e.edit} value={b.extra?.women_share} words={w => `${w}% women · ${100 - w}% men`}
            onChange={v => e.up(x => { x.extra = { ...x.extra, women_share: v } })} />
        ) : (
          <Ratio label={`${sideWords(sides[0])[0].toUpperCase()}${sideWords(sides[0]).slice(1)} among new users`} edit={e.edit}
            value={b.extra?.[share]} words={w => `${w}% ${sideWords(sides[0])} · ${100 - w}% ${sideWords(sides[1])}`}
            onChange={v => e.up(x => { x.extra = { ...x.extra, [share]: v } })} />
        )}
        <Field label="Who it is for" wide error={e.errors['audience.who']}>
          <Text multiline edit={e.edit} max={LIMITS.who} value={b.audience.who} onChange={v => e.up(x => { x.audience.who = v })} />
        </Field>
      </Grid>
      <More summary="income, work and lifestyle, interests, how quickly they try new apps">
        <Grid>
          <Field label="Income">
            <Select edit={e.edit} options={INCOME} value={b.audience.income} empty="Not given"
              onChange={v => e.up(x => { x.audience.income = v })} />
          </Field>
          <Field label="New apps">
            <Select edit={e.edit} options={NEW_APPS} value={b.audience.new_apps} empty="Not given"
              onChange={v => e.up(x => { x.audience.new_apps = v })} />
          </Field>
          <Field label="Work and lifestyle">
            <Text edit={e.edit} max={LIMITS.lifestyle} value={b.audience.lifestyle} onChange={v => e.up(x => { x.audience.lifestyle = v })} />
          </Field>
          <Field label="Interests">
            <Text edit={e.edit} max={LIMITS.interests} value={b.audience.interests} onChange={v => e.up(x => { x.audience.interests = v })} />
          </Field>
        </Grid>
      </More>
    </Section>
  )
}

// A share between two groups, as a slider (absent: the market's default)
function Ratio({ label, value, edit, words, onChange }: {
  label: string; value: number | undefined; edit: boolean; words: (pct: number) => string; onChange: (v: number) => void
}) {
  const pct = Math.round((value ?? 0.5) * 100)
  return (
    <Field label={label} hint={edit && value === undefined ? 'Starts at the market’s usual mix' : undefined}>
      {edit ? (
        <div className="flex items-center gap-4 py-2">
          <input type="range" min={5} max={95} step={1} value={pct} onChange={ev => onChange(Number(ev.target.value) / 100)}
            className="w-full cursor-pointer accent-blue-600" />
          <span className="min-w-[220px] text-body text-strong tabular-nums">{words(pct)}</span>
        </div>
      ) : <div className="w-full rounded-card border border-line bg-bg px-4 py-3 text-body text-strong">{value === undefined ? 'The market’s usual mix' : words(pct)}</div>}
    </Field>
  )
}

function Product({ b, e }: { b: Brief; e: Edit }) {
  const slots = imageSlots(b.category, 0).filter(s => s !== 'paywall')
  return (
    <Section n="03" title="Product experience" required>
      <div className="flex flex-wrap gap-4">
        {slots.map(s => <Shot key={s} label={SLOT_WORDS[s]} src={e.images[s]} edit={e.edit} onPick={() => e.pick(s)} error={e.errors[`image.${s}`]} />)}
      </div>
      <Grid className="mt-8">
        <Field label="Sign-up methods" error={e.errors['product.signup_methods']}>
          <Chips multi edit={e.edit} options={SIGNUP} value={b.product.signup_methods} onChange={v => e.up(x => { x.product.signup_methods = v })} />
        </Field>
        <Field label="Permissions asked">
          <Chips multi edit={e.edit} options={PERMISSIONS} value={b.product.permissions ?? []} onChange={v => e.up(x => { x.product.permissions = v })} />
        </Field>
        <Field label="Free limits">
          <Text edit={e.edit} max={LIMITS.free_limits} value={b.product.free_limits} placeholder="For example: 5 likes a day"
            onChange={v => e.up(x => { x.product.free_limits = v })} />
        </Field>
        {b.category === 'dating' && (e.edit || b.extra?.free_likes_per_day !== undefined) && (
          <Field label="Free likes a day">
            <Num edit={e.edit} min={0} value={b.extra?.free_likes_per_day ?? 5} after="a day" width="w-24"
              onChange={v => e.up(x => { x.extra = { ...x.extra, free_likes_per_day: v } })} />
          </Field>
        )}
      </Grid>
    </Section>
  )
}

function Money({ b, e }: { b: Brief; e: Edit }) {
  const m = b.money, pct = m.per === 'percent'
  const setModel = (model: Brief['money']['model']) => e.up(x => {
    x.money.model = model
    if (model === 'subscription') { x.money.per = 'week'; if (x.money.price < 1) x.money.price = 9.99 }
    else if (model === 'one_time') { x.money.per = 'transaction'; if (x.money.price < 1) x.money.price = 19.99 }
    else { x.money.per = 'percent'; if (x.money.price >= 1) x.money.price = 0.1; x.money.paywall = 'at_checkout' }
  })
  const fields = (
    <Grid>
      <Field label="How it makes money">
        <Chips edit={e.edit} options={MODELS[b.category].map(k => [k, MODEL_WORDS[k]])} value={[m.model]} onChange={([v]) => setModel(v)} />
      </Field>
      <Field label="Price" error={e.errors['money.price']}>
        {e.edit ? (
          <span className="flex flex-wrap items-center gap-3">
            <Num edit min={0} step={pct ? 1 : 0.01} before={pct ? undefined : '$'} after={pct ? `% of each ${b.category === 'rides' ? 'ride' : 'sale'}` : undefined}
              value={pct ? m.price * 100 : m.price} onChange={v => e.up(x => { x.money.price = pct ? v / 100 : v })} />
            {m.model === 'subscription' && (
              <Select edit className="w-auto" options={[['week', 'a week'], ['month', 'a month']]} value={m.per as 'week' | 'month'}
                onChange={v => e.up(x => { x.money.per = v ?? 'week' })} />
            )}
            {m.model === 'one_time' && <span className="text-body">once</span>}
          </span>
        ) : <div className="w-full rounded-card border border-line bg-bg px-4 py-3 text-body text-strong">{priceWords(m, b.category)}</div>}
      </Field>
      <Field label="When the paywall appears">
        <Chips edit={e.edit} options={PAYWALL} value={[m.paywall]} onChange={([v]) => e.up(x => { x.money.paywall = v })} />
      </Field>
      <Field label="Free trial">
        <Num edit={e.edit} min={0} value={m.trial_days ?? 0} after="days" width="w-24" onChange={v => e.up(x => { x.money.trial_days = v })} />
      </Field>
      {b.category === 'rides' && (
        <Field label="Fare per ride">
          <Num edit={e.edit} min={1} step={0.5} before="$" value={b.extra?.fare_usd ?? 14} width="w-24"
            onChange={v => e.up(x => { x.extra = { ...x.extra, fare_usd: v } })} />
        </Field>
      )}
      <Field label="What is free">
        <Text edit={e.edit} max={LIMITS.free} value={m.free} onChange={v => e.up(x => { x.money.free = v })} />
      </Field>
      <Field label="What is paid">
        <Text edit={e.edit} max={LIMITS.paid} value={m.paid} onChange={v => e.up(x => { x.money.paid = v })} />
      </Field>
    </Grid>
  )
  return (
    <Section n="04" title="Monetization" required>
      {b.category === 'dating' ? (
        <div className="grid gap-8 md:grid-cols-[150px_1fr]">
          <Shot label={SLOT_WORDS.paywall} src={e.images.paywall} edit={e.edit} onPick={() => e.pick('paywall')} error={e.errors['image.paywall']} />
          {fields}
        </div>
      ) : fields}
    </Section>
  )
}

function Ads({ b, e }: { b: Brief; e: Edit }) {
  return (
    <Section n="05" title="Marketing campaign" required>
      <p className="max-w-[760px] text-body text-dim">
        Up to three ads. Each person sees one, and the report shows which kinds of people each ad reached.
        Channels, budget and cities are part of the experiment setup below.
      </p>
      <div className="mt-8 grid gap-8 md:grid-cols-3">
        {b.ads.map((ad, i) => (
          <div key={ad.id} className="min-w-0">
            <Shot tall={false} label={`Ad ${i + 1}`} add="Add the ad image" src={e.images[ad.id]} edit={e.edit} onPick={() => e.pick(ad.id)} error={e.errors[`image.${ad.id}`]} />
            <div className="mt-4 space-y-4">
              <Field label="Angle">
                <Chips edit={e.edit} options={ANGLES} value={[ad.angle]} onChange={([v]) => e.up(x => { x.ads[i].angle = v })} />
              </Field>
              <Field label="Line" error={e.errors[`ads.${i}`]}>
                <Text edit={e.edit} max={LIMITS.line} value={ad.line} onChange={v => e.up(x => { x.ads[i].line = v })} />
              </Field>
              {e.edit && b.ads.length > 1 && <Link onClick={() => e.removeAd(i)}>Remove this ad</Link>}
            </div>
          </div>
        ))}
        {e.edit && b.ads.length < 3 && (
          <button type="button" onClick={e.addAd}
            className="flex h-[250px] cursor-pointer items-center justify-center rounded-card border border-dashed border-blue-200 bg-blue-50 text-body text-blue-600">
            Add an ad
          </button>
        )}
      </div>
      {e.errors.ads && <div className="mt-4 text-label font-medium text-strong">{e.errors.ads}</div>}
    </Section>
  )
}
