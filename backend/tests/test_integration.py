"""真实网络集成测试：B站解析 + 真实下载（需网络，手动/CI 运行）。

运行方式：
    python -m pytest tests/test_integration.py -m integration -v
"""
import time
from pathlib import Path

import pytest

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# yt-dlp 官方测试视频：B站《Never Gonna Give You Up》官方 MV，稳定且时长较短
BILI_URL = "https://www.bilibili.com/video/BV1GJ411x7h7"

pytestmark = pytest.mark.integration


def test_parse_bilibili():
    resp = client.post("/api/parse", json={"url": BILI_URL})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["title"]
    assert data["thumbnail"].startswith("http")
    assert data["extractor"].lower() == "bilibili"
    assert len(data["formats"]) >= 3, "B站视频应提供多个清晰度"
    heights = [f["height"] for f in data["formats"]]
    assert heights == sorted(heights, reverse=True), "格式应按分辨率降序排列"


def test_download_bilibili_lowest_quality():
    # 先解析取最低清晰度格式
    info = client.post("/api/parse", json={"url": BILI_URL}).json()
    lowest = info["formats"][-1]
    print(f"\n[integration] 使用格式: {lowest['height']}p (format_id={lowest['format_id']})")

    resp = client.post("/api/download",
                       json={"url": BILI_URL, "format_id": lowest["format_id"]})
    assert resp.status_code == 200
    task_id = resp.json()["id"]

    # 轮询等待下载完成（最多 240 秒）
    deadline = time.time() + 240
    last = None
    while time.time() < deadline:
        last = client.get(f"/api/tasks/{task_id}").json()
        if last["status"] in ("done", "error"):
            break
        time.sleep(1)

    assert last is not None
    assert last["status"] == "done", f"下载失败: {last['error']}"
    assert last["filepath"]
    assert last["percent"] == 100.0

    # 验证文件确实可下载
    file_resp = client.get(f"/api/files/{task_id}")
    assert file_resp.status_code == 200
    assert len(file_resp.content) > 100 * 1024, "下载文件过小，疑似异常"
    print(f"\n[integration] 下载成功: {last['filename']} ({len(file_resp.content)} bytes)")


def test_download_two_resolutions_produce_distinct_files():
    """同一视频下载两个不同清晰度，必须各自落盘为不同文件（不能复用第一次的文件）。"""
    info = client.post("/api/parse", json={"url": BILI_URL}).json()
    formats = info["formats"]
    assert len(formats) >= 2, "B站视频应提供至少两个清晰度"

    # 取最低与次低两档，控制下载体积
    picks = [formats[-1], formats[-2]]
    paths = {}

    for f in picks:
        resp = client.post("/api/download",
                           json={"url": BILI_URL, "format_id": f["format_id"]})
        assert resp.status_code == 200
        task_id = resp.json()["id"]

        deadline = time.time() + 240
        last = None
        while time.time() < deadline:
            last = client.get(f"/api/tasks/{task_id}").json()
            if last["status"] in ("done", "error"):
                break
            time.sleep(1)

        assert last and last["status"] == "done", f"下载失败: {last and last['error']}"
        assert last["filepath"]
        # 下载记录需要分辨率与体量标签
        assert last["height"] == f["height"], (
            f"{f['height']}p 任务应记录 height={f['height']}，实际 {last['height']}"
        )
        assert last["filesize"] > 0, "完成后应记录文件体积"
        paths[f["format_id"]] = last["filepath"]
        print(f"\n[integration] {f['height']}p (format_id={f['format_id']}) -> "
              f"{last['filename']} ({last['filesize']} bytes)")

    first, second = picks[0]["format_id"], picks[1]["format_id"]
    assert paths[first] != paths[second], (
        f"不同清晰度必须产生不同文件：{first}={paths[first]}, {second}={paths[second]}"
    )
    for path in paths.values():
        assert Path(path).is_file(), f"文件应实际存在: {path}"
