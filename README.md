# 瞬下 SnapDown · 万能视频下载

[![CI](https://github.com/paysonx/SnapDown/actions/workflows/ci.yml/badge.svg)](https://github.com/paysonx/SnapDown/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-20+-green.svg)](https://nodejs.org/)

粘贴链接，即刻下载。支持 B站、抖音、YouTube、小红书等 **1000+ 平台**，默认视频+音频一起下载，也可一键**仅提取音频（MP3）**，自由选择清晰度，实时进度显示，手机电脑都能用。

> ⚠️ 仅供个人学习与备份使用，请尊重原作者版权，下载内容请勿用于商业用途或二次传播。

## 📚 项目文档

| 文档 | 内容 |
|---|---|
| [CONTRIBUTING.md](CONTRIBUTING.md) | **想贡献代码请先读这里**：开发环境、提交规范，以及不会被接受的改动 |
| [docs/requirements.md](docs/requirements.md) | 需求基线：原始需求、已确认决策、设计语言、二期候选功能 |
| [docs/design.md](docs/design.md) | 方案设计：架构、API 契约、实现要点、测试策略、扩展路线图 |
| [docs/tech-stack.md](docs/tech-stack.md) | 技术选型逐项说明、踩坑记录、经验教训 |
| [AGENTS.md](AGENTS.md) | AI 协作入口：关键事实、沙箱注意、常用命令速查 |

## 技术栈

| 层 | 技术 |
|---|---|
| 下载核心 | [yt-dlp](https://github.com/yt-dlp/yt-dlp)（PyPI 包，直接 Python 库封装） |
| 后端 | Python FastAPI（异步、轻量、无数据库） |
| 前端 | Vue 3 + Vite + Tailwind CSS（工程化构建） |
| 音视频合并 | ffmpeg（由 npm 包 `@ffmpeg-installer/ffmpeg` 按平台安装，**无需手动安装**） |

## 目录结构

```
free-video-download/
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI 路由 + 静态托管
│   │   ├── downloader.py  # yt-dlp 封装（解析/下载/进度钩子）
│   │   ├── douyin.py      # 抖音专用通道（游客身份 + a_bogus 签名 + 直链下载，无需用户 Cookie）
│   │   ├── douyin_signer/ # 纯 Python a_bogus 签名器（Apache-2.0，来源见包内说明）
│   │   ├── tasks.py       # 内存任务队列
│   │   └── config.py      # 配置与 ffmpeg 定位
│   ├── tests/             # 单元测试 + B站集成测试
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   ├── src/               # Vue 组件（Hero/结果卡片/历史/页脚）
│   ├── scripts/smoke.mjs  # Playwright 冒烟测试
│   └── vite.config.js     # 开发代理 /api → 8000
├── downloads/             # 下载文件保存目录
├── run.py                 # 启动入口（同时托管前端构建产物）
└── Dockerfile             # 部署预留
```

> ffmpeg **不在仓库里**——仓库分发二进制会让 clone 体积膨胀到 60MB+，且 Windows 版对 Linux/macOS 用户毫无意义。前端 `npm install` 时会通过 `@ffmpeg-installer/ffmpeg` 装上当前平台的静态二进制，定位逻辑见 `backend/app/config.py` 的 `find_ffmpeg()`。

## 快速开始（Windows）

环境要求：Python 3.12+、Node.js 20+（**无需自行安装 ffmpeg**）。

```powershell
# 1. 创建虚拟环境并安装依赖
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt -r backend\requirements-dev.txt

# 2. 构建前端（一次性；之后无需重复）
#    npm install 会顺带装好 ffmpeg 静态二进制
cd frontend
npm install
npm run build
cd ..

# 3. 启动服务
.\.venv\Scripts\python run.py
```

打开 http://127.0.0.1:8000 即可使用。

<details>
<summary>macOS / Linux</summary>

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt
cd frontend && npm install && npm run build && cd ..
./.venv/bin/python run.py
```
</details>

## 开发模式（前后端热更新）

```powershell
# 终端 1：后端
.\.venv\Scripts\python run.py

# 终端 2：前端 Vite dev server（已配置 /api 代理）
cd frontend
npm run dev        # http://localhost:5173
```

## 测试

```powershell
# 单元测试（离线）
.\.venv\Scripts\python -m pytest backend

# 集成测试（真实网络：B站解析 + 真实下载）
.\.venv\Scripts\python -m pytest backend\tests\test_integration.py -m integration -v

# 前端冒烟测试（需先启动服务，Playwright 自动驱动 Firefox）
cd frontend
node scripts\smoke.mjs
```

## 参与贡献

欢迎提 issue 和 PR，动手前请先读 [CONTRIBUTING.md](CONTRIBUTING.md) —— 里面写清了本项目的一条硬边界：**不碰 DRM 破解**，也不接受引入数据库 / 登录鉴权这类破坏「零数据库、零登录」架构的改动。

## 配置（环境变量）

| 变量 | 默认值 | 说明 |
|---|---|---|
| `FVD_HOST` / `FVD_PORT` | `127.0.0.1` / `8000` | 监听地址（局域网访问可设 `0.0.0.0`） |
| `FVD_DOWNLOADS_DIR` | `./downloads` | 下载保存目录 |
| `FVD_MAX_FILESIZE` | `0`（不限） | 单文件大小上限（字节） |
| `FVD_FFMPEG_PATH` | 自动探测 | 自定义 ffmpeg 路径（优先级最高） |

ffmpeg 定位优先级：`FVD_FFMPEG_PATH` → `frontend/node_modules/@ffmpeg-installer/` 静态二进制 → 系统 PATH。

## API 概览

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/parse` | 解析视频：`{url}` → 标题/封面/时长/清晰度列表 |
| POST | `/api/download` | 创建下载任务：`{url, format_id, mode}`，`mode=video`（默认）或 `audio` → 任务对象 |
| GET | `/api/tasks/{id}` | 查询任务进度（前端 1s 轮询） |
| GET | `/api/tasks` | 历史任务列表 |
| GET | `/api/files/{id}` | 下载完成文件 |
| GET | `/api/health` | 健康检查 |

## 免责声明

本项目基于开源工具 yt-dlp 构建，不包含任何 DRM 破解能力。请仅在遵守目标平台服务条款与当地法律、且获得内容授权的情况下使用。
