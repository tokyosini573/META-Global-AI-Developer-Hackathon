import { useEffect, useState, type ReactNode } from 'react'

export const STAGE_W = 1920
export const STAGE_H = 1080
// ?still: 스크린샷 모드 (scripts/shot.sh). 줄이지 않고, 숫자를 굴리지 않는다.
export const STILL = new URLSearchParams(location.search).has('still')

// 화면은 항상 1920×1080 한 장으로 그리고 창에 맞게 줄인다. 영상과 사이트가 똑같이 보이게.
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
