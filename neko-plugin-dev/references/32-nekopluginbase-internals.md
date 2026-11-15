# 32 — NekoPluginBase 内部机制深度解析

> **来源**：N.E.K.O-main `plugin/sdk/plugin/base.py` + `plugin/sdk/shared/core/base.py` 深度逆向分析  
> **适用**：理解插件基类的完整内部机制，包括 entry 收集、Router 绑定、SDK 上下文封装

---

## 1. 类继承层次

```
NekoPluginBase (shared/core/base.py)
    ↑ 共享基础实现
    │
NekoPluginBase (sdk/plugin/base.py)
    ↑ 插件开发者使用的基类
    │
YourPlugin (你的插件)
```

两层设计的原因：
- `shared/core/base.py`：纯逻辑，不依赖任何框架细节，可独立测试
- `sdk/plugin/base.py`：继承共享基础，添加框架集成（PluginRouter、LLM Tool、Static UI 等）

---

## 2. 构造函数全流程

### 2.1 shared/core/base.py 的 __init__

```python
def __init__(self, ctx: PluginContextProtocol):
    # 1. 保存原始宿主上下文
    self._host_ctx = ctx

    # 2. 包装为 SDK 上下文（提供更友好的 API）
    self.ctx = ensure_sdk_context(ctx)

    # 3. 惰性导入 PluginConfig 和 Plugins（避免循环导入）
    from .config import PluginConfig
    from .plugins import Plugins

    # 4. 初始化核心属性
    self.config = PluginConfig(self.ctx)
    self.plugins = Plugins(self.ctx)
    self._routers: list[RouterProtocol] = []

    # 5. 设置日志
    self.logger = get_plugin_logger(ctx.plugin_id)
    self.sdk_logger = self.logger  # 别名

    # 6. 惰性导入存储/数据库/状态持久化
    self.plugin_dir = self._resolve_plugin_dir()
    self.store = PluginStore(self.ctx) if store_enabled else None
    self.db = PluginDatabase(self.ctx) if db_enabled else None
    self.state = PluginStatePersistence(self.ctx, backend=state_backend)
```

### 2.2 sdk/plugin/base.py 的 __init__

```python
def __init__(self, ctx: PluginContextProtocol):
    super().__init__(ctx)  # 调用共享基础

    # 1. 注册 LLM 工具
    self._llm_tools: dict[str, LlmToolMeta] = {}
    self._collect_llm_tools()

    # 2. 注册 Static UI
    self._static_uis: dict[str, StaticUiMeta] = {}
    self._collect_static_uis()

    # 3. 注册动态 entry
    self._dynamic_entries: dict[str, EventMeta] = {}

    # 4. 注册 list_actions（前端列表操作）
    self._list_actions: list[dict] = []

    # 5. 设置 export_push（导出推送）
    self._export_push_enabled = False
```

---

## 3. Entry 收集机制

### 3.1 装饰器注册

```python
@plugin_entry(id="my_action")
async def my_action(self, *, param: str):
    return Ok({"result": param})
```

内部原理：
```python
# decorators.py 中的 @plugin_entry 实现（简化）
def plugin_entry(*, id: str, description: str = "", ...):
    def decorator(func):
        # 在函数上存储元数据
        setattr(func, EVENT_META_ATTR, EventMeta(
            id=id,
            description=description,
            handler=func,
            ...
        ))
        return func
    return decorator
```

### 3.2 collect_entries 流程

```python
def collect_entries(self) -> dict[str, EventMeta]:
    """收集所有 entry（装饰器 + 动态）"""
    entries = {}

    # 1. 扫描装饰器注册的 entry
    for name, obj in inspect.getmembers_static(type(self)):
        if name.startswith('_'):
            continue
        # 展开 staticmethod/classmethod
        if isinstance(obj, (staticmethod, classmethod)):
            obj = obj.__func__
        meta = getattr(obj, EVENT_META_ATTR, None)
        if meta and meta.id:
            handler = getattr(self, name)  # 获取绑定方法
            entries[meta.id] = meta

    # 2. 合并 Router 的 entry
    for router in self._routers:
        router_entries = router.collect_entries()
        for eid, meta in router_entries.items():
            full_id = f"{router.prefix}:{eid}" if router.prefix else eid
            entries[full_id] = meta

    # 3. 合并动态注册的 entry
    entries.update(self._dynamic_entries)

    return entries
```

### 3.3 关键细节

1. **`inspect.getmembers_static`** 而非 `inspect.getmembers`：避免触发 property/descriptor 的 `__get__`
2. **跳过 `_` 开头**：私有属性不会被收集为 entry
3. **`staticmethod`/`classmethod` 展开**：取 `__func__` 获取底层函数
4. **Router 前缀合并**：`router.prefix + ":" + entry_id`

---

## 4. PluginRouter 绑定机制

### 4.1 include_router

```python
def include_router(self, router: RouterProtocol):
    """在 __init__ 中注册 Router"""
    # 1. 绑定 Router 到插件
    if hasattr(router, '_bind'):
        router._bind(self)  # 内部方法，非协议方法

    # 2. 加入路由器列表
    self._routers.append(router)

    # 3. 调用 on_mount 生命周期
    if hasattr(router, 'on_mount'):
        router.on_mount()
```

### 4.2 Router 的 _bind 内部方法

```python
# router.py 中的 _bind（非协议方法，通过 getattr 访问）
def _bind(self, plugin_instance):
    """将 Router 绑定到主插件实例"""
    self._main_plugin = plugin_instance
    self._is_bound = True

    # 代理属性：Router 可以访问主插件的 ctx/config/plugins
    self._ctx = plugin_instance.ctx
    self._config = plugin_instance.config
    self._plugins = plugin_instance.plugins
```

### 4.3 Router 的懒解析

Router 中的 `@plugin_entry` 装饰器条目不立即解析，而是延迟到 `collect_entries()` 调用时：

```python
# Router.__init__ 中
def __init__(self, ...):
    self._decorated_entries: list[tuple[str, EventMeta, callable]] = []
    self._collect_decorated_entries()  # 只扫描，不解析

# 原因：include_router() 之后可能 set_prefix()，提前解析会导致 prefix 错误
```

---

## 5. SDK 上下文封装 (ensure_sdk_context)

### 5.1 封装目的

原始 `PluginContext` 接口较底层，SDK 上下文提供了更友好的封装：

```python
def ensure_sdk_context(raw_ctx: PluginContextProtocol) -> SdkContext:
    """将原始上下文包装为 SDK 友好的上下文"""
    return SdkContext(
        # 原始上下文的所有方法
        push_message=raw_ctx.push_message,
        update_status=raw_ctx.update_status,
        query_memory=raw_ctx.query_memory,
        trigger_event=raw_ctx.trigger_event,
        get_own_config=raw_ctx.get_own_config,
        update_own_config=raw_ctx.update_own_config,

        # 添加 SDK 层面的增强
        bus=SdkBusWrapper(raw_ctx.bus),  # BusList 支持
        report_status=raw_ctx.report_status,
        finish=raw_ctx.finish,
        export_push=raw_ctx.export_push,

        # 添加 SDK 独有功能
        get_data_path=raw_ctx.get_data_path,
        get_plugin_dir=self.plugin_dir,
    )
```

### 5.2 Bus 包装

> ⚠️ **v0.9 更新**：Bus 是**只读/订阅门面**（非 pub/sub），查询链已改为 `get(...).filter(field=value).sort(by=...).limit()`；`get_recent()` / `reload()` / `union()/intersect()/difference()` 已移除。下面为历史源码结构，理解原理用，勿照抄旧接口（现行用法见 [31-bus-system-internals.md](31-bus-system-internals.md)）。

SDK 上下文中的 `bus` 属性是包装过的，返回可链式查询的容器：

```python
class SdkBusWrapper:
    """包装原始 Bus，返回 BusList 而非原始记录"""
    def __init__(self, raw_bus):
        self._raw = raw_bus

    @property
    def messages(self):
        return SdkMessagesClient(self._raw.messages)

    @property
    def events(self):
        return SdkEventsClient(self._raw.events)

    # ... 其他总线类似
```

---

## 6. LLM Tool 注册机制

### 6.1 @llm_tool 装饰器

```python
@llm_tool(
    name="search_files",
    description="搜索文件",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"}
        },
        "required": ["query"]
    }
)
async def search_files(self, *, query: str):
    """LLM 可调用的工具"""
    results = await self._do_search(query)
    return {"files": results}
```

### 6.2 内部注册流程

```python
def _collect_llm_tools(self):
    """扫描所有被 @llm_tool 装饰的方法"""
    for name, obj in inspect.getmembers_static(type(self)):
        if name.startswith('_'):
            continue
        if isinstance(obj, (staticmethod, classmethod)):
            obj = obj.__func__
        meta = getattr(obj, LLM_TOOL_META_ATTR, None)
        if meta:
            self._llm_tools[meta.name] = meta
            # 注册到宿主
            self.register_llm_tool(meta)

def register_llm_tool(self, meta: LlmToolMeta):
    """将 LLM Tool 注册到宿主，使其对 LLM 可见"""
    self._host_ctx.register_llm_tool(
        plugin_id=self.plugin_id,
        tool_name=meta.name,
        description=meta.description,
        parameters=meta.parameters,
        handler=meta.handler  # 绑定方法
    )
```

### 6.3 LLM Tool 调用流程

```
LLM 决定调用工具
    │
    ▼
main_server 查找 tool 注册表
    │
    ▼
找到对应插件的 tool handler
    │
    ▼
通过 ZMQ 发送 CALL_LLM_TOOL 命令
    │
    ▼
子进程执行 handler(tool_args)
    │
    ▼
结果通过 ZMQ 返回 → main_server → LLM
```

---

## 7. Static UI 注册

### 7.1 @static_ui 装饰器

```python
@static_ui(
    id="my_panel",
    title="我的面板",
    icon="settings",
    entry="my_panel.html"  # 前端入口文件
)
class MyPanel:
    """纯前端面板"""
    pass
```

### 7.2 内部注册

```python
def _collect_static_uis(self):
    """扫描所有 @static_ui 装饰的类"""
    for name, obj in inspect.getmembers_static(type(self)):
        meta = getattr(obj, STATIC_UI_META_ATTR, None)
        if meta:
            self._static_uis[meta.id] = meta
            self.register_static_ui(meta)

def register_static_ui(self, meta: StaticUiMeta):
    """将 Static UI 注册到宿主"""
    self._host_ctx.register_static_ui(
        plugin_id=self.plugin_id,
        ui_id=meta.id,
        title=meta.title,
        icon=meta.icon,
        entry=meta.entry  # HTML/JS 入口路径
    )
```

---

## 8. list_actions 机制

`list_actions` 允许插件在前端列表（如插件管理器）中显示操作按钮：

```python
# 在 __init__ 或 startup 钩子中设置
self.set_list_actions([
    {
        "id": "open_settings",
        "label": "打开设置",
        "icon": "settings",
        "action": "open_ui",
        "entry": "settings"
    },
    {
        "id": "refresh",
        "label": "刷新",
        "icon": "refresh",
        "action": "call_entry",
        "entry": "refresh_data"
    }
])
```

---

## 9. export_push — 导出推送

`export_push` 允许插件将消息推送到外部系统（如 QQ、Telegram 等）：

```python
# 启用导出推送
self._export_push_enabled = True

# 推送消息时，同时导出到外部系统
await self.export_push(
    content="你好",
    target="qq_group_12345"
)
```

---

## 10. PluginStore / PluginDatabase / PluginStatePersistence

### 10.1 PluginStore — 键值存储

```python
# 类似 dict 的 API
await self.store.set("key", "value")
value = (await self.store.get("key")).unwrap_or(None)
await self.store.delete("key")
keys = await self.store.keys()
```

### 10.2 PluginDatabase — SQL 数据库

```python
# 需要 plugin.toml 中 database.enabled = true
async with self.db.session() as session:
    result = await session.execute(
        "SELECT * FROM my_table WHERE id = :id",
        {"id": 123}
    )
    rows = result.fetchall()
```

### 10.3 PluginStatePersistence — 状态持久化

```python
# 自动持久化插件状态
self.state.set("last_run", datetime.now().isoformat())
last_run = self.state.get("last_run")
```

---

## 11. 完整插件模板（修订版）

> **修订说明**：旧版本本节写了 `from nekog.sdk import ...`（不存在的包）、`self,,` 语法错误、`@lifecycle("on_init")` 位置参数与 `on_init` / `on_start` / `on_stop` 三个不存在的钩子、`store.get()` 当裸值、以及定时器里 `asyncio.new_event_loop()`。以上全部按官方源码更正。**可直接抄写的完整示例见 [`../examples/minimal_plugin/`](../examples/minimal_plugin/README.md)**，本节只用于对照基类能力。

```python
from typing import Annotated

from plugin.sdk.plugin import (
    NekoPluginBase, neko_plugin, PluginRouter, plugin_entry,
    lifecycle, timer_interval, llm_tool, Ok, Err, unwrap_or,
)


class MyRouter(PluginRouter):
    """子路由：只放 @plugin_entry，不要放 @llm_tool。"""
    def __init__(self):
        super().__init__(prefix="sub", name="sub")

    @plugin_entry(id="sub_action", name="子入口", description="子路由入口")
    async def sub_action(self, param: Annotated[str, "参数"] = "", **_):
        return Ok({"result": param})


@neko_plugin
class MyPlugin(NekoPluginBase):
    def __init__(self, ctx):
        super().__init__(ctx)              # ctx 由宿主注入，用 self.ctx 取
        self.include_router(MyRouter())    # 注册必须在 super().__init__ 之后

    # ─── 生命周期：只允许 6 个 id，且用 id= 关键字 ───
    @lifecycle(id="startup")
    async def on_startup(self, **_):
        self._count = int(unwrap_or(await self.store.get("count"), 0))
        return Ok({"status": "ready"})

    @lifecycle(id="shutdown")
    async def on_shutdown(self, **_):
        await self.store.set("count", self._count)
        return Ok({"status": "stopped"})

    @lifecycle(id="config_change")
    async def on_config_change(self, *, old_config=None, new_config=None, mode=None, **_):
        # 框架以 kwargs 传这三个参数
        return Ok({"status": "reloaded"})

    # ─── 入口 ───
    @plugin_entry(id="do_something", name="执行操作", description="执行操作")
    async def do_something(self, param: Annotated[str, "参数"] = "", **_):
        return Ok({"result": param})

    # ─── LLM 工具：只扫主类，参数必须 keyword-only ───
    @llm_tool(name="get_info", description="读取一个键")
    async def get_info(self, *, key: str):
        value = unwrap_or(await self.store.get(key), None)   # store.get 返回 Result
        return {"key": key, "value": value}

    # ─── 定时器：宿主 asyncio.run(fn())，必须 async def ───
    @timer_interval(id="auto_refresh", seconds=300, name="定时刷新", auto_start=True)
    async def _auto_refresh(self, **_):
        self._count += 1
        await self.store.set("count", self._count)
        return Ok({"count": self._count})
```

**易错点对照**：`@neko_plugin` 不带括号参数（元信息写 `plugin.toml`）；跨插件用 `self.plugins.call_entry(...)`，没有事件广播 API；`push_message` 是同步方法，用 `parts`，不要 `await`。

---

## 12. 常见陷阱

### 陷阱 32-1：在 __init__ 中调用 self.plugins
```python
# ❌ 错误：其他插件尚未加载
def __init__(self, ctx):
    super().__init__(ctx)
    self.plugins.call_entry("other:entry")  # 崩溃

# ✅ 正确：在 startup 钩子中调用
@lifecycle(id="startup")
async def on_startup(self, **_):
    await self.plugins.call_entry("other:entry")
```

### 陷阱 32-2：忘记 super().__init__
```python
# ❌ 错误：不调用父类 __init__
def __init__(self, ctx):
    self.ctx = ctx  # config, plugins, logger 等全部缺失

# ✅ 正确
def __init__(self, ctx):
    super().__init__(ctx)
```

### 陷阱 32-3：Router 的 entry ID 冲突
```python
# ❌ 错误：主插件和 Router 有相同 entry ID
class MyPlugin(NekoPluginBase):
    @plugin_entry(id="action", name="操作", description="主插件入口")
    async def action(self, **_):
        return Ok({"from": "main"})

    def __init__(self, ctx):
        super().__init__(ctx)
        self.include_router(MyRouter())  # Router 中也有 id="action"

# ✅ 正确：使用 prefix 隔离
def __init__(self, ctx):
    super().__init__(ctx)
    router = MyRouter()
    router.set_prefix("sub")
    self.include_router(router)
    # 现在 Router 的 entry 是 "sub:action"
```
