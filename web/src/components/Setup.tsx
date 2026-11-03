import { useEffect, useRef, useState } from 'react'
import { imageSlots, validate, type Brief, type Category } from '../brief'
import { packOf, PLANS, type Replay } from '../replay'
import { exampleBrief } from './setup/examples'
import { ExperimentSetup } from './setup/Experiments'
import { Chips } from './setup/fields'
import { LiveRun } from './setup/LiveRun'
import { AppSections, type Edit } from './setup/Sections'
import { CATEGORY_WORDS, EXAMPLE_REPLAY } from './setup/words'

// v2 Setup page (?new): one scrolling page with sections 01-08 of the brief (docs/brief-format.md).
// ?new&replay=<name> shows that example's meta.brief read-only; ?new&admin edits it and runs it live.

const CATEGORIES = Object.entries(CATEGORY_WORDS) as [Category, string][]
const wrap = 'mx-auto w-full max-w-[1200px] px-6 md:px-16'
const src = (s: string) => (s.startsWith('/') || s.startsWith('http') ? s : `/screens/${s}.png`)
const base = (s: string) => s.split('/').pop()!.replace(/\.\w+$/, '')

// Which of a replay's screens fills each image of the brief. Exact names first (live runs upload
// main_rider.png, ...), then the demo apps' own names (reloop_list_m0_few is what a seller sees).
const LOOKS: Record<string, RegExp> = {
  store: /store/, signup: /sign_?up/, paywall: /paywall/, main: /(^|_)(main|swipe)(?![_a-z])/,
  main_seller: /(^|_)(list|sell)/, main_buyer: /(^|_)buy/, main_driver: /(^|_)drive/, main_rider: /(^|_)ride(?!r_)/,
}
function exampleImages(r: Replay, b: Brief) {
  const screens = packOf(r).screens ?? ['ad', 'store', 'paywall_m0_none']
  const out: Record<string, string> = {}
  for (const [slot, s] of Object.entries(b.images ?? {})) out[slot] = src(s)   // v2 replays name them
  for (const slot of imageSlots(b.category, 0)) {
    if (out[slot]) continue
    const s = screens.find(x => base(x) === slot || base(x).endsWith(`_${slot}`)) ?? screens.find(x => LOOKS[slot]?.test(base(x)))
    if (s) out[slot] = src(s)
  }
  for (const ad of r.meta.ads ?? []) if (ad.screen) out[ad.id] = src(ad.screen)
  const ad = screens.find(x => /(^|_)ad(_1)?$/.test(base(x)))
  if (!out.ad_1 && ad) out.ad_1 = src(ad)
  return out
}

function Page({ switcher, label, children }: { switcher: React.ReactNode; label: string; children: React.ReactNode }) {
  return (
    <div className="min-h-full bg-bg text-text">
      <nav className={`${wrap} flex items-center justify-between py-6`}>
        <a href="/" className="flex items-center gap-3 text-lead font-semibold text-strong">
          <img src="/landing/dolphin/smile.webp" alt="" className="h-10" />Rehearsal
        </a>
      </nav>
      <header className={`${wrap} flex flex-col gap-8 pt-8 pb-12 md:flex-row md:items-end md:justify-between`}>
        <div>
          <div className="label text-blue-600">{label}</div>
          <h1 className="mt-4 text-title font-semibold text-strong">Let’s rehearse your app.</h1>
          <p className="mt-4 max-w-[680px] text-lead text-dim">
            Add your app’s screens and a few facts. Simulated people in the United States will try it, and two
            experiments show which launch works better.
          </p>
        </div>
        <div className="flex-none">{switcher}</div>
      </header>
      {children}
    </div>
  )
}

export function Setup() {
  const q = new URLSearchParams(location.search)
  return q.has('admin') ? <AdminSetup /> : <ExampleSetup first={q.get('replay') ?? 'engine'} />
}

const none = () => {}
const readOnly = (images: Record<string, string>): Edit =>
  ({ edit: false, up: none, images, pick: none, errors: {}, addAd: none, removeAd: none })

// A finished example, read-only
function ExampleSetup({ first }: { first: string }) {
  const [name, setName] = useState(first)
  const [replay, setReplay] = useState<Replay | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let live = true
    fetch(`/replays/${encodeURIComponent(name)}.json`).then(r => r.json())
      .then((r: Replay) => live && setReplay(r)).catch(() => live && setFailed(true))
    return () => { live = false }
  }, [name])

  const b = replay?.meta.brief
  const category: Category | undefined = b?.category ?? (replay ? packOf(replay).id as Category : undefined)
  const go = (c: Category) => {
    const n = EXAMPLE_REPLAY[c]
    if (n === name) return
    history.replaceState(null, '', `/?new&replay=${n}`)
    setReplay(null); setFailed(false); setName(n)
  }
  const watch = (
    <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
      <p className="max-w-[560px] text-body text-dim">
        This example was rehearsed ahead of time. Watch how both experiments played out over {b?.setup.days ?? replay?.meta.days ?? 90} days.
      </p>
      <a href={`/?replay=${encodeURIComponent(name)}`} className="rounded-card bg-blue-600 px-8 py-4 text-center text-body font-medium text-white hover:bg-blue-900">
        Watch the rehearsal
      </a>
    </div>
  )
  const switcher = <Chips edit options={CATEGORIES} value={category ? [category] : []} onChange={([c]) => go(c)} />
  const label = replay ? `Example · ${replay.meta.app} · read only` : 'Example'

  if (failed) return <Page switcher={switcher} label="Example"><Calm text="This example could not be loaded. Try another market above." /></Page>
  if (!replay) return <Page switcher={switcher} label={label}><div className={`${wrap} h-[600px]`} /></Page>
  if (!b) return <Page switcher={switcher} label={label}><NoBrief replay={replay} footer={watch} /></Page>
  return (
    <Page switcher={switcher} label={label}>
      <AppSections b={b} e={readOnly(exampleImages(replay, b))} />
      <ExperimentSetup b={b} e={readOnly({})} replay={replay} footer={watch} />
    </Page>
  )
}

const Calm = ({ text }: { text: string }) => (
  <section className="border-t border-line"><div className={`${wrap} py-12 text-lead text-dim`}>{text}</div></section>
)

// An example rehearsed before the full setup existed: its screens and its two experiments only
function NoBrief({ replay, footer }: { replay: Replay; footer: React.ReactNode }) {
  const screens = packOf(replay).screens ?? ['ad', 'store', 'paywall_m0_none']
  return (
    <>
      <Calm text="This example was rehearsed before the full setup existed, so only what people saw and the two experiments are shown." />
      <section className="border-t border-line">
        <div className={`${wrap} flex flex-wrap gap-4 py-12`}>
          {screens.map(s => <img key={s} src={src(s)} alt="" className="h-[250px] w-[150px] rounded-card border border-line bg-surface object-contain" />)}
        </div>
      </section>
      <section className="border-t border-line bg-surface">
        <div className={`${wrap} py-12`}>
          <div className="grid gap-12 md:grid-cols-2">
            {PLANS.map(k => (
              <div key={k} className={`border-t-2 pt-6 ${k === 'a' ? 'border-plan-a' : 'border-plan-b'}`}>
                <div className={`label ${k === 'a' ? 'text-plan-a' : 'text-plan-b'}`}>Experiment {k.toUpperCase()}</div>
                <div className="mt-4 text-lead text-strong">{replay.plans[k].card?.title ?? replay.plans[k].summary}</div>
                {replay.plans[k].card && (['where', 'ads', 'price'] as const).map(f => (
                  <div key={f} className="mt-4 grid grid-cols-[96px_1fr] gap-4 border-t border-line pt-4">
                    <span className="label pt-[3px]">{f}</span><span className="text-body">{replay.plans[k].card![f]}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
          <div className="mt-12">{footer}</div>
        </div>
      </section>
    </>
  )
}

// The admin's form: the chosen market's example brief (text only), the admin's own images
function AdminSetup() {
  const [brief, setBrief] = useState<Brief>(() => exampleBrief('dating'))
  const [files, setFiles] = useState<Record<string, File>>({})
  const [shown, setShown] = useState<Record<string, string>>({})
  const [tried, setTried] = useState(false)
  const touched = useRef(false)
  const picking = useRef('')
  const fileInput = useRef<HTMLInputElement>(null)

  // The example replay's own brief, when it has one, replaces the built-in text (until the admin types)
  useEffect(() => {
    let live = true
    fetch(`/replays/${EXAMPLE_REPLAY[brief.category]}.json`).then(r => r.json()).then((r: Replay) => {
      const x = r.meta.brief
      if (!live || touched.current || !x || x.category !== brief.category) return
      setBrief(b => {
        const ids = x.ads.map(a => a.id)
        const keep = (ads?: string[]) => ads?.filter(a => ids.includes(a))
        const exp = (k: 'a' | 'b') => ({ ...b.setup.experiments[k], ads: keep(b.setup.experiments[k].ads) })
        const out: Brief = { ...structuredClone(x), setup: { ...b.setup, people: x.setup.people, days: x.setup.days } }
        out.extra = { ...b.extra, ...x.extra }
        if (out.setup.campaign) out.setup.campaign = { ...out.setup.campaign, ads: ids }
        out.setup.experiments = { a: exp('a'), b: exp('b') }
        for (const k of ['a', 'b'] as const) if (!out.setup.experiments[k].ads?.length) delete out.setup.experiments[k].ads
        return out
      })
    }).catch(() => { /* the built-in example stays */ })
    return () => { live = false }
  }, [brief.category])

  const up = (f: (b: Brief) => void) => {
    touched.current = true
    setBrief(prev => { const n = structuredClone(prev); f(n); return n })
  }
  const setImage = (name: string, f: File | undefined) => {
    setFiles(x => { const n = { ...x }; if (f) n[name] = f; else delete n[name]; return n })
    setShown(x => {
      if (x[name]) URL.revokeObjectURL(x[name])
      const n = { ...x }; if (f) n[name] = URL.createObjectURL(f); else delete n[name]; return n
    })
  }
  const pick = (name: string) => { picking.current = name; fileInput.current?.click() }

  const switchTo = (c: Category) => {
    if (c === brief.category) return
    Object.values(shown).forEach(u => URL.revokeObjectURL(u))
    touched.current = false
    setFiles({}); setShown({}); setTried(false)
    setBrief(exampleBrief(c))
  }

  const addAd = () => up(b => {
    const id = `ad_${b.ads.length + 1}`
    b.ads.push({ id, angle: 'feature', line: '' })
    b.setup.campaign?.ads.push(id)
  })
  // Ads stay numbered ad_1..ad_n, so the images and every list of ads shown move along with them
  const removeAd = (i: number) => {
    const rename = (id: string) => { const j = Number(id.slice(3)) - 1; return j === i ? null : `ad_${j > i ? j : j + 1}` }
    const move = (ids?: string[]) => ids?.map(rename).filter((x): x is string => x !== null)
    up(b => {
      b.ads.splice(i, 1)
      b.ads.forEach((a, j) => { a.id = `ad_${j + 1}` })
      if (b.setup.campaign) b.setup.campaign.ads = move(b.setup.campaign.ads)!
      for (const k of ['a', 'b'] as const) if (b.setup.experiments[k].ads) b.setup.experiments[k].ads = move(b.setup.experiments[k].ads)
    })
    const nf: Record<string, File> = {}, ns: Record<string, string> = {}
    for (const [k, v] of Object.entries(files)) { const r = k.startsWith('ad_') ? rename(k) : k; if (r) nf[r] = v }
    for (const [k, v] of Object.entries(shown)) { const r = k.startsWith('ad_') ? rename(k) : k; if (r) ns[r] = v; else URL.revokeObjectURL(v) }
    setFiles(nf); setShown(ns)
  }

  const errors = tried ? validate(brief, files) : {}
  const check = () => {
    setTried(true)
    const ok = Object.keys(validate(brief, files)).length === 0
    if (!ok) requestAnimationFrame(() => document.querySelector('[data-error]')?.scrollIntoView({ behavior: 'smooth', block: 'center' }))
    return ok
  }
  const e: Edit = { edit: true, up, images: shown, pick, errors, addAd, removeAd }
  const count = Object.keys(errors).filter(k => !k.startsWith('image.')).length

  return (
    <Page label="Live rehearsal · admin" switcher={
      <div>
        <Chips edit options={CATEGORIES} value={[brief.category]} onChange={([c]) => switchTo(c)} />
        <div className="mt-2 text-label text-dim">Switching starts again from that market’s example.</div>
      </div>
    }>
      <AppSections b={brief} e={e} />
      <ExperimentSetup b={brief} e={e} footer={<>
        {count > 0 && (
          <div className="mb-6 text-body font-medium text-strong">
            {count === 1 ? 'One thing' : `${count} things`} to fix before the run: {Object.entries(errors)
              .filter(([k]) => !k.startsWith('image.')).map(([, v]) => v).join(' ')}
          </div>
        )}
        <LiveRun brief={brief} files={files} check={check} />
      </>} />
      <input ref={fileInput} type="file" accept="image/png,image/jpeg" className="hidden"
        onChange={ev => { setImage(picking.current, ev.target.files?.[0]); ev.target.value = '' }} />
    </Page>
  )
}
