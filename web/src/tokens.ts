// Canvas can't use CSS classes, so read the token values straight from index.css.
const css = getComputedStyle(document.documentElement)
const v = (name: string) => css.getPropertyValue(name).trim()

export const color = {
  dotIdle: v('--color-dot-idle'),
  dim: v('--color-dim'),
  strong: v('--color-strong'),
  a: v('--color-plan-a'),
  b: v('--color-plan-b'),
}
