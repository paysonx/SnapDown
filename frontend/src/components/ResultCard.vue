<script setup>
import { computed } from 'vue'
import { fileUrl } from '../api.js'

const props = defineProps({
  info: { type: Object, default: null },
  task: { type: Object, default: null },
  selectedFormat: { type: String, default: 'best' },
  mode: { type: String, default: 'video' },
})

const emit = defineEmits(['select-format', 'select-mode', 'download', 'reset'])

const MODES = [
  { id: 'video', label: '视频', desc: '画面 + 声音' },
  { id: 'audio', label: '仅音频', desc: '只提取声音' },
]

const PLATFORM_NAMES = {
  bilibili: 'B站',
  youtube: 'YouTube',
  douyin: '抖音',
  kuaishou: '快手',
  xiaohongshu: '小红书',
  weibo: '微博',
  twitter: 'Twitter',
  instagram: 'Instagram',
  tiktok: 'TikTok',
}

const platformName = computed(
  () => PLATFORM_NAMES[props.info?.extractor?.toLowerCase()] || props.info?.extractor || '视频',
)

const downloading = computed(() => props.task && ['pending', 'downloading'].includes(props.task.status))

/** 下载完成后收起清晰度选择：此时它已无对应下载动作，留着就是死控件 */
const isDone = computed(() => props.task?.status === 'done')

const bestFormat = { format_id: 'best', ext: '', height: 0, fps: 0, filesize: null, note: '' }

const allFormats = computed(() => [bestFormat, ...(props.info?.formats || [])])

const currentFormat = computed(
  () => allFormats.value.find((f) => f.format_id === props.selectedFormat) || bestFormat,
)

const needsMerge = computed(
  () =>
    props.selectedFormat !== 'best' &&
    (currentFormat.value.acodec === 'none' || !currentFormat.value.acodec),
)

function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes >= 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(0)} MB`
  return `${(bytes / 1024).toFixed(0)} KB`
}

function fmtLabel(f) {
  if (f.format_id === 'best') return '最佳画质'
  const parts = [f.height ? `${f.height}P` : f.note]
  if (f.fps && f.fps > 30) parts.push(`${Math.round(f.fps)}帧`)
  return parts.filter(Boolean).join(' · ')
}

function onSelect(f) {
  emit('select-format', f.format_id)
}

function onSelectMode(m) {
  emit('select-mode', m.id)
}
</script>

<template>
  <section
    class="animate-fade-up mx-auto mt-2 max-w-2xl px-4 sm:px-6"
    aria-live="polite"
  >
    <div class="card overflow-hidden">
      <!-- 视频信息 -->
      <div class="flex flex-col gap-4 p-5 sm:flex-row sm:gap-5 sm:p-6">
        <div class="relative shrink-0 overflow-hidden rounded-lg bg-slate-100 ring-1 ring-slate-200/50 sm:w-64">
          <img
            v-if="info.thumbnail"
            :src="info.thumbnail"
            :alt="`${info.title} 的封面`"
            class="aspect-video w-full object-cover sm:h-full"
            loading="lazy"
            referrerpolicy="no-referrer"
          />
          <div v-else class="flex aspect-video items-center justify-center text-slate-300">
            <svg class="h-10 w-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
              <rect x="2" y="4" width="20" height="16" rx="3" />
              <path d="m10 9 5 3-5 3V9Z" fill="currentColor" stroke="none" />
            </svg>
          </div>
          <span
            v-if="info.duration"
            class="absolute bottom-2 right-2 rounded-md bg-black/70 px-1.5 py-0.5 text-xs font-medium text-white"
          >
            {{ info.duration }}
          </span>
        </div>

        <div class="min-w-0 flex-1">
          <span
            class="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700 ring-1 ring-blue-100"
          >
            {{ platformName }}
          </span>
          <h2 class="mt-2 line-clamp-2 text-lg font-bold leading-snug text-slate-900">
            {{ info.title }}
          </h2>
          <p class="mt-1.5 flex items-center gap-1.5 text-sm text-slate-500">
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            {{ info.uploader || '未知作者' }}
            <span class="text-slate-300">·</span>
            <span>{{ info.duration ? `时长 ${info.duration}` : '时长未知' }}</span>
          </p>
          <p v-if="info.subtitles?.length" class="mt-2 flex items-center gap-1.5 text-xs text-slate-400">
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
              <rect x="2" y="4" width="20" height="16" rx="2" />
              <path d="M6 12h4M6 16h8M14 12h4" />
            </svg>
            含 {{ info.subtitles.length }} 种语言字幕
          </p>
        </div>
      </div>

      <!-- 下载内容与清晰度选择：下载完成后收起，避免出现"选了也没用"的死控件 -->
      <div v-if="!isDone" class="border-t border-slate-100 p-5 sm:p-6">
        <label class="mb-3 block text-sm font-semibold text-slate-900" id="mode-label">
          下载内容
        </label>
        <div
          class="flex flex-wrap gap-2.5"
          role="radiogroup"
          aria-labelledby="mode-label"
        >
          <button
            v-for="m in MODES"
            :key="m.id"
            type="button"
            role="radio"
            :aria-checked="mode === m.id"
            :disabled="downloading"
            class="flex min-h-11 min-w-0 flex-1 basis-[45%] flex-col items-start justify-center rounded-xl px-3.5 py-2 text-left ring-1 transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-60 sm:basis-[45%]"
            :class="
              mode === m.id
                ? 'bg-blue-600 text-white ring-blue-600 shadow-lg shadow-blue-600/25'
                : 'bg-white text-slate-700 ring-slate-200 hover:ring-blue-400 hover:text-blue-700'
            "
            @click="onSelectMode(m)"
          >
            <span class="text-sm font-semibold">{{ m.label }}</span>
            <span
              class="text-xs"
              :class="mode === m.id ? 'text-blue-100' : 'text-slate-400'"
            >
              {{ m.desc }}
            </span>
          </button>
        </div>

        <template v-if="mode === 'video'">
          <label class="mb-3 mt-5 block text-sm font-semibold text-slate-900" id="format-label">
            选择清晰度
          </label>
          <div
            class="flex flex-wrap gap-2.5"
            role="radiogroup"
            aria-labelledby="format-label"
          >
            <button
              v-for="f in allFormats"
              :key="f.format_id"
              type="button"
              role="radio"
              :aria-checked="selectedFormat === f.format_id"
              :disabled="downloading"
              class="flex min-h-11 min-w-0 flex-1 basis-[45%] flex-col items-start justify-center rounded-xl px-3.5 py-2 text-left ring-1 transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-60 sm:basis-[30%]"
              :class="
                selectedFormat === f.format_id
                  ? 'bg-blue-600 text-white ring-blue-600 shadow-lg shadow-blue-600/25'
                  : 'bg-white text-slate-700 ring-slate-200 hover:ring-blue-400 hover:text-blue-700'
              "
              @click="onSelect(f)"
            >
              <span class="text-sm font-semibold">{{ fmtLabel(f) }}</span>
              <span
                class="text-xs"
                :class="selectedFormat === f.format_id ? 'text-blue-100' : 'text-slate-400'"
              >
                {{ f.format_id === 'best' ? '自动匹配最高质量' : `${f.ext || '视频'}${formatSize(f.filesize) ? ' · ' + formatSize(f.filesize) : ''}` }}
              </span>
            </button>
          </div>
          <p v-if="needsMerge" class="mt-3 flex items-center gap-1.5 text-xs text-slate-400">
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 16v-4M12 8h.01" />
            </svg>
            该清晰度为独立视频流，下载后将自动合并最佳音轨并输出 MP4
          </p>
        </template>
        <p v-else class="mt-3 flex items-center gap-1.5 text-xs text-slate-400">
          <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
            <path d="M9 18V5l12-2v13" />
            <circle cx="6" cy="18" r="3" />
            <circle cx="18" cy="16" r="3" />
          </svg>
          只提取声音、不下载画面，输出 MP3 音频文件
        </p>
      </div>

      <!-- 下载区 -->
      <div
        class="border-t border-slate-100 p-5 sm:p-6"
        :class="isDone ? 'bg-emerald-50/40' : 'bg-slate-50/60'"
      >
        <!-- 下载中 -->
        <div v-if="downloading" class="space-y-3.5">
          <div class="flex items-center justify-between text-sm">
            <span class="flex items-center gap-2 font-semibold text-slate-900">
              <svg class="h-4.5 w-4.5 animate-spin text-blue-600" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-90" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4Z" />
              </svg>
              正在下载…
            </span>
            <span class="font-bold tabular-nums text-blue-600">{{ task.percent || 0 }}%</span>
          </div>
          <div class="progress-track" role="progressbar" :aria-valuenow="task.percent || 0" aria-valuemin="0" aria-valuemax="100" aria-label="下载进度">
            <div class="progress-fill progress-stripes" :style="{ width: `${task.percent || 0}%` }"></div>
          </div>
          <div class="flex items-center justify-between text-xs text-slate-500">
            <span v-if="task.speed">{{ task.speed }}</span>
            <span v-else>准备中…</span>
            <span v-if="task.eta">剩余 {{ task.eta }}</span>
          </div>
        </div>

        <!-- 下载完成：清爽成功卡片（分辨率 / 体积 / 时长标签 + 保存 / 再来一个） -->
        <div v-else-if="isDone" class="space-y-4">
          <div class="flex items-start gap-3">
            <span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
              <svg class="h-5.5 w-5.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M20 6 9 17l-5-5" />
              </svg>
            </span>
            <div class="min-w-0 flex-1">
              <p class="text-base font-bold text-slate-900">下载完成</p>
              <p class="mt-0.5 truncate text-xs text-slate-500" :title="task.filename">
                {{ task.filename }}
              </p>
              <div class="mt-2.5 flex flex-wrap items-center gap-1.5">
                <span
                  v-if="task.mode === 'audio'"
                  class="inline-flex items-center rounded-md bg-violet-50 px-2 py-0.5 text-[11px] font-semibold text-violet-700 ring-1 ring-violet-100"
                >
                  音频 MP3
                </span>
                <span
                  v-else-if="task.height"
                  class="inline-flex items-center rounded-md bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-blue-700 ring-1 ring-blue-100"
                >
                  {{ task.height }}P
                </span>
                <span
                  v-if="task.filesize"
                  class="inline-flex items-center rounded-md bg-white px-2 py-0.5 text-[11px] font-medium text-slate-600 ring-1 ring-slate-200"
                >
                  {{ formatSize(task.filesize) }}
                </span>
                <span
                  v-if="info.duration"
                  class="inline-flex items-center rounded-md bg-white px-2 py-0.5 text-[11px] font-medium text-slate-600 ring-1 ring-slate-200"
                >
                  时长 {{ info.duration }}
                </span>
              </div>
            </div>
          </div>

          <div class="flex flex-col gap-2.5 sm:flex-row">
            <a :href="fileUrl(task.id)" download class="btn-primary flex-1 !py-3">
              <svg class="h-4.5 w-4.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <path d="m7 10 5 5 5-5" />
                <path d="M12 15V3" />
              </svg>
              保存到本地
            </a>
            <button
              type="button"
              class="inline-flex h-12 shrink-0 items-center justify-center rounded-xl px-5 text-sm font-semibold text-slate-600 ring-1 ring-slate-200 transition-colors hover:bg-white hover:text-blue-600 hover:ring-blue-300"
              @click="emit('reset')"
            >
              再来一个
            </button>
          </div>
        </div>

        <!-- 下载失败 -->
        <div v-else-if="task?.status === 'error'" class="space-y-3">
          <p role="alert" class="flex items-start gap-2 text-sm font-medium text-red-600">
            <svg class="mt-0.5 h-4.5 w-4.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 8v4M12 16h.01" />
            </svg>
            <span>下载失败：{{ task.error }}</span>
          </p>
          <button type="button" class="btn-primary !py-2.5 !text-sm" @click="emit('download')">
            重试下载
          </button>
        </div>

        <!-- 初始状态：下载按钮 -->
        <button v-else type="button" class="btn-primary w-full" @click="emit('download')">
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M12 3v12" />
            <path d="m7 10 5 5 5-5" />
            <path d="M4 21h16" />
          </svg>
          {{ mode === 'audio' ? '下载 MP3 音频' : `下载 ${fmtLabel(currentFormat)}` }}
        </button>
      </div>
    </div>
  </section>
</template>
