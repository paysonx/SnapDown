"""离线单元测试：不访问真实网络，通过 monkeypatch 隔离 yt-dlp。"""
import pytest
from fastapi.testclient import TestClient

from app import downloader
from app.main import app
from app.tasks import tasks

client = TestClient(app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_parse_empty_url():
    resp = client.post("/api/parse", json={"url": "   "})
    assert resp.status_code == 400


def test_parse_invalid_url(monkeypatch):
    def fake_parse(url):
        raise downloader.ParseError("Unsupported URL")
    monkeypatch.setattr(downloader, "parse_video", fake_parse)
    resp = client.post("/api/parse", json={"url": "https://unknown-site.example/v/1"})
    assert resp.status_code == 422
    assert "Unsupported" in resp.json()["detail"]


def test_parse_playlist_rejected(monkeypatch):
    def fake_parse(url):
        raise downloader.PlaylistNotSupported("播放列表暂不支持")
    monkeypatch.setattr(downloader, "parse_video", fake_parse)
    resp = client.post("/api/parse", json={"url": "https://example.com/playlist"})
    assert resp.status_code == 400
    assert "播放列表" in resp.json()["detail"]


def test_parse_returns_clean_fields(monkeypatch):
    monkeypatch.setattr(downloader, "parse_video", lambda url: {
        "title": "测试视频", "thumbnail": "http://img/x.jpg", "duration": "3:33",
        "uploader": "up", "webpage_url": url, "extractor": "BiliBili",
        "formats": [{"format_id": "16", "ext": "mp4", "height": 1080, "width": 1920,
                     "fps": 30, "vcodec": "avc1", "acodec": "none",
                     "filesize": 123456, "note": "1080P"}],
        "subtitles": [{"lang": "zh-Hans", "ext": "vtt"}],
    })
    resp = client.post("/api/parse", json={"url": "https://example.com/v/1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "测试视频"
    assert data["formats"][0]["height"] == 1080
    assert data["subtitles"][0]["lang"] == "zh-Hans"


def test_download_task_lifecycle(monkeypatch):
    def fake_start(task):
        tasks.update(task, status="done", percent=100.0,
                     filepath="C:/fake/a.mp4", filename="a.mp4")
    monkeypatch.setattr(downloader, "start_download", fake_start)

    resp = client.post("/api/download",
                       json={"url": "https://example.com/v/1", "format_id": "best"})
    assert resp.status_code == 200
    task_id = resp.json()["id"]

    resp = client.get(f"/api/tasks/{task_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"
    assert resp.json()["percent"] == 100.0

    assert client.get("/api/tasks/nonexistent").status_code == 404
    # 文件不存在（fake 路径），应返回 404 而非 500
    assert client.get(f"/api/files/{task_id}").status_code == 404

    listing = client.get("/api/tasks").json()
    assert any(t["id"] == task_id for t in listing)


def test_download_task_error_state(monkeypatch):
    def fake_start(task):
        tasks.update(task, status="error", error="网络超时")
    monkeypatch.setattr(downloader, "start_download", fake_start)

    resp = client.post("/api/download",
                       json={"url": "https://example.com/v/2", "format_id": "16"})
    task_id = resp.json()["id"]
    data = client.get(f"/api/tasks/{task_id}").json()
    assert data["status"] == "error"
    assert "网络超时" in data["error"]


def test_download_defaults_to_video_mode(monkeypatch):
    """不传 mode 时默认按视频模式下载（视频+音频一起）。"""
    captured = {}

    def fake_start(task):
        captured["task"] = task
        tasks.update(task, status="downloading")

    monkeypatch.setattr(downloader, "start_download", fake_start)
    resp = client.post("/api/download",
                       json={"url": "https://example.com/v/mode-default", "format_id": "best"})
    assert resp.status_code == 200
    assert captured["task"].mode == "video"


def test_download_audio_mode_persists(monkeypatch):
    """仅音频模式必须把 mode 存进任务，供下载记录展示与后端分流。"""
    captured = {}

    def fake_start(task):
        captured["task"] = task
        tasks.update(task, status="downloading")

    monkeypatch.setattr(downloader, "start_download", fake_start)
    resp = client.post("/api/download", json={
        "url": "https://example.com/v/mode-audio",
        "format_id": "best",
        "mode": "audio",
    })
    assert resp.status_code == 200
    task_id = resp.json()["id"]
    assert captured["task"].mode == "audio"
    assert client.get(f"/api/tasks/{task_id}").json()["mode"] == "audio"

    # 非法 mode 由 Pydantic 拦截
    assert client.post("/api/download", json={
        "url": "https://example.com/v/mode-bad",
        "mode": "karaoke",
    }).status_code == 422


def test_download_persists_title_and_thumbnail(monkeypatch):
    """下载记录必须带上标题与封面（前端解析结果回传）。"""
    def fake_start(task):
        tasks.update(task, status="downloading")

    monkeypatch.setattr(downloader, "start_download", fake_start)
    resp = client.post("/api/download", json={
        "url": "https://example.com/v/3",
        "format_id": "best",
        "title": "测试视频",
        "thumbnail": "https://img.example.com/a.jpg",
    })
    assert resp.status_code == 200
    task_id = resp.json()["id"]

    data = client.get(f"/api/tasks/{task_id}").json()
    assert data["title"] == "测试视频"
    assert data["thumbnail"] == "https://img.example.com/a.jpg"
    # 历史列表中同样可见
    listed = next(t for t in client.get("/api/tasks").json() if t["id"] == task_id)
    assert listed["thumbnail"] == "https://img.example.com/a.jpg"


def test_normalize_thumbnail():
    """协议相对封面地址补全为 https，非法地址丢弃。"""
    assert downloader._normalize_thumbnail("//i0.hdslb.com/a.jpg") == "https://i0.hdslb.com/a.jpg"
    assert downloader._normalize_thumbnail("  https://x/a.jpg  ") == "https://x/a.jpg"
    assert downloader._normalize_thumbnail("http://x/a.jpg") == "http://x/a.jpg"
    assert downloader._normalize_thumbnail("") == ""
    assert downloader._normalize_thumbnail(None) == ""
    assert downloader._normalize_thumbnail("ftp://x/a.jpg") == ""


def test_backfill_meta_from_info_dict():
    """前端未回传时，用 yt-dlp 的 info 补齐标题、封面与分辨率。"""
    task = tasks.create(url="https://example.com/v/4", format_id="best")
    downloader._backfill_meta(task, {"title": "补标题", "thumbnail": "//img/x.jpg", "height": 1080})
    assert task.title == "补标题"
    assert task.thumbnail == "https://img/x.jpg"
    assert task.height == 1080

    # 已有值不被覆盖
    downloader._backfill_meta(task, {"title": "另一个", "thumbnail": "https://other/x.jpg", "height": 360})
    assert task.title == "补标题"
    assert task.thumbnail == "https://img/x.jpg"
    assert task.height == 1080


def test_task_to_dict_includes_size_fields():
    """任务字典必须暴露 height / filesize，供下载记录展示分辨率与体量。"""
    task = tasks.create(url="https://example.com/v/5", format_id="best",
                        title="标题", thumbnail="https://img/x.jpg")
    tasks.update(task, height=720, filesize=123456789)
    data = task.to_dict()
    assert data["height"] == 720
    assert data["filesize"] == 123456789


def test_outtmpl_contains_format_id():
    """输出文件名必须包含 format_id，否则同一视频不同清晰度会复用旧文件。"""
    tpl = downloader._outtmpl()
    assert "%(format_id)s" in tpl
    assert "%(id)s" in tpl
    assert "%(title).120B" in tpl


# ---------- 同分辨率格式优选（m3u8_native 抢占的回归测试） ----------

def _fmt(format_id, height, protocol="https", tbr=2000, acodec="none", vcodec="avc1.640028", **extra):
    f = {"format_id": format_id, "ext": "mp4", "height": height, "width": height * 16 // 9,
         "fps": 30, "vcodec": vcodec, "acodec": acodec, "tbr": tbr,
         "protocol": protocol, "format_note": f"{height}p"}
    f.update(extra)
    return f


def test_m3u8_native_does_not_win_over_dash():
    """yt-dlp 把 m3u8_native 排在 formats 最前，同分辨率下不能再被它抢走。

    m3u8 是切片流：逐片请求、并发低、下载完还要 ffmpeg 拼接，
    实测比同分辨率 DASH 直连流慢一个数量级。
    """
    raw = [
        _fmt("m3u8_native", 1080, protocol="m3u8_native", tbr=4500),
        _fmt("137", 1080, tbr=4400),
    ]
    result = downloader._build_format_list(raw, duration=600)
    assert [f["format_id"] for f in result] == ["137"]


def test_progressive_wins_over_video_only_at_same_height():
    """同分辨率下带音轨的渐进式格式优先——省掉一次 ffmpeg 合并。

    YouTube 从 1080p 起强制 DASH，所以这条只对 720p 及以下生效。
    """
    raw = [
        _fmt("136", 720, tbr=1100, vcodec="vp9", ext="webm"),   # video-only webm
        _fmt("22", 720, tbr=1500, acodec="mp4a.40.2"),          # progressive mp4
    ]
    result = downloader._build_format_list(raw, duration=600)
    assert [f["format_id"] for f in result] == ["22"]
    assert result[0]["acodec"] == "mp4a"


def test_same_rank_prefers_higher_bitrate():
    """优先级相同时（如同为主流 video-only DASH）取码率更高的那个。"""
    raw = [
        _fmt("248", 1080, tbr=4200, vcodec="vp9", ext="webm"),
        _fmt("137", 1080, tbr=4400),
    ]
    result = downloader._build_format_list(raw, duration=600)
    assert [f["format_id"] for f in result] == ["137"]


def test_m3u8_not_excluded_when_it_is_the_only_option():
    """纯 HLS 源（没有 DASH 对应流）时仍要能选中 m3u8，不能过滤成空列表。"""
    raw = [_fmt("m3u8_native", 720, protocol="m3u8_native", tbr=2500)]
    result = downloader._build_format_list(raw, duration=600)
    assert [f["format_id"] for f in result] == ["m3u8_native"]


def test_format_list_filters_audio_only_and_zero_height():
    """纯音频流（vcodec=none）与无分辨率条目仍应被过滤。"""
    raw = [
        _fmt("140", 0, acodec="mp4a.40.2", vcodec="none"),
        _fmt("sb3", 0, acodec="mp4a.40.2"),
        _fmt("137", 1080),
    ]
    result = downloader._build_format_list(raw, duration=600)
    assert [f["format_id"] for f in result] == ["137"]


def test_format_list_sorted_by_height_desc_and_estimates_filesize():
    """输出按分辨率降序，filesize 缺失时按 tbr 估算。"""
    raw = [_fmt("137", 1080, tbr=4400), _fmt("22", 720, tbr=1500, acodec="mp4a.40.2")]
    result = downloader._build_format_list(raw, duration=600)
    assert [f["height"] for f in result] == [1080, 720]
    assert result[0]["filesize"] == int(4400 * 1024 / 8 * 600)
