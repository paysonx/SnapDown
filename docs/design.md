# 方案设计文档 · 瞬下 SnapDown 万能视频下载

> 版本：v1.0（对应 MVP 首版）　更新时间：2026-09
> 配套阅读：`docs/requirements.md`（需求基线）。扩展功能时先读需求文档确认决策，再读本文档了解架构与实现细节。

## 1. 总体架构

```
┌───────────────────────────── 浏览器（桌面 / 手机）─────────────────────────────┐
│  Vue 3 SPA（Vite 构建，Tailwind 样式）                                        │
│  HeroSection(链接输入) → ResultCard(清晰度选择/进度) → TaskList(历史)          │
│  状态驱动：App.vue 持有 url/info/task/taskList，1s 轮询 /api/tasks/{id}        │
└────────────────────────────────────┬────────────────────────────────────────────┘
                                     │ HTTP（开发时 Vite 代理 /api → :8000；生产同源托管）
┌────────────────────────────────────▼────────────────────────────────────────────┐
│  FastAPI 后端（Python，单进程，无数据库）                                      │
│  main.py      —— 路由 + 静态托管 + CORS                                        │
│  downloader.py—— yt-dlp 库封装（解析 / 下载 / progress_hooks）                 │
│  tasks.py     —— 内存任务管理（OrderedDict + 线程锁，上限 100 条）             │
│  config.py    —— 路径 / 端口 / ffmpeg 定位 / 环境变量                          │
│  下载任务在 daemon 线程中执行，通过 progress_hooks 回写任务状态                │
└────────────────────────────────────┬────────────────────────────────────────────┘
                                     │ Python 库调用（非子进程）
                          ┌──────────▼──────────┐
                          │      yt-dlp         │
                          │  parse: extract_info│  合并音视频 → 调用 ffmpeg
                          │  download + hooks   │  （npm 静态二进制，见 config.py）
                          └──────────┬──────────┘
                                     │ 下载写入 downloads/ 目录（标题[ID].mp4）
```

## 2. 技术选型与理由

| 层 | 选型 | 理由 |
|---|---|---|
| 下载核心 | yt-dlp（PyPI 包） | 用户指定；1000+ 平台；GitHub 本机不可达但 PyPI 可达 |
| 后端 | FastAPI + uvicorn | 轻量、异步、自带 OpenAPI 文档；Python 生态统一 |
| 存储 | 内存任务表 + 文件系统 | 用户要求"先不需要数据库" |
| 前端 | Vue 3 + Vite + Tailwind CSS v4（`@tailwindcss/vite` 插件） | 用户确认的工程化方案 |
| 合并工具 | ffmpeg 静态二进制（npm 包 `@ffmpeg-installer/ffmpeg` 随平台安装） | B站 DASH 流需要视频+音频合并；`npm install` 即可获得，用户零安装 |
| 前端测试 | Playwright（Firefox，浏览器内置在 `.playwright-browsers/`） | 本机 Edge/Chrome 在沙箱下无法常驻 |

## 3. 后端设计

### 3.1 API 契约

| 方法 | 路径 | 请求体 | 响应 | 错误 |
|---|---|---|---|---|
| POST | `/api/parse` | `{"url": "..."}` | `{title, thumbnail, duration, uploader, webpage_url, extractor, formats[], subtitles[]}` | 空链接 400；播放列表 400；解析失败 422 |
| POST | `/api/download` | `{"url", "format_id", "mode"}`，`mode=video`（默认）或 `audio` | 任务对象（含 `id`） | 空链接 400；非法 `mode` 422 |
| GET | `/api/tasks/{id}` | — | 任务对象 | 不存在 404 |
| GET | `/api/tasks` | — | 任务数组（按时间倒序，最多 100 条） | — |
| GET | `/api/files/{id}` | — | 文件流（`Content-Disposition: attachment`，UTF-8 文件名） | 未完成/被清理 404 |
| GET | `/api/health` | — | `{"status":"ok"}` | — |

`format` 条目：`{format_id, ext, height, width, fps, vcodec, acodec, filesize, note}`，按 `height` 降序；仅保留有画面的格式，同一分辨率去重。`subtitles` 条目：`{lang, ext}`（合并手动字幕与自动字幕）。

任务对象：`{id, url, format_id, mode, title, thumbnail, status, percent, speed, eta, filepath, filename, height, filesize, error, created_at, finished_at}`；状态机 `pending → downloading → done | error`。`mode` 为 `video`（默认，视频+音频一起）或 `audio`（仅提取音频）。`height`（分辨率高度，像素）由 yt-dlp 解析的 `info["height"]` 回填，`filesize`（字节）在下载完成后取最终文件 `stat().st_size`，二者供下载记录展示标签。

### 3.2 yt-dlp 封装要点（downloader.py）

- 统一基础选项：`quiet, no_warnings, noplaylist, socket_timeout=30`，有 ffmpeg 时注入 `ffmpeg_location`
- **format 选择器**（重要，经历过真实 bug）：
  - `format_id == "best"` → `"bestvideo+bestaudio[ext=m4a]/bestvideo+bestaudio/best"`（B站只有 DASH 流时 `"best"` 会报 "Requested format is not available"）
  - 其他 → `f"{format_id}+bestaudio[ext=m4a]/{format_id}+bestaudio/{format_id}/best"`（优先合并最佳音轨，逐级回退）
  - 音频优先选 m4a：让最终容器尽量是 mp4（兼容性最好），找不到 m4a 再回退任意最佳音轨
- **仅音频模式**（`mode == "audio"`）：`format` 固定为 `"bestaudio/best"`，并用
  `FFmpegExtractAudio` 后处理器转出 **MP3（192k）**；ffmpeg 缺失时退化为只下载原始音轨
- 输出模板：`downloads/%(title).120B [%(id)s] [%(format_id)s].%(ext)s`，`merge_output_format: mp4/mkv`
  —— **必须带 `%(format_id)s`**（经历过真实 bug）：不带它时同一视频的不同清晰度都落盘成同名文件，
  第二次下载会被 yt-dlp 因"文件已存在"跳过而复用上一次（错误分辨率）的文件
  —— **`merge_output_format` 必须是偏好列表而非硬性 mp4**（经历过真实 bug）：YouTube 的 `bestaudio`
  常命中 opus/webm（如 `251`），而 ffmpeg 4.1 把 opus 封装进 mp4 视为 experimental，
  强制 `mp4` 会报 `ERROR: Postprocessing: Stream #1:0 -> #0:1 (copy)`。写成 `mp4/mkv` 后 yt-dlp
  会按音视频编码自动挑容器：avc1/av01/vp9 + m4a → mp4，opus 音轨 → mkv，合并不再失败
- `progress_hooks` 回写 `percent/speed/eta`（total 取 `total_bytes` 或 `total_bytes_estimate`）
- 完成后取 `info["requested_downloads"][0]["filepath"]`（合并/转码后的最终路径），回退 `ydl.prepare_filename(info)`
- 同「视频 + 同清晰度」的文件已存在时 yt-dlp 默认跳过不覆盖（幂等，扩展时注意）

### 3.3 抖音专用通道（douyin.py）

yt-dlp 的 Douyin 解析器会报 `Fresh cookies (not necessarily logged in) are needed`——它缺的不是登录态，而是一份**游客设备身份**（`s_v_web_id`/`ttwid`/`uifid`）+ 完整签名。为做到「用户无需提供 Cookie」，后端在检测到抖音链接时**绕过 yt-dlp**，走独立通道，并按「快路径 → 浏览器兜底」两级降级：

**通道一：纯 Python 直连（快）**

1. 解析短链/视频链接拿到 `aweme_id`——路径 `/video/<id>`、`/note/<id>` 之外，**还必须认 `?modal_id=<id>`**（用户主页点开弹窗后复制出来的分享链接就是这个形态，早期实现只认路径，直接报「无法解析出视频 ID」）
2. 本地生成 `s_v_web_id`，调 `ttwid.bytedance.com/ttwid/union/register/` 注册游客 `ttwid`（内存缓存 12h）
3. 用内置纯 Python 签名器（`douyin_signer/`，Apache-2.0）给 `aweme/v1/web/aweme/detail/` 接口计算 `a_bogus`
4. 从 `aweme_detail.video.bit_rate[]` 中按分辨率去重，每个分辨率只保留码率最高的 `mp4`（自带音轨，免 ffmpeg 合并）
5. 下载时重新取详情拿最新 CDN 直链，流式写盘并复用同一套任务进度字段

**通道二：无头浏览器桥（兜底，`douyin_browser_bridge.js`）**

抖音后续在该接口上又加了一层校验：除了 `a_bogus`，还要求 `msToken`、`verifyFp`/`fp`，以及 secsdk 的 `uifid` + `timestamp` + `x-secsdk-web-signature` 三件套。这些由页面里的 `bdms`/`secsdk` 运行时在真实浏览器环境中生成（依赖 ECDSA 会话密钥与服务器签发的 ticket），**纯 Python 复现不现实**——此时直连必定被
`HTTP 403 Blocked by ArgusSecurityPlugin Uifid Not Found` 拒绝。

因此通道一被风控拒绝（403 / 空响应 / 非 JSON / 响应里没有视频但成因不明）时，`_fetch_detail()` 自动回退到浏览器桥：

- Node 跑 Playwright 启动 **headless Firefox**（浏览器内置在 `.playwright-browsers/`），打开 `www.douyin.com/video/<id>`
- 等页面自带的签名运行时初始化完成后，用**页内 `fetch`** 请求详情接口——签名参数由页面自己补全，后端不碰签名算法
- 页内请求会重试直至拿到数据（secsdk 未就绪时会被 403，稍等即可），结果写入临时 JSON 由 Python 读回
- 桥依赖：`node` + `frontend/node_modules/playwright`（已在 `frontend/package.json` 声明）+ 无头浏览器；缺任一项时会在错误信息里说明缺什么、怎么补

两条通道都失败时，报错会带上**真实原因**（HTTP 状态码 + 响应体片段），而不是笼统的「请稍后重试」。

> 注意：`aweme_detail` 里的 CDN 直链约 1–2 小时过期，所以下载开始时必须重新取一次详情，不能复用解析阶段的直链。

该通道不影响其他平台（仍走 yt-dlp）；抖音图文/私密/已删除会明确报错。

**抖音文件名必须按 `mode` 区分**（经历过真实 bug）：抖音的 mp4 自带音轨，没有独立纯音频流，因此「仅音频」模式先下载视频流再用 ffmpeg 提音轨。早期实现里视频与音频共用 `…[分辨率].mp4` 作为缓存判断目标，导致「先下视频、再下同链接音频」时，第二次下载命中第一次的视频 mp4 直接返回、跳过提音轨。现改为：视频缓存查 `.mp4`、音频缓存查已提取好的 `.mp3/.m4a`（`_existing_audio`）；音频模式把视频流下载到独立中间文件 `…[分辨率].audio.src.mp4`，提音轨后即删除，绝不覆盖/误删正式视频文件。

### 3.4 ffmpeg 定位顺序（config.py）

1. 环境变量 `FVD_FFMPEG_PATH`
2. `frontend/node_modules/@ffmpeg-installer/<平台>/ffmpeg`（前端 `npm install` 时装上）
3. 系统 PATH 中的 `ffmpeg`

仓库不内置 ffmpeg 二进制（会让 clone 体积膨胀到 60MB+，且 Windows 版对 Linux/macOS 无意义）。

### 3.5 配置项（环境变量）

`FVD_HOST`（默认 127.0.0.1）/ `FVD_PORT`（8000）/ `FVD_DOWNLOADS_DIR`（./downloads）/ `FVD_MAX_FILESIZE`（0=不限，字节）/ `FVD_FFMPEG_PATH`。

### 3.6 生产托管

`main.py` 启动时检测 `frontend/dist` 存在则挂载 `/assets` 与 `/`（StaticFiles html=True）。因此**生产模式只需 `python run.py` 一个进程**；开发模式后端 8000 + Vite dev 5173（`vite.config.js` 已配 `/api` 代理）。

## 4. 前端设计

### 4.1 设计系统（白底极简 + 品牌渐变）

- 底色为**渐变白**（`body` 上 `linear-gradient(180deg, #fff → #e6efff → #dee8ff → #f2ecff)`，`background-attachment: fixed`），主色 `#2563eb`（blue-600），渐变 `linear-gradient(135deg, #2563eb, #4f46e5)` 用于 Logo/CTA/进度条
- 文字：标题 slate-900 粗体；正文 slate-700；次要 slate-500；装饰 slate-300/400
- 卡片：`rounded-xl + ring-1 ring-slate-200/60`，悬停 `shadow-2xl` 蓝色光晕（`--tw-shadow-color: rgb(37 99 235 / .1)`）
- 字体：`PingFang SC / HarmonyOS Sans SC / MiSans / Segoe UI / system-ui`，16px 基准
- 动效：fade-up/fade-in 入场（60ms 递增 delay）、进度条纹 shimmer、CTA 悬停上浮；**尊重 `prefers-reduced-motion`**
- 可访问性：对比度 ≥4.5:1、表单错误就近提示（`role="alert"`）、radiogroup 语义、触控目标 ≥44px、输入框 `sr-only` label + aria-label

### 4.2 组件结构（frontend/src）

| 文件 | 职责 |
|---|---|
| `router.js` | 极简 hash 路由（无额外依赖）：`/` 主页、`/why` 为什么选 SnapDown、`/vip` 开通 VIP；导出 `route` ref + `navigate()` |
| `App.vue` | 状态编排：`url/info/task/taskList/selectedFormat/historyOpen` + 按路由切换视图，提交校验，下载后 1s 轮询至终态 |
| `components/SiteHeader.vue` | 白底顶栏：**纯英文 SnapDown Logo** + 「为什么选 SnapDown」（跳 `/why`）+ 「下载记录」（开抽屉）+ 「开通VIP」（橙色 `.btn-vip`，跳 `/vip`） |
| `components/HeroSection.vue` | 大标题「万能视频即刻下载」（渐变关键词）+ 副标题（智能解析…）+ 输入框（粘贴按钮/清空/错误提示）+ 平台标签 #chips（有解析结果时收起）；主按钮为**「开始解析」**（表单独有提交语义） |
| `components/ResultCard.vue` | 封面/标题/平台徽章/时长作者 → 清晰度 radiogroup（`flex-wrap` + `basis-[45%]/sm:basis-[30%]`，最后一行自动加宽铺满、不留空位；DASH 提示"自动合并音轨"）→ 下载按钮/进度条（percent+speed+eta）。**下载完成后（`isDone`）收起整个清晰度选择区**（此时它已没有对应的下载动作，留着就是死控件），改为清爽成功卡片：绿色对勾 + 「下载完成」+ 文件名 + 分辨率/体积/时长标签 + 「保存到本地」主按钮 + 「再来一个」，底色转为 `bg-emerald-50/40`；失败态为错误提示 + 重试 |
| `components/HistoryDrawer.vue` | 右侧「下载记录」抽屉（`role="dialog"` + ESC/遮罩关闭 + 锁定 body 滚动），承载 `TaskList`，保证主页不滚动 |
| `components/TaskList.vue` | 下载记录卡片网格（列表体，不含标题）：封面图（加载失败回退占位图标）、状态徽章、迷你进度条、完成可点击保存、三个元信息标签（分辨率 `height`P、体量 `filesize`、下载时间精确到分钟） |
| `components/SiteFooter.vue` | 版权声明 + 「由 Payson 独立设计与开发」个人署名（不再出现 yt-dlp/技术栈） |
| `pages/WhyPage.vue` | 「为什么选 SnapDown」介绍页：愿景 3 卡 + 核心能力 6 卡 + 方案对比表 + 使用场景 + Pro 会员预告 + FAQ + 结尾 CTA |
| `pages/VipPage.vue` | VIP 订阅页：深色金色 Hero + 权益 6 卡 + 三档套餐（月/年/终身）+ 免费 vs Pro 对比表 + 信任保障 + FAQ；点击开通弹「内测中」提示（**未接真实支付**） |
| `api.js` | fetch 封装：parseVideo / startDownload / getTask / listTasks / fileUrl，统一错误信息提取（detail） |

> UI 改版（2026，第二轮）：主页删除 FeatureStrip（原「为什么选择瞬下」区块）改为独立 `/why` 页面；
> 主 CTA 由「开始下载」改为付费导向的「开通VIP」；主页压缩为一屏不滚动，下载记录收进抽屉；
> 全站品牌名统一为 **SnapDown**（不再显示中文「瞬下」），页脚去掉开源/技术栈信息，改为个人署名。

### 4.3 关键交互约定

- URL 校验：非空 + `http(s)://` 前缀，错误显示在输入框下方
- 下载内容二选一：`视频`（默认，画面+声音）与 `仅音频`（只提取声音）。选「仅音频」时隐藏清晰度选择，
  下载按钮变为「下载 MP3 音频」；下载记录与完成卡片用紫色「音频」标签代替分辨率标签
- 下载按钮文案绑定当前选中格式（如「下载 1080P」）；`最佳画质` = format_id `"best"`
- 下载记录的标题与封面：前端在 `POST /api/download` 时回传解析结果里的 `title/thumbnail`；
  后端 `_backfill_meta()` 在 progress_hook 与下载完成时用 yt-dlp `info_dict` 兜底（保证直接用 API 调用也有记录可读）
- 轮询：`setInterval 1s`，`done/error` 后停止并刷新历史；组件卸载时清理定时器
- 「粘贴」按钮：只用 `navigator.clipboard.readText()`（现代标准）。Chrome/Edge 首次弹一次浏览器"读取剪贴板"授权，允许后永久静默；Firefox 每次弹确认（浏览器安全机制，网页无法绕过）；不支持/被拒则聚焦输入框 + 琥珀色提示手动 Ctrl+V。**不要回退 `document.execCommand('paste')`**：Chromium 会对它弹原生"粘贴(P)"确认气泡（用户必须再点一次），Firefox 也会多弹一次确认，适得其反
- 静态资源缓存（`main.py` 的 `add_cache_headers` 中间件）：`/assets/*`（Vite 内容指纹）→ `public, max-age=31536000, immutable`；入口 HTML → `no-cache, must-revalidate`。缺少它会让浏览器缓存住旧 `index.html` 与旧 bundle，出现"代码已改但页面行为没变"的假象
- **页面内跳转一律用 `scrollIntoView()`**：hash 路由下 `href="#plans"` 会被解析成路由 `/plans` 并回退渲染主页（VIP 页曾因此"点击跳回首页"）；`App.vue` 对未知 hash 做兜底清理

## 5. 测试策略

| 层级 | 文件 | 方式 |
|---|---|---|
| 单元 | `backend/tests/test_api.py` | TestClient + monkeypatch 隔离 yt-dlp，覆盖 400/404/422、任务生命周期、错误态 |
| 集成 | `backend/tests/test_integration.py` | 真实 B站（`BV1GJ411x7h7`），解析字段断言 + 最低清晰度真实下载 + 文件完整性，pytest marker `integration`（默认跳过，`-m integration` 运行） |
| 冒烟 | `frontend/scripts/smoke.mjs` | Playwright + Firefox：桌面全流程（解析→选格式→下载→完成→历史）+ iPhone 13 视口（无横向滚动）+ 零 JS/控制台错误，输出截图到 `frontend/smoke-screenshots/` |

注意：冒烟测试点击表单按钮必须用 `button[type="submit"]`（页头还有一个同文案的滚动按钮，曾导致误判）。

## 6. 部署预留

- `Dockerfile`：多阶段构建（node 构建前端 → python:3.12-slim + apt ffmpeg），`FVD_HOST=0.0.0.0`，卷挂载 downloads（未实机验证，使用前需测试）
- 局域网访问：`FVD_HOST=0.0.0.0` 启动即可；公网需域名/HTTPS/备案（国内）另行规划

## 7. 已知问题与限制

1. **YouTube/GitHub 本机不可达**（网络层），代码无问题，部署海外服务器即可
2. **抖音通道为逆向/浏览器双通道方案，平台可能改版**：`a_bogus` / secsdk 参数若失效，通道一（直连）会失效，此时靠通道二（无头浏览器桥）兜底；若连页面签名运行时也改版，需按 `douyin_browser_bridge.js` 与 `douyin_signer/` 说明重新对齐（2026-09 实测：直连已被 secsdk 拦截，实际由浏览器桥出数据）
3. 抖音走浏览器桥时单次解析约 **10–15 秒**（要启动无头浏览器并等签名运行时就绪），比直连慢；直连可用时不会触发桥
3. 播放列表明确拒绝（`noplaylist` + 解析时检测 entries 返回 400 提示）
4. 任务历史在内存中，服务重启即清空
5. yt-dlp 平台解析器有时效性（平台改版会导致失效），升级 `yt-dlp` 版本通常可修复
6. 同链接同格式重复下载会跳过（yt-dlp 不覆盖），若需强制覆盖需加 `overwrites: True`
7. 未做并发下载数与速率限制（二期会员分层时一并设计）；抖音走浏览器桥时每次调用会新起一个无头浏览器进程，并发量大会吃内存，需要时再加信号量或常驻浏览器
8. Docker 镜像（第 6 节）只装了 python+ffmpeg，**没有 Node 与浏览器**，因此容器里抖音只能走通道一；要在容器里启用浏览器桥需额外装 Node + Playwright Firefox

## 8. 未来扩展路线图与扩展点

| 功能 | 切入位置 | 备注 |
|---|---|---|
| 批量/播放列表 | downloader 去掉 `noplaylist` + tasks 支持父子任务；前端批量 URL 输入 | 注意 playlist 检测逻辑已在 parse 中 |
| 字幕下载/翻译 | parse 已返回 `subtitles`；下载时加 `writesubtitles`；翻译接 LLM | 前端 ResultCard 已显示字幕数但未使用 |
| AI 视频总结 | 新增 `/api/summary`：下载音轨 → 转写/LLM，需可配置 API Key（环境变量） | 建议独立模块 `ai.py` |
| 会员分层 | 新增中间件/装饰器做权限校验；兑换码表（先文件后 DB） | 需求文档：首版明确不做，做前重新确认 |
| 持久化 | tasks.py 的 TaskManager 换成 sqlite/sqlalchemy | 字段结构已稳定可直接迁移 |
| 部署 | Dockerfile 验证 + 反代（nginx/caddy）+ HTTPS | — |

## 9. 本机环境特殊处理（沙箱适配，正常环境可忽略）

本项目是在受限沙箱中开发的，以下适配已固化在代码/文件里，**在用户自己的正常终端环境无需这些操作**：

1. `.venv/Lib/site-packages/sitecustomize.py`：替换 `tempfile.mkdtemp` 为 `os.makedirs` 实现（沙箱拒绝写入 mkdtemp 创建的子目录，曾导致 pip 安装失败）。**注意**：重建 venv 后此文件会丢失，需重新放置
2. npm 需设置 `npm_config_cache=<root>/.npm-cache`（沙箱禁止写用户级 npm 缓存）
3. pip 需设置 `TMP/TEMP=<root>/.tmp` 与 `--cache-dir <root>/.pip-cache`
4. Vite 构建、Playwright 启动浏览器需要子进程管道（沙箱默认拒绝，需升级权限执行）
5. Playwright 浏览器位于 `<root>/.playwright-browsers/`（Firefox-1543 + winldd-1007，手动下载解压 + `INSTALLATION_COMPLETE` 标记）；运行冒烟测试需设置 `PLAYWRIGHT_BROWSERS_PATH`
6. 项目 venv 基于用户安装的 Python（`py -3`，3.14.x）创建于 `<root>/.venv`

## 10. 常用命令速查

```powershell
# 启动生产模式（托管前端构建产物）
python run.py                                  # 或 .\.venv\Scripts\python run.py

# 前端开发/构建
cd frontend; npm run dev                       # 5173，/api 代理到 8000
npm run build                                  # 产出 dist/，由后端托管

# 测试
.\.venv\Scripts\python -m pytest backend                          # 单元（离线）
.\.venv\Scripts\python -m pytest backend\tests\test_integration.py -m integration -v
node frontend\scripts\smoke.mjs                 # 需先启动服务（冒烟测试）
```
