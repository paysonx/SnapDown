<script setup>
import { ref } from 'vue'

defineProps({
  url: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  /** 解析出结果后收起平台标签，保证主页一屏可见 */
  showPlatforms: { type: Boolean, default: true },
})

const emit = defineEmits(['update:url', 'submit'])

const platforms = ['B站', '抖音', '快手', '小红书', 'YouTube', '微博', 'Twitter', 'Instagram', 'TikTok', '西瓜视频']

const pasted = ref(false)
const pasteHint = ref('')

function showPasteHint(message) {
  pasteHint.value = message
  setTimeout(() => (pasteHint.value = ''), 4000)
}

/**
 * 一键粘贴剪贴板链接。
 * 只走现代 Clipboard API（navigator.clipboard.readText）：
 * - Chrome/Edge：首次会弹一次浏览器"读取剪贴板"授权（点一次"允许"后永久生效，之后一点即粘贴）；
 * - Firefox：每次都会弹确认（浏览器的安全机制，网页无法绕过）；
 * - 不支持 / 被拒绝 / 剪贴板为空：聚焦输入框并提示手动粘贴。
 * 注意：**不要**回退到 document.execCommand('paste')——Chromium 会对它弹出
 * "粘贴(P)" 原生确认气泡（用户必须再点一次），Firefox 也会多弹一次确认，适得其反。
 */
function pasteFromClipboard() {
  const input = document.getElementById('video-url')

  if (!navigator.clipboard?.readText) {
    input?.focus()
    showPasteHint('当前浏览器不支持自动读取剪贴板，请按 Ctrl+V 粘贴')
    return
  }

  navigator.clipboard
    .readText()
    .then((text) => {
      if (text) {
        applyPaste(text)
      } else {
        input?.focus()
        showPasteHint('剪贴板是空的，请先复制视频链接')
      }
    })
    .catch(() => {
      input?.focus()
      showPasteHint('未能读取剪贴板（浏览器未授权），请在输入框按 Ctrl+V 粘贴')
    })
}

/** 把剪贴板文本写入输入框并给出"已粘贴"反馈 */
function applyPaste(text) {
  const clean = String(text || '').trim()
  if (!clean) return
  pasteHint.value = ''
  emit('update:url', clean)
  pasted.value = true
  setTimeout(() => (pasted.value = false), 1600)
}

function onSubmit() {
  emit('submit')
}
</script>

<template>
  <section id="downloader" class="relative overflow-hidden">
    <div class="relative mx-auto max-w-3xl px-4 pb-8 pt-10 text-center sm:px-6 sm:pb-10 sm:pt-14">
      <span
        class="animate-fade-up inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3.5 py-1.5 text-xs font-semibold text-blue-700 ring-1 ring-blue-100"
      >
        <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path d="M13 2 4.5 13.5H11L9.5 22 19 10h-6.5L13 2Z" />
        </svg>
        已支持 1000+ 平台 · 电脑手机都能用
      </span>

      <h1
        class="animate-fade-up mt-4 text-3xl font-bold leading-tight tracking-tight text-slate-900 sm:text-[2.75rem]"
        style="animation-delay: 60ms"
      >
        <span class="bg-gradient-to-r from-blue-600 to-indigo-500 bg-clip-text text-transparent"
          >万能视频</span
        >即刻下载
      </h1>
      <p class="animate-fade-up mx-auto mt-3 max-w-xl text-[15px] text-slate-500 sm:text-base" style="animation-delay: 120ms">
        智能解析，高清画质自由选择，实时进度一目了然，随时随地离线观看
      </p>

      <form class="animate-fade-up mt-7" style="animation-delay: 180ms" @submit.prevent="onSubmit">
        <label for="video-url" class="sr-only">视频链接</label>
        <div
          class="flex flex-col gap-3 rounded-2xl bg-white p-2 ring-1 ring-slate-200 transition-shadow duration-300 focus-within:shadow-xl focus-within:shadow-blue-600/10 focus-within:ring-blue-600/50 sm:flex-row sm:items-center sm:rounded-full"
        >
          <div class="relative flex flex-1 items-center">
            <svg
              class="pointer-events-none absolute left-4 h-5 w-5 text-slate-400"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              aria-hidden="true"
            >
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            </svg>
            <input
              id="video-url"
              :value="url"
              type="url"
              inputmode="url"
              autocomplete="off"
              spellcheck="false"
              placeholder="粘贴视频链接，如 https://www.bilibili.com/video/..."
              class="h-13 w-full rounded-xl bg-transparent pl-12 pr-24 text-[15px] text-slate-900 outline-none placeholder:text-slate-400 sm:rounded-full"
              @input="emit('update:url', $event.target.value)"
              @keydown.enter="onSubmit"
            />
            <button
              v-if="url"
              type="button"
              class="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
              aria-label="清空输入"
              @click="emit('update:url', '')"
            >
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="flex items-center gap-2">
            <button
              type="button"
              class="inline-flex h-11 shrink-0 items-center gap-1.5 rounded-full px-4 text-sm font-medium text-blue-600 transition-colors hover:bg-blue-50"
              :class="{ 'bg-emerald-50 !text-emerald-600': pasted }"
              @click="pasteFromClipboard"
            >
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <rect x="8" y="2" width="8" height="4" rx="1" />
                <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
              </svg>
              {{ pasted ? '已粘贴' : '粘贴' }}
            </button>
            <button type="submit" class="btn-primary !rounded-full !py-3 sm:w-auto" :disabled="loading || !url.trim()">
              <svg
                v-if="loading"
                class="h-5 w-5 animate-spin"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden="true"
              >
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-90" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4Z" />
              </svg>
              <svg v-else class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <circle cx="11" cy="11" r="7" />
                <path d="m20 20-3.5-3.5" />
              </svg>
              {{ loading ? '解析中…' : '开始解析' }}
            </button>
          </div>
        </div>

        <p v-if="error" role="alert" class="animate-fade-in mt-3 flex items-center justify-center gap-1.5 text-sm font-medium text-red-600">
          <svg class="h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 8v4M12 16h.01" />
          </svg>
          {{ error }}
        </p>
        <p v-else-if="pasteHint" role="status" class="animate-fade-in mt-3 text-sm font-medium text-amber-600">
          {{ pasteHint }}
        </p>
      </form>

      <div
        v-if="showPlatforms"
        class="animate-fade-in mt-6 flex flex-wrap items-center justify-center gap-x-1 gap-y-2"
        style="animation-delay: 260ms"
      >
        <span class="text-xs text-slate-400">支持平台：</span>
        <span v-for="p in platforms" :key="p" class="chip">#{{ p }}</span>
      </div>
    </div>
  </section>
</template>
