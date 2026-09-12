"""内存任务管理：无数据库，进程内保存下载任务状态与历史。"""
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Optional

# 历史任务最多保留数量
MAX_TASKS = 100


@dataclass
class Task:
    id: str
    url: str
    format_id: str
    mode: str = "video"     # video=视频+音频一起下载；audio=仅提取音频
    title: str = ""
    thumbnail: str = ""
    status: str = "pending"  # pending | downloading | done | error
    percent: float = 0.0
    speed: str = ""
    eta: str = ""
    filepath: Optional[str] = None
    filename: Optional[str] = None
    height: int = 0          # 分辨率高度（像素），0 表示未知
    filesize: int = 0        # 文件体积（字节），0 表示未知
    error: str = ""
    created_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "url": self.url,
            "format_id": self.format_id,
            "mode": self.mode,
            "title": self.title,
            "thumbnail": self.thumbnail,
            "status": self.status,
            "percent": round(self.percent, 1),
            "speed": self.speed,
            "eta": self.eta,
            "filepath": self.filepath,
            "filename": self.filename,
            "height": self.height,
            "filesize": self.filesize,
            "error": self.error,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
        }


class TaskManager:
    def __init__(self) -> None:
        self._tasks: "OrderedDict[str, Task]" = OrderedDict()
        self._lock = threading.Lock()

    def create(self, url: str, format_id: str, title: str = "", thumbnail: str = "",
               mode: str = "video") -> Task:
        task = Task(id=uuid.uuid4().hex[:12], url=url, format_id=format_id,
                    mode=mode, title=title, thumbnail=thumbnail)
        with self._lock:
            self._tasks[task.id] = task
            while len(self._tasks) > MAX_TASKS:
                self._tasks.popitem(last=False)
        return task

    def get(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def list(self) -> list[dict]:
        with self._lock:
            items = list(self._tasks.values())
        items.sort(key=lambda t: t.created_at, reverse=True)
        return [t.to_dict() for t in items]

    def update(self, task: Task, **fields) -> None:
        for key, value in fields.items():
            setattr(task, key, value)


tasks = TaskManager()
