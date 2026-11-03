// v2 Setup page (?new): one scrolling page with sections 01-08 of the brief (docs/brief-format.md).
// ?new&replay=<name> shows that example's meta.brief read-only; ?new&admin edits and runs it live.
// Replaces components/Input.tsx and components/AdminInput.tsx.
export function Setup() {
  return (
    <div className="min-h-full bg-bg px-6 py-24 text-text">
      <div className="mx-auto max-w-[1200px]">
        <h1 className="text-title font-semibold text-strong">Let&apos;s rehearse your app.</h1>
      </div>
    </div>
  )
}
