import { useEffect, useState, type ReactNode } from 'react'

export const STAGE_W = 1920
export const STAGE_H = 1080
// ?still: screenshot mode (scripts/shot.sh). No scaling, no counting numbers.
export const STILL = new URLSearchParams(location.search).has('still')

// Always draw one 1920×1080 stage and scale it to the window, so the site looks exactly like the video.
export function Stage({ children }: { children: ReactNode }) {
  const [scale, setScale] = useState(1)
  useEffect(() => {
    if (STILL) return
    const fit = () => setScale(Math.min(window.innerWidth / STAGE_W, window.innerHeight / STAGE_H))
    fit()
    addEventListener('resize', fit)
    return () => removeEventListener('resize', fit)
  }, [])
  return (
    <div className="grid h-full place-items-center overflow-hidden bg-bg">
      <div style={{ width: STAGE_W * scale, height: STAGE_H * scale }}>
        <div className="relative origin-top-left overflow-hidden bg-bg"
          style={{ width: STAGE_W, height: STAGE_H, transform: `scale(${scale})` }}>
          {children}
        </div>
      </div>
    </div>
  )
}
