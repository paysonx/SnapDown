"""抖音 Web 接口签名工具（纯 Python，无第三方依赖）。

代码来源与许可：
- `sm3.py` / `abogus.py` 改编自 Evil0ctal/Douyin_TikTok_Download_API（v5，
  commit 3fa19d9aeb5326df3ade80a7ce75f62f7a154dfb，Apache License 2.0）。
- 仅保留本项目的抖音 `a_bogus` 签名所需的最小实现，删除了原仓库的
  框架依赖（dtk.*），并把 SM3 导入改为包内相对导入。
- Apache-2.0 许可全文：https://www.apache.org/licenses/LICENSE-2.0
"""

from .abogus import ABogus, DEFAULT_BROWSER_INFO, build_browser_info

__all__ = ["ABogus", "DEFAULT_BROWSER_INFO", "build_browser_info"]
