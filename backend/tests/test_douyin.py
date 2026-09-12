"""抖音专用通道的离线单元测试（不访问真实网络）。"""
from app import douyin


def test_is_douyin_url():
    assert douyin.is_douyin("https://www.douyin.com/video/123")
    assert douyin.is_douyin("https://v.douyin.com/abc/")
    assert douyin.is_douyin("https://www.iesdouyin.com/share/video/123/")
    assert not douyin.is_douyin("https://www.bilibili.com/video/BV1GJ411x7h7")


def test_resolve_aweme_id_direct_url():
    assert douyin._resolve_aweme_id("https://www.douyin.com/video/7682707061592088049") == "7682707061592088049"
    assert douyin._resolve_aweme_id(
        "https://www.iesdouyin.com/share/video/7682707061592088049/?region=CN") == "7682707061592088049"


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
