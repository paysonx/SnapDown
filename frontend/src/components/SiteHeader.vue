<script setup>
import { ROUTES, navigate } from '../router.js'

defineProps({
  historyCount: { type: Number, default: 0 },
})

const emit = defineEmits(['open-history'])
</script>

<template>
  <header class="sticky top-0 z-40 border-b border-slate-100 bg-white/85 backdrop-blur-md">
    <div class="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
      <a
        href="#/"
        class="flex items-center gap-2.5"
        aria-label="SnapDown 首页"
        @click.prevent="navigate(ROUTES.home)"
      >
        <span
          class="flex h-9 w-9 items-center justify-center rounded-lg text-white shadow-md shadow-blue-600/30"
          style="background-image: linear-gradient(135deg, #2563eb 0%, #6366f1 100%)"
        >
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M13 2 4.5 13.5H11L9.5 22 19 10h-6.5L13 2Z" />
          </svg>
        </span>
        <span class="text-lg font-bold tracking-tight text-slate-900">SnapDown</span>
      </a>

      <nav class="flex items-center gap-1.5 sm:gap-4" aria-label="主导航">
        <a
          href="#/why"
          class="hidden rounded-lg px-2 py-2 text-sm font-medium text-slate-600 transition-colors hover:text-blue-600 sm:inline"
          @click.prevent="navigate(ROUTES.why)"
        >
          为什么选 SnapDown
        </a>

        <button
          type="button"
          class="relative inline-flex items-center gap-1.5 rounded-lg px-2 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-blue-600"
          aria-label="打开下载记录"
          @click="emit('open-history')"
        >
          <svg class="h-4.5 w-4.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 7v5l3.5 2" />
          </svg>
          <span class="hidden sm:inline">下载记录</span>
          <span
            v-if="historyCount"
            class="ml-0.5 inline-flex min-w-5 items-center justify-center rounded-full bg-blue-600 px-1.5 text-[11px] font-semibold leading-5 text-white"
          >
            {{ historyCount > 99 ? '99+' : historyCount }}
          </span>
        </button>

        <button type="button" class="btn-vip !px-3.5 !py-2" @click="navigate(ROUTES.vip)">
          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M3 7.5 7 11l5-7 5 7 4-3.5-2 11H5l-2-11Z" />
            <path d="M5 20h14v1.5H5z" />
          </svg>
          开通VIP
        </button>
      </nav>
    </div>
  </header>
</template>
