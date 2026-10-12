"""抖音专用解析与下载通道。

为什么需要独立于 yt-dlp 的通道：
    yt-dlp 的 Douyin 解析器调用 `www.douyin.com/aweme/v1/web/aweme/detail/`
    时既不带签名，也不带游客身份 cookie（`s_v_web_id` / `ttwid` / `uifid`），
    因此抖音风控返回空 JSON，yt-dlp 只能报：
        ERROR: [Douyin] ...: Fresh cookies (not necessarily logged in) are needed

该报错里的 "cookies" 并不要求用户登录，而是一份**游客设备身份**。本模块按两条通道
依次尝试，用户全程无感、无需提供任何 Cookie：

    通道一（直连，快）：生成游客 `s_v_web_id` + 注册 `ttwid` + 用内置纯 Python
        `a_bogus` 签名器给详情接口签名。2026-09 可用。
    通道二（浏览器桥，兜底）：抖音后来在该接口上追加了 secsdk 签名要求 ——
        除 `a_bogus` 外还要 `msToken`、`verifyFp`/`fp`，以及 secsdk 的
        `uifid` + `timestamp` + `x-secsdk-web-signature`（依赖 ECDSA 会话密钥与
        服务器 ticket，纯 Python 复现不现实）。此时直连会被
        `403 Blocked by ArgusSecurityPlugin Uifid Not Found` 拒绝，改由
        `douyin_browser_bridge.js` 在无头 Firefox 里打开视频页，让页面自带的
        `bdms`/`secsdk` 运行时补全签名后代取详情 JSON。

签名器来源：`backend/app/douyin_signer/`（Apache-2.0，见包内说明）。
"""
import json
import os
import random
import re
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

import httpx

from .config import (DOUYIN_BRIDGE_SCRIPT, DOWNLOADS_DIR, FRONTEND_DIR,
                     PLAYWRIGHT_BROWSERS_PATH, find_ffmpeg, find_node)
from .douyin_signer import ABogus, DEFAULT_BROWSER_INFO
from .tasks import Task, tasks

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

DETAIL_API = "https://www.douyin.com/aweme/v1/web/aweme/detail/"
TTWID_API = "https://ttwid.bytedance.com/ttwid/union/register/"

_DOUYIN_HOSTS = ("douyin.com", "iesdouyin.com", "amemv.com")

#: 链接里直接给出 aweme_id 的查询参数（用户主页弹窗分享用 `modal_id`）
_ID_QUERY_KEYS = ("modal_id", "aweme_id", "item_ids", "vid")
_URL_RE = re.compile(r"/(?:video|note|share/video)/(\d+)", re.I)

#: 浏览器桥单次请求的等待上限（秒）
_BRIDGE_TIMEOUT = 150

# ttwid 游客身份缓存（注册接口会下发长期有效的值，没必要每次请求都重新注册）
_ttwid_cache: dict[str, object] = {}
_ttwid_lock = threading.Lock()


class DouyinError(Exception):
    """抖音通道内部错误。"""


class _RiskControlBlocked(DouyinError):
    """直连详情接口被风控拒绝（可回退浏览器桥）。"""


def is_douyin(url: str) -> bool:
    """判断链接是否属于抖音。"""
    host = _host_of(url)
    return any(host == h or host.endswith("." + h) for h in _DOUYIN_HOSTS)


def _host_of(url: str) -> str:
    return (url.split("://", 1)[1] if "://" in url else url).split("/", 1)[0].split("?", 1)[0].lower()


def _extract_id_from_url(url: str) -> Optional[str]:
    """从链接中取 aweme_id。

    抖音的分享链接不止 `/video/<id>` 一种：从用户主页点开弹窗分享出来的是
    `/user/<sec_uid>?modal_id=<id>`，短链跳转后也可能只剩查询参数。因此路径和查询
    参数都要看：路径里明确写了 `/video/<id>` 时以路径为准，否则回退到
    `modal_id` / `aweme_id` / `item_ids` 等查询参数。
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return None

    m = _URL_RE.search(parsed.path or url)
    if m:
        return m.group(1)

    for key in _ID_QUERY_KEYS:
        for value in parse_qs(parsed.query).get(key, []):
            value = value.strip()
            if value.isdigit():
                return value
    return None


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
    """请求抖音详情接口并返回 `aweme_detail` 字典。

    先走快路径（纯 Python 直连），被风控拒绝时自动回退到浏览器桥。
    """
    try:
        return _fetch_detail_direct(aweme_id)
    except _RiskControlBlocked as blocked:
        detail = _fetch_detail_via_browser(aweme_id)
        if detail is not None:
            return detail

        bridge = _browser_bridge_status()
        if not bridge["ready"]:
            raise DouyinError(
                f"{blocked}；浏览器兜底通道也不可用：{bridge['reason']}"
            ) from None
        raise DouyinError(
            f"抖音接口风控拦截（{blocked}），浏览器兜底通道同样未能取到数据，请稍后重试"
        ) from None


def _detail_status_error(data: dict) -> Optional[str]:
    """从详情响应里读出业务错误；能判定是「该视频本身不可下载」时返回错误文案。

    返回 None 表示响应虽然没给出视频，但成因不明（可能只是风控壳页），应继续兜底尝试。
    """
    status_code = data.get("status_code") or 0
    if status_code == 0:
        return None
    if status_code in (11110, 2154):  # encrypt_data_miss / 无权限
        return "该链接没有可下载的视频（可能是图文、私密或已删除）"
    return None


def _raise_detail_error(data: dict) -> None:
    """响应里既没有 `aweme_detail` 也不是「无视频」时，抛出可诊断的错误。"""
    hint = _detail_status_error(data)
    if hint:
        raise DouyinError(hint)
    status_code = data.get("status_code")
    extra = f"（status_code={status_code}）" if status_code else ""
    raise _RiskControlBlocked(f"接口未返回视频数据{extra}")


def _fetch_detail_direct(aweme_id: str) -> dict:
    """直连详情接口（纯 Python + a_bogus）。被风控拦下时抛 `_RiskControlBlocked`。"""
    url, cookies = _sign_detail_url(aweme_id)
    headers = {
        "User-Agent": UA,
        "Referer": f"https://www.douyin.com/video/{aweme_id}",
        "Accept": "application/json, text/plain, */*",
    }
    try:
        resp = httpx.get(url, headers=headers, cookies=cookies, timeout=20,
                         follow_redirects=False)
    except httpx.HTTPError as exc:
        raise _RiskControlBlocked(f"详情接口请求失败：{exc}") from exc

    if resp.status_code != 200:
        snippet = resp.text.strip()[:80] or "空响应"
        raise _RiskControlBlocked(f"详情接口返回 HTTP {resp.status_code}：{snippet}")
    if not resp.content:
        raise _RiskControlBlocked("详情接口返回空响应")

    try:
        data = resp.json()
    except ValueError as exc:
        raise _RiskControlBlocked("详情接口返回了非 JSON 数据") from exc

    detail = data.get("aweme_detail") or {}
    if not detail or not detail.get("video"):
        _raise_detail_error(data)
    return detail


def _browser_bridge_status() -> dict:
    """检查浏览器桥是否可用，返回 `{ready, reason}` 供报错时给出可操作提示。"""
    if not DOUYIN_BRIDGE_SCRIPT.is_file():
        return {"ready": False, "reason": "未找到 bridge 脚本 douyin_browser_bridge.js"}
    if find_node() is None:
        return {"ready": False, "reason": "未找到 Node.js，请先安装 Node.js 18+"}
    if not (FRONTEND_DIR / "node_modules" / "playwright").is_dir():
        return {"ready": False,
                "reason": "frontend 未安装 playwright，请在 frontend 目录执行 `npm install`"}
    if not Path(PLAYWRIGHT_BROWSERS_PATH).is_dir():
        return {"ready": False,
                "reason": "未找到 Playwright 浏览器，请执行 `npx playwright install firefox`"}
    return {"ready": True, "reason": ""}


def _fetch_detail_via_browser(aweme_id: str) -> Optional[dict]:
    """用无头浏览器会话代取详情（页面自带签名运行时）。不可用或失败时返回 None。"""
    if not _browser_bridge_status()["ready"]:
        return None

    env = dict(os.environ)
    env.setdefault("PLAYWRIGHT_BROWSERS_PATH", PLAYWRIGHT_BROWSERS_PATH)
    tmp_dir = Path(tempfile.mkdtemp(prefix="douyin-bridge-"))
    out_file = tmp_dir / "detail.json"
    urls_file = tmp_dir / "urls.json"
    target = f"https://www.douyin.com/video/{aweme_id}"
    try:
        urls_file.write_text(json.dumps([target]), encoding="utf-8")
        cmd = [find_node(), str(DOUYIN_BRIDGE_SCRIPT),
               "--urls-file", str(urls_file), "--out", str(out_file)]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=_BRIDGE_TIMEOUT,
                                  cwd=str(FRONTEND_DIR), env=env)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if proc.returncode != 0 or not out_file.is_file():
            return None
        payload = json.loads(out_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    finally:
        for path in (out_file, urls_file):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        try:
            tmp_dir.rmdir()
        except OSError:
            pass

    if not payload.get("ok"):
        return None
    result = (payload.get("results") or {}).get(target) or {}
    detail = result.get("detail") or {}
    if result.get("ok") and detail.get("video"):
        return detail
    return None


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


def _select_format(formats: list[dict], format_id: str) -> dict:
    """按 format_id 选择格式；`best` 或未命中时回退到最高清晰度（formats[0]）。"""
    if format_id != "best":
        for fmt in formats:
            if fmt["format_id"] == str(format_id):
                return fmt
    return formats[0]


def _existing_audio(stem: str) -> Optional[Path]:
    """查找已提取好的音频文件（mp3 优先，m4a 兜底），无则返回 None。"""
    base = Path(DOWNLOADS_DIR) / stem
    for suffix in (".mp3", ".m4a"):
        path = base.with_suffix(suffix)
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


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

        selected = _select_format(formats, task.format_id)
        title = detail.get("desc") or detail.get("item_title") or "未知标题"
        _backfill(task, title, detail, selected["height"])

        stem = f"{_safe_title(title)} [{aweme_id}] [{selected['format_id']}]"

        if task.mode == "audio":
            # 最终产物是音频（mp3，ffmpeg 失败时回退 m4a）。缓存命中检查必须针对
            # 音频文件本身，否则「先下视频、再下音频」会命中同一个 mp4 而错误复用视频。
            filepath = _existing_audio(stem)
            if filepath:
                tasks.update(task, status="done", percent=100.0,
                             filepath=str(filepath), filename=filepath.name,
                             filesize=filepath.stat().st_size, finished_at=time.time())
                return
            # 音频模式先把视频流下载到独立中间文件，提取后即删除，
            # 绝不覆盖 / 误删同高度已存在的正式视频 mp4。
            video_path = Path(DOWNLOADS_DIR) / f"{stem}.audio.src.mp4"
        else:
            video_path = Path(DOWNLOADS_DIR) / f"{stem}.mp4"
            if video_path.is_file() and video_path.stat().st_size > 0:
                tasks.update(task, status="done", percent=100.0,
                             filepath=str(video_path), filename=video_path.name,
                             filesize=video_path.stat().st_size, finished_at=time.time())
                return

        tmp_path = video_path.with_suffix(video_path.suffix + ".part")
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

        tmp_path.replace(video_path)

        if task.mode == "audio":
            # ffmpeg 提音轨期间没有下载进度，给一个明确的处理中提示，避免用户以为卡死。
            tasks.update(task, speed="正在提取音频…", eta="")
            filepath = _extract_audio(video_path, Path(DOWNLOADS_DIR) / stem)
        else:
            filepath = video_path

        filesize = filepath.stat().st_size
        tasks.update(task, status="done", percent=100.0, speed="", eta="",
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
            # 字节流已全部落盘：立即把进度推到 100%。否则最后一个 0.25s 采样点
            # 往往停在 99.x%，随后进入（可能较长的）音频提取阶段，进度条就卡在那里。
            if received > 0:
                tasks.update(task, status="downloading", percent=100.0,
                             speed="", eta="")
            return received > 0
    except httpx.HTTPError as exc:
        raise DouyinError(f"视频下载失败：{exc}") from exc


def _extract_audio(video_path: Path, out_stem: Path) -> Path:
    """用 ffmpeg 从已下载的视频文件中抽出 MP3 音频（失败回退 M4A），并删除原视频文件。

    抖音直链返回的是带音轨的 mp4，没有独立的纯音频流；因此“仅音频”模式
    先把视频流下载到独立中间文件，再在本机用 ffmpeg 提取音轨到 `out_stem`。
    """
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise DouyinError("仅音频下载需要 ffmpeg，但当前环境未找到")

    attempts = [
        (".mp3", ["-vn", "-c:a", "libmp3lame", "-b:a", "192k"]),
        (".m4a", ["-vn", "-c:a", "aac", "-b:a", "192k"]),
    ]
    for suffix, args in attempts:
        audio_path = out_stem.with_suffix(suffix)
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
