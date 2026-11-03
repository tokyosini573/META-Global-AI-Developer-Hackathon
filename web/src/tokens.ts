// Canvas can't use CSS classes, so read the token values straight from index.css.
const css = getComputedStyle(document.documentElement)
const v = (name: string) => css.getPropertyValue(name).trim()

export const color = {
  land: v('--color-blue-200'),
  dim: v('--color-dim'),
  strong: v('--color-strong'),
  a: v('--color-plan-a'),
  b: v('--color-plan-b'),
}
