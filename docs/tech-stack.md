# 技术栈与知识点沉淀 · 瞬下 SnapDown 万能视频下载

> 版本：v1.0（基于 2026-09 交付代码快照整理）
> 定位：本文是**工程级"技术栈 + 知识点"总览**，用于快速建立全局认知与二次开发时的知识索引。
> 配套阅读：`docs/requirements.md`（需求基线）、`docs/design.md`（方案设计）、`README.md`（快速开始）。

---

## 1. 项目一句话概览

一个**本地部署优先**的万能视频下载网站：Python FastAPI 后端直接以**库调用**方式封装开源工具 yt-dlp（不做命令行调用），前端 Vue 3 + Vite + Tailwind 的工程化 SPA，通过内存任务表 + 1 秒轮询实现「粘贴链接 → 解析 → 选画质 → 下载 → 进度/历史」的完整闭环；抖音因 yt-dlp 解析器被风控拦截，走了一条**服务端自动生成游客身份 + 纯 Python `a_bogus` 签名**的独立通道。

**合规底线**：只使用 yt-dlp 合法能力，不碰 DRM 破解；页面保留版权提示。

---

## 2. 技术栈总览（含版本）

### 2.1 后端（Python）

| 依赖 | 版本约束 | 用途 | 关键知识点 |
|---|---|---|---|
| Python | 3.12+（本机 venv 基于 3.14；Docker 用 `python:3.12-slim`） | 运行时 | 类型注解用 `X \| None`、`list[dict]` 等 3.10+ 语法 |
| [FastAPI](https://fastapi.tiangolo.com/) | `>=0.115.0` | Web 框架 | 路由、Pydantic 请求体、`FileResponse`、`StaticFiles`、中间件 |
| [uvicorn](https://www.uvicorn.org/) | `>=0.30.0`（`[standard]`） | ASGI 服务器 | `run.py` 内 `uvicorn.run(app, ...)` |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | `>=2025.6.30` | 下载核心 | 直接用 `yt_dlp.YoutubeDL` 库，非子进程 |
| [httpx](https://www.python-httpx.org/) | `>=0.28.0` | HTTP 客户端 | 抖音通道请求 + 短链跳转 + 流式下载；测试也用 |
| python-multipart | `>=0.0.9` | 表单解析（预留） | FastAPI 处理 multipart 的依赖 |
| pytest | `>=8.0.0`（dev） | 单元/集成测试 | `pytest.ini` 里 marker 机制 |
| ffmpeg | 内置静态二进制 `tools/ffmpeg/ffmpeg.exe`（4.1，2018 构建） | 音视频合并 | 随项目内置，用户零安装 |

### 2.2 前端（Node）

| 依赖 | 版本 | 用途 | 关键知识点 |
|---|---|---|---|
| [Vue](https://vuejs.org/) | `^3.5.42` | UI 框架 | Composition API + `<script setup>` SFC |
| [Vite](https://vitejs.dev/) | `^8.3.0` | 构建/开发服务器 | **Vite 8 底层已切换为 Rolldown（Rust 打包器）**，`node_modules` 中可见 `rolldown` / `@rolldown/*` |
| [@vitejs/plugin-vue](https://github.com/vitejs/vite-plugin-vue) | `^6.0.8` | Vue SFC 编译 | — |
| [Tailwind CSS](https://tailwindcss.com/) | `^4.3.3` | 原子化 CSS | **v4 采用 CSS-first 配置**：`@import "tailwindcss"` + `@theme` 指令，**无需 `tailwind.config.js`** |
| [@tailwindcss/vite](https://tailwindcss.com/docs/installation/using-vite) | `^4.3.3` | Tailwind 的 Vite 插件 | 取代 v3 的 PostCSS 插件 |
| [Playwright](https://playwright.dev/) | `^1.63.0` | 前端冒烟测试 | 驱动 Firefox（浏览器内置 `.playwright-browsers/`） |

### 2.3 测试与部署

| 层 | 技术 | 说明 |
|---|---|---|
| 后端单元测试 | pytest + `fastapi.testclient.TestClient` + `monkeypatch` | 离线隔离 yt-dlp，不碰真实网络 |
| 后端集成测试 | pytest `integration` marker | 真实 B站解析 + 真实下载，默认跳过 |
| 前端冒烟测试 | Playwright（Firefox headless）+ iPhone 13 视口 | 断言 UI 文案/交互/缓存头/响应式，输出截图 |
| 容器化 | 多阶段 `Dockerfile` | node 构建前端 → python:3.12-slim + apt ffmpeg（预留，未实机验证） |

---

## 3. 目录结构（精确）

```
free-video-download/
├── run.py                          # 启动入口：uvicorn 托管 backend.app.main:app
├── Dockerfile                      # 部署预留（多阶段构建）
├── AGENTS.md / README.md / prompt.md
├── docs/
│   ├── requirements.md             # 需求基线
│   ├── design.md                   # 方案设计
│   └── tech-stack.md               # 本文
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 路由 + 静态托管 + CORS + 缓存中间件
│   │   ├── downloader.py           # yt-dlp 库封装（解析/下载/进度钩子）
│   │   ├── douyin.py               # 抖音独立通道（游客身份 + 签名 + 直链下载）
│   │   ├── douyin_signer/
│   │   │   ├── abogus.py           # a_bogus 签名器（纯 Python）
│   │   │   └── sm3.py              # SM3 国密哈希（纯 Python，无第三方依赖）
│   │   ├── tasks.py                # 内存任务管理（OrderedDict + 线程锁）
│   │   └── config.py               # 路径/端口/ffmpeg 定位/环境变量
│   ├── tests/
│   │   ├── conftest.py             # sys.path 注入（保证 `from app import ...`）
│   │   ├── test_api.py             # 离线单元测试（10 例）
│   │   ├── test_douyin.py          # 抖音通道离线单测（4 例）
│   │   └── test_integration.py     # B站真实集成测试（3 例，integration marker）
│   ├── requirements.txt / requirements-dev.txt
│   └── pytest.ini                  # marker + 默认跳过 integration
├── frontend/
│   ├── src/
│   │   ├── main.js                 # createApp(App).mount('#app')
│   │   ├── App.vue                 # 状态编排 + 路由视图切换 + 轮询
│   │   ├── router.js               # 自研极简 hash 路由（无 vue-router）
│   │   ├── api.js                  # fetch 封装 + 错误信息提取
│   │   ├── scroll.js               # 滚动/动效偏好/精确指针工具
│   │   ├── style.css               # Tailwind 入口 + @theme + 全局动效
│   │   ├── components/             # SiteHeader / HeroSection / ResultCard /
│   │   │                           #   HistoryDrawer / TaskList / SiteFooter
│   │   └── pages/                  # WhyPage（介绍页）/ VipPage（会员页）
│   ├── scripts/smoke.mjs           # Playwright 冒烟测试
│   ├── vite.config.js              # vue + tailwind 插件 + /api 代理 + preserveSymlinks
│   ├── index.html / package.json / package-lock.json
│   └── public/favicon.svg
├── tools/ffmpeg/ffmpeg.exe         # 内置合并工具
└── downloads/                      # 下载文件保存目录（.gitignore 忽略）
```

---

## 4. 架构与数据流

```
浏览器（桌面/手机，Vue 3 SPA）
  ├─ 路由（自研 hash）：/ 主页 · /why 介绍页 · /vip 会员页
  ├─ 主页状态：url / info / task / taskList / selectedFormat
  └─ 1s 轮询 GET /api/tasks/{id} 直到 done/error
        │  HTTP（开发：Vite /api 代理 → :8000；生产：同源托管 frontend/dist）
        ▼
FastAPI 后端（单进程，无数据库）
  ├─ main.py     路由 + 静态托管 + CORS + Cache-Control 中间件
  ├─ downloader.py  yt-dlp 库封装（B站等平台）
  ├─ douyin.py      抖音独立通道（绕过 yt-dlp）
  ├─ tasks.py       内存任务表（OrderedDict + Lock，上限 100）
  └─ config.py      路径 / 端口 / ffmpeg 定位
        │  下载任务在 daemon 线程执行，progress_hooks 回写任务状态
        ▼
yt-dlp 库（parse: extract_info / download + hooks）
        │  音视频合并 → 调用 ffmpeg
        ▼
downloads/ 目录（`标题 [id] [format_id].mp4`）
```

---

## 5. 后端知识点

### 5.1 yt-dlp 的 Python 库封装（非命令行）

`downloader.py` 核心设计：直接实例化 `yt_dlp.YoutubeDL`，通过 `opts` 字典控制行为，仅做「解析出前端需要的信息 + 进度钩子回写」两层薄封装。

```python
with yt_dlp.YoutubeDL(opts) as ydl:
    info = ydl.extract_info(url, download=False)   # 解析（skip_download=True）
    # 或
    info = ydl.extract_info(url, download=True)    # 下载
```

**统一基础选项**（`_base_opts()`）：`quiet`、`no_warnings`、`noplaylist`、`socket_timeout=30`，有 ffmpeg 时注入 `ffmpeg_location`，受 `FVD_MAX_FILESIZE` 控制时注入 `max_filesize`。

### 5.2 format 选择器（经历过真实 bug，重点）

| 场景 | 选择器 | 原因 |
|---|---|---|
| `format_id == "best"` | `bestvideo+bestaudio[ext=m4a]/bestvideo+bestaudio/best` | B站只有 DASH 流时，裸 `best` 会报 "Requested format is not available" |
| 其他 format_id | `{fmt}+bestaudio[ext=m4a]/{fmt}+bestaudio/{fmt}/best` | 优先合并最佳音轨，逐级回退 |

- **音频优先选 m4a**：让最终容器尽量是 mp4（兼容性最好）；找不到 m4a 再回退任意最佳音轨。
- 选择器中的 `/` 是 yt-dlp 的**回退语义**（左侧失败才试右侧），`+` 是**合并语义**（视频流 + 音频流）。

### 5.3 输出文件名模板必须带 `%(format_id)s`（真实 bug）

```python
def _outtmpl():
    return str(DOWNLOADS_DIR / "%(title).120B [%(id)s] [%(format_id)s].%(ext)s")
```

- **坑**：若模板只有 `标题 [id].ext`，同一视频的不同清晰度会落盘成**同名文件**；第二次下载会被 yt-dlp 因「文件已存在」跳过，复用上一次（错误分辨率）的文件。
- **带 `%(format_id)s` 后天然唯一**：实测 B站 1080P=`100026+30280`、360P=`30016+30280`。
- `%(title).120B` 表示标题按**字节**截断到 120（防止 Windows 长路径/非法字符）。

### 5.4 `merge_output_format` 必须是偏好列表（真实 bug）

```python
"merge_output_format": "mp4/mkv",   # 而非硬性 "mp4"
```

- **坑**：YouTube 的 `bestaudio` 常命中 opus/webm（如 `251`），内置 ffmpeg（4.1）把 opus 封装进 mp4 视为 experimental，强制 `mp4` 会报 `ERROR: Postprocessing: Stream #1:0 -> #0:1 (copy)`。
- **解**：写成 `mp4/mkv`，yt-dlp 按音视频编码自动挑容器：`avc1/av01/vp9 + m4a → mp4`，`opus 音轨 → mkv`。

### 5.5 progress_hooks 与最终文件路径

- `progress_hooks` 回调里 `d["status"]` 分 `downloading` / `finished`：
  - `downloading`：`percent = downloaded_bytes / (total_bytes or total_bytes_estimate)`，同时回写 `speed`、`eta`（注意 `d` 是字典，字段为 snake_case）。
  - `finished`：置 `percent=100`。
- **取最终文件路径**：合并/转码后的路径在 `info["requested_downloads"][0]["filepath"]`，回退 `ydl.prepare_filename(info)`。这是拿到「真正成品文件」而非中间 `.f{...}.mp4` 的关键。
- 完成后 `filesize = filepath.stat().st_size`（回填体积标签）。

### 5.6 解析字段整理（`parse_video`）

- **播放列表检测**：`info.get("_type") == "playlist" or info.get("entries")` → 抛 `PlaylistNotSupported`（400 提示）。
- **格式列表**（`_build_format_list`）：仅保留 `height > 0` 且 `vcodec != "none"` 的格式，按 `height` 去重、降序；`filesize` 缺失时用 `tbr * 1024 / 8 * duration` 估算。
- **字幕列表**（`_build_subtitle_list`）：合并 `subtitles`（手动）与 `automatic_captions`（自动），返回 `{lang, ext}`。
- **封面归一化**（`_normalize_thumbnail`）：协议相对地址 `//host/x.jpg` 补全为 `https:`，非 http(s) 值丢弃。
- **时长/速度/ETA 人性化**：`_human_duration` / `_human_speed` / `_human_eta` 三个纯函数。

### 5.7 下载记录元信息补齐（`_backfill_meta`）

- 前端 `POST /api/download` 会回传解析结果的 `title/thumbnail`；后端在 progress_hook 与下载完成时用 yt-dlp `info_dict` **兜底补齐**（保证直接用 API 调用也有记录可读）。
- **不覆盖已有值**：`task.title or info.get("title")` 的写法，只有任务字段为空时才回填。
- `height` 来自 `info["height"]`（像素高度）。

### 5.8 内存任务管理（`tasks.py`）

- `Task` 用 `@dataclass` 定义，字段含状态机 `pending → downloading → done | error`、`percent`、`speed`、`eta`、`filepath`、`filename`、`height`、`filesize`、`error`、`created_at`、`finished_at`。
- `TaskManager` 用 `collections.OrderedDict` + `threading.Lock` 保证线程安全；`MAX_TASKS = 100`，超出时 `popitem(last=False)` 淘汰最旧。
- `task.id = uuid.uuid4().hex[:12]`。
- `list()` 按 `created_at` 倒序。
- **无数据库、重启即清空**——这是用户明确要求的"先不需要数据库"约束。

### 5.9 FastAPI 路由与托管（`main.py`）

- API 路由：`/api/parse`、`/api/download`、`/api/tasks/{id}`、`/api/tasks`、`/api/files/{id}`、`/api/health`。
- **错误码约定**：空链接 400、播放列表 400、解析失败 422、任务/文件不存在 404。
- **下载文件**：`FileResponse(path, filename=path.name, media_type="application/octet-stream")`，`filename` 触发浏览器 `Content-Disposition: attachment`（UTF-8 文件名）。
- **生产同源托管**：检测 `frontend/dist` 存在则 `app.mount("/assets", ...)` 与 `app.mount("/", StaticFiles(html=True))`——**生产只需 `python run.py` 一个进程**。
- **CORS**：开发态允许 `http://localhost:5173` 与 `http://127.0.0.1:5173`。

### 5.10 静态资源缓存策略（`add_cache_headers` 中间件，真实 bug）

```python
if path.startswith("/assets/"):
    response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
else:
    response.headers["Cache-Control"] = "no-cache, must-revalidate"
```

- **坑**：缺了它，浏览器会缓存旧 `index.html` + 旧 bundle，出现「代码已改但页面行为没变」的假象。
- **要点**：`/assets/*` 是 Vite 内容指纹资源（文件名含 hash），可长期强缓存；入口 HTML 必须 `no-cache` 回源校验。

### 5.11 配置与 ffmpeg 定位（`config.py`）

- `ROOT_DIR = Path(__file__).resolve().parent.parent.parent`（config.py 上三级 = 项目根）。
- 环境变量：`FVD_HOST`（默认 127.0.0.1）、`FVD_PORT`（8000）、`FVD_DOWNLOADS_DIR`、`FVD_MAX_FILESIZE`（0=不限）、`FVD_FFMPEG_PATH`、`FVD_FRONTEND_DIST`。
- `find_ffmpeg()` 优先级：环境变量 → 内置 `tools/ffmpeg/ffmpeg.exe` → 系统 PATH。

---

## 6. 前端知识点

### 6.1 Vue 3 Composition API（`<script setup>`）

- 全站使用 `<script setup>` SFC：`ref`/`computed`/`watch`/`onMounted`/`onUnmounted`。
- 组件通信：`defineProps` + `defineEmits`，`v-model:url` 语法糖（HeroSection 的 `update:url` 事件）。
- `Teleport to="body"` 用于抽屉（HistoryDrawer）与弹窗（VipPage），避免被父级 `overflow` 裁剪。
- `computed` 派生：`view`（路由→视图映射）、`downloading`/`isDone`（任务状态派生）、`year`（动态版权年份）。

### 6.2 自研 hash 路由（`router.js`，不引入 vue-router）

```js
export const ROUTES = { home: '/', why: '/why', vip: '/vip' }
export const route = ref(parse(window.location.hash))
window.addEventListener('hashchange', () => (route.value = parse(...)))
export function navigate(path) { window.location.hash = target }
```

- **知识点**：`route` 是响应式 `ref`，App.vue 用 `computed` 把它映射成视图。
- **未知 hash 兜底**：`App.vue` 的 `watch(route)` 检测未匹配 hash 时 `navigate(ROUTES.home)` 并清理地址栏——避免「路由落空仍渲染主页」。
- **坑（页面内锚点）**：hash 路由下 `href="#plans"` 会被解析成路由 `/plans`，导致「点击跳回首页」。页面内跳转**一律用 `scrollIntoView()`**（`scroll.js` 的 `scrollToElement`）。

### 6.3 Vite 配置（`vite.config.js`）

```js
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: { preserveSymlinks: true },   // 避免 Windows 上子进程解析真实路径
  server: { port: 5173, proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } } },
})
```

- Tailwind v4 以 **Vite 插件**形式接入（`@tailwindcss/vite`），无需 PostCSS 配置。
- 开发态 `/api` 代理到后端 8000，规避跨域。

### 6.4 Tailwind CSS v4 的 CSS-first 配置（`style.css`）

```css
@import "tailwindcss";
@theme {
  --font-sans: "PingFang SC", "HarmonyOS Sans SC", ...;
  --animate-fade-up: fade-up 0.5s cubic-bezier(...) both;
  /* ... */
}
```

- **v4 变化**：无 `tailwind.config.js`，主题通过 `@theme` 声明自定义设计令牌（字体、动画）；`@apply` 仍在组件/工具类中使用。
- 品牌工具类：`.btn-primary`（蓝→靛渐变 CTA）、`.btn-vip`（暖橙金渐变，付费引导对比）、`.card`/`.card-hover`（圆角 + 细描边 + 蓝色光晕）、`.chip`（平台标签）、`.progress-track/.progress-fill/.progress-stripes`（进度条 + shimmer 条纹）、`.text-gold`（金色渐变文字）。
- **渐变白背景**：`body` 上 `linear-gradient(180deg, #fff → #e6efff → #dee8ff → #f2ecff)`，`background-attachment: fixed`。

### 6.5 动效与无障碍

- 入场动效 `fade-up`/`fade-in` 用 `animation-delay` 递增（60ms 步进）做错落感。
- **尊重 `prefers-reduced-motion`**：`style.css` 用 media query 把动画/过渡时长压到 `0.01ms`；`scroll.js` 的 `scrollToTop/scrollToElement` 也根据该偏好切换 `smooth`/`auto`。
- **无障碍**：表单错误 `role="alert"`、清晰度选择 `role="radiogroup"` + `role="radio"` + `aria-checked`、抽屉 `role="dialog" aria-modal`、输入框 `sr-only` label + `aria-label`、对比度 ≥4.5:1、触控目标 ≥44px。
- `aria-live="polite"` 用于结果卡片区域。

### 6.6 一键粘贴（`navigator.clipboard`，真实 bug）

- **只走** `navigator.clipboard.readText()`：
  - Chrome/Edge 首次弹一次「读取剪贴板」授权，允许后永久静默；
  - Firefox 每次弹确认（浏览器安全机制，网页无法绕过）；
  - 不支持/被拒/为空 → 聚焦输入框 + 琥珀色提示手动 Ctrl+V。
- **坑**：不要回退 `document.execCommand('paste')`——Chromium 会对它弹原生「粘贴(P)」确认气泡（用户必须再点一次），Firefox 也会多弹一次。

### 6.7 状态编排与轮询（`App.vue`）

- 顶层状态：`url / error / loading / info / task / taskList / selectedFormat / historyOpen`。
- 提交流程：校验（非空 + `/^https?:\/\//i`）→ `parseVideo` → 置 `info` 并重置 `task`/`selectedFormat`。
- 下载流程：`startDownload` → `startPolling()`（`setInterval 1s` 查 `getTask`，`done/error` 后 `stopPolling` + `refreshHistory`）。
- `onUnmounted` 清理定时器；`handleReset`（「再来一个」）清空所有状态 + 回顶部 + 桌面端（`hasFinePointer()`）自动聚焦输入框（手机端不聚焦避免误弹键盘）。

### 6.8 下载完成态（`ResultCard.vue`，真实 bug）

- **坑**：下载完成后清晰度选择区仍是可点的「死控件」（选了也没用）。解：`isDone` 时**收起整个清晰度选择区**，改为清爽成功卡片（绿色对勾 + 文件名 + 分辨率/体积/时长标签 + 「保存到本地」+「再来一个」）。
- 清晰度区用 `flex-wrap` + `basis-[45%]/sm:basis-[30%]`，让最后一行自动加宽铺满不留空位。
- DASH 提示：`currentFormat.acodec === 'none'` 时提示「自动合并音轨输出 MP4」。

### 6.9 下载记录（`TaskList.vue` / `HistoryDrawer.vue`）

- 三枚元信息标签：蓝色「`height`P」、灰色「体积 MB/GB」、灰色「`YYYY-MM-DD HH:mm`」（取 `finished_at || created_at`，精确到分钟）。
- 封面 `loading="lazy"` + `referrerpolicy="no-referrer"`（跨域封面）；加载失败回退占位图标（`brokenThumbs` Set 记录失败 id）。
- 抽屉：`Teleport` + `role="dialog"` + ESC/遮罩关闭 + 打开时锁定 `document.body.style.overflow = 'hidden'`。

---

## 7. 抖音逆向签名通道（`douyin.py` + `douyin_signer/`，重点知识点）

### 7.1 为什么绕过 yt-dlp

yt-dlp 的 Douyin 解析器调 `www.douyin.com/aweme/v1/web/aweme/detail/` 时**既不带 `a_bogus` 签名，也不带游客身份 cookie**，风控返回空 JSON，报 `Fresh cookies (not necessarily logged in) are needed`。这里的 "cookies" 不是登录态，而是一份**游客设备身份**（`s_v_web_id` / `ttwid`）+ `a_bogus` 签名。

### 7.2 通道流程

1. **解析 aweme_id**：正则从 `douyin.com/iesdouyin.com/amemv.com` 域名下的 `/video/...`、`/note/...`、`/share/video/...` 提取数字 id；短链则用 httpx `follow_redirects=True` 跟随跳转取最终 URL。
2. **游客身份**：
   - `s_v_web_id`：本地生成（与抖音 `verifyFp` 同构，`verify_` + 时间戳 base36 + 36 位随机串，含 UUID-v4 风格的第 14 位 `4` 与第 19 位变体）。
   - `ttwid`：调 `ttwid.bytedance.com/ttwid/union/register/` 注册，**内存缓存 12h**（`_ttwid_cache` + 双重检查锁）。
   - `msToken`：本地伪造的 126 位 base64 随机串。
3. **签名**：用内置纯 Python 签名器给详情接口 query 计算 `a_bogus`。
4. **取直链**：从 `aweme_detail.video.bit_rate[]` 按分辨率去重，每个分辨率只保留码率最高的 **mp4**（自带音轨，免 ffmpeg 合并）；dash 是纯视频流被跳过。
5. **下载**：重新取详情拿最新 CDN 直链，httpx 流式写盘到 `.part` 临时文件，成功后 `replace` 为正式文件，复用同一套任务进度字段。

### 7.3 签名器技术细节（`douyin_signer/`）

- **来源与许可**：改编自 Evil0ctal/Douyin_TikTok_Download_API（v5，Apache-2.0），仅保留最小实现，删除 `dtk.*` 框架依赖，SM3 改为包内相对导入。（注：`abogus.py` 模块 docstring 引用 `docs/design/17-signature-reversing.md` 与 `dtk.signing.*` 等**不在本仓库**的内容，是从更大原始工程带入的遗留说明。）
- **SM3 国密哈希**（`sm3.py`）：GB/T 32905-2016，纯 Python 实现，与 `gmssl.sm3.sm3_hash` 输出逐字节一致；无第三方依赖，可对照公开测试向量单测。签名链：`SM3(SM3(text + SALT))`（SALT=`"dhzx"`），User-Agent 链为单次 SM3。
- **自定义密码原语**（`abogus.py`）：
  - `rc4`：非教科书 RC4（S-box **降序**初始化 + 密钥调度用**乘法**），单字节密钥 `0xD3`。
  - `encode_base64/decode_base64`：标准 base64 结构，但字符集是 `bdms.js` 内自定义字母表（`s3`/`s4`）。
  - `js_bytes`：把 JS 字符串按 UTF-16 code unit 转字节（非 UTF-8）——中文 2 字节、代理对 4 字节。
  - `_mask_pair/_unmask_pair`、`_expand_noise/_collapse_noise`：可逆的噪声扩散层，把真实字节的比特位拆分藏进噪声。
  - `DigestChain` / `FIELD_ORDER`：50 个标量字段的固定排列，三个摘要（query/body/user_agent）各取 3 字节落入固定槽位。
- **可验证性**：`structure_error()` / `decode()` 能对签名做结构校验（字母表、长度、header magic、SDK 版本、checksum），用于诊断与测试——这是「签名是否被平台接受」之外，**自证实现正确**的手段。

### 7.4 该通道的边界

- 不影响其他平台（仍走 yt-dlp）。
- 抖音**图文/私密/已删除**会明确报错（`aweme_detail` 为空或 `status_code` 非 0）。
- 逆向方案有时效性：`a_bogus`/`ttwid` 参数若平台改版失效，需按 `douyin_signer/` 说明重新对齐（实测 2026-09 可用）。

---

## 8. 测试体系

### 8.1 分层与运行方式

| 层级 | 文件 | 方式 | 命令 |
|---|---|---|---|
| 单元 | `test_api.py`、`test_douyin.py` | `TestClient` + `monkeypatch` 隔离 yt-dlp，离线 | `pytest backend` |
| 集成 | `test_integration.py` | 真实 B站（`BV1GJ411x7h7`）解析 + 下载 | `pytest backend/tests/test_integration.py -m integration -v` |
| 冒烟 | `scripts/smoke.mjs` | Playwright + Firefox，UI 全流程 | `node frontend/scripts/smoke.mjs`（需先启动服务） |

### 8.2 pytest 知识点

- `pytest.ini`：`addopts = -m "not integration"`（默认跳过集成）、`markers` 声明 `integration`、`testpaths = tests`。
- `conftest.py` 注入 `sys.path`，让 `from app import ...` 可用（backend 目录作为包根）。
- `monkeypatch.setattr(downloader, "parse_video", fake_parse)` 隔离真实网络。
- 集成测试用 `time.time()` 截止时间 + `while` 轮询任务状态（最长 240s），断言文件 `len(content) > 100KB`。

### 8.3 Playwright 冒烟测试知识点

- `firefox.launch({ headless: true })`（本机 Edge/Chrome 沙箱下无法常驻，故用内置 Firefox）。
- `reducedMotion: 'reduce'` 让入场动画瞬时完成，保证截图/断言稳定可复现。
- 关键断言（约 30+ 条）：主页一屏（`scrollHeight <= innerHeight + 2`）、背景为渐变白、按钮文案、`execCommand` 不存在、缓存头、未知 hash 兜底、页脚年份动态化、粘贴直填、下载完成收起清晰度、下载记录三标签、移动端无横向滚动、零 JS/控制台错误。
- **高级技巧**：
  - `page.addInitScript` 伪造 `Date`（`class MockDate extends RealDate`）验证版权年份动态变化。
  - `Object.defineProperty(navigator, 'clipboard', ...)` 桩掉 `readText`，验证「粘贴→直填」与「被拒→提示并聚焦」两条路径。
  - `page.evaluate` 里用 `[...document.querySelectorAll('button')].find(b => b.textContent.includes(...))` 定位按钮（页头有同文案滚动按钮时须用 `button[type="submit"]`）。

---

## 9. 工程化与部署知识点

### 9.1 启动与构建

- **生产**：`python run.py` 单进程同时托管 API 与 `frontend/dist`（先 `npm run build`）。
- **开发**：后端 `python run.py`（8000）+ 前端 `npm run dev`（5173，`/api` 代理）。
- 修改后端需重启 `run.py`；修改前端需重新 `npm run build`（或 dev 模式热更新）。

### 9.2 Dockerfile（多阶段，预留）

```dockerfile
FROM node:22-alpine AS webbuild     # 构建前端
FROM python:3.12-slim               # apt 装 ffmpeg + pip 装依赖 + 拷贝 dist
ENV FVD_HOST=0.0.0.0 FVD_PORT=8000
```

- 关键点：前端构建产物 `dist` 从 build 阶段拷贝到运行阶段；ffmpeg 用 `apt-get install` 而非内置 exe（Linux 环境）。

### 9.3 本机沙箱适配（正常环境可忽略）

项目在受限沙箱开发，以下适配已固化（详见设计文档第 9 节）：

- `.venv/.../sitecustomize.py` 替换 `tempfile.mkdtemp`（沙箱拒绝写入其创建的子目录）。
- npm 设 `npm_config_cache=<root>/.npm-cache`；pip 设 `TMP/TEMP=<root>/.tmp` + `--cache-dir`。
- Vite 构建、Playwright 启动浏览器需子进程管道（需升级权限执行）。
- Playwright 浏览器内置在 `.playwright-browsers/`，运行冒烟测试设 `PLAYWRIGHT_BROWSERS_PATH`。

---

## 10. 关键"坑"与经验教训速查（真实 bug 汇总）

| # | 坑 | 根因 | 解法 | 位置 |
|---|---|---|---|---|
| 1 | B站「best」报 Requested format is not available | B站只有 DASH 流，`best` 不合并 | 用 `bestvideo+bestaudio` 选择器 | downloader.py |
| 2 | 同视频不同清晰度复用旧文件 | outtmpl 缺 `%(format_id)s`，同名跳过 | 模板带 `%(format_id)s` | downloader.py |
| 3 | opus 音轨合并报 Postprocessing 错误 | 强制 `mp4` 而内置 ffmpeg 视 opus 为 experimental | `merge_output_format: "mp4/mkv"` | downloader.py |
| 4 | 浏览器跑旧构建（改代码无效） | 缺 Cache-Control，缓存旧 html/bundle | 入口 `no-cache`、assets `immutable` | main.py |
| 5 | 下载记录无封面/标题 | `/api/download` 只传 url+format_id | 请求体回传 + `_backfill_meta` 兜底 | main.py/downloader.py |
| 6 | VIP「立即开通」跳回主页 | hash 路由下 `href="#plans"` 被当路由 | 改 `scrollIntoView()` | VipPage.vue |
| 7 | 「粘贴」弹二次确认气泡 | 回退 `execCommand('paste')` | 只用 `navigator.clipboard.readText()` | HeroSection.vue |
| 8 | 下载完成后清晰度区成死控件 | 无下载动作仍可点 | `isDone` 收起，改成功卡片 | ResultCard.vue |
| 9 | 「再来一个」不清空链接/不回顶 | 只清 info/task | `handleReset` 全清 + 回顶 + 聚焦 | App.vue |
| 10 | 抖音解析报 Fresh cookies | yt-dlp 缺游客身份 + a_bogus | 独立通道自动生成身份 + 签名 | douyin.py |
| 11 | 抖音 dash 流需合并 | dash 是纯视频流 | 只选自带音轨的 mp4 | douyin.py |

---

## 11. 已知限制与扩展点（速览）

- **限制**：播放列表明确拒绝；任务历史在内存（重启清空）；YouTube/GitHub 本机不可达（代码支持，部署海外即可）；抖音逆向方案有时效性；未做并发数与速率限制。
- **扩展点**（对应切入位置）：批量/播放列表（去掉 `noplaylist` + 父子任务）、字幕下载/翻译（parse 已返回 `subtitles`）、AI 总结（新增 `ai.py` + LLM Key）、会员分层（权限中间件 + 兑换码表）、持久化（TaskManager 换 sqlite/sqlalchemy）、部署（验证 Dockerfile + 反代 + HTTPS）。

---

## 12. 阅读指引

| 想要了解 | 看哪里 |
|---|---|
| 需求背景 / 已确认决策 / 二期候选 | `docs/requirements.md` |
| 架构 / API 契约 / 各模块实现细节 / 扩展路线图 | `docs/design.md` |
| 技术栈 + 知识点索引（本文） | `docs/tech-stack.md` |
| 快速开始 / 环境变量 / 目录结构 | `README.md` |
| AI 协作约定 / 沙箱注意 / 命令速查 | `AGENTS.md` |
