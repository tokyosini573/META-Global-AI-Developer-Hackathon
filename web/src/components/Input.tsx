import { useEffect, useState } from 'react'
import { PLANS, type Replay } from '../replay'
import { STILL } from './Stage'

const STEP_MS = 900 // the example is precomputed, so the steps only show what was done for it

// The screens people see, exactly as the engine's models looked at them
const SCREENS = ['ad', 'store', 'paywall_m0_none']

function Step({ state, text }: { state: 'done' | 'now' | 'todo'; text: string }) {
  return (
    <div className="flex items-baseline gap-4">
      <span className={`size-2 flex-none -translate-y-0.5 rounded-full ${state === 'done' ? 'bg-strong'
        : state === 'now' ? 'border-[1.5px] border-strong' : 'border-[1.5px] border-dot-idle'}`} />
      <span className={`text-body ${state === 'todo' ? 'text-dim' : ''}`}>{text}</span>
    </div>
  )
}

export function Input({ replay, onDone }: { replay: Replay; onDone: () => void }) {
  const { meta, plans } = replay
  // ?new&step=2 freezes the progress on a step (screenshots)
  const fixed = new URLSearchParams(location.search).get('step')
  const [step, setStep] = useState<number | null>(fixed ? Number(fixed) : null)
  const steps = [
    'Read the ad, the store page and the paywall',
    `Designed ${meta.people_types?.length ?? 'the'} kinds of people for this market`,
    'Gave each person a life, a job and a mood',
    `Ran ${meta.days} days, both plans, ${meta.runs ?? 'many'} times`,
  ]

  useEffect(() => {
    if (step === null || fixed || STILL) return
    const id = setTimeout(() => (step + 1 >= steps.length ? onDone() : setStep(step + 1)), STEP_MS)
    return () => clearTimeout(id)
  }, [step]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <header className="label absolute top-12 right-16 left-16 flex justify-between">
        <span className="text-strong">Rehearsal</span>
        <span>New rehearsal · {meta.market} · {meta.days} days</span>
      </header>

      <section className="absolute top-28 left-16 w-[1100px]">
        <h1 className="text-headline font-semibold text-strong">Rehearse a launch.</h1>
        <p className="mt-6 max-w-[760px] text-body">
          Show what people will see, and two ways to launch it. Rehearsal builds the market and runs both.
        </p>
      </section>

      <section className="absolute top-[328px] left-16">
        <div className="label">Your app · {meta.app} · what people see</div>
        <div className="mt-4 flex gap-6">
          {SCREENS.map(s => (
            <div key={s} className="h-[432px] w-[220px] overflow-hidden rounded-card border border-line bg-surface">
              <img src={`/screens/${s}.png`} alt="" className="size-full object-cover" />
            </div>
          ))}
        </div>
      </section>

      <section className="absolute top-[328px] right-16 left-[836px] grid grid-cols-2 gap-6">
        {PLANS.map(k => (
          <div key={k}>
            <div className={`label ${k === 'a' ? 'text-plan-a' : 'text-plan-b'}`}>{plans[k].name}</div>
            <div className="mt-4 h-[432px] rounded-card bg-surface p-8">
              <div className="mb-12 text-number font-medium text-strong">{plans[k].card?.title ?? plans[k].summary}</div>
              {plans[k].card && (['where', 'ads', 'price'] as const).map(f => (
                <div key={f} className="grid grid-cols-[96px_1fr] gap-4 border-t border-line py-4">
                  <span className="label pt-[3px]">{f}</span>
                  <span className="text-body">{plans[k].card![f]}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </section>

      {step === null ? (
        <section className="absolute top-[824px] right-16 left-16 flex items-center gap-6">
          <button onClick={() => setStep(0)}
            className="cursor-pointer rounded-card bg-strong px-8 py-5 text-body font-medium text-bg">
            Run both plans
          </button>
          <span className="label">
            {replay.people.a.length.toLocaleString('en-US')} people each · same ${meta.budget_usd.toLocaleString('en-US')} budget
          </span>
        </section>
      ) : (
        <section className="absolute top-[824px] right-16 left-16">
          <div className="label">Muse Wonder is building the market</div>
          <div className="relative mt-4 h-0.5 bg-line">
            <i className="absolute inset-y-0 left-0 bg-strong transition-[width] duration-[900ms] ease-linear"
              style={{ width: `${((step + 1) / steps.length) * 100}%` }} />
          </div>
          <div className="mt-6 grid grid-cols-4 gap-6">
            {steps.map((t, i) => <Step key={t} text={t} state={i < step ? 'done' : i === step ? 'now' : 'todo'} />)}
          </div>
        </section>
      )}
    </>
  )
}
