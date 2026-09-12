# 44 · 本地插件架构逆向：真实插件是怎么拆的

> 来源：直接逆向工作区 `plugins/` 下真实插件（`lifekit` / `neko_roast` / `galgame_plugin` / `sts2_autoplay` / `game_agent_minecraft` / `web_search` / `mcp_adapter` 等）的源码，提取可复用的**架构骨架**。
>
> 目的：官方指南只讲"单个文件怎么写"，但大型插件（几百~上千行）的真实形态是**拆分 + 合成**。本文档给你经过验证的三种拆分范式、生命周期/配置/工具注册的真实写法，以及防御性模式。所有结论都带 `文件:行号` 出处，**不是推断**。

---

## 0 · 三条铁证（先纠正常见误解）

逆向后确认几件和"直觉"或"旧模板"不一样的事：

1. **框架不传 `ctx` 参数**。所有 `@lifecycle` / `@plugin_entry` 方法签名统一是 `async def xxx(self, **_):`，没有、也不需要 `_ctx=None`。要上下文用 `self.ctx` 属性。
2. **配置不用 `@config` 装饰器**。真实插件用 `class Settings(PluginSettings)` + `SettingsField(hot=True)` 声明式模型，运行时靠 `self.config.dump()` / `self.config.update()` 读写（`lifekit/__init__.py:54-67`、`:124-129`、`:352-409`）。
3. **UI 动作不写进 `plugin.toml`**。TOML 里只有 `[[plugin.ui.panel]]` / `[[plugin.ui.guide]]`，**没有** `[[plugin.ui.action]]`。所有动作由 Python 的 `@ui.action(...)` 装饰器生成（`neko_roast/__init__.py:108+` 有 30+ 个；`lifekit/__init__.py:337-350`）。
4. **返回值统一是 `Ok(...)` / `Err(...)`**（来自 SDK 的 `plugin.sdk.plugin`）。入口/工具方法返回这两个，框架据此判定成功与否。

---

## 1 · 三种拆分范式（按插件体量选）

### 范式 A — Router 子包（中等插件，推荐起步）

主类只负责生命周期 + 共享基础设施，业务 entry 拆进 `routers/` 子包，在 `__init__` 里用 `self.include_router(router_cls())` 注册。

- 主类声明：`lifekit/__init__.py:50-51`（`class LifeKitPlugin(NekoPluginBase)`）
- Router 清单 + 注册：`lifekit/__init__.py:70-76`（`__routers__ = [CurrentWeatherRouter, ...]`）、`:87-88`
  ```python
  for router_cls in self.__routers__:
      self.include_router(router_cls())
  ```
- Router 子包：`lifekit/routers/__init__.py`

**何时用**：你的插件有 ≥3 个相对独立的业务域（天气 / 汇率 / 提醒…），每个域有自己的 entry + UI action。把每个域做成一个 `Router` 子类。

### 范式 B — Mixin 多重继承合成（超大型插件）

最激进的拆分：主类由 N 个 `_XxxMixin` 组成，最后继承 `NekoPluginBase`；每个 Mixin 单独成文件。

- `galgame_plugin`：主类由 **40 个** `_Galgame*Mixin` 合成（`galgame_plugin/plugin_core.py:268-310`）：
  ```python
  class GalgamePlugin(
      _GalgameAgentCommandMixin,
      _GalgameApplyRecommendedOcrCaptureProfileMixin,
      ...
      _GalgameValidateOcrScreenTemplatesMixin,
      NekoPluginBase,
  ):
      def __init__(self, ctx): ...   # :311-318
  ```
- `neko_roast`：薄主类（`__init__.py:10-13`），真实运行时 `RoastRuntime` 由 9 个 `Runtime*ApiMixin` 合成（`neko_roast/core/runtime.py:81-91`）：
  ```python
  class RoastRuntime(
      RuntimeAuthApiMixin, RuntimeInstructionApiMixin, RuntimeConfigApiMixin,
      RuntimeLiveInputApiMixin, RuntimeDeveloperApiMixin, RuntimeControlApiMixin,
      RuntimeHostingApiMixin, RuntimeStatusApiMixin, RuntimeActiveEngagementApiMixin,
  ):
      ...
  ```

**何时用**：确实有几十个互相正交的能力要聚合（游戏助手、直播互动）。**不要**在中小插件里滥用——那是过度工程（见 `40-engineering-discipline.md` §6 YAGNI 阶梯第 4–5 级）。

### 范式 C — 运行时拼装（逻辑集中但文件分散）

主类极薄，把"业务运行时"单独抽成 `core/runtime.py`，由一组 ApiMixin 拼成；主类只把这层组合起来。同范式 B 的 `neko_roast`，区别是 Mixin 拼的是"运行时"而非"插件类"本身。

---

## 2 · 生命周期 & 入口的真实签名

所有 `@lifecycle` 方法统一 `self, **_` 且返回 `Ok` / `Err`：

- `lifekit` 三件套（`lifekit/__init__.py`）：
  - `:92-93` `async def startup(self, **_):`
  - `:115-117` `async def shutdown(self, **_):` → `return Ok({"status": "stopped"})`
  - `:119-122` `async def on_config_change(self, **_):`
- `sts2_autoplay`：`:38-43` startup → `return Ok({"status": "ready", ...})`；`:45-48` shutdown
- `game_agent_minecraft`：`:217-218` startup 只做配置；`:238-239` shutdown
- `galgame_plugin`：`:3182-3183` startup；`:3265-3267` shutdown

`@plugin_entry(...)` 签名多为 `async def xxx(self, **kwargs):`（如 `lifekit:349`、`:376`；`web_search:316`），同样返回 `Ok`/`Err`。

**模板（照抄）**：
```python
@lifecycle(id="startup")
async def startup(self, **_) -> Ok | Err:
    # 只做：读配置、建连接、起后台任务（耗时操作丢 asyncio.create_task）
    return Ok({"status": "ready"})

@lifecycle(id="shutdown")
async def shutdown(self, **_) -> Ok | Err:
    return Ok({"status": "stopped"})

@lifecycle(id="config_change")
async def on_config_change(self, **_) -> Ok | Err:
    await self._reload_config()
    return Ok({"status": "reloaded"})
```

> 为什么 `**_` 而非具名参数：框架目前不传任何关键字；`**_` 是"前向兼容 + 显式忽略"的惯用法，加不加都行，加了更稳（见 `SKILL.md` 铁律 #4）。

---

## 3 · 配置模型（Settings + self.config）

**声明式**（最完整范例 `lifekit`）：
```python
# lifekit/__init__.py:54-67
class Settings(PluginSettings):
    model_config = {"toml_section": "lifekit"}
    default_city: str = SettingsField("", hot=True, description="默认城市")
    # hot=True 的字段会自动出现在 Hosted UI 设置面板
```

**读取**（`lifekit/__init__.py:124-129`）：
```python
async def _reload_config(self):
    raw = await self.config.dump(timeout=5.0)   # 取整个 [lifekit] 段
    self._cfg = raw.get("lifekit", {})
```

**暴露给 UI + 保存**（带强校验，多处 `return Err`）：
- 读：`lifekit/__init__.py:337-350` `@ui.action` + `@plugin_entry` 的 `get_config_entry` → `return Ok(dict(self._cfg))`
- 写：`lifekit/__init__.py:352-409` `update_config_entry` 先 `await self.config.update({"lifekit": updates})`，再 `_reload_config()`，异常 `return Err(SdkError(...))`

**范式结论**：
- 用户能改的字段 → `SettingsField(hot=True)` 自动出面板，不要手写 TOML `[[plugin.ui.action]]`。
- 写配置永远走 `self.config.update(...)` + 重新 `dump()`，不要直接改 `plugin.toml` 文件。
- 校验失败一律 `return Err(...)`，UI 侧 `setSettings` 会收到并提示。

---

## 4 · UI 动作与上下文（@ui.action / @ui.context）

- `@ui.context(id="dashboard", ...)`：`lifekit/__init__.py:323-333`、`neko_roast/__init__.py:104`
- `@ui.action(id=..., label=tr(...), group=..., order=..., refresh_context=True)`：`neko_roast/__init__.py:108+`（update_config、connect_live_room、bili_login 等 30+ 个）、`wechat_integration:272,308,393,404`

**范式**：每个"按钮能触发的事"都是一个 `@ui.action`，UI 用 `api.call("插件id.动作id", {...})` 调用。危险动作（清空/删除）在 UI 侧加 `ConfirmDialog`，后端仍要校验（见 `43-security-hardening.md` §8）。

---

## 5 · @llm_tool 注册（让 LLM 自动调你）

统一注册进 ToolRegistry，全 provider 通用。两个真实范例：

**最简**（`sts2_autoplay/__init__.py:50-57`）：
```python
@llm_tool(name="sts2_get_status",
          description=tr("tools.sts2_get_status.description", default="..."),
          parameters={"type": "object", "properties": {}}, timeout=10.0)
async def llm_get_status(self, **_: Any) -> JsonObject:
    return await self._service.get_status()
```

**带防御性 schema 容错**（`game_agent_minecraft/__init__.py`）：
- JSON Schema 抽成模块级常量：`:48-65`（`MINECRAFT_TASK_SCHEMA`）
- 装饰：`:293-302` `@llm_tool(name="minecraft_task", ..., timeout=300.0)`
- 关键技巧：把 `task` 声明为 `Any = None` 而非 `str`（`:303-375`），因为 LLM 偶尔违反 schema，强类型会抛 `TypeError`；改成 `Any` 后能在方法内返回结构化错误摘要而不是崩整个工具。

**范式结论**：
- schema 抽到模块级常量，别内联在装饰器里（可读性 + 复用）。
- 对"LLM 可能乱填"的参数用 `Any` + 入口内校验，比硬类型更稳。
- `@llm_tool` 返回普通 `dict`（`{"output":..., "is_error":...}`），不是 `Ok`/`Err`（见 `19-llm-workflow-design.md`）。

---

## 6 · 防御性模式（try/except → Err）

这是真实插件里出现频率最高的"安全网"写法：

**(a) 入口包装：捕获 SdkError / Exception → Err**（`sts2_autoplay/__init__.py:59-72`）：
```python
try:
    return await self._service.do_something()
except SdkError as error:
    self.logger.warning("sts2 entry failed: %s", error)
    return Err(str(error))
except Exception as error:
    self.logger.exception("Unexpected STS2 plugin entry failure")
    return Err(self.i18n.t("errors.internal", ...))
```

**(b) 网络调用静默降级**（不阻断主流程）：
- `web_search/__init__.py:48-62` `_detect_country` 用 `httpx` 包 `try/except Exception: return None`
- `lifekit/__init__.py:210-214` `geoip_locate` 失败仅 `pass`，继续 fallback

**(c) 重连接 / 资源释放广泛 try/except**（`mcp_adapter/__init__.py:339-427` 校验 `config.command` 后 try/except 返回 `False`；`:732-775` tools/call 超时 → `{"error": ...}`；`:663-713` `writer.close()` / `process.terminate()` 包裹 `try/except (CancelledError, TimeoutError, Exception))`

**(d) 状态回传**（非异常，但属"对外汇报"）：`sts2_autoplay:419-420` `self.push_message(source="game_agent_minecraft", ...)`；`game_agent_minecraft:143` 把 `push_message` 注入 service。

**范式**：任何"会失败且失败不该崩插件"的调用，要么包成 `try/except → Err`，要么降级为 `None`/`pass` 并打日志。绝不让未捕获异常从 entry 冒泡（会变成"无响应"）。

---

## 7 · plugin.toml 的标准形态

`[plugin]` 标准字段：`id` / `name` / `description` / `short_description` / `keywords` / `version` / `entry`（偶见 `passive` / `type`）。

**范例 A — lifekit**（`lifekit/plugin.toml:1-8`）：
```toml
[plugin]
id = "lifekit"
name = "生活助手"
description = "基于地理位置的多功能生活服务。..."
short_description = "Location-based life services: ..."
keywords = ["天气", "weather", ...]
version = "0.2.0"
entry = "plugin.plugins.lifekit:LifeKitPlugin"
```
附带 `[plugin.author]`、 `[plugin.i18n]`、 `[plugin.sdk]`、 `[plugin.ui]`、 `[plugin_runtime]`、 `[plugin.store]`、配置段 `[lifekit]`。

**范例 B — web_search**（`web_search/plugin.toml:1-8`）：字段**顺序可不同**（`id` 在 `version` 之后），框架兼容；`entry` 统一为 `"<python 模块路径>:<类名>"`。

**范例 C — neko_roast**（`neko_roast/plugin.toml:1-19`）：多 `passive = true`（`:17`，表示该插件不主动常驻 UI）。

**Panel 段**（`lifekit/plugin.toml:24-33`）：`[[plugin.ui.panel]]` `id="main"`、`context = "dashboard"`、`permissions = [...]`。多面板插件（如 `study_companion` 有 14 个 panel，`:115-220`）就是重复 `[[plugin.ui.panel]]` 块。

---

## 8 · 给你的"照抄骨架"

中等插件（Router 子包范式）的最小可运行骨架：
```
my_plugin/
├── plugin.toml            # [plugin] + [[plugin.ui.panel]] + [my_plugin] 配置段
├── __init__.py            # 主类：@neko_plugin + startup/shutdown(**_)→Ok/Err + include_router
├── routers/
│   ├── __init__.py
│   └── weather.py         # class WeatherRouter(PluginRouter): @plugin_entry / @ui.action
└── ui/settings.tsx        # 设置面板（hot 字段自动出现，无需手写 action）
```
主类 `__init__`：
```python
@neko_plugin
class MyPlugin(NekoPluginBase):
    __routers__ = [WeatherRouter]
    def __init__(self, ctx):
        super().__init__(ctx)
        for r in self.__routers__:
            self.include_router(r())
```

> 交叉阅读：`02-python-plugin.md`（装饰器与模式）、`20-plugin-router.md`（Router 拆分）、`03-ui-settings.md`（设置面板）、`40-engineering-discipline.md`（先跑通再拆，别过度 mixin）、`43-security-hardening.md`（入口校验与 Err）。
