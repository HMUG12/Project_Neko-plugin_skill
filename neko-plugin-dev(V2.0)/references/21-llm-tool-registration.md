# 21 - @llm_tool：LLM 工具调用注册

## 概述

让 LLM 可以在对话过程中**直接调用**插件提供的功能。例如插件提供 `get_weather`，LLM 在用户问"北京天气怎么样"时会自动调用它，等待返回结果，再用返回值生成最终回复。

本机制由 `main_logic/tool_calling.py` 的 `ToolRegistry` 支撑，对所有支持工具调用的 provider（OpenAI / Gemini / GLM / Qwen Omni / StepFun 等）统一抽象。

---

## TL;DR：推荐路径 — @llm_tool

如果你写的是常规 `NekoPluginBase` 插件，直接用 SDK 的 `@llm_tool` 装饰器。注册、注销、回调路由、shutdown 清理全自动，零样板代码：

```python
from plugin.sdk.plugin import neko_plugin, NekoPluginBase, llm_tool, lifecycle, Ok

@neko_plugin
class WeatherPlugin(NekoPluginBase):
    @lifecycle(id="startup")
    async def startup(self, **_):
        return Ok({"status": "ready"})

    @llm_tool(
        name="get_weather",
        description="查询指定城市的天气。",
        parameters={
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名，如 '北京'"},
            },
            "required": ["city"],
        },
    )
    async def get_weather(self, *, city: str):
        return {"city": city, "temp_c": 22, "weather": "晴"}
```

整个集成就这些。装饰器在插件构造期间被 SDK 基类自动发现；插件服务通过 HTTP 向 main_server 注册工具，并把 LLM 的 dispatch 通过既有的 IPC 路由回插件进程；插件停止时，每个注册的工具会以 best-effort 方式从 main_server 清掉。

---

## 架构

分两层叠在一起：

### 第一层 — 原始 HTTP（通用）

```
┌──────────────────┐  HTTP /api/tools/register   ┌──────────────────────┐
│  Plugin (process)│ ───────────────────────────▶│  Main Server         │
│                  │                             │  - ToolRegistry      │
│  callback_url    │ ◀──── HTTP POST tool ──────│  - Realtime / Offline│
│  /tool_invoke    │       call invocation      │    LLM clients       │
└──────────────────┘                             └──────────────────────┘
```

1. 插件通过 HTTP 注册工具到 main_server 的 `ToolRegistry`
2. LLM 触发工具调用时，main_server POST 到插件的 `callback_url`
3. 插件返回 JSON 结果，main_server 把结果喂回 LLM 继续生成

直接走这一层只在 SDK helper 覆盖不到的场景才必要。

### 第二层 — @llm_tool SDK helper（插件首选）

```
                 (1) IPC: LLM_TOOL_REGISTER
                          ┌──────────────────────────────┐
                          ▼                              │
┌────────────────────┐         ┌──────────────────────┐  │  ┌─────────────────┐
│ Plugin process     │         │ user_plugin_server   │──┼─▶│  Main Server    │
│  @llm_tool methods │         │ /api/llm-tools/      │  │  │  ToolRegistry   │
│                    │◀────────│  callback/{pid}/{n}  │◀─┼──│ POSTs callback  │
│  IPC trigger       │  (3)    │ POST main_server     │  │  │ when LLM picks  │
└────────────────────┘  via    └──────────────────────┘  │  │ the tool        │
                       host.trigger      ▲               │  └─────────────────┘
                                          │              │           │
                                          └──────────────┘           │
                                              (2) HTTP /api/tools/register
                                                  with callback_url pointing
                                                  back at user_plugin_server
```

插件进程不直接和 main_server 说 HTTP，它发一条 IPC，host 翻译成第一层的 HTTP 调用；main_server 的 dispatch 也走同一套 IPC trigger 管线（与 `@plugin_entry` 完全一致）回到插件。

---

## @llm_tool 装饰器详解

定义在 `plugin/sdk/plugin/llm_tool.py`，从 SDK 顶层导入：

```python
from plugin.sdk.plugin import llm_tool

@llm_tool(
    *,
    name: str | None = None,        # 默认取方法的 __name__
    description: str = "",          # 给 LLM 看的，决定它什么时候调用
    parameters: dict | None = None, # JSON Schema（OpenAI 风格）；默认无参数
    timeout: float = 30.0,          # 单次调用超时（秒，≤ 300）
    role: str | None = None,        # None = 全局，或指定猫娘名
)
```

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | `str \| None` | 方法名 | 工具名（≤64 字符），LLM 看到的就是它 |
| `description` | `str` | `""` | 描述给 LLM 看，决定它什么时候调用 |
| `parameters` | `dict \| None` | `None` | JSON Schema，OpenAI 风格 |
| `timeout` | `float` | `30.0` | 单次调用超时，最大 300 秒 |
| `role` | `str \| None` | `None` | `None`=所有猫娘，指定字符串=只给那个猫娘用 |

### 方法签名

被装饰的方法以 kwargs 形式接收解析后的 JSON 参数。**建议在签名里用 `*` 强制 keyword-only：**

```python
@llm_tool(name="search", parameters={
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "搜索关键词"},
        "limit": {"type": "integer", "default": 10},
    },
    "required": ["query"],
})
async def search(self, *, query: str, limit: int = 10):
    # query 一定会被传入，limit 有默认值
    ...
```

`name` 必须匹配 `[A-Za-z0-9_.\-]{1,64}`，这样能直接拼进 callback URL 路径段不需要转义。

---

## 错误返回

普通值（str / dict / int ...）会作为成功结果回给 LLM。要不抛异常但向 LLM 标记工具级错误，返回这个 shape：

```python
return {
    "output": {"reason": "city not found"},
    "is_error": True,
    "error": "CITY_NOT_FOUND"
}
```

handler 里直接 `raise` 也会被翻译成错误回给 LLM（异常类名 + message 作为 error），插件本身不会崩溃 — 只有那一次工具调用算失败。

---

## 命令式 API

参数 schema 在运行期才能确定的工具（比如根据配置动态生成）走命令式 API：

```python
# NekoPluginBase 实例方法
self.register_llm_tool(
    name="custom_tool",
    description="...",
    parameters={"type": "object", "properties": {...}},
    handler=my_async_callable,
    timeout=30.0,
    role=None,
)

# 取消注册
self.unregister_llm_tool(name)

# 列出当前已注册的工具
tools = self.list_llm_tools()  # → list[dict]
```

> 重名会抛 `EntryConflictError`。

---

## 生命周期与时序

1. `@llm_tool` 装饰过的方法在 `NekoPluginBase.__init__` 末尾自动注册，即 `super().__init__(ctx)` 一返回就完成
2. handler 真正执行要等到 LLM 选中该工具，所以在子类 `__init__` 还没 setup 完的时候完成注册是安全的
3. IPC 通知（`LLM_TOOL_REGISTER`）会缓存在插件 host 的 message queue 上。如果通知到达时 main_server 还没起来，注册调用会失败 — 等 main_server 起来后通过 reload 插件或命令式 API 再注册一次
4. 插件停止时，`lifecycle_service.stop_plugin` 会调 `clear_plugin_tools`，发 `POST /api/tools/clear`，body 为 `{"source": "plugin:{plugin_id}", "role": null}`，一次性清掉该插件注册的所有工具。这步是 best-effort

---

## main_server 重启会发生什么

> ⚠️ **重要：** `tool_registry` 是 `LLMSessionManager` 的内存属性，main_server 重启会全部丢失。

两种应对策略：

### 策略 A：插件比 main_server 长寿（更常见）

插件需要监听 main_server 心跳/连接断开事件，重连后重新调 register。最简单的做法是插件内起一个后台任务：

```python
import asyncio

async def _health_check_loop(self):
    """后台任务：定期检查工具是否还在，不在就重新注册。"""
    while True:
        await asyncio.sleep(30)
        try:
            # 检查工具是否还在
            tools = await self._list_registered_tools()
            expected = self.list_llm_tools()
            if len(tools) != len(expected):
                self.logger.warning("工具丢失，重新注册...")
                await self._re_register_all()
        except Exception:
            pass  # main_server 可能挂了，下次再试
```

### 策略 B：插件跟 main_server 同生死

只要插件启动 hook 里调了注册，main_server 重启时插件也会被重启，自然会重新注册。

---

## 切换猫娘

每个猫娘有独立的 `LLMSessionManager` 实例，但它们共享插件注册的工具（取决于 `role` 字段）：

| role 设置 | 行为 |
|-----------|------|
| `role: null` | 注册到所有猫娘 → 切换不需要重新注册 |
| `role: "小八"` | 只注册到指定猫娘 → 切到别的猫娘后这个工具不可用 |

切换猫娘不会重启 main_server，所以不会丢失 registry。

---

## 注意事项

1. **不要在工具名里放敏感信息** — LLM 会在生成时把工具名写进 `tool_calls`，最终持久化进对话历史
2. **callback_url 必须指向本机 loopback** — 服务端校验 host 在 `127.0.0.0/8` / `::1` / `localhost` 之内
3. **timeout_seconds ≤ 300** — 超过 5 分钟的同步工具应改为"立即返回 + 通过插件自己的事件机制异步推送结果"
4. **工具失败要返回明确的错误** — `is_error: true` + 一句人类可读的 `error`，不要静默返回空结果
5. **重复 register 是覆盖语义** — 同名工具会被新的覆盖，可以用来热更新参数 schema
6. **output 字段提取规则** — main_server 调用 `body.get("output", body)`，建议始终显式包一层 `{"output": ...}`

---

## 与 @plugin_entry 的区别

| 特性 | `@plugin_entry` | `@llm_tool` |
|------|-----------------|-------------|
| 调用方式 | 用户主动/插件间调用 | LLM 自动选择调用 |
| 参数 schema | `input_schema` 或 `params` | `parameters`（JSON Schema） |
| 返回值 | `Ok(...)` / `Err(...)` | 普通 dict / 错误 shape |
| 超时控制 | `timeout` 参数 | `timeout` 参数 |
| 用户可见 | 面板中可见 | 对 LLM 可见，用户无感知 |
| UI 集成 | 可通过 `@ui.action` 暴露 | 不涉及 UI |

---

## 完整示例：带数据库的工具

```python
from plugin.sdk.plugin import neko_plugin, NekoPluginBase, llm_tool, lifecycle, Ok, unwrap

@neko_plugin
class NotesToolPlugin(NekoPluginBase):

    @lifecycle(id="startup")
    async def startup(self, **_):
        # 确保表存在
        async with unwrap(await self.db.session()) as session:
            await session.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await session.commit()
        return Ok({"status": "ready"})

    @llm_tool(
        name="create_note",
        description="创建一条新笔记。",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "笔记标题"},
                "content": {"type": "string", "description": "笔记内容"},
            },
            "required": ["title", "content"],
        },
    )
    async def create_note(self, *, title: str, content: str):
        async with unwrap(await self.db.session()) as session:
            await session.execute(
                "INSERT INTO notes (title, content) VALUES (?, ?)",
                (title, content)
            )
            await session.commit()
        return {"output": f"笔记「{title}」已创建", "is_error": False}

    @llm_tool(
        name="search_notes",
        description="搜索笔记，支持按关键词模糊匹配标题。",
        parameters={
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "搜索关键词"},
            },
            "required": ["keyword"],
        },
    )
    async def search_notes(self, *, keyword: str):
        async with unwrap(await self.db.session()) as session:
            cursor = await session.execute(
                "SELECT title, content FROM notes WHERE title LIKE ?",
                (f"%{keyword}%",)
            )
            rows = cursor.fetchall()
        if not rows:
            return {"output": f"没有找到包含「{keyword}」的笔记", "is_error": False}
        results = [{"title": r["title"], "content": r["content"]} for r in rows]
        return {"output": {"count": len(results), "notes": results}, "is_error": False}
```

---

## 相关文档

- [02 - Python 插件核心](02-python-plugin.md) — @plugin_entry 基础
- [08 - AI 友好设计](08-ai-friendly-design.md) — description 三要素、input_schema 设计
- [19 - LLM 对话工作流设计](19-llm-workflow-design.md) — check_setup、多入口编排
