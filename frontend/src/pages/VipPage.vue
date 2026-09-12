<script setup>
import { onUnmounted, ref, watch } from 'vue'
import { scrollToElement } from '../scroll.js'

const emit = defineEmits(['go-download'])

const plans = [
  {
    id: 'monthly',
    name: '月度会员',
    price: '19',
    unit: '元 / 月',
    tagline: '先试一个月，随时取消',
    perks: ['4K / 8K 原画通道', '批量解析下载', '极速优先队列', '纯净无广告界面'],
    featured: false,
    badge: '',
  },
  {
    id: 'yearly',
    name: '年度会员',
    price: '128',
    unit: '元 / 年',
    tagline: '相当于 10.7 元 / 月，省 100 元',
    perks: ['包含月度会员全部权益', '8K 原画 + 高帧率优先', '队列并发提升到 5 个任务', '新平台适配第一时间开放'],
    featured: true,
    badge: '最受欢迎',
  },
  {
    id: 'lifetime',
    name: '终身会员',
    price: '298',
    unit: '元 · 一次买断',
    tagline: '一次付费，长期可用',
    perks: ['包含年度会员全部权益', '后续大版本更新免费', '专属标识与优先支持', '不限期限使用'],
    featured: false,
    badge: '买断制',
  },
]

const benefits = [
  {
    title: '4K / 8K 原画通道',
    desc: '解锁平台提供的最高码率原画，不再被压缩画质限制。',
    icon: 'M4 5h16v14H4zM9 9l6 3-6 3V9Z',
  },
  {
    title: '批量解析下载',
    desc: '一次粘贴多条链接，队列自动排队执行，效率翻倍。',
    icon: 'M4 6h16M4 12h16M4 18h10',
  },
  {
    title: '极速优先队列',
    desc: '高峰期优先处理你的任务，解析更快、等待更短。',
    icon: 'M13 2 3 14h9l-1 8 10-12h-9l1-8Z',
  },
  {
    title: '队列并发提升',
    desc: '同时进行的下载任务更多，追剧、备份资料不用一个一个等。',
    icon: 'M8 4h8v6H8zM4 14h6v6H4zM14 14h6v6h-6z',
  },
  {
    title: '纯净无广告界面',
    desc: '没有弹窗、跳转与诱导下载，界面里只有你要保存的视频。',
    icon: 'M12 3 4 6.5v5c0 4.6 3.4 8.4 8 9.5 4.6-1.1 8-4.9 8-9.5v-5L12 3Z',
  },
  {
    title: '字幕与封面打包',
    desc: '需要时连字幕、封面一并收好，归档整理一次到位。',
    icon: 'M3 5h18v14H3zM6 12h4M6 16h8M14 12h4',
  },
]

const matrix = [
  { item: '解析与下载次数', free: '无限次', pro: '无限次 · 更快通道' },
  { item: '最高画质', free: '1080P', pro: '4K / 8K 原画' },
  { item: '同时下载任务', free: '1 个', pro: '最多 5 个' },
  { item: '批量粘贴链接', free: '—', pro: '支持' },
  { item: '优先处理队列', free: '—', pro: '支持' },
  { item: '界面广告', free: '无', pro: '无' },
  { item: '字幕 / 封面打包', free: '字幕可选', pro: '字幕 + 封面' },
  { item: '新功能抢先体验', free: '—', pro: '支持' },
]

const trust = [
  { title: '7 天无理由退款', desc: '开通后 7 天内不满意，可申请全额退款。', icon: 'M20 6 9 17l-5-5' },
  { title: '到期不自动续费', desc: '默认一次性购买，不会悄悄扣款。', icon: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18ZM12 8v5' },
  { title: '文件留在本地', desc: '解析与下载在本机服务完成，不经过第三方服务器。', icon: 'M4 6h16v12H4zM9 12h6' },
  { title: '合规使用提示', desc: '仅供个人学习与备份，请尊重原作者版权。', icon: 'M12 3 4 6.5v5c0 4.6 3.4 8.4 8 9.5 4.6-1.1 8-4.9 8-9.5v-5L12 3Z' },
]

const faqs = [
  {
    q: '现在可以直接付款开通吗？',
    a: 'SnapDown Pro 正在内测，支付通道还在接入中。内测期间全部会员能力对所有用户免费开放，正式上线后会第一时间在站内公告。',
  },
  {
    q: '会员到期会自动续费吗？',
    a: '不会。所有套餐默认一次性购买，到期后权益自动结束，不产生任何额外扣费。',
  },
  {
    q: '开通后可以退款吗？',
    a: '支持 7 天无理由退款。如果 Pro 体验没有达到你的预期，可以申请全额退回。',
  },
  {
    q: '免费版会被限制或降速吗？',
    a: '不会。免费版的解析与下载保持完整可用，Pro 提供的是更快的通道与批量能力，而不是把免费版故意变慢。',
  },
  {
    q: '换设备之后权益还在吗？',
    a: '权益跟随账号而非设备，账号体系正在同步开发中；上线前内测用户的权益会完整保留。',
  },
]

const activePlan = ref(null)
const plansSection = ref(null)

/** 滚动到本页套餐区。
 *  注意：不能用 href="#plans" —— 本站是 hash 路由，#plans 会被当成路由 "/plans"，
 *  未匹配时回退渲染主页，表现就是"点了跳回首页"。 */
function scrollToPlans() {
  scrollToElement(plansSection.value)
}

function choosePlan(plan) {
  activePlan.value = plan
}

function closeDialog() {
  activePlan.value = null
}

function onKeydown(e) {
  if (e.key === 'Escape') closeDialog()
}

if (typeof window !== 'undefined') {
  window.addEventListener('keydown', onKeydown)
}

watch(activePlan, (plan) => {
  document.body.style.overflow = plan ? 'hidden' : ''
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})
</script>

<template>
  <div class="animate-fade-in">
    <!-- Hero -->
    <section class="relative overflow-hidden" style="background-image: linear-gradient(160deg, #0f172a 0%, #1e293b 55%, #422006 100%)">
      <div
        class="pointer-events-none absolute -top-32 left-1/4 h-[420px] w-[560px] opacity-80"
        style="background: radial-gradient(closest-side, rgb(245 158 11 / 0.34), transparent 100%)"
        aria-hidden="true"
      ></div>
      <div
        class="pointer-events-none absolute -bottom-32 right-1/4 h-[380px] w-[520px] opacity-80"
        style="background: radial-gradient(closest-side, rgb(234 88 12 / 0.36), transparent 100%)"
        aria-hidden="true"
      ></div>

      <div class="relative mx-auto max-w-4xl px-4 py-16 text-center sm:px-6 sm:py-20">
        <span
          class="animate-fade-up inline-flex items-center gap-1.5 rounded-full bg-amber-400/15 px-3.5 py-1.5 text-xs font-bold text-amber-300 ring-1 ring-amber-400/40"
        >
          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M3 7.5 7 11l5-7 5 7 4-3.5-2 11H5l-2-11ZM5 20h14v1.5H5z" />
          </svg>
          SnapDown Pro 会员
        </span>

        <h1
          class="animate-fade-up mt-5 text-3xl font-bold leading-tight tracking-tight text-white sm:text-5xl"
          style="animation-delay: 60ms"
        >
          解锁<span class="text-gold">高速通道</span>，把体验拉满
        </h1>

        <p
          class="animate-fade-up mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-slate-300 sm:text-base"
          style="animation-delay: 120ms"
        >
          4K / 8K 原画、批量下载、优先队列与干净无广告的界面——为每天都要保存视频的人准备。
          让等待消失，让画质不再妥协。
        </p>

        <div
          class="animate-fade-up mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row"
          style="animation-delay: 180ms"
        >
          <button type="button" class="btn-vip w-full !px-7 !py-3.5 !text-base sm:w-auto" @click="scrollToPlans">
            立即开通 VIP
          </button>
          <button
            type="button"
            class="inline-flex w-full items-center justify-center rounded-xl bg-white/10 px-6 py-3.5 text-base font-semibold text-white ring-1 ring-white/25 backdrop-blur transition-colors hover:bg-white/20 sm:w-auto"
            @click="emit('go-download')"
          >
            先免费用一次
          </button>
        </div>

        <p class="animate-fade-up mt-5 text-xs text-amber-200/80" style="animation-delay: 240ms">
          内测阶段 · 支付通道接入中，当前全部会员能力免费开放
        </p>
      </div>
    </section>

    <!-- 会员权益 -->
    <section class="mx-auto max-w-6xl px-4 py-14 sm:px-6">
      <div class="text-center">
        <h2 class="text-2xl font-bold tracking-tight text-slate-900">会员能拿到什么</h2>
        <p class="mt-2 text-sm text-slate-500">六项实打实的能力升级，不做数字游戏</p>
      </div>

      <div class="mt-9 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div v-for="b in benefits" :key="b.title" class="card card-hover p-6">
          <span class="flex h-11 w-11 items-center justify-center rounded-xl bg-orange-50 text-orange-700 ring-1 ring-orange-100">
            <svg class="h-5.5 w-5.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path :d="b.icon" />
            </svg>
          </span>
          <h3 class="mt-4 text-base font-bold text-slate-900">{{ b.title }}</h3>
          <p class="mt-1.5 text-sm leading-relaxed text-slate-500">{{ b.desc }}</p>
        </div>
      </div>
    </section>

    <!-- 套餐 -->
    <section id="plans" ref="plansSection" class="scroll-mt-20 border-y border-slate-100 bg-slate-50/70">
      <div class="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <div class="text-center">
          <h2 class="text-2xl font-bold tracking-tight text-slate-900">选择适合你的方案</h2>
          <p class="mt-2 text-sm text-slate-500">价格均为内测标价，正式上线前可能微调</p>
        </div>

        <div class="mt-10 grid grid-cols-1 gap-5 lg:grid-cols-3">
          <div
            v-for="plan in plans"
            :key="plan.id"
            class="relative flex flex-col p-6"
            :class="plan.featured ? 'card-vip lg:-mt-4 lg:mb-4' : 'card card-hover'"
          >
            <span
              v-if="plan.badge"
              class="absolute -top-3 left-6 rounded-full px-3 py-1 text-[11px] font-bold"
              :class="plan.featured ? 'bg-orange-700 text-white' : 'bg-slate-100 text-slate-500 ring-1 ring-slate-200'"
            >
              {{ plan.badge }}
            </span>

            <h3 class="text-base font-bold text-slate-900">{{ plan.name }}</h3>
            <p class="mt-1 text-xs text-slate-500">{{ plan.tagline }}</p>

            <p class="mt-5 flex items-end gap-1.5">
              <span class="text-xl font-bold text-slate-400">¥</span>
              <span
                class="text-4xl font-bold leading-none tracking-tight"
                :class="plan.featured ? 'text-orange-700' : 'text-slate-900'"
              >
                {{ plan.price }}
              </span>
              <span class="text-xs font-medium text-slate-500">{{ plan.unit }}</span>
            </p>

            <ul class="mt-5 flex-1 space-y-2.5">
              <li v-for="p in plan.perks" :key="p" class="flex items-start gap-2 text-sm text-slate-600">
                <svg
                  class="mt-0.5 h-4 w-4 shrink-0"
                  :class="plan.featured ? 'text-orange-700' : 'text-blue-600'"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <path d="M20 6 9 17l-5-5" />
                </svg>
                {{ p }}
              </li>
            </ul>

            <button
              type="button"
              class="mt-6 w-full"
              :class="plan.featured ? 'btn-vip !py-3.5 !text-base' : 'btn-primary !py-3.5 !text-base'"
              @click="choosePlan(plan)"
            >
              立即开通 {{ plan.name }}
            </button>
          </div>
        </div>

        <p class="mt-6 text-center text-xs text-slate-400">
          当前为内测演示界面，尚未接入真实支付；点击开通只会展示提示，不会产生任何扣费。
        </p>
      </div>
    </section>

    <!-- 免费 vs Pro -->
    <section class="mx-auto max-w-4xl px-4 py-14 sm:px-6">
      <div class="text-center">
        <h2 class="text-2xl font-bold tracking-tight text-slate-900">免费版 vs Pro 会员</h2>
        <p class="mt-2 text-sm text-slate-500">免费版本就足够好用，Pro 只是让高频使用更省时间</p>
      </div>

      <div class="mt-8 overflow-hidden rounded-2xl ring-1 ring-slate-200/70">
        <table class="w-full border-separate border-spacing-0 text-sm">
          <caption class="sr-only">免费版与 Pro 会员权益对比</caption>
          <thead>
            <tr>
              <th scope="col" class="bg-slate-50 px-4 py-3 text-left text-xs font-semibold text-slate-500">权益</th>
              <th scope="col" class="bg-slate-50 px-4 py-3 text-center text-xs font-semibold text-slate-500">免费版</th>
              <th scope="col" class="bg-orange-700 px-4 py-3 text-center text-xs font-bold text-white">Pro 会员</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in matrix" :key="row.item">
              <th scope="row" class="border-b border-slate-100 px-4 py-3 text-left text-sm font-medium text-slate-700" :class="i % 2 ? 'bg-white' : 'bg-slate-50/50'">
                {{ row.item }}
              </th>
              <td class="border-b border-slate-100 px-4 py-3 text-center text-sm text-slate-500" :class="i % 2 ? 'bg-white' : 'bg-slate-50/50'">
                {{ row.free }}
              </td>
              <td class="border-b border-orange-100 bg-orange-50/60 px-4 py-3 text-center text-sm font-semibold text-orange-800">
                {{ row.pro }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 信任保障 -->
    <section class="border-y border-slate-100 bg-slate-50/70">
      <div class="mx-auto max-w-6xl px-4 py-12 sm:px-6">
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div v-for="t in trust" :key="t.title" class="flex gap-3">
            <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white text-orange-700 ring-1 ring-orange-100">
              <svg class="h-4.5 w-4.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path :d="t.icon" />
              </svg>
            </span>
            <div>
              <p class="text-sm font-bold text-slate-900">{{ t.title }}</p>
              <p class="mt-0.5 text-xs leading-relaxed text-slate-500">{{ t.desc }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- FAQ -->
    <section class="mx-auto max-w-3xl px-4 py-14 sm:px-6">
      <h2 class="text-center text-2xl font-bold tracking-tight text-slate-900">开通前常见问题</h2>
      <div class="mt-7 space-y-3">
        <details v-for="f in faqs" :key="f.q" class="card group px-5 py-4">
          <summary class="flex cursor-pointer list-none items-center justify-between gap-4 text-sm font-semibold text-slate-900">
            {{ f.q }}
            <svg class="h-4 w-4 shrink-0 text-slate-400 transition-transform duration-300 group-open:rotate-45" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
              <path d="M12 5v14M5 12h14" />
            </svg>
          </summary>
          <p class="mt-3 text-sm leading-relaxed text-slate-500">{{ f.a }}</p>
        </details>
      </div>
    </section>

    <!-- 结尾 CTA -->
    <section class="mx-auto max-w-4xl px-4 pb-16 sm:px-6">
      <div
        class="rounded-3xl px-6 py-10 text-center ring-1 ring-orange-200"
        style="background-image: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%)"
      >
        <h2 class="text-2xl font-bold tracking-tight text-slate-900">先免费用，觉得值再开会员</h2>
        <p class="mx-auto mt-3 max-w-xl text-sm text-slate-600">
          内测期间所有 Pro 能力都已免费开放。先用起来，觉得顺手了再考虑支持我们。
        </p>
        <button type="button" class="btn-primary mt-6 w-full !py-3.5 sm:w-auto" @click="emit('go-download')">
          回主页解析一个链接
        </button>
      </div>
    </section>

    <!-- 内测提示弹窗 -->
    <Teleport to="body">
      <div v-if="activePlan" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="animate-fade-in absolute inset-0 bg-slate-900/45 backdrop-blur-[2px]" @click="closeDialog"></div>

        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="vip-dialog-title"
          class="animate-fade-up relative w-full max-w-sm rounded-2xl bg-white p-6 text-center shadow-2xl"
        >
          <span class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-orange-50 text-orange-700 ring-1 ring-orange-100">
            <svg class="h-6 w-6" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M3 7.5 7 11l5-7 5 7 4-3.5-2 11H5l-2-11ZM5 20h14v1.5H5z" />
            </svg>
          </span>
          <h2 id="vip-dialog-title" class="mt-4 text-lg font-bold text-slate-900">
            {{ activePlan.name }} · 内测中
          </h2>
          <p class="mt-2 text-sm leading-relaxed text-slate-500">
            支付通道正在接入，暂时还无法完成付款。内测期间所有会员能力已免费开放，你现在就能直接使用。
          </p>
          <div class="mt-5 flex gap-2.5">
            <button
              type="button"
              class="flex-1 rounded-xl px-4 py-3 text-sm font-semibold text-slate-600 ring-1 ring-slate-200 transition-colors hover:bg-slate-50"
              @click="closeDialog"
            >
              知道了
            </button>
            <button
              type="button"
              class="btn-primary flex-1 !py-3 !text-sm"
              @click="closeDialog(); emit('go-download')"
            >
              先去免费用
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
