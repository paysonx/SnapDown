/**
 * 极简 hash 路由：不引入额外依赖，配合后端静态托管即可多页切换。
 * 路由表：/（主页下载器）、/why（为什么选 SnapDown）、/vip（开通 VIP）
 */
import { ref } from 'vue'
import { scrollToTop } from './scroll.js'

export const ROUTES = {
  home: '/',
  why: '/why',
  vip: '/vip',
}

/** 把 location.hash 归一化成 "/xxx" 形式 */
function parse(hash) {
  const raw = String(hash || '').replace(/^#/, '').trim()
  if (!raw || raw === '/') return ROUTES.home
  return raw.startsWith('/') ? raw : `/${raw}`
}

export const route = ref(
  typeof window === 'undefined' ? ROUTES.home : parse(window.location.hash),
)

if (typeof window !== 'undefined') {
  window.addEventListener('hashchange', () => {
    route.value = parse(window.location.hash)
  })
}

/** 跳转到指定路由 */
export function navigate(path) {
  const target = path.startsWith('/') ? path : `/${path}`
  if (parse(window.location.hash) === target) {
    // 同一路由重复点击时也要让页面回到顶部，避免"点了没反应"
    scrollToTop()
    return
  }
  window.location.hash = target
}
