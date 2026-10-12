# 贡献指南

感谢你考虑为 SnapDown 贡献代码。这份文档说明本地环境、提交规范，以及**哪些改动不会被接受**。

## 本地开发

```bash
# 后端依赖
py -3 -m venv .venv            # Python 3.12+
./.venv/Scripts/python -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt

# 前端依赖（同时会装上 @ffmpeg-installer/ffmpeg 静态二进制，无需单独装 ffmpeg）
cd frontend && npm install && npm run build && cd ..
```

启动：后端 `./.venv/Scripts/python run.py`，前端热更新 `cd frontend && npm run dev`。

## 提交前必跑

```bash
./.venv/Scripts/python -m pytest backend                    # 离线单元测试，必须全绿
cd frontend && npm run build                                 # 构建必须无报错
```

`backend/tests/test_integration.py` 会打真实网络（默认跳过）。**提交 PR 前请至少跑一次**并确认通过：

```bash
./.venv/Scripts/python -m pytest backend/tests/test_integration.py -m integration -v
```

## 提交信息

沿用 Conventional Commits：`feat:` / `fix:` / `docs:` / `refactor:` / `chore:` / `test:`。

## 不接受的改动

这个项目有一条硬边界，请务必遵守：

- ❌ **任何 DRM 绕过或解密能力**。本项目不包含也不会加入此类功能。
- ❌ 绕过平台风控 / 反爬机制的**大规模**对抗性实现。抖音通道的游客身份与签名只为让公开视频能正常下载，不做批量账号模拟。
- ❌ 引入数据库或需要用户注册鉴权的强依赖。当前架构刻意保持零数据库、零登录。
- ❌ 把构建产物、依赖目录或二进制文件提交进仓库（`.gitignore` 已覆盖，请勿用 `git add -f` 绕过）。
- ❌ 未经讨论的大规模重构。开个 issue 先聊清楚再动手。

## 涉及抖音的改动

抖音走的是独立通道（`backend/app/douyin.py`），两级降级：纯 Python 直连 → 无头浏览器桥。平台风控策略变动频繁，如果你改这块，请在 PR 描述里附上**实测结果**（真实链接 + 解析输出），纯推断的改动很容易是错的。

## 许可

提交即表示你同意你的代码以 **Apache-2.0** 协议开源。`backend/app/douyin_signer/` 来自第三方项目且已标注来源与许可，修改它时请保留原有的 LICENSE 与来源说明。