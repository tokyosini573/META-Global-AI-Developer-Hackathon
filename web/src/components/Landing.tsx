import { useEffect, useState } from 'react'
import type { Replay } from '../replay'
import { PlanMap } from './PlanMap'

// The front page: what Rehearsal is, how to use it, what you get, why trust it and which models it
// runs on, then a choice at the bottom between a precomputed example and the admin's live run.
// Every other view (replay, drawer, input, backtest) is the 1920×1080 stage behind a URL parameter.

const LOOP_SECONDS = 14 // the hero map plays 90 days in this long, then holds the last day
const HOLD_SECONDS = 3

const MARKETS = [
  { replay: 'engine', market: 'Dating', app: 'Kindred', ad: '/screens/ad.png', a: 'Nationwide ads, paywall from day 1',
    b: 'Austin, then Denver and Nashville, free for 30 days', result: 'Plan B wins 25 of 30 runs',
    detail: '450 paying users against 240' },
  { replay: 'reloop', market: 'Resale', app: 'Reloop', ad: '/screens/reloop_ad.png', a: 'Nationwide feed ads, everyone at once',
    b: 'Seattle, then Portland, sellers first', result: 'Plan B wins 30 of 30 runs',
    detail: '540 completed sales against 0' },
  { replay: 'hopway', market: 'Rides', app: 'Hopway', ad: '/screens/hopway_ad.png', a: 'Three cities at once, riders and drivers together',
    b: 'Austin, then Denver, drivers first', result: 'Plan A wins 27 of 30 runs',
    detail: '1,485 completed rides against 780' },
]

const STEPS = [
  { title: 'Show what people will see', text: "Your app's ad, its store page and the screen each side uses. Then two ways to launch it: where, which ads, what price.", model: 'You' },
  { title: 'Simulated people decide', text: 'Muse Wonder designs the people in the market. Each one looks at your real screens and decides, day by day, whether to install, use, pay or leave.', model: 'Muse Wonder · Muse Glimmer · Muse Spark' },
  { title: 'See who wins, and ask why', text: 'Both plans run 30 times over 90 days. Click anyone on the map and ask them, by voice or text, why they did what they did.', model: 'Muse Spark · Muse Voice Transcribe' },
]

const DOLPHIN = '/landing/dolphin/'

const GETS = [
  { img: '/landing/verdict.png', title: 'A verdict with a reason', text: 'Which plan wins, in how many of 30 runs, and why, in one plain sentence.' },
  { img: '/landing/person.png', title: 'Every person, on the map', text: 'Each dot is a simulated person. Open one to see the ad they saw, what they did each day, and ask them.' },
  { img: '/landing/live.png', title: 'Your own app, live', text: 'Upload your own screens, choose the channels and budgets, and rehearse your own launch in a few minutes.' },
]

const MODELS = [
  { name: 'Muse Wonder', role: 'Reads your screens and plans, designs the kinds of people in the market, and writes why the winner won.' },
  { name: 'Muse Spark', role: 'Looks at each screen as a person would and decides what they do. Answers your questions live, in character.' },
  { name: 'Muse Glimmer', role: 'A 30B model distilled from Spark, with open weights. Decides for each of 2,928 people in the dating example.',
    link: { href: 'https://huggingface.co/Yesini/Rehearsal-Glimmer-30B-r1', text: 'Weights on Hugging Face' } },
  { name: 'Muse Voice Transcribe', role: 'Turns the question you speak to a simulated person into text.' },
]

const wrap = 'mx-auto w-full max-w-[1200px] px-6 md:px-16'

function Section({ id, band, title, lead, children }: {
  id?: string; band?: boolean; title: string; lead?: string; children: React.ReactNode
}) {
  return (
    <section id={id} className={`py-24 ${band ? 'bg-surface' : ''}`}>
      <div className={wrap}>
        <h2 className="text-title font-semibold text-strong">{title}</h2>
        {lead && <p className="mt-4 max-w-[760px] text-lead text-dim">{lead}</p>}
        <div className="mt-12">{children}</div>
      </div>
    </section>
  )
}

// Both plans of the dating example, playing on a loop
function HeroMaps() {
  const [replay, setReplay] = useState<Replay | null>(null)
  const [t, setT] = useState(0)
  useEffect(() => { fetch('/replays/engine.json').then(r => r.json()).then(setReplay) }, [])
  useEffect(() => {
    if (!replay) return
    const days = replay.meta.days, start = performance.now()
    let raf = 0
    const tick = (now: number) => {
      const s = ((now - start) / 1000) % (LOOP_SECONDS + HOLD_SECONDS)
      setT(Math.min(days, (s / LOOP_SECONDS) * days))
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [replay])
  if (!replay) return <div className="aspect-[2/1] rounded-card bg-surface" />
  const days = replay.meta.days
  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <span className="label">Dating example · same $40,000 budget</span>
        <span className="label text-strong">{t >= days ? 'Plan B wins' : `Day ${Math.floor(t)} of ${days}`}</span>
      </div>
      <div className="mt-6 grid gap-8 md:grid-cols-2">
        {(['a', 'b'] as const).map(k => (
          <div key={k}>
            <div className={`text-body font-medium ${k === 'a' ? 'text-plan-a' : 'text-plan-b'}`}>
              Plan {k.toUpperCase()} · {k === 'a' ? 'Nationwide ads' : 'City by city'}
            </div>
            <div className="mt-2"><PlanMap replay={replay} plan={k} t={t} width={520} /></div>
          </div>
        ))}
      </div>
      <p className="mt-4 text-body text-dim">
        Each dot stands for 60 simulated people. A line is a match. Plan A&apos;s users are spread too thin to meet anyone.
      </p>
    </div>
  )
}

// A phone showing one of the demo app's real screens
function Phone({ src, className = '' }: { src: string; className?: string }) {
  return (
    <div className={`overflow-hidden rounded-[28px] border-[6px] border-strong bg-strong ${className}`}>
      <img src={src} alt="" className="block w-full" />
    </div>
  )
}

// The picture beside each step of "How it works"
function StepPicture({ i }: { i: number }) {
  if (i === 0)
    return (
      <div className="relative mx-auto flex h-[420px] max-w-[460px] items-end justify-center rounded-card bg-blue-50">
        <Phone src="/screens/reloop_ad.png" className="absolute top-10 left-8 w-[132px] -rotate-6" />
        <Phone src="/screens/reloop_store.png" className="absolute top-6 right-8 w-[132px] rotate-6" />
        <img src={`${DOLPHIN}tablet.webp`} alt="" className="relative h-[300px]" />
      </div>
    )
  if (i === 1)
    return (
      <div className="mx-auto flex h-[420px] max-w-[460px] flex-col items-center justify-center rounded-card bg-blue-50 px-6">
        <img src={`${DOLPHIN}crowd.webp`} alt="" className="w-full" />
        <div className="label mt-2 text-blue-900">Thousands of people, each deciding for themselves</div>
      </div>
    )
  return (
    <div className="mx-auto h-[420px] max-w-[460px] overflow-hidden rounded-card border border-line bg-surface">
      <img src="/landing/person.png" alt="" className="h-full w-full object-cover object-right" />
    </div>
  )
}

function Start() {
  const [open, setOpen] = useState(false)
  return (
    <section id="start" className="relative overflow-hidden bg-blue-900 py-24 text-white">
      <img src={`${DOLPHIN}wave.webp`} alt=""
        className="pointer-events-none absolute right-6 -bottom-6 hidden h-[340px] lg:block xl:right-[max(24px,calc(50%-660px))]" />
      <div className={`${wrap} relative`}>
        <h2 className="text-title font-semibold">Start a rehearsal</h2>
        <p className="mt-4 max-w-[640px] text-lead text-blue-100">
          Watch a finished example, or run your own app live.
        </p>
        {!open ? (
          <button onClick={() => setOpen(true)}
            className="mt-12 cursor-pointer rounded-card bg-white px-8 py-5 text-body font-medium text-blue-900">
            Start a rehearsal
          </button>
        ) : (
          <div className="mt-12 grid max-w-[860px] gap-6 md:grid-cols-2">
            <div className="rounded-card bg-white p-8 text-text">
              <div className="label text-blue-600">Free · starts at once</div>
              <h3 className="mt-3 text-number font-medium text-strong">Watch an example</h3>
              <p className="mt-4 text-body text-dim">
                Three made-up apps, rehearsed ahead of time with Muse Glimmer and Muse Spark. Pick a market.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                {MARKETS.map(m => (
                  <a key={m.replay} href={`/?new&replay=${m.replay}`}
                    className="rounded-card border border-blue-200 bg-blue-50 px-5 py-3 text-body font-medium text-blue-900 hover:border-blue-600">
                    {m.market}
                  </a>
                ))}
              </div>
            </div>
            <div className="rounded-card bg-blue-600 p-8 text-white">
              <div className="label text-blue-100">Admin key · a few minutes</div>
              <h3 className="mt-3 text-number font-medium">Run it live</h3>
              <p className="mt-4 text-body text-blue-100">
                Upload your own ad, store page and app screens, set the channels and budgets, and Muse Wonder and
                Muse Spark rehearse it now.
              </p>
              <a href="/?new&admin"
                className="mt-8 inline-block rounded-card bg-white px-5 py-3 text-body font-medium text-blue-900">
                Open the live form
              </a>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

export function Landing() {
  return (
    <div className="min-h-full bg-bg text-text">
      <nav className={`${wrap} flex items-center justify-between py-6`}>
        <a href="/" className="flex items-center gap-3 text-lead font-semibold text-strong">
          <img src={`${DOLPHIN}smile.webp`} alt="" className="h-10" />Rehearsal
        </a>
        <div className="flex items-center gap-8">
          <span className="hidden gap-8 text-body text-dim md:flex">
            <a href="#how" className="hover:text-strong">How it works</a>
            <a href="#markets" className="hover:text-strong">Markets</a>
            <a href="#trust" className="hover:text-strong">Trust</a>
            <a href="#models" className="hover:text-strong">Models</a>
          </span>
          <a href="#start" className="rounded-card bg-blue-600 px-5 py-3 text-body font-medium text-white">Start</a>
        </div>
      </nav>

      <header className={`${wrap} pt-8 pb-24`}>
        <div className="grid items-center gap-12 md:grid-cols-[1fr_180px]">
          <div>
            <div className="label text-blue-600">Launch rehearsal for two-sided apps</div>
            <h1 className="mt-4 text-title font-semibold text-strong md:text-headline">Rehearse your launch.</h1>
            <p className="mt-6 max-w-[680px] text-lead text-dim">
              Before you spend the budget, thousands of simulated Americans try your app. Give Rehearsal two launch
              plans: it plays both for 90 days, tells you which one wins and why, and lets you ask anyone what they
              thought.
            </p>
            <div className="mt-10 flex flex-wrap gap-4">
              <a href="#start" className="rounded-card bg-blue-600 px-8 py-5 text-body font-medium text-white">Start a rehearsal</a>
              <a href="#how" className="rounded-card border border-line px-8 py-5 text-body font-medium text-strong hover:border-blue-200">
                See how it works
              </a>
            </div>
          </div>
          <div className="relative mx-auto hidden h-[200px] w-[180px] md:block">
            <div className="absolute inset-x-0 bottom-0 h-[150px] rounded-full bg-blue-50" />
            <img src={`${DOLPHIN}smile.webp`} alt="" className="absolute bottom-3 left-1/2 h-[190px] -translate-x-1/2" />
          </div>
        </div>
        <div className="mt-16"><HeroMaps /></div>
      </header>

      <section className="bg-surface py-24">
        <div className={`${wrap} grid items-center gap-12 md:grid-cols-[300px_1fr]`}>
          <img src={`${DOLPHIN}surprised.webp`} alt="" className="mx-auto h-[300px]" />
          <div>
            <h2 className="text-title font-semibold text-strong">You launch only once.</h2>
            <p className="mt-4 max-w-[760px] text-lead text-dim">
              An app that needs two sides, like daters, buyers and sellers, or riders and drivers, is empty until both
              sides are near each other. Where and how you launch decides whether they ever meet.
            </p>
            <div className="mt-10 grid gap-8 md:grid-cols-3">
              {[['Same budget, different fate', 'Two plans with the same money can end with twice the users, or none.'],
                ['Testing for real is slow', 'Trying a plan in the market takes months and the whole budget.'],
                ['Surveys miss the map', 'People can say they like an app, and still leave when nobody is nearby.']].map(([h, p]) => (
                <div key={h} className="border-t-2 border-blue-600 pt-4">
                  <h3 className="text-lead font-semibold text-strong">{h}</h3>
                  <p className="mt-2 text-body text-dim">{p}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="how" className="py-24">
        <div className={wrap}>
          <h2 className="text-title font-semibold text-strong">How it works</h2>
          <p className="mt-4 max-w-[760px] text-lead text-dim">Three steps, from your screens to a verdict you can question.</p>
          <div className="relative mt-16">
            <div className="absolute top-0 bottom-0 left-1/2 hidden border-l-2 border-dashed border-blue-200 md:block" />
            {STEPS.map((st, i) => (
              <div key={st.title} className="relative grid items-center gap-10 py-10 md:grid-cols-2 md:gap-24">
                <div className={i % 2 ? 'md:order-2' : ''}>
                  <div className="text-headline font-semibold text-blue-200">{i + 1}</div>
                  <h3 className="mt-2 text-title font-semibold text-strong">{st.title}</h3>
                  <p className="mt-4 text-lead text-dim">{st.text}</p>
                  <div className="label mt-6 text-blue-600">{st.model}</div>
                </div>
                <div className={`relative bg-bg ${i % 2 ? 'md:order-1' : ''}`}><StepPicture i={i} /></div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <Section band title="What you get">
        <div className="grid gap-6 md:grid-cols-3">
          {GETS.map(g => (
            <div key={g.title} className="overflow-hidden rounded-card border border-line bg-white">
              <img src={g.img} alt="" className="aspect-video w-full border-b border-line object-cover object-left-top" />
              <div className="p-8">
                <h3 className="text-lead font-semibold text-strong">{g.title}</h3>
                <p className="mt-3 text-body text-dim">{g.text}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section id="markets" title="Three markets, three answers"
        lead="Each example is a made-up app with its own screens, people and two launch plans. The winner is not always the same kind of plan.">
        <div className="grid gap-6 md:grid-cols-3">
          {MARKETS.map(m => (
            <a key={m.replay} href={`/?replay=${m.replay}`}
              className="overflow-hidden rounded-card border border-line hover:border-blue-200">
              <div className="flex h-[260px] items-end justify-center overflow-hidden bg-blue-50 pt-8">
                <Phone src={m.ad} className="-mb-24 w-[150px]" />
              </div>
              <div className="p-8">
                <div className="label text-blue-600">{m.market} · {m.app}</div>
                <div className="mt-6 text-body"><span className="font-medium text-plan-a">A</span> {m.a}</div>
                <div className="mt-2 text-body"><span className="font-medium text-plan-b">B</span> {m.b}</div>
                <div className="mt-6 text-lead font-semibold text-strong">{m.result}</div>
                <div className="text-body text-dim">{m.detail}</div>
                <div className="mt-6 text-body font-medium text-blue-600">Watch this rehearsal</div>
              </div>
            </a>
          ))}
        </div>
      </Section>

      <section id="trust" className="bg-surface py-24">
        <div className={`${wrap} grid items-center gap-16 md:grid-cols-[1fr_420px]`}>
          <div>
            <h2 className="text-title font-semibold text-strong">Can you trust it?</h2>
            <p className="mt-4 max-w-[640px] text-lead text-dim">
              We fixed the rules first, committed the predictions, and only then looked at what really happened to five
              real launches the method had never seen.
            </p>
            <div className="mt-10 text-headline font-semibold text-blue-600">16 of 20</div>
            <div className="mt-2 text-body text-dim">turning points called right</div>
            <p className="mt-6 max-w-[640px] text-body text-dim">
              A model that always says &ldquo;it grows&rdquo; gets 11 of 20. Five cases is a check of the method, not a
              measured accuracy.{' '}
              <a href="/?backtest" className="font-medium text-blue-600">See every case</a>
            </p>
          </div>
          <img src={`${DOLPHIN}magnify.webp`} alt="" className="w-full rounded-card" />
        </div>
      </section>

      <Section id="models" title="Built with Meta models" lead="Each model has one job.">
        <div className="grid gap-6 md:grid-cols-2">
          {MODELS.map(m => (
            <div key={m.name} className="rounded-card border border-line p-8">
              <h3 className="text-lead font-semibold text-strong">{m.name}</h3>
              <p className="mt-3 text-body text-dim">{m.role}</p>
              {m.link && <a href={m.link.href} className="mt-4 inline-block text-body font-medium text-blue-600">{m.link.text}</a>}
            </div>
          ))}
        </div>
      </Section>

      <Start />

      <footer className={`${wrap} flex flex-wrap justify-between gap-4 py-10 text-body text-dim`}>
        <span>Built solo for the Meta Global AI Developer Hackathon.</span>
        <a href="https://github.com/tokyosini573/META-Global-AI-Developer-Hackathon" className="hover:text-strong">Source on GitHub</a>
      </footer>
    </div>
  )
}
