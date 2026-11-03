import { useState } from 'react'

// The Setup page's parts. Each one shows a value read-only (edit=false) or lets the admin change it.
// One look for both: a white field on a 1px rule, 12px radius, body-size text.

export const box = 'w-full min-w-0 rounded-card border border-line bg-bg px-4 py-3 text-body text-strong'
const editable = 'outline-none focus:border-blue-600 placeholder:text-dim'

export function Section({ n, title, required, collapsed, summary, band, children }: {
  n: string; title: string; required?: boolean; collapsed?: boolean; summary?: string; band?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(!collapsed)
  const head = (
    <h2 className="flex flex-wrap items-center gap-4 text-lead font-semibold text-strong">
      <span>{n} {title}</span>
      <span className={`label rounded-full px-3 py-1 ${required ? 'bg-blue-50 text-blue-600' : 'bg-surface'}`}>
        {required ? 'Required' : 'Optional'}
      </span>
    </h2>
  )
  return (
    <section className={`border-t border-line ${band ? 'bg-surface' : ''}`}>
      <div className="mx-auto max-w-[1200px] px-6 py-12 md:px-16">
        {open ? head : (
          <button onClick={() => setOpen(true)} className="flex w-full cursor-pointer flex-wrap items-center justify-between gap-4 text-left">
            {head}
            <span className="text-body text-blue-600">{summary} ›</span>
          </button>
        )}
        {open && <div className="mt-8">{children}</div>}
      </div>
    </section>
  )
}

export function Field({ label, error, hint, wide, children }: {
  label: string; error?: string; hint?: string; wide?: boolean; children: React.ReactNode
}) {
  return (
    <div className={`min-w-0 ${wide ? 'md:col-span-2' : ''}`} data-error={error ? true : undefined}>
      <div className="mb-2 text-label text-dim">{label}</div>
      {children}
      {(error || hint) && <div className={`mt-2 text-label ${error ? 'font-medium text-strong' : 'text-dim'}`}>
        {error && <span className="mr-2 inline-block size-2 rounded-full bg-blue-600" />}{error || hint}
      </div>}
    </div>
  )
}

export const Grid = ({ children, className = '' }: { children: React.ReactNode; className?: string }) =>
  <div className={`grid gap-6 md:grid-cols-2 ${className}`}>{children}</div>

export function Text({ value, onChange, edit, max, multiline, placeholder }: {
  value: string | undefined; onChange?: (v: string) => void; edit: boolean; max?: number; multiline?: boolean; placeholder?: string
}) {
  if (!edit) return <div className={`${box} ${multiline ? 'min-h-[84px]' : ''} ${value ? '' : 'text-dim'}`}>{value || 'Not given'}</div>
  const props = {
    value: value ?? '', maxLength: max, placeholder, className: `${box} ${editable}`,
    onChange: (e: { target: { value: string } }) => onChange?.(e.target.value),
  }
  return multiline ? <textarea rows={3} {...props} className={`${props.className} block resize-y`} /> : <input {...props} />
}

export function Num({ value, onChange, edit, min, max, step, before, after, width = 'w-32' }: {
  value: number | undefined; onChange?: (v: number) => void; edit: boolean
  min?: number; max?: number; step?: number; before?: string; after?: string; width?: string
}) {
  const shown = value === undefined || !Number.isFinite(value) ? '' : String(Math.round(value * 100) / 100)
  if (!edit) return <div className={`${box} tabular-nums`}>{[before, shown || '—', after].filter(Boolean).join(before === '$' ? '' : ' ')}{before === '$' && after ? ` ${after}` : ''}</div>
  return (
    <span className="inline-flex items-center gap-2 text-body whitespace-nowrap text-text">
      {before}
      <input type="number" inputMode="decimal" value={shown} min={min} max={max} step={step ?? 1}
        onChange={e => onChange?.(e.target.value === '' ? NaN : Number(e.target.value))}
        className={`${box} ${editable} ${width} tabular-nums`} />
      {after}
    </span>
  )
}

// Pills: one value (multi=false) or any number of them
export function Chips<T extends string | number>({ options, value, onChange, edit, multi }: {
  options: [T, string][]; value: T[]; onChange?: (v: T[]) => void; edit: boolean; multi?: boolean
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map(([k, words]) => {
        const on = value.includes(k)
        return (
          <button key={String(k)} type="button" disabled={!edit} aria-pressed={on}
            onClick={() => onChange?.(multi ? (on ? value.filter(v => v !== k) : [...value, k]) : [k])}
            className={`rounded-full border px-4 py-2 text-body ${on ? 'border-blue-600 bg-blue-50 text-blue-900' : 'border-line text-dim'
              } ${edit ? 'cursor-pointer hover:border-blue-200' : ''} ${edit && on ? 'hover:border-blue-600' : ''}`}>
            {words}
          </button>
        )
      })}
    </div>
  )
}

export function Select<T extends string>({ options, value, onChange, edit, empty, className = '' }: {
  options: [T, string][]; value: T | undefined; onChange?: (v: T | undefined) => void; edit: boolean; empty?: string; className?: string
}) {
  const words = options.find(([k]) => k === value)?.[1]
  if (!edit) return <div className={`${box} ${words ? '' : 'text-dim'}`}>{words ?? empty ?? 'Not given'}</div>
  return (
    <select value={value ?? ''} onChange={e => onChange?.((e.target.value || undefined) as T | undefined)}
      className={`${box} ${editable} cursor-pointer ${className}`}>
      {empty !== undefined && <option value="">{empty}</option>}
      {options.map(([k, w]) => <option key={k} value={k}>{w}</option>)}
    </select>
  )
}

// "More details: ..." folds the optional fields of a section
export function More({ summary, children }: { summary: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return open ? <div className="mt-8">{children}</div> : (
    <button onClick={() => setOpen(true)} className="mt-6 cursor-pointer text-left text-body text-blue-600">
      More details: {summary} ›
    </button>
  )
}

// One image a run needs: a preview, or an empty slot to add it
export function Shot({ label, src, edit, onPick, error, tall = true, add }: {
  label: string; src?: string; edit: boolean; onPick?: () => void; error?: string; tall?: boolean; add?: string
}) {
  const size = tall ? 'h-[250px] w-[150px]' : 'h-[250px] w-full'
  const inner = src
    ? <img src={src} alt={label} className={`${size} rounded-card border border-line bg-surface object-contain`} />
    : <div className={`${size} flex items-center justify-center rounded-card border border-dashed p-4 text-center text-label ${edit
      ? 'border-blue-200 bg-blue-50 text-blue-600' : 'border-line bg-surface text-dim'}`}>
      {edit ? add ?? `Add ${label.startsWith('What') ? '' : 'the '}${label.toLowerCase()}` : 'Not in this example'}
    </div>
  return (
    <div className={tall ? 'w-[150px]' : 'w-full'} data-error={error ? true : undefined}>
      {edit ? <button type="button" onClick={onPick} className="block w-full cursor-pointer text-left">{inner}</button> : inner}
      <div className="mt-2 text-label text-dim">{label}</div>
      {edit && src && <button type="button" onClick={onPick} className="cursor-pointer text-label text-blue-600">Replace</button>}
      {error && <div className="text-label font-medium text-strong"><span className="mr-2 inline-block size-2 rounded-full bg-blue-600" />{error}</div>}
    </div>
  )
}

export const Link = ({ onClick, children }: { onClick: () => void; children: React.ReactNode }) =>
  <button type="button" onClick={onClick} className="cursor-pointer text-body text-blue-600 hover:text-blue-900">{children}</button>
