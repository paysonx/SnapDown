<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import SiteHeader from './components/SiteHeader.vue'
import HeroSection from './components/HeroSection.vue'
import ResultCard from './components/ResultCard.vue'
import HistoryDrawer from './components/HistoryDrawer.vue'
import SiteFooter from './components/SiteFooter.vue'
import WhyPage from './pages/WhyPage.vue'
import VipPage from './pages/VipPage.vue'
import { ROUTES, navigate, route } from './router.js'
import { hasFinePointer, scrollToTop } from './scroll.js'
import { parseVideo, startDownload, getTask, listTasks } from './api.js'

const url = ref('')
const error = ref('')
const loading = ref(false)
const info = ref(null)
const task = ref(null)
const taskList = ref([])
const selectedFormat = ref('best')
const downloadMode = ref('video')
const historyOpen = ref(false)

let pollTimer = null

const view = computed(() => {
  if (route.value === ROUTES.why) return 'why'
  if (route.value === ROUTES.vip) return 'vip'
  return 'home'
})

onMounted(() => {
  refreshHistory()
})

onUnmounted(() => {
  stopPolling()
})

const KNOWN_ROUTES = Object.values(ROUTES)

watch(
  route,
  (current) => {
    historyOpen.value = false
    // 未匹配的 hash（如历史遗留的 #features / #plans）统一回主页并清理地址栏，
    // 避免"路由落空仍渲染主页"这种看起来像跳错页的行为
    if (!KNOWN_ROUTES.includes(current)) {
      navigate(ROUTES.home)
      return
    }
    window.scrollTo({ top: 0, behavior: 'auto' })
  },
  { immediate: true },
)

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function refreshHistory() {
  try {
    taskList.value = await listTasks()
  } catch {
    /* 历史列表加载失败不影响主流程 */
  }
}

function openHistory() {
  refreshHistory()
  historyOpen.value = true
}

/** 从介绍页/VIP 页回到主页并聚焦输入框 */
function goDownload() {
  navigate(ROUTES.home)
  setTimeout(() => document.getElementById('video-url')?.focus(), 80)
}

async function handleSubmit() {
  const link = url.value.trim()
  if (!link) {
    error.value = '请先粘贴视频链接'
    return
  }
  if (!/^https?:\/\//i.test(link)) {
    error.value = '链接格式不正确，请粘贴以 http(s):// 开头的完整链接'
    return
  }

  error.value = ''
  loading.value = true
  try {
    info.value = await parseVideo(link)
    task.value = null
    selectedFormat.value = 'best'
    downloadMode.value = 'video'
  } catch (e) {
    error.value = e.message || '解析失败，请检查链接或稍后重试'
    info.value = null
  } finally {
    loading.value = false
  }
}

async function handleDownload() {
  if (!info.value) return
  error.value = ''
  try {
    task.value = await startDownload(url.value.trim(), selectedFormat.value, {
      title: info.value.title,
      thumbnail: info.value.thumbnail,
      mode: downloadMode.value,
    })
    startPolling()
    refreshHistory()
  } catch (e) {
    error.value = e.message || '创建下载任务失败'
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    if (!task.value) return
    try {
      task.value = await getTask(task.value.id)
      if (['done', 'error'].includes(task.value.status)) {
        stopPolling()
        refreshHistory()
      }
    } catch {
      /* 轮询失败静默重试 */
    }
  }, 1000)
}

/** 「再来一个」：彻底回到刚进入主页时的初始状态
 *  —— 清空链接与结果、收起卡片、回到顶部、桌面端自动聚焦输入框（手机端不聚焦，避免误弹键盘） */
function handleReset() {
  stopPolling()
  info.value = null
  task.value = null
  url.value = ''
  error.value = ''
  selectedFormat.value = 'best'
  downloadMode.value = 'video'
  scrollToTop()
  if (hasFinePointer()) {
    document.getElementById('video-url')?.focus({ preventScroll: true })
  }
  refreshHistory()
}
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <SiteHeader :history-count="taskList.length" @open-history="openHistory" />

    <main class="flex flex-1 flex-col">
      <template v-if="view === 'home'">
        <!-- 主页内容垂直居中，一屏望尽 -->
        <div class="flex flex-1 flex-col justify-center">
          <HeroSection
            v-model:url="url"
            :loading="loading"
            :error="error"
            :show-platforms="!info"
            @submit="handleSubmit"
          />

          <ResultCard
            v-if="info"
            :info="info"
            :task="task"
            :selected-format="selectedFormat"
            :mode="downloadMode"
            @select-format="(f) => (selectedFormat = f)"
            @select-mode="(m) => (downloadMode = m)"
            @download="handleDownload"
            @reset="handleReset"
          />
        </div>
      </template>

      <WhyPage v-else-if="view === 'why'" @go-download="goDownload" />

      <VipPage v-else @go-download="goDownload" />
    </main>

    <SiteFooter />

    <HistoryDrawer :open="historyOpen" :tasks="taskList" @close="historyOpen = false" />
  </div>
</template>
