<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import TaskList from './TaskList.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  tasks: { type: Array, default: () => [] },
})

const emit = defineEmits(['close'])

const panel = ref(null)

const doneCount = computed(() => props.tasks.filter((t) => t.status === 'done').length)

function onKeydown(e) {
  if (e.key === 'Escape' && props.open) emit('close')
}

if (typeof window !== 'undefined') {
  window.addEventListener('keydown', onKeydown)
}

watch(
  () => props.open,
  (open) => {
    document.body.style.overflow = open ? 'hidden' : ''
    if (open) panel.value?.focus()
  },
)

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-50" role="presentation">
      <div
        class="animate-fade-in absolute inset-0 bg-slate-900/35 backdrop-blur-[2px]"
        @click="emit('close')"
      ></div>

      <aside
        ref="panel"
        tabindex="-1"
        role="dialog"
        aria-modal="true"
        aria-label="下载记录"
        class="absolute right-0 top-0 flex h-full w-full max-w-lg flex-col bg-slate-50 shadow-2xl outline-none"
      >
        <header class="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3.5">
          <div>
            <h2 class="text-base font-bold text-slate-900">下载记录</h2>
            <p class="text-xs text-slate-400">
              记录保存在当前服务中，重启后自动清空<span v-if="doneCount"> · 已完成 {{ doneCount }} 个</span>
            </p>
          </div>
          <button
            type="button"
            class="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
            aria-label="关闭下载记录"
            @click="emit('close')"
          >
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </header>

        <div class="flex-1 overflow-y-auto px-4 py-4">
          <TaskList :tasks="tasks" />
        </div>
      </aside>
    </div>
  </Teleport>
</template>
