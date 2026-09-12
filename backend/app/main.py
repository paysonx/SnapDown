"""万能视频下载网站 —— FastAPI 主应用。"""
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, downloader
from .tasks import Task, tasks

app = FastAPI(title="FlashDown 万能视频下载", version="0.1.0")

# 开发模式允许 Vite dev server 跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    """静态资源缓存策略。

    - `/assets/*` 带内容指纹，可长期强缓存；
    - 入口 HTML 与其它文件必须每次回源校验（`no-cache`），否则用户会一直跑在旧构建上
      —— 重新构建后旧 bundle 已被 Vite 清理，浏览器缓存里的旧页面却仍能运行
      （曾导致"代码已改但页面行为没变"的排查困难）。
    """
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/api/"):
        return response
    if path.startswith("/assets/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    else:
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


class ParseRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    format_id: str = "best"
    # 下载模式：video=视频+音频（默认）；audio=仅提取音频
    mode: Literal["video", "audio"] = "video"
    # 可选：前端解析结果回传，用于下载记录展示标题与封面
    title: str = ""
    thumbnail: str = ""


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": "flashdown"}


@app.post("/api/parse")
def api_parse(req: ParseRequest) -> dict:
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="链接不能为空")
    try:
        return downloader.parse_video(url)
    except downloader.PlaylistNotSupported as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except downloader.ParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/download")
def api_download(req: DownloadRequest) -> dict:
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="链接不能为空")
    task = tasks.create(url=url, format_id=req.format_id, mode=req.mode,
                        title=req.title.strip(), thumbnail=req.thumbnail.strip())
    downloader.start_download(task)
    return task.to_dict()


@app.get("/api/tasks/{task_id}")
def api_task(task_id: str) -> dict:
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task.to_dict()


@app.get("/api/tasks")
def api_tasks() -> list[dict]:
    return tasks.list()


@app.get("/api/files/{task_id}")
def api_file(task_id: str) -> FileResponse:
    task: Task | None = tasks.get(task_id)
    if task is None or not task.filepath:
        raise HTTPException(status_code=404, detail="文件不存在或尚未下载完成")
    path = Path(task.filepath)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="文件已被清理")
    return FileResponse(path, filename=path.name, media_type="application/octet-stream")


# 生产模式：托管前端构建产物（存在 dist 时生效）
if config.FRONTEND_DIST.is_dir():
    assets = config.FRONTEND_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIST, html=True), name="frontend")
