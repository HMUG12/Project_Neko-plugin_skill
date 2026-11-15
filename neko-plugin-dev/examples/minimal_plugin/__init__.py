"""N.E.K.O 最小插件示例 —— 零第三方依赖。

演示要点（以官方 main 的公开 SDK 为准）：
  · 6 个合法的生命周期 id，且用 id= 关键字
  · @plugin_entry 都是 async def；@llm_tool 放在主类且用 keyword-only 参数
  · @ui.action 必须与 @plugin_entry 叠加，否则前端拿不到可调用 action
  · Router 子包必须继承 PluginRouter
  · store.get 返回 Result，取值要 unwrap_or
  · @timer_interval 必须是 async def，不要自建事件循环
  · push_message 是同步方法，用 v2 parts，返回 PushMessageResult，要判 submitted
  · 面板保存走 self.config.update()，startup / config_change 从 self.config.dump() 重读，
    Reload 后配置不丢；config.example.toml 的 [minimal_plugin].greeting 会被真正读取。

配置读写方法名参照官方 plugin/plugins/lifekit/__init__.py 的公开用法
（config.dump(timeout=...) / config.update({...})）。
"""
import asyncio
from typing import Annotated

from plugin.sdk.plugin import (
    Err,
    NekoPluginBase,
    Ok,
    SdkError,
    lifecycle,
    llm_tool,
    neko_plugin,
    plugin_entry,
    timer_interval,
    ui,
    unwrap_or,
)

MAX_TEXT = 200
DEFAULT_GREETING = "你好"


@neko_plugin
class MinimalPlugin(NekoPluginBase):
    """主类只负责生命周期、入口与面板；Router 业务逻辑在 routers/notes.py。"""

    def __init__(self, ctx):
        super().__init__(ctx)
        self._greeting = DEFAULT_GREETING
        self._frozen = False
        self._ticks = 0
        from .routers.notes import NotesRouter

        self.include_router(NotesRouter())

    # ── 配置：与 config.example.toml 的 [minimal_plugin] 命名空间一致 ──
    async def _reload_config(self):
        cfg = await self.config.dump(timeout=5.0)
        cfg = cfg if isinstance(cfg, dict) else {}
        section = cfg.get("minimal_plugin", {})
        value = section.get("greeting", DEFAULT_GREETING) if isinstance(section, dict) else DEFAULT_GREETING
        self._greeting = str(value).strip()[:MAX_TEXT] or DEFAULT_GREETING

    # ── 生命周期 ──
    @lifecycle(id="startup")
    async def on_startup(self, **_):
        await self._reload_config()
        self._ticks = int(unwrap_or(await self.store.get("ticks"), 0))
        return Ok({"status": "ready", "greeting": self._greeting})

    @lifecycle(id="shutdown")
    async def on_shutdown(self, **_):
        await self.store.set("ticks", self._ticks)
        return Ok({"status": "stopped"})

    @lifecycle(id="config_change")
    async def on_config_change(self, **_):
        await self._reload_config()
        return Ok({"status": "reloaded", "greeting": self._greeting})

    @lifecycle(id="freeze")
    async def on_freeze(self, **_):
        self._frozen = True
        return Ok({"status": "frozen"})

    @lifecycle(id="unfreeze")
    async def on_unfreeze(self, **_):
        self._frozen = False
        return Ok({"status": "unfrozen"})

    # ── AI 入口 ──
    @plugin_entry(
        id="count",
        name="计数",
        description="把计数器加一；无需任何参数",
        input_schema={"type": "object", "properties": {}},
    )
    async def count(self, **_):
        self._ticks += 1
        return Ok({"ticks": self._ticks})

    @llm_tool(name="echo", description="回显一段文本，演示 keyword-only 参数")
    async def echo(self, *, text: Annotated[str, "要回显的文本"] = ""):
        if not text:
            return Err(SdkError("text 不能为空"))
        return Ok({"text": text[:MAX_TEXT]})

    # ── 设置面板：双装饰器缺一不可；保存必须落盘，不能只改内存 ──
    @ui.action(label="保存设置", tone="primary", refresh_context=True)
    @plugin_entry(id="save_settings", name="保存设置", description="保存设置面板的问候语")
    async def save_settings(self, config: dict | None = None, **_):
        if not isinstance(config, dict):
            return Err(SdkError("config 必须是对象"))
        greeting = str(config.get("greeting", "")).strip()[:MAX_TEXT]
        if not greeting:
            return Err(SdkError("greeting 不能为空"))
        try:
            await self.config.update({"minimal_plugin": {"greeting": greeting}})
            await self._reload_config()
        except Exception as exc:
            return Err(SdkError(f"保存配置失败: {exc}"))
        return Ok({"status": "saved", "greeting": self._greeting})

    @ui.context(id="settings")
    async def settings_context(self):
        return {
            "config": {"greeting": self._greeting},
            "status": {"ticks": self._ticks, "frozen": self._frozen},
        }

    # ── 定时器：宿主执行 asyncio.run(fn()) ──
    @timer_interval(id="tick", seconds=60, name="定时整理", auto_start=True)
    async def on_tick(self, **_):
        if self._frozen:
            return Ok({"skipped": True})
        await asyncio.to_thread(self._light_work)
        return Ok({"status": "done"})

    def _light_work(self):
        self.logger.debug("minimal_plugin tick")

    # ── 消息推送：同步方法，返回本地提交回执 ──
    def notify(self, text: str):
        result = self.ctx.push_message(
            visibility=["chat"],
            ai_behavior="blind",
            parts=[{"type": "text", "text": text[:MAX_TEXT]}],
            source="minimal_plugin",
            priority=0,
        )
        if not result["submitted"]:
            self.logger.warning("message submission failed: %s", result.get("reason"))
            return Err(SdkError(f"push_message 未提交: {result.get('reason')}"))
        return Ok({"status": "submitted"})
