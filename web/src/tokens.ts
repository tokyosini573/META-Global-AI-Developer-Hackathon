// 캔버스는 CSS 클래스를 못 쓰므로 index.css 의 토큰 값을 그대로 읽어 온다.
const css = getComputedStyle(document.documentElement)
const v = (name: string) => css.getPropertyValue(name).trim()

export const color = {
  dotIdle: v('--color-dot-idle'),
  dim: v('--color-dim'),
  strong: v('--color-strong'),
  a: v('--color-plan-a'),
  b: v('--color-plan-b'),
}
