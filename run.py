"""开发/生产通用启动入口。

用法：
    python run.py              # 启动后端（同时托管 frontend/dist，若已构建）
"""
import uvicorn

from backend.app import config
from backend.app.main import app

if __name__ == "__main__":
    print(f"[SnapDown] 服务地址: http://{config.HOST}:{config.PORT}")
    print(f"[SnapDown] 下载目录: {config.DOWNLOADS_DIR}")
    uvicorn.run(app, host=config.HOST, port=config.PORT)
