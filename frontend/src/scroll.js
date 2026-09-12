/** 滚动相关的小工具：统一处理"减少动效"偏好，避免各处重复判断。 */

export function prefersReducedMotion() {
  return (
    typeof window !== 'undefined' &&
    !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  )
}

/** 回到页面顶部 */
export function scrollToTop() {
  if (typeof window === 'undefined') return
  window.scrollTo({ top: 0, behavior: prefersReducedMotion() ? 'auto' : 'smooth' })
}

/** 滚动到指定元素（页面内跳转请用它，不要写 href="#id"，会与 hash 路由冲突） */
export function scrollToElement(el, block = 'start') {
  if (!el) return
  el.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block })
}

/** 是否为桌面级精确指针设备（决定要不要自动聚焦输入框，避免手机上误弹键盘） */
export function hasFinePointer() {
  return (
    typeof window !== 'undefined' &&
    !!window.matchMedia?.('(hover: hover) and (pointer: fine)').matches
  )
}
