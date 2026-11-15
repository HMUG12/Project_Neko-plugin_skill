# 45 · 融合速查：7 个外部 skill + 本地逆向的"照抄清单"

> 本文是 `40–44` 的压缩版——只留**触发场景 + 一句话规则 + 可抄片段**。写插件时先翻这篇，需要展开再跳对应篇。
> 融合来源：mattpocock / ponytail / impeccable / hallmark / firecrawl / strix / agentskills + 本地 `plugins/` 逆向。

---

## 0 · 决策树：我现在该看哪篇？

```
要写/改代码？        → 40（工程纪律：小步/TDD/YAGNI阶梯）
要写设置面板/UI？     → 41（反 AI 味：≤1色/无嵌套卡片/对比度≥4.5:1）
要联网抓取/搜索？     → 42（firecrawl SDK 封装成深模块）
涉及外部URL/文件/密钥？→ 43（SSRF进阶/注入/Zip Slip/提示注入）
设计大型插件/抄骨架？  → 44（本地真实插件：Router/Mixin/Settings/@ui.action）
以上都要快速回顾？     → 本篇 45
```

---

## 1 · 工程纪律（来自 40，mattpocock + ponytail）

**规则**：先跑通最小壳再拆；抽象只在 YAGNI 阶梯第 3 级才上；复杂度收进深函数。

**最小可运行壳**：
```python
@neko_plugin
class MyPlugin(NekoPluginBase):
    @lifecycle(id="startup")
    async def startup(self, **_) -> Ok | Err:
        return Ok({"status": "ready"})
```

**YAGNI 阶梯（只在够低层就停）**：`(0)不做 → (1)复制 → (2)抽函数 → (3)加参数 → (4)抽类 → (5)抽象基类(需≥3实现) → (6)插件化 → (7)DSL → (8)分布式`。准备写 6–8 级前先问"能降到 1–2 级吗？"

**深函数**：entry 只做 `取参 → 调深函数 → Ok/Err`，内部重试/限流/格式转换藏起来。

---

## 2 · UI 反 AI 味（来自 41，impeccable + hallmark）

**10 秒自检**：
- [ ] 品牌色 ≤ 1 个？渐变 ≤ 1 处（仅主 CTA）？
- [ ] 无嵌套卡片（card-in-card）？阴影只给 Modal/Dropdown？
- [ ] 灰字 ≥ `#6b7280`（对比度 ≥ 4.5:1）？
- [ ] 文案具体（"保存配置"非 "Get started"）？
- [ ] 无英雄区 / 光晕 / 网格点等纯装饰？
- [ ] 状态用 `StatusBadge` 语义色，非彩色方块？

**impeccable 绝对禁令**：不用 emoji 装饰、不渐变背景、不无目的阴影、不统一 16px 圆角套娃、不彩虹色块。

---

## 3 · 网页数据集成（来自 42，firecrawl）

**规则**：用官方 SDK，密钥走配置，能力藏进深函数；同步 SDK 用 `asyncio.to_thread` 包。

```python
from firecrawl import Firecrawl
fc = Firecrawl(api_key=key, api_url=url)          # 同步客户端
doc = await asyncio.to_thread(fc.scrape, u, ["markdown"])
res = await asyncio.to_thread(fc.search, q, 5)
# 结构化抽取：fc.extract(urls=[...], prompt=..., schema=MyModel.model_json_schema())
```

**入口守卫**（见 §4）：凡用户给 URL 先 `_is_safe_url` 再调。

---

## 4 · 安全加固（来自 43，strix 攻击者视角）

**URL 输入预筛选（解析 IP 防编码绕过；⚠️ 非完整 SSRF 防护）**：
```python
import ipaddress, socket
from urllib.parse import urlparse

def _is_safe_url(self, raw: str) -> bool:
    """输入预筛选：只降低风险，挡不住 DNS rebinding / TOCTOU / 重定向 / 第三方代发。"""
    try:
        p = urlparse(raw); host = (p.hostname or "").lower()
    except Exception:
        return False
    if p.scheme not in ("http", "https"): return False
    if host in ("localhost","127.0.0.1","0.0.0.0","::1") or host.endswith(".local"): return False
    if host in ("169.254.169.254","100.100.100.200","metadata.google.internal"): return False
    try:
        for info in socket.getaddrinfo(host, None):
            ip = ipaddress.ip_address(info[4][0])
            if (ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_reserved or ip.is_multicast): return False
    except Exception:
        return False
    return True
```

**三条铁规**：① 访问用户 URL 先过输入预筛选，并清楚**执行请求那一层**的防护边界；② 拼命令/SQL 必参数化（禁 `shell=True`、禁 `*Raw` 拼用户输入、禁 `eval`）；③ 解 zip 必校验条目路径仍落在 `self.data_path` 内（Zip Slip）。敏感操作（删/发）加 `ConfirmDialog` 或 `confirm=true`，外部内容当数据不当指令（防提示注入混淆 deputy）。

---

## 5 · 本地真实插件范式（来自 44，逆向 `plugins/`）

**配置（声明式，无 `@config`）**：
```python
class Settings(PluginSettings):
    model_config = {"toml_section": "my_plugin"}
    city: str = SettingsField("", hot=True, description="默认城市")  # hot=True 自动出面板
# 读：raw = await self.config.dump(); cfg = raw.get("my_plugin", {})
# 写：await self.config.update({"my_plugin": updates})
```

**UI 动作（无 `[[plugin.ui.action]]`，用装饰器）**：
```python
@ui.action(id="refresh", label=tr("refresh"), group="main", refresh_context=True)
@plugin_entry(name="refresh", description="...", input_schema={"type":"object","properties":{}})
async def refresh(self, **_):
    return Ok({"output": "ok"})
```

**@llm_tool 防御（防 LLM 违反 schema）**：
```python
MINECRAFT_TASK_SCHEMA = {"type":"object","properties":{"task":{"type":"string"}}}  # 模块级常量
@llm_tool(name="minecraft_task", description="...", parameters=MINECRAFT_TASK_SCHEMA, timeout=300.0)
async def do_task(self, *, task: Any = None) -> dict:   # Any 而非 str，避免 TypeError
    if not task: return {"output":"task 不能为空","is_error":True}
    return {"output": await self._run(task), "is_error": False}
```

**防御性入口（异常不冒泡）**：
```python
try:
    return await self._service.run()
except SdkError as e:
    self.logger.warning("fail: %s", e); return Err(str(e))
except Exception as e:
    self.logger.exception("unexpected"); return Err(self.i18n.t("errors.internal"))
```

**大插件拆分选型**：
- 中等（≥3 业务域）→ Router 子包：`__routers__ = [ARouter, BRouter]` + `for r in self.__routers__: self.include_router(r())`（lifekit 范式）
- 超大型（几十个正交能力）→ Mixin 合成：`class P(_MixA, _MixB, ..., NekoPluginBase)`（galgame 40 Mixin / neko_roast 9 Runtime Mixin）

---

## 6 · 一句话收口

> 小步跑通 → 复杂度藏深函数 → UI 克制 → 外部调用先防 SSRF/注入 → 大插件抄本地真实骨架。这 5 句就是 7 个外部 skill + 本地逆向的全部精髓。

> 展开阅读：`40-engineering-discipline.md` · `41-ui-design-quality.md` · `42-web-data-integration.md` · `43-security-hardening.md` · `44-local-plugin-architecture.md`
