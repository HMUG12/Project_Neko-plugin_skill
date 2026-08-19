# N.E.K.O 官方插件开发指南（权威总结）

> 本文基于官方开发者文档 **project-neko.online** 与 GitHub 仓库 `Project-N-E-K-O/N.E.K.O` 的 `plugins/` 真实代码逐条核实整理，用于补充/校正 `neko-plugin-dev` Skill 的实战经验。
>
> 关键勘误见文末「§11 与实战 Skill 的勘误」。

---

## 1. 概览与安装

N.E.K.O 插件是放在 `plugins/` 目录下的独立文件夹，每个插件至少包含：

- `plugin.toml` — 插件清单（元数据、入口、依赖、UI、i18n、SDK 约束）
- `__init__.py` — 用 `@neko_plugin` 装饰的插件类，内部用 `@plugin_entry` / `@lifecycle` 等注册能力

安装方式：把插件文件夹复制到 NEKO 的 `plugins/<your-plugin>/`，重启程序，或输入 `/plugin load <id>`（若支持）。

---

## 2. 最小插件（Quick Start）

`plugin.toml`：

```toml
[plugin]
id = "greeter"
name = "Greeter"
version = "1.0.0"
entry = "plugin.plugins.greeter:GreeterPlugin"  # 官方格式：plugin.plugins.目录名:类名
description = "一个会打招呼的示例插件"

[plugin.sdk]
version = ">=1.0"   # 按主程序实际 SDK 版本约束填写
```

`__init__.py`：

```python
from plugin.commons.types import Ok, JsonObject
from plugin.commons.utils import tr
from plugin.sdk.plugin import neko_plugin, plugin_entry
from typing import Annotated

@neko_plugin
class GreeterPlugin:
    @plugin_entry(id="greet", name="Greet", description="Say hello to someone")
    async def greet(self, name: Annotated[str, "Name to greet"] = "World") -> JsonObject:
        return Ok({"message": f"Hello, {name}!"})
```

要点：

- `@neko_plugin` 装饰在类上，**必须**。
- 入口用 `@plugin_entry(id=, name=, description=...)`；参数可用 `Annotated[type, "描述"]` 类型提示，SDK 会自动生成 JSON Schema。
- 聊天里输入 `@your-plugin ...` 或在 UI 中触发即可调用。
- 上下文**不**通过函数参数传入；用 `self.ctx`（见 §4）。

---

## 3. 装饰器全集

| 装饰器 | 作用 | 备注 |
|--------|------|------|
| `@neko_plugin` | 标记插件类 | 必须 |
| `@plugin_entry(id, name, description, input_schema, params, kind, auto_start, persist, model_validate, timeout, llm_result_fields, llm_result_model, metadata)` | 注册 AI 可调用入口 | 三选一声明参数（见 §5） |
| `@lifecycle(id="startup"\|"shutdown"\|"reload"\|"freeze"\|"unfreeze"\|"config_change")` | 生命周期钩子 | 仅做真实初始化/清理 |
| `@timer_interval(id, seconds, name, auto_start)` | 定时器 | 独立线程，需 `new_event_loop()` |
| `@ui.action(label=tr(...), tone="primary", refresh_context=True)` | Hosted UI 行为 | 常与 `@plugin_entry` 叠加，官方示例顺序：`@ui.action` 在上、`@plugin_entry` 在下 |
| `@ui.context(id)` | Hosted UI 数据 | id 须匹配 `plugin.toml` 的 `[[plugin.ui.panel]].context` |
| `@llm_tool(name, description, parameters, timeout, role)` | 注册 LLM 自动调用工具 | 见 §6 |
| `@message` / `@on_event` / `@custom_event` | 消息/事件订阅 | — |
| `@hook` / `before_entry` / `after_entry` / `around_entry` / `replace_entry` | 入口钩子（包装/替换） | monkey-patch 式 |
| `@quick_action` | 快捷操作 | — |
| `@plugin.entry` / `@plugin.lifecycle` / `@plugin.hook` / `@plugin.timer` | 等价命名空间写法 | 与上文同名装饰器等价 |

导入方式（推荐使用命名空间，避免散装导入）：

```python
from plugin.sdk.plugin import plugin_entry, lifecycle, timer_interval, ui, llm_tool, hook, message
# 或
from plugin.sdk.plugin import neko_plugin, plugin_entry
```

> **签名铁律（已纠正）**：入口/生命周期/UI 方法的签名里**不要加 `_ctx=None`**（框架从不传入该参数）。需要运行时上下文用 `self.ctx`。`**_` 仅作为前向兼容 catch-all（官方示例普遍写，但非强制；官方 Best Practice 建议「仅在有意消费额外参数时」才加）。

---

## 4. `NekoPluginBase` 可用属性与方法

| 属性/方法 | 说明 |
|-----------|------|
| `self.ctx` | 运行时上下文 `PluginContext`（替代不存在的 `_ctx` 参数） |
| `self.config` | 插件配置（`dump()` / `update()` / `save()`） |
| `self.store` | 键值持久化（`get` / `set` / `delete`） |
| `self.db` | SQLite（`[plugin.database] enabled=true` 时可用） |
| `self.logger` | 日志（支持 `loguru` 花括号与 stdlib `%`） |
| `self.bus` | 事件总线（`events` / `memory` 惰性查询，支持 `.watch()`） |
| `self.plugins` | 跨插件调用（`call_entry("other_plugin:entry", {...})`） |
| `self.plugin_id` / `self.config_dir` / `self.metadata` / `self.system_info` | 元信息 |
| `report_status(dict)` | 上报状态 |
| `push_message(source, visibility, ai_behavior, parts, priority)` | 推送消息（v2 schema，见下） |
| `data_path(*parts)` | 返回插件私有目录下的安全路径 |
| `include_router` / `exclude_router` | 注册/注销 HTTP Router |
| `register_dynamic_entry` / `unregister_dynamic_entry` | 动态注册入口 |
| `register_llm_tool` / `unregister_llm_tool` | 动态注册 LLM 工具 |
| `run_update(async_fn, ...)` | 长任务中保持 NEKO 响应 |
| `finish()` / `export_push(...)` | 结束/导出推送 |

`push_message` v2 参数：

- `source`: `"plugin"` | `"system"`
- `visibility`: `"user"` | `"group"`
- `ai_behavior`: `"mention"` | `"ignore"` | `"summary"`
- `parts`: `[{"type": "text"|"image"|"file"|"card", "text": ...}]`
- `priority`: `0–10`（`0-2`=低/信息，`3-5`=中/一般通知，`6-8`=高/重要通知，`9-10`=紧急）

---

## 5. 参数声明的三种方式（任选其一）

```python
# 方式 A：input_schema（JSON Schema，最常用，真实插件主流）
@plugin_entry(id="x", name="X", description="...", input_schema={
    "type": "object",
    "properties": {"param1": {"type": "string", "description": "参数描述"}},
    "required": ["param1"],
})

# 方式 B：params = Pydantic 模型（类型安全，自动校验）
class MyParams(BaseModel):
    param1: str
@plugin_entry(id="x", name="X", description="...", params=MyParams)

# 方式 C：Annotated 类型提示（Quick Start 写法，自动生成 schema）
@plugin_entry(id="greet", name="Greet", description="Say hello")
async def greet(self, name: Annotated[str, "Name to greet"] = "World"):
    ...
```

---

## 6. `@llm_tool`（LLM 工具调用）

与 `@plugin_entry` 的区别：用 `name=` 而非 `id=`，参数 schema 用 `parameters=` 而非 `input_schema`；返回**普通 dict**（非 `Ok/Err`）；错误用 `{"output":{...}, "is_error": True, "error": "CODE"}`。

```python
from plugin.commons.types import JsonObject
from plugin.sdk.plugin import llm_tool

@llm_tool(
    name="get_weather",
    description="查询天气",
    parameters={"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
    timeout=30.0,
)
async def get_weather(self, *, city: str):   # 框架以 kwargs 传参，推荐 * 强制 keyword-only
    return {"output": {"city": city, "temp": 22}, "is_error": False}
```

> 真实插件（如 `sts2_autoplay`、`game_agent_minecraft`）用 `async def llm_xxx(self, **_: Any) -> JsonObject:` 配合 `parameters` schema，两种签名均可。

---

## 7. 生命周期钩子

| id | 触发时机 |
|----|----------|
| `startup` | 插件加载完成 |
| `shutdown` | 程序关闭 |
| `reload` | 配置/代码热重载 |
| `freeze` | 资源紧张时挂起 |
| `unfreeze` | 恢复 |
| `config_change` | 配置变更后 |

```python
@lifecycle(id="startup")
async def on_startup(self, **_):
    await self.store.set("counter", 0)

# 注意：真实插件统一用 **_ 然后 self.config.dump() 重新读取；
# 官方 Best Practices 示例写成 (self, old_config, new_config)，两种写法二选一，
# 推荐以 **_ + 重新 dump 保证兼容性。
@lifecycle(id="config_change")
async def on_config_change(self, **_):
    cfg = await self.config.dump()
    self.theme = cfg.get("settings", {}).get("theme", self.theme)
```

---

## 8. Hosted UI（设置面板）

`@ui.context(id=...)` 提供数据，`@ui.action` 处理行为（常叠加 `@plugin_entry`）。TSX 文件放在 `ui/`，`plugin.toml` 用 `[[plugin.ui.panel]]` 声明 `context` 与 `entry`。

**组件全表（官方 `@neko/plugin-ui`）**：

| 分类 | 组件 |
|------|------|
| 布局 | `Page` `Card` `Section` `Stack` `Grid` `Heading` `Divider` |
| 文本/展示 | `Text`(color: primary/secondary/muted) `StatCard` `KeyValue` `DataTable` `List` `JsonView` `CodeBlock` `Alert` `Tip` `Warning` `InlineError` `EmptyState` |
| 表单/输入 | `Field` `Input` `Textarea` `Select` `Switch` `Form` `ActionForm` |
| 状态/交互 | `StatusBadge` `ActionButton` `RefreshButton` `Modal` `ConfirmDialog` `AsyncBlock` |
| Hooks | `useLocalState` `useAsync` `useForm` `useToast` `useConfirm` `useDebounce` `useDebouncedState` `useI18n` |

**TSX 沙箱限制**：禁止使用 npm 包、class 组件、React Context / Portals / Suspense。
**重命名**：`Table`→`DataTable`、`Button`→`ActionButton`、`useState`→`useLocalState`；`Text` color **不支持** `danger`/`warning`/`default`；**没有 `Slider` 组件**（用 `Input` 数字或 `Select` 替代）。

```python
@ui.context(id="settings")
async def settings_context(self, **_) -> dict:
    return {"theme": self.theme}

@ui.action(
    label=tr("actions.save.label", default="保存"),
    tone="primary",
    refresh_context=True,  # 保存后自动刷新面板
)
async def save_settings(self, theme: str, **_) -> JsonObject:
    self.theme = theme
    cfg = await self.config.dump()
    cfg["settings"] = {"theme": theme}
    await self.config.save(cfg)
    return Ok({"ok": True})
```

---

## 9. 五个完整示例（均可直接运行）

### 9.1 hello_world

```python
from plugin.commons.utils import tr
from plugin.commons.types import Ok, JsonObject
from plugin.sdk.plugin import neko_plugin, plugin_entry

@neko_plugin
class HelloWorldPlugin:
    """Hello World 示例插件。"""
    def __init__(self):
        self.greeting = "Hello"

    @plugin_entry(id="hello", name=tr("Hello"), description=tr("返回问候语"))
    async def hello(self, **_) -> JsonObject:
        return Ok({"greeting": self.greeting})
```

### 9.2 kv_store

```python
from plugin.commons.types import Ok, Err, JsonObject
from plugin.commons.utils import tr
from plugin.sdk.plugin import neko_plugin, plugin_entry, lifecycle

@neko_plugin
class KvStorePlugin:
    """键值存储示例插件。"""
    def __init__(self):
        self.prefix = "kv:"

    @lifecycle(id="startup")
    async def on_startup(self, **_) -> None:
        await self.store.set("counter", 0)

    @plugin_entry(id="kv_get", name=tr("读取"), description=tr("读取键值"))
    async def kv_get(self, key: str, **_) -> JsonObject:
        value = await self.store.get(self.prefix + key)
        if value is None:
            return Err("KEY_NOT_FOUND", tr("键不存在: {key}").format(key=key))
        return Ok({"value": value})

    @plugin_entry(id="kv_set", name=tr("写入"), description=tr("写入键值"))
    async def kv_set(self, key: str, value: str, **_) -> JsonObject:
        await self.store.set(self.prefix + key, value)
        return Ok({"ok": True})
```

### 9.3 config_panel

```python
from plugin.commons.types import Ok, JsonObject
from plugin.commons.utils import tr
from plugin.sdk.plugin import neko_plugin, plugin_entry, ui

@neko_plugin
class ConfigPanelPlugin:
    """带设置面板的示例插件。"""
    def __init__(self):
        self.theme = "light"

    @ui.context(id="settings")
    async def settings_context(self, **_) -> dict:
        return {"theme": self.theme}

    @ui.action(
        label=tr("actions.save.label", default="保存"),
        tone="primary",
        refresh_context=True,  # 保存后自动刷新面板
    )
    async def save_settings(self, theme: str, **_) -> JsonObject:
        self.theme = theme
        cfg = await self.config.dump()
        cfg["settings"] = {"theme": theme}
        await self.config.save(cfg)
        return Ok({"ok": True})
```

### 9.4 scheduler

```python
from plugin.commons.types import Ok, JsonObject
from plugin.commons.utils import tr
from plugin.sdk.plugin import neko_plugin, plugin_entry, timer_interval

@neko_plugin
class SchedulerPlugin:
    """定时任务示例插件。"""
    def __init__(self):
        self.count = 0

    @timer_interval(id="tick", seconds=10, name=tr("心跳"), auto_start=True)
    async def tick(self, **_) -> None:
        self.count += 1
        self.report_status({"ticks": self.count})

    @plugin_entry(id="ticks", name=tr("查看次数"), description=tr("查看已触发次数"))
    async def ticks(self, **_) -> JsonObject:
        return Ok({"ticks": self.count})
```

### 9.5 todo

```python
from plugin.commons.types import Ok, Err, JsonObject
from plugin.commons.utils import tr
from plugin.sdk.plugin import neko_plugin, plugin_entry, lifecycle

@neko_plugin
class TodoPlugin:
    """待办事项示例插件。"""
    def __init__(self):
        self.items = []

    @lifecycle(id="startup")
    async def on_startup(self, **_) -> None:
        saved = await self.store.get("todos") or []
        self.items = saved

    @plugin_entry(id="add", name=tr("添加"), description=tr("添加待办"))
    async def add(self, title: str, done: bool = False, **_) -> JsonObject:
        self.items.append({"title": title, "done": done})
        await self.store.set("todos", self.items)
        return Ok({"item": self.items[-1]})

    @plugin_entry(id="list", name=tr("列表"), description=tr("列出待办"))
    async def list_items(self, **_) -> JsonObject:
        return Ok({"items": self.items})

    @plugin_entry(id="toggle", name=tr("切换"), description=tr("切换完成状态"))
    async def toggle(self, index: int, **_) -> JsonObject:
        if index < 0 or index >= len(self.items):
            return Err("INDEX_OUT_OF_RANGE", tr("索引越界"))
        self.items[index]["done"] = not self.items[index]["done"]
        await self.store.set("todos", self.items)
        return Ok({"item": self.items[index]})

    @plugin_entry(id="remove", name=tr("删除"), description=tr("删除待办"))
    async def remove(self, index: int, **_) -> JsonObject:
        if index < 0 or index >= len(self.items):
            return Err("INDEX_OUT_OF_RANGE", tr("索引越界"))
        removed = self.items.pop(index)
        await self.store.set("todos", self.items)
        return Ok({"removed": removed})
```

---

## 10. Best Practices（官方）

1. 所有 entry 返回 `Ok` / `Err`；跨插件调用需处理 `Err`。
2. 生命周期只做真正的初始化/清理；耗时操作丢 `asyncio.create_task`。
3. 入口参数：推断 schema / 显式 `input_schema` / Pydantic `params` **三选一**。
4. 处理器签名显式声明用到的字段；`**_` 仅在「有意」消费额外参数时使用。
5. 普通日志走 `logger`；隐私敏感原始内容**绝不**进日志。
6. 用定时器时务必用锁保护共享状态。
7. `plugin.toml` 的 `[plugin].entry` 路径与 SDK 版本约束必须正确。

---

## 11. 与实战 Skill 的勘误

| 旧版 Skill 说法 | 官方/真实代码事实 | 修正 |
|----------------|------------------|------|
| 所有 `@plugin_entry`/`@ui.action` 必须含 `_ctx=None` | 框架从不传入该参数；`plugins/` 真实代码 0 处使用 | 删掉 `_ctx=None`；上下文用 `self.ctx` |
| 所有 `@lifecycle` 必须含 `**_` | `**_` 是可选前向兼容 catch-all | 可加但非强制；Best Practice 建议「有意才加」 |
| `on_config_change(self, old_config, new_config)` | 真实插件统一 `async def on_config_change(self, **_)` 后 `self.config.dump()` | 采用 `**_` + 重新 dump |
| 存在 `Slider` UI 组件 | 官方组件库**无** Slider | 改用 `Input`(数字) / `Select` |
| `@llm_tool` 用 `id=`/`input_schema=` | 实际用 `name=`/`parameters=`，返回普通 dict | 见 §6 |
| 仅 `loguru` 花括号 | `logger` 同时支持 `loguru` `{}` 与 stdlib `%` | 两者皆可 |

---

*参考来源：project-neko.online（Plugins 文档）、github.com/Project-N-E-K-O/N.E.K.O 仓库 `plugins/` 目录真实代码。*
