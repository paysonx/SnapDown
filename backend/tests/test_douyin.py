"""抖音专用通道的离线单元测试（不访问真实网络）。"""
import json
from pathlib import Path

import pytest

from app import douyin
from app.tasks import Task


def test_is_douyin_url():
    assert douyin.is_douyin("https://www.douyin.com/video/123")
    assert douyin.is_douyin("https://v.douyin.com/abc/")
    assert douyin.is_douyin("https://www.iesdouyin.com/share/video/123/")
    assert not douyin.is_douyin("https://www.bilibili.com/video/BV1GJ411x7h7")


def test_resolve_aweme_id_direct_url():
    assert douyin._resolve_aweme_id("https://www.douyin.com/video/7682707061592088049") == "7682707061592088049"
    assert douyin._resolve_aweme_id(
        "https://www.iesdouyin.com/share/video/7682707061592088049/?region=CN") == "7682707061592088049"


def test_extract_id_from_user_modal_url():
    """用户主页弹窗分享出来的链接（?modal_id=）必须能取到 aweme_id。

    这类链接没有 `/video/` 路径，早期实现只认路径，直接报「无法解析出视频 ID」。
    """
    url = ("https://www.douyin.com/user/MS4wLjABAAAAkGPUlxhANi-quQ-g2HAFIHVArZmHUNeyutqfY_bKvS0"
           "?modal_id=7678988219672792355")
    assert douyin._resolve_aweme_id(url) == "7678988219672792355"
    # 参数顺序/多余参数不影响
    assert douyin._extract_id_from_url(
        "https://www.douyin.com/user/abc?from_tab_name=main&modal_id=123456") == "123456"
    # 路径里明确是 /video/<id> 时以路径为准
    assert douyin._extract_id_from_url("https://www.douyin.com/video/999?modal_id=111") == "999"
    # 只有查询参数时（短链跳转后的形态）用查询参数
    assert douyin._extract_id_from_url(
        "https://www.douyin.com/discover?modal_id=111") == "111"
    # 非数字的 modal_id 不该被当成 ID
    assert douyin._extract_id_from_url("https://www.douyin.com/user/abc?modal_id=xyz") is None


class _FakeResponse:
    def __init__(self, status_code=200, body=b"", payload=None):
        self.status_code = status_code
        self.content = body if payload is None else json.dumps(payload).encode()
        self.text = self.content.decode("utf-8", "replace")

    def json(self):
        return json.loads(self.content)


def _detail_payload():
    return {
        "aweme_detail": {
            "desc": "测试视频",
            "video": {"duration": 1000, "bit_rate": [
                {"format": "mp4", "bit_rate": 1000,
                 "play_addr": {"height": 720, "width": 1280, "url_list": ["https://cdn/720.mp4"]}}]},
        }
    }


def test_fetch_detail_uses_direct_channel_when_available(monkeypatch):
    """直连通道成功时不应触发浏览器桥（桥很慢，只在被风控时才用）。"""
    monkeypatch.setattr(douyin.httpx, "get",
                        lambda *a, **k: _FakeResponse(payload=_detail_payload()))
    called = []
    monkeypatch.setattr(douyin, "_fetch_detail_via_browser",
                        lambda aweme_id: called.append(aweme_id))

    detail = douyin._fetch_detail("123")
    assert detail["desc"] == "测试视频"
    assert called == []


def test_fetch_detail_falls_back_to_browser_when_risk_controlled(monkeypatch):
    """直连被风控（403 Uifid Not Found）时应自动回退浏览器桥。"""
    blocked = _FakeResponse(status_code=403,
                            body=b"Blocked by ArgusSecurityPlugin Uifid Not Found")
    monkeypatch.setattr(douyin.httpx, "get", lambda *a, **k: blocked)
    monkeypatch.setattr(douyin, "_fetch_detail_via_browser",
                        lambda aweme_id: _detail_payload()["aweme_detail"])

    detail = douyin._fetch_detail("123")
    assert detail["video"]["bit_rate"][0]["play_addr"]["url_list"] == ["https://cdn/720.mp4"]


def test_fetch_detail_reports_actionable_error_when_both_channels_fail(monkeypatch):
    """两条通道都失败时，报错要说明风控事实并给出可操作建议，而不是笼统的「稍后重试」。"""
    blocked = _FakeResponse(status_code=403,
                            body=b"Blocked by ArgusSecurityPlugin Uifid Not Found")
    monkeypatch.setattr(douyin.httpx, "get", lambda *a, **k: blocked)
    monkeypatch.setattr(douyin, "_fetch_detail_via_browser", lambda aweme_id: None)
    monkeypatch.setattr(douyin, "_browser_bridge_status",
                        lambda: {"ready": False, "reason": "未找到 Node.js"})

    with pytest.raises(douyin.DouyinError) as excinfo:
        douyin._fetch_detail("123")
    message = str(excinfo.value)
    assert "403" in message and "Uifid" in message
    assert "Node.js" in message


def test_fetch_detail_reports_when_video_is_unavailable(monkeypatch):
    """接口明确说「没权限/加密数据缺失」时，应报图文/私密/已删除，且不再走浏览器桥。"""
    monkeypatch.setattr(douyin.httpx, "get", lambda *a, **k: _FakeResponse(
        payload={"status_code": 2154, "aweme_detail": None}))
    called = []
    monkeypatch.setattr(douyin, "_fetch_detail_via_browser",
                        lambda aweme_id: called.append(aweme_id))

    with pytest.raises(douyin.DouyinError) as excinfo:
        douyin._fetch_detail("123")
    assert "图文" in str(excinfo.value)
    assert called == []


def test_browser_bridge_status_reports_missing_prerequisites(monkeypatch):
    """桥不可用时要给出具体缺什么，便于用户按提示修好。"""
    monkeypatch.setattr(douyin, "DOUYIN_BRIDGE_SCRIPT", Path("缺失的脚本.js"))
    status = douyin._browser_bridge_status()
    assert status["ready"] is False
    assert "bridge 脚本" in status["reason"]


def test_video_formats_prefers_mp4_and_dedupes_by_height():
    detail = {
        "video": {
            "duration": 10000,  # ms
            "bit_rate": [
                {"format": "dash", "bit_rate": 9999999, "play_addr": {"height": 1080, "width": 1920, "url_list": ["https://cdn/dash-1080.mp4"]}},
                {"format": "mp4", "bit_rate": 4000000, "play_addr": {"height": 1080, "width": 1920, "url_list": ["https://cdn/mp4-1080.mp4"]}},
                {"format": "mp4", "bit_rate": 1000000, "play_addr": {"height": 720, "width": 1280, "url_list": ["https://cdn/mp4-720.mp4"]}},
            ],
        }
    }
    formats = douyin._video_formats(detail)
    assert [f["height"] for f in formats] == [1080, 720]
    assert formats[0]["url"] == "https://cdn/mp4-1080.mp4"
    assert formats[0]["filesize"] == int(4000000 * 10 / 8)
    # 返回给前端前应剥掉内部字段
    cleaned = [dict(f) for f in formats]
    for f in cleaned:
        f.pop("url", None)
        f.pop("bit_rate", None)
    assert "url" not in cleaned[0]
    assert "bit_rate" not in cleaned[0]


def test_safe_title_removes_illegal_chars_and_truncates():
    title = douyin._safe_title('a/b\\c:d*e?f"g<h>i|j\r\n')
    assert "/" not in title and "\\" not in title and ":" not in title
    assert douyin._safe_title("", max_bytes=10) == "douyin"
    assert len(douyin._safe_title("x" * 500, max_bytes=120).encode("utf-8")) <= 120


def test_video_then_audio_produce_distinct_files(monkeypatch, tmp_path):
    """先下视频、再下同链接音频：音频必须落盘为独立 mp3，而不是复用第一遍的视频 mp4。"""
    monkeypatch.setattr(douyin, "DOWNLOADS_DIR", tmp_path)
    monkeypatch.setattr(douyin, "_resolve_aweme_id", lambda url: "12345")
    monkeypatch.setattr(douyin, "_fetch_detail", lambda aweme_id: {
        "desc": "测试视频",
        "video": {
            "duration": 10000,
            "bit_rate": [
                {"format": "mp4", "bit_rate": 1000000,
                 "play_addr": {"height": 1080, "width": 1920,
                               "url_list": ["https://cdn/1080.mp4"]}},
            ],
        },
    })

    def fake_download(path, url, headers, task):
        path.write_bytes(b"FAKE_VIDEO")
        return True

    def fake_extract_audio(video_path, out_stem):
        audio_path = out_stem.with_suffix(".mp3")
        audio_path.write_bytes(b"FAKE_AUDIO")
        video_path.unlink(missing_ok=True)
        return audio_path

    monkeypatch.setattr(douyin, "_download_to", fake_download)
    monkeypatch.setattr(douyin, "_extract_audio", fake_extract_audio)

    url = "https://www.douyin.com/video/12345"

    # 第一遍：视频（best → 最高清晰度 1080）
    video_task = Task(id="t1", url=url, format_id="best", mode="video")
    douyin._run_douyin_download(video_task)
    assert video_task.status == "done", video_task.error
    assert video_task.filepath.endswith(".mp4")
    video_path = Path(video_task.filepath)
    assert video_path.is_file()
    assert video_path.read_bytes() == b"FAKE_VIDEO"

    # 第二遍：音频 —— 必须得到 mp3，而不是复用第一遍的 mp4
    audio_task = Task(id="t2", url=url, format_id="best", mode="audio")
    douyin._run_douyin_download(audio_task)
    assert audio_task.status == "done", audio_task.error
    assert audio_task.filepath.endswith(".mp3"), (
        f"音频任务应产出 mp3，实际 {audio_task.filepath}"
    )
    audio_path = Path(audio_task.filepath)
    assert audio_path.is_file()
    assert audio_path.read_bytes() == b"FAKE_AUDIO"
    # 音频任务不能覆盖 / 误删第一遍的正式视频文件
    assert video_path.is_file() and video_path.read_bytes() == b"FAKE_VIDEO"


def test_download_to_reaches_100_percent(monkeypatch, tmp_path):
    """字节流全部落盘后必须立即把进度推到 100%，不能卡在最后一个采样点（如 99.9%）。"""
    # 冻结单调时钟：让所有 0.25s 采样点都不触发，只验证「收尾强制 100%」这步
    monkeypatch.setattr(douyin.time, "monotonic", lambda: 1000.0)

    class FakeResponse:
        status_code = 200
        headers = {"content-length": "10"}

        def iter_bytes(self, chunk_size):
            yield b"01234"
            yield b"56789"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeStream:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return FakeResponse()

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(douyin.httpx, "stream", lambda *a, **k: FakeStream())

    task = Task(id="t", url="https://x", format_id="best", mode="audio")
    target = tmp_path / "out.mp4"
    ok = douyin._download_to(target, "https://cdn/x.mp4", {}, task)
    assert ok is True
    assert target.read_bytes() == b"0123456789"
    assert task.percent == 100.0
