<script setup>
import { ref } from 'vue'
import { fileUrl } from '../api.js'

defineProps({
  tasks: { type: Array, default: () => [] },
})

/** 封面加载失败的记录，回退为占位图标 */
const brokenThumbs = ref(new Set())

function onThumbError(taskId) {
  brokenThumbs.value.add(taskId)
}

const STATUS = {
  pending: { label: '排队中', cls: 'bg-slate-100 text-slate-500' },
  downloading: { label: '下载中', cls: 'bg-blue-50 text-blue-600' },
  done: { label: '已完成', cls: 'bg-emerald-50 text-emerald-600' },
  error: { label: '失败', cls: 'bg-red-50 text-red-600' },
}

function statusOf(task) {
  return STATUS[task.status] || STATUS.pending
}

/** 文件体积：自动切换 KB / MB / GB */
function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes >= 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024).toFixed(0)} KB`
}

/** 下载时间（精确到分钟）：YYYY-MM-DD HH:mm；完成取 finished_at，否则取创建时间 */
function formatDateTime(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
</script>

<template>
  <div>
    <p
      v-if="!tasks.length"
      class="rounded-xl bg-white py-12 text-center text-sm text-slate-400 ring-1 ring-slate-100"
    >
      还没有下载记录，去主页粘贴一个视频链接试试吧
    </p>

    <div v-else class="grid grid-cols-1 gap-3">
      <a
        v-for="task in tasks.slice(0, 24)"
        :key="task.id"
        :href="task.status === 'done' ? fileUrl(task.id) : undefined"
        :download="task.status === 'done' ? true : undefined"
        class="card card-hover group flex gap-3 p-3"
        :class="task.status === 'done' ? 'cursor-pointer' : 'cursor-default'"
        :aria-label="`任务：${task.title || task.url}，${statusOf(task).label}`"
      >
        <div class="relative h-14 w-24 shrink-0 overflow-hidden rounded-lg bg-slate-100 ring-1 ring-slate-200/50">
          <img
            v-if="task.thumbnail && !brokenThumbs.has(task.id)"
            :src="task.thumbnail"
            alt=""
            class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
            loading="lazy"
            referrerpolicy="no-referrer"
            @error="onThumbError(task.id)"
          />
          <div v-else class="flex h-full w-full items-center justify-center text-slate-300">
            <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
              <rect x="2" y="4" width="20" height="16" rx="3" />
              <path d="m10 9 5 3-5 3V9Z" fill="currentColor" stroke="none" />
            </svg>
          </div>
          <div v-if="task.status === 'downloading'" class="absolute inset-x-0 bottom-0 h-1 bg-white/60" aria-hidden="true">
            <div class="progress-fill h-full" :style="{ width: `${task.percent || 0}%` }"></div>
          </div>
        </div>

        <div class="flex min-w-0 flex-1 flex-col justify-between py-0.5">
          <div class="min-w-0">
            <span class="inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold" :class="statusOf(task).cls">
              {{ statusOf(task).label }}
              <template v-if="task.status === 'downloading'"> {{ task.percent || 0 }}%</template>
            </span>
            <p class="mt-1.5 line-clamp-2 text-[13px] font-semibold leading-snug text-slate-900 group-hover:text-blue-600">
              {{ task.title || task.url }}
            </p>
          </div>
          <!-- 元信息标签：分辨率 · 视频体量 · 下载时间（精确到分钟） -->
          <div class="mt-2 flex flex-wrap items-center gap-1.5">
            <span
              v-if="task.mode === 'audio'"
              class="inline-flex items-center rounded-md bg-violet-50 px-1.5 py-0.5 text-[11px] font-semibold text-violet-700 ring-1 ring-violet-100"
            >
              音频
            </span>
            <span
              v-else-if="task.height"
              class="inline-flex items-center rounded-md bg-blue-50 px-1.5 py-0.5 text-[11px] font-semibold text-blue-700 ring-1 ring-blue-100"
            >
              {{ task.height }}P
            </span>
            <span
              v-if="task.filesize"
              class="inline-flex items-center rounded-md bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-600"
            >
              {{ formatSize(task.filesize) }}
            </span>
            <span
              class="inline-flex items-center gap-1 rounded-md bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-600"
            >
              <svg class="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 6v6l4 2" />
              </svg>
              {{ formatDateTime(task.finished_at || task.created_at) }}
            </span>
          </div>
        </div>
      </a>
    </div>
  </div>
</template>
