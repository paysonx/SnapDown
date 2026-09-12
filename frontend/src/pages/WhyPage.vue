<script setup>
import { ROUTES, navigate } from '../router.js'

const emit = defineEmits(['go-download'])

const stats = [
  { value: '1000+', label: '支持平台' },
  { value: '4K', label: '最高画质' },
  { value: '秒级', label: '解析速度' },
  { value: '0', label: '安装 · 登录' },
]

const visions = [
  {
    title: '让保存变简单',
    desc: '视频不应该因为「下载」这个动作变复杂。复制链接、粘进输入框，剩下的交给 SnapDown。',
    icon: 'M13 2 4.5 13.5H11L9.5 22 19 10h-6.5L13 2Z',
    tone: 'blue',
  },
  {
    title: '让画质不打折',
    desc: '你值得拿到原画，而不是被二次压缩的「高清」。最高支持 4K，音视频自动合并为可直接播放的 MP4。',
    icon: 'M4 5h16v14H4zM9 10l6 3-6 3z',
    tone: 'indigo',
  },
  {
    title: '让体验保持干净',
    desc: '没有弹窗、没有诱导安装、没有「先下载下载器」。打开网页，就是全部功能。',
    icon: 'M12 3 4 6.5v5c0 4.6 3.4 8.4 8 9.5 4.6-1.1 8-4.9 8-9.5v-5L12 3Z',
    tone: 'emerald',
  },
]

const features = [
  {
    title: '秒级解析',
    desc: '粘贴链接即返回标题、封面、时长、作者与全部可用画质，不用等转圈。',
    icon: 'M13 2 3 14h9l-1 8 10-12h-9l1-8Z',
    tone: 'blue',
  },
  {
    title: '画质自由选',
    desc: '从 360P 到 4K，逐条列出分辨率、帧率与文件体积，选你真正需要的那一档。',
    icon: 'M4 6h16v12H4zM8 10h3M8 14h8M14 10h2',
    tone: 'indigo',
  },
  {
    title: '音视频自动合并',
    desc: '遇到独立视频流时自动匹配最佳音轨，合并输出标准 MP4，打开就能播。',
    icon: 'M12 3 3 8l9 5 9-5-9-5ZM3 14l9 5 9-5',
    tone: 'violet',
  },
  {
    title: '字幕一并保留',
    desc: '识别视频自带的多语言字幕轨道，需要时连字幕一起收下，方便学习与归档。',
    icon: 'M3 5h18v14H3zM6 12h4M6 16h8M14 12h4',
    tone: 'amber',
  },
  {
    title: '手机同样好用',
    desc: '响应式界面适配手机浏览器，通勤路上、躺在沙发上都能保存想看的内容。',
    icon: 'M7 2h10v20H7zM11 19h2',
    tone: 'sky',
  },
  {
    title: '进度实时可见',
    desc: '下载百分比、速度与剩余时间实时刷新，心里有数，不用盯着猜。',
    icon: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18ZM12 7v5l4 2',
    tone: 'rose',
  },
]

const toneMap = {
  blue: 'bg-blue-50 text-blue-600 ring-blue-100',
  indigo: 'bg-indigo-50 text-indigo-600 ring-indigo-100',
  emerald: 'bg-emerald-50 text-emerald-600 ring-emerald-100',
  violet: 'bg-violet-50 text-violet-600 ring-violet-100',
  amber: 'bg-amber-50 text-amber-600 ring-amber-100',
  sky: 'bg-sky-50 text-sky-600 ring-sky-100',
  rose: 'bg-rose-50 text-rose-600 ring-rose-100',
}

const comparisons = [
  { item: '需要安装软件', sn: '不需要', desktop: '需要', online: '不需要' },
  { item: '广告 / 诱导下载', sn: '没有', desktop: '较常见', online: '较多' },
  { item: '登录注册', sn: '无需登录', desktop: '部分需要', online: '多数需要' },
  { item: '画质上限', sn: '4K 原画', desktop: '取决于软件', online: '常见 720P' },
  { item: '手机浏览器可用', sn: '完整支持', desktop: '一般不支持', online: '支持但常带水印' },
  { item: '速度限制', sn: '不限速', desktop: '视软件而定', online: '常有限速排队' },
  { item: '文件与隐私', sn: '任务在本机服务完成', desktop: '本地处理', online: '链接需上传服务器' },
]

const scenes = [
  {
    title: '学习资料备份',
    desc: '把公开课、讲座与教程存到本地，断网、出差、地铁里都能反复观看。',
    icon: 'M4 5h16v14H4zM8 3v4M16 3v4M8 13h8M8 16h5',
  },
  {
    title: '旅行离线观看',
    desc: '出发前把想看的存进手机，飞机上、信号差的地方也不消耗一点流量。',
    icon: 'M3 12h18M12 3a15 15 0 0 1 0 18 15 15 0 0 1 0-18ZM12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z',
  },
  {
    title: '创作者素材归档',
    desc: '保存自己发布过的作品与灵感参考，二次剪辑时随时取用，不怕原链接失效。',
    icon: 'M4 4h16v16H4zM4 9h16M9 4v16',
  },
]

const proBenefits = [
  { title: '4K / 8K 原画通道', desc: '解锁平台提供的最高码率原画，不再被压缩画质限制。' },
  { title: '批量解析下载', desc: '一次粘贴多条链接，队列自动排队执行，效率翻倍。' },
  { title: '极速优先队列', desc: '高峰期优先处理你的任务，解析更快、等待更短。' },
  { title: '纯净无广告体验', desc: '没有弹窗和跳转，界面里只有你和你要下载的视频。' },
]

const faqs = [
  {
    q: 'SnapDown 是免费的吗？',
    a: '基础解析与下载完全免费，无需注册。Pro 会员提供更快的优先通道与批量能力，内测期间全部功能对所有用户免费开放。',
  },
  {
    q: '需要登录或留下个人信息吗？',
    a: '不需要。打开网页粘贴链接即可开始解析，我们不要求邮箱、手机号或任何账号信息。',
  },
  {
    q: '我的链接和文件会被保存到哪里？',
    a: '解析与下载由本机服务完成，文件保存在本地 downloads 目录，任务记录只存在于当前运行的服务中，重启后自动清空。',
  },
  {
    q: '支持哪些平台？',
    a: '已适配 1000+ 视频平台，包括 B站、抖音、快手、小红书、微博、YouTube、TikTok、Instagram 等主流站点。',
  },
  {
    q: '下载的视频可以用于商业用途吗？',
    a: '不可以。本站仅供个人学习与备份使用，请尊重原作者版权，下载内容请勿用于商业用途或二次传播。',
  },
]
</script>

<template>
  <div class="animate-fade-in">
    <!-- Hero -->
    <section class="relative overflow-hidden border-b border-slate-100">
      <div class="relative mx-auto max-w-5xl px-4 py-14 text-center sm:px-6 sm:py-20">
        <span
          class="animate-fade-up inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3.5 py-1.5 text-xs font-semibold text-blue-700 ring-1 ring-blue-100"
        >
          <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M13 2 4.5 13.5H11L9.5 22 19 10h-6.5L13 2Z" />
          </svg>
          为什么选 SnapDown
        </span>

        <h1
          class="animate-fade-up mt-5 text-3xl font-bold leading-tight tracking-tight text-slate-900 sm:text-5xl"
          style="animation-delay: 60ms"
        >
          把想看的视频<br class="sm:hidden" />
          <span class="bg-gradient-to-r from-blue-600 to-indigo-500 bg-clip-text text-transparent">完整留在自己手里</span>
        </h1>

        <p
          class="animate-fade-up mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-slate-500 sm:text-base"
          style="animation-delay: 120ms"
        >
          不装软件、不看广告、不被会员墙打断。SnapDown 把「解析 → 选画质 → 保存」压缩成一次复制粘贴，
          让保存视频回到它本该有的样子：简单、干净、一次就好。
        </p>

        <div
          class="animate-fade-up mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row"
          style="animation-delay: 180ms"
        >
          <button type="button" class="btn-primary w-full sm:w-auto" @click="emit('go-download')">
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M12 3v12M7 10l5 5 5-5M4 21h16" />
            </svg>
            免费开始解析
          </button>
          <button type="button" class="btn-vip w-full !px-6 !py-3.5 !text-base sm:w-auto" @click="navigate(ROUTES.vip)">
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M3 7.5 7 11l5-7 5 7 4-3.5-2 11H5l-2-11Z" />
            </svg>
            查看会员权益
          </button>
        </div>

        <dl
          class="animate-fade-up mx-auto mt-12 grid max-w-3xl grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-4"
          style="animation-delay: 240ms"
        >
          <div v-for="s in stats" :key="s.label" class="text-center">
            <dt class="text-2xl font-bold text-blue-600 sm:text-3xl">{{ s.value }}</dt>
            <dd class="mt-1 text-xs font-medium text-slate-500">{{ s.label }}</dd>
          </div>
        </dl>
      </div>
    </section>

    <!-- 愿景 -->
    <section class="mx-auto max-w-6xl px-4 py-14 sm:px-6">
      <div class="text-center">
        <h2 class="text-2xl font-bold tracking-tight text-slate-900">我们的愿景</h2>
        <p class="mx-auto mt-2 max-w-2xl text-sm text-slate-500">
          我们相信：只要内容是公开可看的，用户就应该能用最少的步骤把它保存下来，带回自己的设备慢慢看。
        </p>
      </div>

      <div class="mt-9 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div v-for="v in visions" :key="v.title" class="card card-hover p-6">
          <span
            class="flex h-11 w-11 items-center justify-center rounded-xl ring-1"
            :class="toneMap[v.tone]"
          >
            <svg class="h-5.5 w-5.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path :d="v.icon" />
            </svg>
          </span>
          <h3 class="mt-4 text-base font-bold text-slate-900">{{ v.title }}</h3>
          <p class="mt-1.5 text-sm leading-relaxed text-slate-500">{{ v.desc }}</p>
        </div>
      </div>
    </section>

    <!-- 核心能力 -->
    <section class="border-y border-slate-100 bg-slate-50/60">
      <div class="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <div class="text-center">
          <h2 class="text-2xl font-bold tracking-tight text-slate-900">核心能力</h2>
          <p class="mt-2 text-sm text-slate-500">从解析到落盘，每一步都按「少一次点击」的标准来做</p>
        </div>

        <div class="mt-9 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div v-for="f in features" :key="f.title" class="card card-hover p-6">
            <span
              class="flex h-11 w-11 items-center justify-center rounded-xl ring-1"
              :class="toneMap[f.tone]"
            >
              <svg class="h-5.5 w-5.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path :d="f.icon" />
              </svg>
            </span>
            <h3 class="mt-4 text-base font-bold text-slate-900">{{ f.title }}</h3>
            <p class="mt-1.5 text-sm leading-relaxed text-slate-500">{{ f.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 独特卖点对比 -->
    <section class="mx-auto max-w-6xl px-4 py-14 sm:px-6">
      <div class="text-center">
        <h2 class="text-2xl font-bold tracking-tight text-slate-900">和常见方案比，SnapDown 有什么不同</h2>
        <p class="mt-2 text-sm text-slate-500">同一件小事，体验差距往往就在这些细节里</p>
      </div>

      <div class="mt-8 overflow-x-auto">
        <table class="w-full min-w-[640px] border-separate border-spacing-0 text-sm">
          <caption class="sr-only">SnapDown 与常见下载方案的能力对比</caption>
          <thead>
            <tr>
              <th scope="col" class="rounded-l-xl bg-slate-50 px-4 py-3 text-left text-xs font-semibold text-slate-500">对比项</th>
              <th scope="col" class="bg-blue-600 px-4 py-3 text-center text-xs font-bold text-white">SnapDown</th>
              <th scope="col" class="bg-slate-50 px-4 py-3 text-center text-xs font-semibold text-slate-500">常见桌面下载器</th>
              <th scope="col" class="rounded-r-xl bg-slate-50 px-4 py-3 text-center text-xs font-semibold text-slate-500">在线解析网站</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in comparisons" :key="row.item">
              <th
                scope="row"
                class="border-b border-slate-100 px-4 py-3 text-left text-sm font-medium text-slate-700"
                :class="i % 2 ? 'bg-white' : 'bg-slate-50/50'"
              >
                {{ row.item }}
              </th>
              <td class="border-b border-blue-100 bg-blue-50/60 px-4 py-3 text-center text-sm font-semibold text-blue-700">
                <span class="inline-flex items-center gap-1">
                  <svg class="h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M20 6 9 17l-5-5" />
                  </svg>
                  {{ row.sn }}
                </span>
              </td>
              <td class="border-b border-slate-100 px-4 py-3 text-center text-sm text-slate-500" :class="i % 2 ? 'bg-white' : 'bg-slate-50/50'">{{ row.desktop }}</td>
              <td class="border-b border-slate-100 px-4 py-3 text-center text-sm text-slate-500" :class="i % 2 ? 'bg-white' : 'bg-slate-50/50'">{{ row.online }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="mt-3 text-center text-xs text-slate-400">
        对比项基于同类工具的普遍情况整理，仅供选购参考。
      </p>
    </section>

    <!-- 使用场景 -->
    <section class="border-y border-slate-100 bg-slate-50/60">
      <div class="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <div class="text-center">
          <h2 class="text-2xl font-bold tracking-tight text-slate-900">谁在用，用在哪</h2>
          <p class="mt-2 text-sm text-slate-500">三种最常见的使用场景，也是我们做产品时反复回看的地方</p>
        </div>

        <div class="mt-9 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div v-for="s in scenes" :key="s.title" class="card card-hover p-6">
            <span class="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-blue-600 ring-1 ring-blue-100">
              <svg class="h-5.5 w-5.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path :d="s.icon" />
              </svg>
            </span>
            <h3 class="mt-4 text-base font-bold text-slate-900">{{ s.title }}</h3>
            <p class="mt-1.5 text-sm leading-relaxed text-slate-500">{{ s.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Pro 会员预告 -->
    <section class="mx-auto max-w-6xl px-4 py-14 sm:px-6">
      <div
        class="relative overflow-hidden rounded-3xl px-6 py-10 ring-1 ring-orange-200/70 sm:px-10"
        style="background-image: linear-gradient(135deg, #fff7ed 0%, #ffedd5 55%, #fed7aa 100%)"
      >
        <div
          class="pointer-events-none absolute -right-24 -top-28 h-[320px] w-[320px]"
          style="background: radial-gradient(closest-side, rgb(234 88 12 / 0.22), rgb(234 88 12 / 0) 100%)"
          aria-hidden="true"
        ></div>

        <div class="relative grid gap-8 lg:grid-cols-[1fr_1.1fr] lg:items-center">
          <div>
            <span class="inline-flex items-center gap-1.5 rounded-full bg-orange-700 px-3 py-1 text-xs font-bold text-white">
              <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M3 7.5 7 11l5-7 5 7 4-3.5-2 11H5l-2-11Z" />
              </svg>
              SnapDown Pro
            </span>
            <h2 class="mt-4 text-2xl font-bold leading-tight tracking-tight text-slate-900 sm:text-3xl">
              更快的通道，更强的能力
            </h2>
            <p class="mt-3 text-sm leading-relaxed text-slate-600 sm:text-[15px]">
              如果你是高频用户——做素材归档、批量备份、每天都要下载——Pro 会员会把等待时间压到最低。
              内测期间，全部 Pro 能力免费开放给所有用户。
            </p>
            <div class="mt-6 flex flex-col gap-3 sm:flex-row">
              <button type="button" class="btn-vip w-full !py-3.5 sm:w-auto" @click="navigate(ROUTES.vip)">
                查看会员方案
              </button>
              <button
                type="button"
                class="inline-flex w-full items-center justify-center rounded-xl bg-white px-6 py-3.5 text-base font-semibold text-orange-800 ring-1 ring-orange-200 transition-colors hover:bg-orange-50 sm:w-auto"
                @click="emit('go-download')"
              >
                先免费试一次
              </button>
            </div>
          </div>

          <ul class="grid gap-3 sm:grid-cols-2">
            <li v-for="b in proBenefits" :key="b.title" class="rounded-2xl bg-white/85 p-4 ring-1 ring-orange-100 backdrop-blur">
              <p class="flex items-center gap-1.5 text-sm font-bold text-slate-900">
                <svg class="h-4 w-4 shrink-0 text-orange-700" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="M20 6 9 17l-5-5" />
                </svg>
                {{ b.title }}
              </p>
              <p class="mt-1 text-xs leading-relaxed text-slate-500">{{ b.desc }}</p>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <!-- FAQ -->
    <section class="mx-auto max-w-3xl px-4 pb-14 sm:px-6">
      <h2 class="text-center text-2xl font-bold tracking-tight text-slate-900">常见问题</h2>
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
        class="relative overflow-hidden rounded-3xl px-6 py-10 text-center sm:px-10"
        style="background-image: linear-gradient(135deg, #1d4ed8 0%, #4f46e5 100%)"
      >
        <div
          class="pointer-events-none absolute -top-32 left-1/2 h-[300px] w-[620px] -translate-x-1/2"
          style="background: radial-gradient(closest-side, rgb(255 255 255 / 0.35), rgb(255 255 255 / 0) 100%)"
          aria-hidden="true"
        ></div>
        <h2 class="relative text-2xl font-bold tracking-tight text-white sm:text-3xl">现在就试一个链接</h2>
        <p class="relative mx-auto mt-3 max-w-xl text-sm text-blue-100">
          粘贴你手边任意一个视频链接，三秒内就能看到它能以什么画质被你带走。
        </p>
        <button
          type="button"
          class="relative mt-6 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-white px-6 py-3.5 text-base font-bold text-blue-700 transition-transform duration-300 hover:-translate-y-0.5 hover:shadow-xl sm:w-auto"
          @click="emit('go-download')"
        >
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M12 3v12M7 10l5 5 5-5M4 21h16" />
          </svg>
          免费开始解析
        </button>
      </div>
    </section>
  </div>
</template>
