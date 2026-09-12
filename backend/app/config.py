"""全局配置：路径、ffmpeg 定位、下载参数。"""
import os
import shutil
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


def find_ffmpeg() -> str | None:
    """按优先级寻找 ffmpeg 可执行文件。

    1. 环境变量 FVD_FFMPEG_PATH
    2. 随项目安装的 @ffmpeg-installer/ffmpeg（node_modules 中的静态二进制）
    3. 系统 PATH 中的 ffmpeg
    """
    env_path = os.environ.get("FVD_FFMPEG_PATH")
    if env_path and Path(env_path).is_file():
        return env_path

    bundled = ROOT_DIR / "tools" / "ffmpeg" / "ffmpeg.exe"
    if bundled.is_file():
        return str(bundled)

    system = shutil.which("ffmpeg")
    return system
