"""抖音专用解析与下载通道。

为什么需要独立于 yt-dlp 的通道：
    yt-dlp 的 Douyin 解析器调用 `www.douyin.com/aweme/v1/web/aweme/detail/`
    时既不带 `a_bogus` 签名，也不带游客身份 cookie（`s_v_web_id` / `ttwid`），
    因此抖音风控返回空 JSON，yt-dlp 只能报：
        ERROR: [Douyin] ...: Fresh cookies (not necessarily logged in) are needed

该报错里的 "cookies" 并不要求用户登录，而是一份**游客设备身份**。本模块在
服务端自动完成三件事，用户全程无感、无需提供任何 Cookie：
    1. 生成/注册游客身份：`s_v_web_id`（本地生成）+ `ttwid`（抖音官方注册接口）
    2. 用内置的纯 Python `a_bogus` 签名器给详情接口签名
    3. 解析出无水印 CDN 直链后直接流式下载

签名器来源：`backend/app/douyin_signer/`（Apache-2.0，见包内说明）。
"""
import json
import random
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

import httpx

from .config import DOWNLOADS_DIR, find_ffmpeg
from .douyin_signer import ABogus, DEFAULT_BROWSER_INFO
from .tasks import Task, tasks

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

DETAIL_API = "https://www.douyin.com/aweme/v1/web/aweme/detail/"
TTWID_API = "https://ttwid.bytedance.com/ttwid/union/register/"

_DOUYIN_HOSTS = ("douyin.com", "iesdouyin.com", "amemv.com")
_URL_RE = re.compile(r"/(?:video|note|share/video)/(\d+)", re.I)

# ttwid 游客身份缓存（注册接口会下发长期有效的值，没必要每次请求都重新注册）
_ttwid_cache: dict[str, object] = {}
_ttwid_lock = threading.Lock()


class DouyinError(Exception):
    """抖音通道内部错误。"""


def is_douyin(url: str) -> bool:
    """判断链接是否属于抖音。"""
    host = _host_of(url)
    return any(host == h or host.endswith("." + h) for h in _DOUYIN_HOSTS)


def _host_of(url: str) -> str:
    return (url.split("://", 1)[1] if "://" in url else url).split("/", 1)[0].split("?", 1)[0].lower()


def _extract_id_from_url(url: str) -> Optional[str]:
    m = _URL_RE.search(url)
    return m.group(1) if m else None


def _resolve_aweme_id(url: str) -> str:
    """从抖音各种链接中解析 aweme_id；短链会跟随跳转。"""
    aweme_id = _extract_id_from_url(url)
    if aweme_id:
        return aweme_id

    try:
        with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": UA}) as client:
            with client.stream("GET", url) as resp:
                final_url = str(resp.url)
    except httpx.HTTPError as exc:
        raise DouyinError(f"无法打开抖音短链接：{exc}") from exc

    aweme_id = _extract_id_from_url(final_url)
    if not aweme_id:
        raise DouyinError("无法从抖音链接中解析出视频 ID，请粘贴完整的视频链接")
    return aweme_id


def _gen_s_v_web_id() -> str:
    """本地生成 s_v_web_id（与抖音 verifyFp 同构，非登录态）。"""
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    ms = round(time.time() * 1000)
    digits: list[str] = []
    while ms > 0:
        rem = ms % 36
        digits.append(str(rem) if rem < 10 else chr(ord("a") + rem - 10))
        ms //= 36
    base36 = "".join(reversed(digits)) or "0"

    tail: list[str] = [""] * 36
    for i in (8, 13, 18, 23):
        tail[i] = "_"
    tail[14] = "4"
    for i in range(36):
        if tail[i]:
            continue
        n = int(random.random() * len(alphabet))
        if i == 19:
            n = 3 & n | 8
        tail[i] = alphabet[n]
    return "verify_" + base36 + "_" + "".join(tail)


def _gen_fake_ms_token() -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-"
    return "".join(random.choice(alphabet) for _ in range(126)) + "=="


def _get_ttwid() -> str:
    """从抖音官方接口注册游客 ttwid，失败则返回空串（不阻塞解析）。"""
    now = time.time()
    cached = _ttwid_cache.get("value")
    cached_at = _ttwid_cache.get("ts") or 0
    if isinstance(cached, str) and now - cached_at < 12 * 3600:
        return cached

    with _ttwid_lock:
        cached = _ttwid_cache.get("value")
        cached_at = _ttwid_cache.get("ts") or 0
        if isinstance(cached, str) and now - cached_at < 12 * 3600:
            return cached
        body = json.dumps({
            "region": "cn",
            "aid": 1768,
            "needFid": False,
            "service": "www.ixigua.com",
            "migrate_info": {"ticket": "", "source": "node"},
            "cbUrlProtocol": "https",
            "union": True,
        })
        try:
            resp = httpx.post(TTWID_API, content=body,
                              headers={"Content-Type": "text/plain"}, timeout=15)
            ttwid = resp.cookies.get("ttwid")
            if ttwid:
                _ttwid_cache["value"] = ttwid
                _ttwid_cache["ts"] = time.time()
                return ttwid
        except httpx.HTTPError:
            pass
    return ""


def _detail_params(aweme_id: str) -> dict[str, str]:
    return {
        "device_platform": "webapp",
        "aid": "6383",
        "channel": "channel_pc_web",
        "pc_client_type": "1",
        "version_code": "290100",
        "version_name": "29.1.0",
        "cookie_enabled": "true",
        "screen_width": "1920",
        "screen_height": "1080",
        "browser_language": "zh-CN",
        "browser_platform": "Win32",
        "browser_name": "Chrome",
        "browser_version": "130.0.0.0",
        "browser_online": "true",
        "engine_name": "Blink",
        "engine_version": "130.0.0.0",
        "os_name": "Windows",
        "os_version": "10",
        "cpu_core_num": "12",
        "device_memory": "8",
        "platform": "PC",
        "downlink": "10",
        "effective_type": "4g",
        "round_trip_time": "0",
        "update_version_code": "170400",
        "aweme_id": str(aweme_id),
        "msToken": _gen_fake_ms_token(),
    }


def _sign_detail_url(aweme_id: str) -> tuple[str, dict[str, str]]:
    """构造带 a_bogus 签名的详情接口 URL，返回 (url, cookies)。"""
    from urllib.parse import urlencode, quote

    params = _detail_params(aweme_id)
    query = urlencode(params)
    bogus = ABogus(UA, browser_info=DEFAULT_BROWSER_INFO).get_value(query)
    url = f"{DETAIL_API}?{query}&a_bogus={quote(bogus, safe='')}"

    cookies = {"s_v_web_id": _gen_s_v_web_id()}
    ttwid = _get_ttwid()
    if ttwid:
        cookies["ttwid"] = ttwid
    return url, cookies


def _fetch_detail(aweme_id: str) -> dict:
    """请求抖音详情接口并返回 `aweme_detail` 字典。"""
    url, cookies = _sign_detail_url(aweme_id)
    headers = {
        "User-Agent": UA,
        "Referer": f"https://www.douyin.com/video/{aweme_id}",
        "Accept": "application/json, text/plain, */*",
    }
    try:
        resp = httpx.get(url, headers=headers, cookies=cookies, timeout=30,
                         follow_redirects=False)
    except httpx.HTTPError as exc:
        raise DouyinError(f"抖音接口请求失败：{exc}") from exc

    if resp.status_code != 200 or not resp.content:
        raise DouyinError("抖音接口返回异常，可能触发了临时风控，请稍后重试")

    try:
        data = resp.json()
    except ValueError as exc:
        raise DouyinError("抖音接口返回了非 JSON 数据，可能触发了风控") from exc

    detail = data.get("aweme_detail") or {}
    if not detail or not detail.get("video"):
        # 图文 / 已删除 / 私密 / 风控壳页都拿不到可下载的视频
        status_code = data.get("status_code")
        if status_code:
            raise DouyinError(f"抖音接口拒绝返回数据（status_code={status_code}）")
        raise DouyinError("该链接没有可下载的视频（可能是图文、私密或已删除）")
    return detail


def _video_formats(detail: dict) -> list[dict]:
    """提取视频格式：每个分辨率只保留码率最高的 mp4（自带音轨，免合并）。"""
    video = detail.get("video") or {}
    duration_ms = video.get("duration") or 0
    best_by_height: dict[int, dict] = {}

    for item in video.get("bit_rate") or []:
        # dash 是纯视频流，需要另外合并音轨；抖音的 mp4 流自带音频，直接选用
        if item.get("format") != "mp4":
            continue
        play_addr = item.get("play_addr") or {}
        url = (play_addr.get("url_list") or [""])[0]
        height = play_addr.get("height") or 0
        if not url or height <= 0:
            continue
        bit_rate = item.get("bit_rate") or 0
        current = best_by_height.get(height)
        if current is None or bit_rate > current["bit_rate"]:
            best_by_height[height] = {
                "url": url,
                "height": height,
                "width": play_addr.get("width") or 0,
                "bit_rate": bit_rate,
            }

    result = []
    for height, fmt in sorted(best_by_height.items(), reverse=True):
        filesize = None
        if fmt["bit_rate"] and duration_ms:
            filesize = int(fmt["bit_rate"] * duration_ms / 1000 / 8)
        result.append({
            "format_id": str(height),
            "ext": "mp4",
            "height": height,
            "width": fmt["width"],
            "fps": 0,
            "vcodec": "avc1",
            "acodec": "aac",
            "filesize": filesize,
            "note": f"{height}P",
            "url": fmt["url"],
            "bit_rate": fmt["bit_rate"],
        })
    return result


def _safe_title(title: str, max_bytes: int = 120) -> str:
    """去除文件系统非法字符并按字节截断标题。"""
    title = re.sub(r'[\\/:*?"<>|\r\n\t]', " ", title).strip()
    while len(title.encode("utf-8", "ignore")) > max_bytes and title:
        title = title[:-1]
    return title or "douyin"


def parse_douyin(url: str) -> dict:
    """解析抖音视频，返回与 `downloader.parse_video` 相同的字段结构。"""
    aweme_id = _resolve_aweme_id(url)
    detail = _fetch_detail(aweme_id)

    video = detail.get("video") or {}
    author = detail.get("author") or {}
    title = detail.get("desc") or detail.get("item_title") or "未知标题"
    duration_ms = video.get("duration") or detail.get("duration") or 0

    formats = _video_formats(detail)
    for fmt in formats:
        fmt.pop("url", None)
        fmt.pop("bit_rate", None)

    cover = (video.get("cover") or {}).get("url_list") or (video.get("origin_cover") or {}).get("url_list") or [""]
    return {
        "title": title,
        "thumbnail": cover[0],
        "duration": _human_duration(duration_ms / 1000) if duration_ms else "",
        "uploader": author.get("nickname") or "",
        "webpage_url": f"https://www.douyin.com/video/{aweme_id}",
        "extractor": "Douyin",
        "formats": formats,
        "subtitles": [],
    }


def _human_duration(seconds: float) -> str:
    seconds = int(seconds)
    if not seconds:
        return ""
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def start_douyin_download(task: Task) -> None:
    """在后台线程中执行抖音直链下载。"""
    thread = threading.Thread(target=_run_douyin_download, args=(task,), daemon=True)
    thread.start()


def _run_douyin_download(task: Task) -> None:
    tasks.update(task, status="downloading", percent=0.0)

    try:
        aweme_id = _resolve_aweme_id(task.url)
        detail = _fetch_detail(aweme_id)
        formats = _video_formats(detail)

        if not formats:
            raise DouyinError("没有找到可下载的视频清晰度")

        selected = None
        if task.format_id == "best":
            selected = formats[0]
        else:
            for fmt in formats:
                if fmt["format_id"] == str(task.format_id):
                    selected = fmt
                    break
            if selected is None:
                selected = formats[0]

        title = detail.get("desc") or detail.get("item_title") or "未知标题"
        _backfill(task, title, detail, selected["height"])

        filename = f"{_safe_title(title)} [{aweme_id}] [{selected['format_id']}].mp4"
        filepath = Path(DOWNLOADS_DIR) / filename

        if filepath.is_file() and filepath.stat().st_size > 0:
            tasks.update(task, status="done", percent=100.0,
                         filepath=str(filepath), filename=filepath.name,
                         filesize=filepath.stat().st_size, finished_at=time.time())
            return

        tmp_path = filepath.with_suffix(filepath.suffix + ".part")
        headers = {
            "User-Agent": UA,
            "Referer": "https://www.douyin.com/",
            "Accept": "*/*",
        }
        try:
            downloaded = _download_to(tmp_path, selected["url"], headers, task)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise
        if not downloaded:
            tmp_path.unlink(missing_ok=True)
            raise DouyinError("下载中断：没有收到数据")

        tmp_path.replace(filepath)

        if task.mode == "audio":
            filepath = _extract_audio(filepath)

        filesize = filepath.stat().st_size
        tasks.update(task, status="done", percent=100.0,
                     filepath=str(filepath), filename=filepath.name,
                     filesize=filesize, finished_at=time.time())
    except DouyinError as exc:
        tasks.update(task, status="error", error=str(exc)[:500],
                     finished_at=time.time())
    except Exception as exc:  # noqa: BLE001 —— 统一转成任务错误状态
        tasks.update(task, status="error", error=f"抖音下载失败：{exc}"[:500],
                     finished_at=time.time())


def _download_to(path: Path, url: str, headers: dict, task: Task) -> bool:
    """流式下载直链，写入临时文件并更新进度。返回是否收到数据。"""
    last_update = 0.0
    start = time.monotonic()

    try:
        with httpx.stream("GET", url, headers=headers, timeout=60,
                          follow_redirects=True) as resp:
            if resp.status_code != 200:
                raise DouyinError(f"视频 CDN 返回 HTTP {resp.status_code}")
            total = int(resp.headers.get("content-length") or 0)
            received = 0
            with open(path, "wb") as fh:
                for chunk in resp.iter_bytes(chunk_size=1024 * 256):
                    if not chunk:
                        continue
                    fh.write(chunk)
                    received += len(chunk)
                    now = time.monotonic()
                    if total:
                        percent = received / total * 100
                    else:
                        percent = 0.0
                    if now - last_update >= 0.25:
                        elapsed = now - start
                        speed = received / elapsed if elapsed > 0 else 0
                        eta = ((total - received) / speed) if total and speed > 0 else None
                        tasks.update(task, status="downloading",
                                     percent=percent,
                                     speed=_human_speed(speed),
                                     eta=_human_eta(eta))
                        last_update = now
            return received > 0
    except httpx.HTTPError as exc:
        raise DouyinError(f"视频下载失败：{exc}") from exc


def _extract_audio(video_path: Path) -> Path:
    """用 ffmpeg 从已下载的视频文件中抽出 MP3 音频，并删除原视频文件。

    抖音直链返回的是带音轨的 mp4，没有独立的纯音频流；因此“仅音频”模式
    先复用现有的视频下载通道，再在本机用 ffmpeg 提取音轨。
    """
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise DouyinError("仅音频下载需要 ffmpeg，但当前环境未找到")

    attempts = [
        (".mp3", ["-vn", "-c:a", "libmp3lame", "-b:a", "192k"]),
        (".m4a", ["-vn", "-c:a", "aac", "-b:a", "192k"]),
    ]
    for suffix, args in attempts:
        audio_path = video_path.with_suffix(suffix)
        cmd = [ffmpeg, "-y", "-loglevel", "error",
               "-i", str(video_path), *args, str(audio_path)]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=300)
        except (OSError, subprocess.TimeoutExpired):
            proc = None
        if proc is not None and proc.returncode == 0 \
                and audio_path.is_file() and audio_path.stat().st_size > 0:
            video_path.unlink(missing_ok=True)
            return audio_path
        audio_path.unlink(missing_ok=True)

    raise DouyinError("音频提取失败，请稍后重试")


def _human_speed(bps: float) -> str:
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


def _backfill(task: Task, title: str, detail: dict, height: int) -> None:
    """补齐下载记录里的标题、封面与分辨率。"""
    updates = {}
    if not task.title:
        updates["title"] = title
    if not task.thumbnail:
        cover = (detail.get("video") or {}).get("cover") or {}
        url = (cover.get("url_list") or [""])[0]
        if url and not url.startswith(("http://", "https://")):
            url = ""
        if url:
            updates["thumbnail"] = url
    if not task.height and height:
        updates["height"] = height
    if updates:
        tasks.update(task, **updates)
