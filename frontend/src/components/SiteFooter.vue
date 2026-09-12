<script setup>
import { computed } from 'vue'
import { ROUTES, navigate } from '../router.js'

/** 版权年份：每次页面加载按系统时间计算，跨年后自动更新，无需改代码 */
const year = computed(() => new Date().getFullYear())
</script>

<template>
  <footer class="border-t border-slate-100">
    <div class="mx-auto flex max-w-6xl flex-col items-center gap-2.5 px-4 py-6 text-center sm:px-6">
      <div class="flex flex-wrap items-center justify-center gap-x-3 gap-y-1.5">
        <span class="flex items-center gap-1.5 text-sm font-bold text-slate-900">
          <span
            class="flex h-6 w-6 items-center justify-center rounded-md text-white"
            style="background-image: linear-gradient(135deg, #2563eb 0%, #6366f1 100%)"
          >
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M13 2 4.5 13.5H11L9.5 22 19 10h-6.5L13 2Z" />
            </svg>
          </span>
          SnapDown
        </span>

        <span
          class="inline-flex items-center gap-1.5 rounded-full bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600 ring-1 ring-slate-200/70"
        >
          <svg class="h-3.5 w-3.5 text-blue-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M12 3v18M5 8.5 12 3l7 5.5" />
          </svg>
          由 <span class="font-bold text-slate-900">Payson</span> 独立设计与开发
        </span>
      </div>

      <p class="max-w-xl text-xs leading-relaxed text-slate-400">
        本站仅供个人学习与备份使用，请尊重原作者版权，下载内容请勿用于商业用途或二次传播。
      </p>

      <div class="flex flex-wrap items-center justify-center gap-x-2.5 gap-y-1 text-xs text-slate-400">
        <span>© {{ year }} SnapDown</span>
        <span class="text-slate-300" aria-hidden="true">·</span>
        <a href="#/why" class="transition-colors hover:text-blue-600" @click.prevent="navigate(ROUTES.why)">
          为什么选 SnapDown
        </a>
        <span class="text-slate-300" aria-hidden="true">·</span>
        <a href="#/vip" class="font-medium text-orange-700 transition-colors hover:text-orange-800" @click.prevent="navigate(ROUTES.vip)">
          开通 VIP
        </a>
      </div>
    </div>
  </footer>
</template>
