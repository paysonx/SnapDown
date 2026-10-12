"""全局配置：路径、ffmpeg 定位、下载参数。"""
import os
import platform
import shutil
import sys
from pathlib import Path

# 项目根目录 = backend/app/config.py 的上三级
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# 下载文件保存目录
DOWNLOADS_DIR = Path(os.environ.get("FVD_DOWNLOADS_DIR", ROOT_DIR / "downloads"))
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

# 前端构建产物目录（存在时由 FastAPI 托管）
FRONTEND_DIST = Path(os.environ.get("FVD_FRONTEND_DIST", ROOT_DIR / "frontend" / "dist"))

# 服务监听地址
HOST = os.environ.get("FVD_HOST", "127.0.0.1")
PORT = int(os.environ.get("FVD_PORT", "8000"))

# 单个视频解析/下载的最大体积上限（字节），0 表示不限制
MAX_FILESIZE = int(os.environ.get("FVD_MAX_FILESIZE", "0"))

# 前端目录（抖音浏览器桥复用其 node_modules 里的 playwright）
FRONTEND_DIR = Path(os.environ.get("FVD_FRONTEND_DIR", ROOT_DIR / "frontend"))

# Playwright 浏览器目录（本机沙箱把浏览器内置在项目内；正常环境留空走默认路径）
PLAYWRIGHT_BROWSERS_PATH = os.environ.get(
    "PLAYWRIGHT_BROWSERS_PATH", str(ROOT_DIR / ".playwright-browsers"))

# 抖音浏览器桥脚本（直连详情接口被风控拒绝时的兜底通道）
DOUYIN_BRIDGE_SCRIPT = Path(__file__).resolve().parent / "douyin_browser_bridge.js"


def _find_npm_ffmpeg() -> str | None:
    """在 frontend/node_modules 的 @ffmpeg-installer 系列包中寻找 ffmpeg。

    前端 `npm install` 时会通过 @ffmpeg-installer/ffmpeg 装上当前平台的静态二进制，
    按平台包名排序保证 darwin-arm64 优先于 darwin-x64、当前架构优先于通用包。
    """
    pkg_root = FRONTEND_DIR / "node_modules" / "@ffmpeg-installer"
    if not pkg_root.is_dir():
        return None

    platform_keys = (sys.platform, platform.machine())
    candidates: list[tuple[str, Path]] = []
    for pkg_dir in pkg_root.iterdir():
        if not pkg_dir.is_dir():
            continue
        for name in ("ffmpeg.exe", "ffmpeg"):
            exe = pkg_dir / name
            if exe.is_file():
                # 包名形如 win32-x64 / darwin-arm64 / linux-x64，关键词命中越多越优先
                score = sum(1 for key in platform_keys
                            if key and key.lower() in pkg_dir.name.lower())
                candidates.append((pkg_dir.name, exe))
                break

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return str(candidates[0][1])


def find_ffmpeg() -> str | None:
    """按优先级寻找 ffmpeg 可执行文件。

    1. 环境变量 FVD_FFMPEG_PATH
    2. frontend/node_modules 中的 @ffmpeg-installer 静态二进制（前端 npm install 时装上）
    3. 系统 PATH 中的 ffmpeg

    项目不再内置 ffmpeg 二进制：仓库里放二进制会让 clone 体积膨胀到 60MB+，
    且 Windows 版对 Linux/macOS 用户无意义。
    """
    env_path = os.environ.get("FVD_FFMPEG_PATH")
    if env_path and Path(env_path).is_file():
        return env_path

    npm_ffmpeg = _find_npm_ffmpeg()
    if npm_ffmpeg:
        return npm_ffmpeg

    system = shutil.which("ffmpeg")
    return system


def find_node() -> str | None:
    """定位 Node.js 可执行文件（抖音浏览器桥需要它跑 Playwright）。"""
    env_path = os.environ.get("FVD_NODE_PATH")
    if env_path and Path(env_path).is_file():
        return env_path
    return shutil.which("node")
