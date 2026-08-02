"""
网页助手（web_assistant）—— 端到端示例插件。

整合本 skill 40–45 的融合精髓：
  · 深函数封装：entry 只做「取参 → 调深函数 → Ok/Err」（40 §5 / 42 §2）
  · Router 子包拆分：中等插件推荐范式（44 §1 范式 A）
  · 设置面板：self.config.dump()/update()（03 / 44 §3）
  · @llm_tool 联网能力：firecrawl 官方 SDK（42 §4.5）
  · SSRF 守卫：凡访问用户给的 URL 先过 _is_safe_url（43 §4）
  · 防御性入口：try/except → Err，异常不冒泡（44 §6）

import 形式以你框架版本为准，本文件沿用 02-python-plugin.md 的约定。
"""
from typing import Any

from plugin.sdk.plugin import (
    NekoPluginBase, neko_plugin, lifecycle, Ok, Err, SdkError,
)


@neko_plugin
class WebAssistantPlugin(NekoPluginBase):
    """主类只负责生命周期 + 注册 Router；业务逻辑在 routers/web.py。"""

    def __init__(self, ctx):
        super().__init__(ctx)
        # Router 子包拆分（lifekit 范式）：避免单文件膨胀
        from .routers.web import WebRouter
        self.include_router(WebRouter())
        self._cfg: dict = {}

    # ── 生命周期：统一 self, **_ → Ok/Err（44 §2）──
    @lifecycle(id="startup")
    async def startup(self, **_) -> Ok | Err:
        try:
            await self._reload_config()
            return Ok({"status": "ready"})
        except Exception as e:                      # 防御性：异常不冒泡（44 §6）
            self.logger.exception("startup failed")
            return Err(str(e))

    @lifecycle(id="shutdown")
    async def shutdown(self, **_) -> Ok | Err:
        return Ok({"status": "stopped"})

    @lifecycle(id="config_change")
    async def on_config_change(self, **_) -> Ok | Err:
        await self._reload_config()
        return Ok({"status": "reloaded"})

    async def _reload_config(self):
        raw = await self.config.dump(timeout=5.0)
        self._cfg = raw.get("web_assistant", {})
