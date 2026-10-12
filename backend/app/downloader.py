"""yt-dlp 封装：视频解析与下载。

设计原则：直接使用 yt-dlp 的 Python 库（不做命令行调用），
仅做两层薄封装：解析出前端需要的信息、下载时通过 progress_hooks 更新任务进度。
"""
import threading
import time
from pathlib import Path
from typing import Optional

import yt_dlp

from . import douyin
from .config import DOWNLOADS_DIR, MAX_FILESIZE, find_ffmpeg
from .tasks import Task, tasks


class PlaylistNotSupported(Exception):
    """播放列表链接暂不支持（MVP 只处理单个视频）。"""


class ParseError(Exception):
    """解析失败（链接无效 / 平台不支持 / 网络问题等）。"""


def _base_opts() -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 30,
    }
    ffmpeg = find_ffmpeg()
    if ffmpeg:
        opts["ffmpeg_location"] = ffmpeg
    if MAX_FILESIZE > 0:
        opts["max_filesize"] = MAX_FILESIZE
    return opts


def _human_speed(bps: Optional[float]) -> str:
    if not bps:
        return ""
    if bps >= 1024 * 1024:
        return f"{bps / 1024 / 1024:.1f} MB/s"
    return f"{bps / 1024:.0f} KB/s"


def _human_eta(seconds: Optional[float]) -> str:
    if seconds is None:
        return ""
    seconds = int(seconds)
    if seconds >= 3600:
        return f"{seconds // 3600}小时{(seconds % 3600) // 60}分"
    if seconds >= 60:
        return f"{seconds // 60}分{seconds % 60}秒"
    return f"{seconds}秒"


def _human_duration(seconds: Optional[float]) -> str:
    if not seconds:
        return ""
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _normalize_thumbnail(url: Optional[str]) -> str:
    """统一封面地址：补全协议相对地址（//host/x.jpg），拒绝非 http(s) 值。"""
    if not url:
        return ""
    url = url.strip()
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith(("http://", "https://")):
        return url
    return ""


def parse_video(url: str) -> dict:
    """解析视频元信息与可用清晰度，不下载任何内容。"""
    if douyin.is_douyin(url):
        try:
            return douyin.parse_douyin(url)
        except douyin.DouyinError as exc:
            raise ParseError(str(exc)) from exc

    opts = _base_opts()
    opts["skip_download"] = True
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        raise ParseError(str(exc)) from exc

    if info is None:
        raise ParseError("无法解析该链接，请检查链接是否正确")

    # 播放列表检测
    if info.get("_type") == "playlist" or info.get("entries"):
        raise PlaylistNotSupported("暂不支持播放列表，请粘贴单个视频链接")

    formats = _build_format_list(info.get("formats") or [], duration=info.get("duration"))
    subtitles = _build_subtitle_list(info)

    return {
        "title": info.get("title") or "未知标题",
        "thumbnail": _normalize_thumbnail(info.get("thumbnail")),
        "duration": _human_duration(info.get("duration")),
        "uploader": info.get("uploader") or info.get("channel") or "",
        "webpage_url": info.get("webpage_url") or url,
        "extractor": info.get("extractor_key") or "",
        "formats": formats,
        "subtitles": subtitles,
    }


def _format_rank(f: dict) -> tuple:
    """同分辨率下比较格式优先级，tuple 比较，越小越优先。

    1. m3u8_native（HLS 切片）最差：切成大量小片段逐个请求，并发度低，
       下完还要 ffmpeg 拼接，实测比同分辨率的 DASH 直连流慢一个数量级。
    2. 其次带音轨的渐进式格式：video+audio 一条流搞定，省掉一次合并。
       （YouTube 从 1080p 起强制 DASH，所以这条只对 720p 及以下生效）
    3. 最后按码率降序。

    注意不能只按 tbr 排序——m3u8_native 的 tbr 往往标得比同分辨率的
    DASH 直连流还高（1080p 下 m3u8 约 4.5M vs itag 137 约 4.4M）。
    """
    protocol = (f.get("protocol") or "").lower()
    is_hls = 1 if "m3u8" in protocol else 0
    no_audio = 0 if (f.get("acodec") or "none") != "none" else 1
    return (is_hls, no_audio, -(f.get("tbr") or 0))


def _build_format_list(raw_formats: list, duration: Optional[float]) -> list[dict]:
    """整理视频格式列表：仅保留有画面的格式，按分辨率去重排序。

    同分辨率下取 _format_rank 最优的那个，而不是原始列表里最先出现的那个——
    yt-dlp 会把 m3u8_native 排在 formats 前面，先到先得会一直选到它。
    """
    best_by_height: dict[int, dict] = {}
    for f in raw_formats:
        height = f.get("height") or 0
        vcodec = f.get("vcodec") or "none"
        if height <= 0 or vcodec == "none":
            continue
        current = best_by_height.get(height)
        if current is None or _format_rank(f) < _format_rank(current):
            best_by_height[height] = f

    result = []
    for height, f in best_by_height.items():
        filesize = f.get("filesize") or f.get("filesize_approx")
        if not filesize and f.get("tbr") and duration:
            filesize = int(f["tbr"] * 1024 / 8 * duration)
        result.append({
            "format_id": f.get("format_id", ""),
            "ext": f.get("ext", ""),
            "height": height,
            "width": f.get("width") or 0,
            "fps": f.get("fps") or 0,
            "vcodec": (f.get("vcodec") or "none").split(".")[0],
            "acodec": (f.get("acodec") or "none").split(".")[0],
            "filesize": filesize or None,
            "note": f.get("format_note") or "",
        })
    result.sort(key=lambda x: x["height"], reverse=True)
    return result


def _build_subtitle_list(info: dict) -> list[dict]:
    """合并手动字幕与自动字幕，返回语言列表。"""
    subs = {}
    for key in ("subtitles", "automatic_captions"):
        for lang, items in (info.get(key) or {}).items():
            if items:
                subs[lang] = subs.get(lang, []) or items[0].get("ext") or "vtt"
    return [{"lang": lang, "ext": ext} for lang, ext in subs.items()]


def _backfill_meta(task: Task, info: Optional[dict]) -> None:
    """用 yt-dlp 返回的信息补齐任务标题、封面与分辨率（前端未回传时兜底）。"""
    if not info:
        return
    updates = {}
    title = task.title or (info.get("title") or "")
    thumbnail = task.thumbnail or _normalize_thumbnail(info.get("thumbnail"))
    height = task.height or (info.get("height") or 0)
    if title != task.title:
        updates["title"] = title
    if thumbnail != task.thumbnail:
        updates["thumbnail"] = thumbnail
    if height != task.height:
        updates["height"] = height
    if updates:
        tasks.update(task, **updates)


def _outtmpl() -> str:
    """输出文件名模板：标题 + 视频 id + 清晰度 format_id。

    关键点：必须带上 `%(format_id)s`。同一视频选择不同清晰度时，yt-dlp 解析出的
    format_id 不同（如 1080P=`100026+30280`、360P=`30016+30280`）；若不带它，
    所有清晰度都会落到同一个 `标题 [id].mp4`，第二次下载会因"文件已存在"被 yt-dlp
    跳过，从而复用上一次（错误分辨率）的文件。
    """
    return str(DOWNLOADS_DIR / "%(title).120B [%(id)s] [%(format_id)s].%(ext)s")


def start_download(task: Task) -> None:
    """在后台线程中执行下载，通过 progress_hooks 持续更新任务状态。"""
    if douyin.is_douyin(task.url):
        douyin.start_douyin_download(task)
        return
    thread = threading.Thread(target=_run_download, args=(task,), daemon=True)
    thread.start()


def _run_download(task: Task) -> None:
    tasks.update(task, status="downloading", percent=0.0)

    def progress_hook(d: dict) -> None:
        # 下载过程中即可拿到 info_dict，用来尽早补齐标题与封面
        _backfill_meta(task, d.get("info_dict"))
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            if total:
                percent = d.get("downloaded_bytes", 0) / total * 100
            else:
                percent = 0.0
            tasks.update(task, status="downloading", percent=percent,
                         speed=_human_speed(d.get("speed")), eta=_human_eta(d.get("eta")))
        elif status == "finished":
            tasks.update(task, percent=100.0, speed="", eta="")

    fmt = task.format_id
    if task.mode == "audio":
        # 仅音频：只下载最佳音轨，不下载画面。之后（有 ffmpeg 时）统一转成 MP3。
        format_sel = "bestaudio/best"
    elif fmt == "best":
        # 最佳画质 = 最佳视频流 + 最佳音频流（自动合并），无 ffmpeg 时回退到最佳合并流。
        # 音频优先选 m4a：这样最终容器尽量是 mp4（兼容性最好）。
        format_sel = "bestvideo+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
    else:
        # 优先合并所选视频流 + 最佳音频流；合并失败则回退到该格式本身。
        # 音频优先选 m4a，理由同上（YouTube 的 bestaudio 常命中 opus/webm，强制 mp4 会失败）。
        format_sel = f"{fmt}+bestaudio[ext=m4a]/{fmt}+bestaudio/{fmt}/best"

    opts = _base_opts()
    opts.update({
        "format": format_sel,
        "outtmpl": _outtmpl(),
        "progress_hooks": [progress_hook],
        "noprogress": True,
    })
    if task.mode == "audio":
        if opts.get("ffmpeg_location"):
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
    else:
        # 只把 mp4 当“偏好”而非硬性要求：yt-dlp 会按音视频编码自动挑容器，
        # 遇到 opus/webm 这类 mp4 装不下的音轨时回退到 mkv，而不是合并失败。
        opts["merge_output_format"] = "mp4/mkv"

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(task.url, download=True)
        _backfill_meta(task, info)
        filepath = _final_filepath(info, ydl)
        filesize = filepath.stat().st_size if (filepath and filepath.is_file()) else 0
        tasks.update(task, status="done", percent=100.0,
                     filepath=str(filepath) if filepath else None,
                     filename=filepath.name if filepath else "",
                     filesize=filesize,
                     finished_at=time.time())
    except Exception as exc:  # noqa: BLE001 —— 统一转成任务错误状态
        message = str(exc)
        tasks.update(task, status="error", error=message[:500],
                     finished_at=time.time())


def _final_filepath(info: dict, ydl: yt_dlp.YoutubeDL) -> Optional[Path]:
    """取下载完成后的最终文件路径（合并/转码后）。"""
    requested = info.get("requested_downloads") or []
    if requested:
        path = requested[0].get("filepath")
        if path:
            return Path(path)
    prepared = ydl.prepare_filename(info)
    return Path(prepared)
