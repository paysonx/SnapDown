# AI 协作指南（AGENTS.md）

本项目是**「瞬下 SnapDown」万能视频下载网站**：Python FastAPI 后端直接封装 yt-dlp，前端 Vue 3 + Vite + Tailwind，MVP 已交付并全部测试通过。

## 开始工作前必读

- [`docs/requirements.md`](docs/requirements.md) —— 需求基线：用户原始需求、**已经用户确认的决策**（前端 Vue3+Tailwind、首版不做会员、MVP 范围、本地部署优先）、参考站 UI 研究结论、二期候选功能
- [`docs/design.md`](docs/design.md) —— 方案设计：架构、API 契约、yt-dlp 封装要点（含 format 选择器的历史 bug）、前端组件职责、测试策略、**本机沙箱特殊处理**（第 9 节）、扩展路线图（第 8 节）

## 关键事实

- 后端入口 `run.py`；生产模式单进程同时托管 `frontend/dist`（先 `npm run build`）
- venv 在 `<root>/.venv`（基于用户安装的 Python 3.14，`py -3`）；若重建 venv 需恢复 `sitecustomize.py`（见设计文档 9.1）
- 下载文件保存在 `<root>/downloads/`，内存任务表上限 100 条（无数据库，勿引入不必要的持久化，除非用户要求）
- ffmpeg 由前端 `npm install` 经 `@ffmpeg-installer/ffmpeg` 装到 `frontend/node_modules/`，定位逻辑在 `backend/app/config.py:find_ffmpeg()`（环境变量 → node_modules → 系统 PATH）；**仓库不分发 ffmpeg 二进制**，改完前端依赖需重跑 `npm install`
- 修改后端后需重启 `run.py`；修改前端需重新 `npm run build`
- 真实下载测试用 B站 `BV1GJ411x7h7`（yt-dlp 官方测试视频）；本机 YouTube/GitHub 不可达
- 抖音走独立通道 `backend/app/douyin.py`，两级降级：①纯 Python 直连（游客 `s_v_web_id`/`ttwid` + 纯 Python `a_bogus` 签名，**无需用户 Cookie**）→ ②被风控拒绝时回退无头浏览器桥 `backend/app/douyin_browser_bridge.js`（Node + Playwright + 内置 Firefox，由页面自带签名运行时代取详情接口）。桥依赖 `frontend/node_modules/playwright`（已在 package.json 声明）与 `.playwright-browsers/`。真实测试视频 `https://www.douyin.com/video/7682707061592088049`（解析链接时注意 `/user/...?modal_id=<id>` 也是有效形态）；抖音图文/私密/已删除会报错
- 合规底线：不碰 DRM 破解，页面保留版权提示

## 终端约定（用户明确要求，务必遵守）

- **所有代码/命令一律在本机 Git Bash 里执行，禁止使用 Windows PowerShell。**
- 解释器路径：`C:\Program Files\Git\bin\bash.exe`；项目根在本环境映射为 `/c/Users/32017/Desktop/free-video-download`。
- 若只能通过 DSH 的 `pwsh` 工具发起（本会话即如此），则用它中转调用 Git Bash：
  `& "C:\Program Files\Git\bin\bash.exe" -lc "<命令>"`
- **沙箱限制（实测）**：Cygwin 启动必须创建命名管道，受限沙箱模式下必然失败 —— 只读模式报 `CreateFileMapping ... Win32 error 5`，`workspace-write` 报 `couldn't create signal pipe, Win32 error 5`，**只有 `danger-full-access` 能正常启动**。所以经 Git Bash 执行每条命令都需要一次授权。
- 路径一律用正斜杠。`python` 在 Git Bash 里会命中 Microsoft Store 占位别名（报 "Python was not found"），**必须显式写 `./.venv/Scripts/python.exe`**。
- 外层 PowerShell 字符串中引用 bash 变量要转义成 `\$VAR`；避免在外层出现 `$(...)`，防止被外层解析而报 `unexpected EOF while looking for matching ')'`。

## 本机沙箱注意（若在此环境运行）

npm 设 `npm_config_cache`、pip 设 `TMP/TEMP` 到工作区、Vite 构建与 Playwright 冒烟测试需升级权限执行；Playwright 浏览器已内置在 `.playwright-browsers/`。详见设计文档第 9 节。

## 本机网络（实测 2026-10）

- **GitHub 需要走本地代理**：直连 `github.com:443` TCP 不通（DNS 正常，解析到 20.205.243.166），但 `github.com:80`、`ssh.github.com:443`、`api.github.com:443` 均可达。本机 xray 在 `127.0.0.1:10808` 提供 HTTP 代理，已对该仓库执行 `git config --local http.proxy/https.proxy`（仅写入 `.git/config`，不进版本库）。**xray 未运行时所有 git 远程操作都会超时。**
- **YouTube 不可达**（同 AGENTS.md 原有记录）；npm、pip、B站、抖音均正常。

## 常用命令（Git Bash）

```bash
./.venv/Scripts/python.exe run.py                     # 启动服务 → http://127.0.0.1:8000
./.venv/Scripts/python.exe -m pytest backend           # 单元测试（离线）
./.venv/Scripts/python.exe -m pytest backend/tests/test_integration.py -m integration -v   # B站真实下载测试
node frontend/scripts/smoke.mjs                        # 前端冒烟测试（需服务已启动）
```
