"""
WebRouter：网页抓取 / 搜索业务域。

设计要点（对应 skill 篇章）：
  · 真正干活的代码藏在 _call_firecrawl（深函数），entry 只做薄封装（40 §5）
  · 同步 SDK 用 asyncio.to_thread 包，不阻塞事件循环（10 性能 / 42 §4.5）
  · 用户给的 URL 先过 _is_safe_url（43 §4 进阶 SSRF 守卫）
  · @llm_tool 参数用 Any + 入口内校验，防 LLM 违反 schema 导致 TypeError（44 §5）
  · 每个会失败的调用都包 try/except → Err（44 §6）
"""
import asyncio
import ipaddress
import socket
from typing import Any
from urllib.parse import urlparse

from plugin.sdk.plugin import plugin_entry, ui, llm_tool, Ok, Err, SdkError


class WebRouter:
    """include_router 后，方法会挂到插件实例上，self 即插件实例。"""

    # ──────────────────────────────────────────────
    # 深函数：真正的外部调用在这里（藏复杂度）
    # ──────────────────────────────────────────────
    async def _call_firecrawl(self, mode: str, arg: str) -> dict:
        raw = await self.config.dump(timeout=5.0)
        cfg = raw.get("web_assistant", {})
        key = cfg.get("firecrawl_api_key") or ""
        url = cfg.get("firecrawl_api_url") or None
        limit = int(cfg.get("search_limit", 5))
        if not key:
            return {"output": "未配置 firecrawl_api_key", "is_error": True}

        # 同步 SDK 必须在 to_thread 里跑
        def _run():
            from firecrawl import Firecrawl
            fc = Firecrawl(api_key=key, api_url=url)
            if mode == "scrape":
                doc = fc.scrape(arg, ["markdown"])
                return {"markdown": doc.markdown,
                        "title": (doc.metadata_dict or {}).get("title", "")}
            res = fc.search(arg, limit)
            return {"results": [{"title": r.title, "url": r.url} for r in res.web]}

        try:
            return await asyncio.to_thread(_run)
        except Exception as e:
            self.logger.exception("firecrawl %s failed", mode)
            return {"output": f"调用失败：{e}", "is_error": True}

    # ──────────────────────────────────────────────
    # SSRF 守卫：解析 IP 再判，防 2130706433 / IPv6 简写 / @混淆（43 §4）
    # ──────────────────────────────────────────────
    def _is_safe_url(self, raw: str) -> bool:
        try:
            p = urlparse(raw)
            host = (p.hostname or "").lower()
        except Exception:
            return False
        if p.scheme not in ("http", "https"):
            return False
        if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or host.endswith(".local"):
            return False
        if host.startswith(("192.168.", "10.", "172.16.", "172.17.", "172.18.",
                            "172.19.", "172.2", "172.30.", "172.31.")):
            return False
        if host in ("169.254.169.254", "100.100.100.200", "metadata.google.internal"):
            return False
        try:
            for info in socket.getaddrinfo(host, None):
                ip = ipaddress.ip_address(info[4][0])
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    return False
        except Exception:
            return False
        return True

    # ──────────────────────────────────────────────
    # AI 入口：抓取网页（SSRF 守卫 + 防御性入口）
    # ──────────────────────────────────────────────
    @plugin_entry(
        id="scrape_page",
        name="抓取网页",
        description="抓取给定 URL 的正文（markdown）。仅允许 http/https 公网地址，内网地址会被拒绝。",
        input_schema={
            "type": "object",
            "properties": {"url": {"type": "string", "description": "要抓取的网页 URL"}},
            "required": ["url"],
        },
    )
    async def scrape_page(self, url: str = "", **_) -> Ok | Err:
        try:
            if not url:
                return Err(SdkError("url 不能为空"))
            if not self._is_safe_url(url):
                return Err(SdkError("不安全的 URL（内网/保留地址），已拒绝"))
            data = await self._call_firecrawl("scrape", url)
            if data.get("is_error"):
                return Err(SdkError(data["output"]))
            return Ok({"url": url, "markdown": data.get("markdown", "")})
        except SdkError as e:
            self.logger.warning("scrape failed: %s", e)
            return Err(str(e))
        except Exception as e:
            self.logger.exception("scrape unexpected error")
            return Err(str(e))

    # ──────────────────────────────────────────────
    # @llm_tool：让 LLM 直接联网搜索（参数面窄 + 防御性 schema）
    # ──────────────────────────────────────────────
    WEB_SEARCH_SCHEMA = {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "搜索关键词"}},
        "required": ["query"],
    }

    @llm_tool(
        name="web_search",
        description="联网搜索网页，返回相关结果标题与链接。用于获取实时/最新信息。",
        parameters=WEB_SEARCH_SCHEMA,
        timeout=30.0,
    )
    async def web_search(self, *, query: Any = None) -> dict:
        # query 用 Any：LLM 偶尔违反 schema，硬类型会 TypeError；入口内校验更稳（44 §5）
        if not query:
            return {"output": "query 不能为空", "is_error": True}
        data = await self._call_firecrawl("search", str(query))
        if data.get("is_error"):
            return {"output": data["output"], "is_error": True}
        return {"output": data.get("results", []), "is_error": False}

    # ──────────────────────────────────────────────
    # UI 动作 + 数据（设置面板用，见 ui/settings.tsx）
    # ──────────────────────────────────────────────
    @ui.action(id="refresh_status", label="刷新状态", refresh_context=True)
    async def refresh_status(self, **_) -> Ok | Err:
        await self._reload_config()
        return Ok({"status": "refreshed"})

    @ui.context("dashboard")
    async def dashboard_context(self) -> dict:
        raw = await self.config.dump(timeout=5.0)
        cfg = raw.get("web_assistant", {})
        return {
            "config": {"has_key": bool(cfg.get("firecrawl_api_key"))},
            "status": {"ready": True},
        }
