# 33 — PluginRouter 与 Entry 系统深度解析

> **来源**：N.E.K.O-main `plugin/sdk/shared/core/router.py` + `plugin/sdk/shared/core/decorators.py` 深度逆向分析  
> **适用**：深入理解 PluginRouter 的内部机制、Entry 注册/分发全流程、装饰器元数据系统

---

## 1. 架构总览

```
@neko_plugin 装饰的类
    │
    ├── @plugin_entry 装饰的方法 → 直接注册到主插件
    │
    └── self.include_router(Router)
            │
            └── Router 中 @plugin_entry 装饰的方法
                    → 自动加 prefix 后合并到主插件
```

---

## 2. @plugin_entry 装饰器内部

### 2.1 完整参数

```python
@plugin_entry(
    id="entry_id",                    # 必需：唯一标识符
    description="描述",               # AI 可见的描述
    name="显示名称",                  # 前端显示名称
    icon="play",                      # 图标
    category="操作",                  # 分类
    input_schema={                    # 输入参数 schema（JSON Schema）
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "参数1"}
        },
        "required": ["param1"]
    },
    output_schema={                   # 输出 schema
        "type": "object",
        "properties": {
            "result": {"type": "string"}
        }
    },
    permission="basic",               # 权限级别
    visibility="public",              # public / private / admin
    tags=["music", "audio"],          # 标签
    kind=EntryKind.ACTION             # EntryKind 枚举
)
async def my_entry(self, _ctx=None, *, param1: str):
    ...
```

### 2.2 内部实现

```python
# decorators.py 简化实现
EVENT_META_ATTR = "__neko_event_meta__"

class EventMeta:
    """Entry 元数据"""
    id: str
    description: str
    name: str
    icon: str
    category: str
    input_schema: dict | None
    output_schema: dict | None
    permission: str
    visibility: str
    tags: list[str]
    kind: EntryKind
    handler: callable  # 原始函数引用

def plugin_entry(*, id: str, **kwargs):
    def decorator(func):
        meta = EventMeta(
            id=id,
            handler=func,
            **kwargs
        )
        setattr(func, EVENT_META_ATTR, meta)
        return func
    return decorator
```

### 2.3 EntryKind 枚举

```python
class EntryKind(enum.Enum):
    ACTION = "action"       # 普通操作入口
    QUERY = "query"         # 查询入口（只读）
    COMMAND = "command"     # 命令入口
    HOOK = "hook"           # 钩子入口
    QUICK_ACTION = "quick"  # 快捷操作（前端快速按钮）
```

---

## 3. PluginRouter 完整接口

### 3.1 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `prefix` | `str` | 路由前缀，所有 entry 自动加此前缀 |
| `tags` | `list[str]` | 标签列表（只读拷贝） |
| `is_bound` | `bool` | 是否已绑定到插件 |
| `entry_ids` | `list[str]` | 所有已注册 entry ID（含前缀） |
| `ctx` | 代理 | 代理到主插件的 `ctx` |
| `config` | 代理 | 代理到主插件的 `config` |
| `plugins` | 代理 | 代理到主插件的 `plugins` |
| `logger` | 代理 | 代理到主插件的 `logger` |
| `store` | 代理 | 代理到主插件的 `store` |
| `db` | 代理 | 代理到主插件的 `db` |
| `plugin_id` | `str` | 主插件 ID |
| `main_plugin` | `NekoPluginBase` | 绑定的主插件对象 |

### 3.2 方法

| 方法 | 说明 |
|------|------|
| `name()` | 返回路由器名称（类名） |
| `set_prefix(prefix)` | 设置前缀 |
| `iter_handlers()` | 返回 `{entry_id: handler}` 映射 |
| `collect_entries()` | 返回 `{entry_id: EventMeta}`（含装饰器+动态） |
| `add_entry(id, handler, **meta)` | 动态注册 entry |
| `remove_entry(id)` | 移除动态 entry |
| `list_entries()` | 列出所有 entry 元数据 |
| `on_mount()` | 挂载时回调（可重写） |
| `on_unmount()` | 卸载时回调（可重写） |
| `report_status(status)` | 转发状态报告 |
| `get_dependency(name, default)` | 从 Router 或插件获取依赖 |
| `get_plugin_attr(name, default)` | 从插件获取属性 |
| `has_plugin_attr(name)` | 检查插件是否有某属性 |

---

## 4. 懒解析策略（核心设计）

### 4.1 为什么需要懒解析

```python
# 典型使用场景
class MyPlugin(NekoPluginBase):
    def __init__(self, ctx):
        super().__init__(ctx)
        router = MyRouter()
        router.set_prefix("sub")      # ← 先设 prefix
        self.include_router(router)   # ← 再注册
```

如果 Router 在 `__init__` 时就解析 `@plugin_entry` 装饰的 entry，prefix 还没设置，entry ID 会是错误的。所以 Router 采用懒解析。

### 4.2 实现

```python
class PluginRouter:
    def __init__(self, ...):
        # 只扫描装饰器，不解析 entry ID
        self._decorated_entries: list[tuple[str, EventMeta, callable]] = []
        self._collect_decorated_entries()

        # 动态注册的 entry
        self._entries: dict[str, _EntryRecord] = {}

        # 懒解析标志
        self._resolved = False

    def _collect_decorated_entries(self):
        """扫描子类中带 EVENT_META_ATTR 的方法"""
        for name, obj in inspect.getmembers_static(type(self)):
            if name.startswith('_'):
                continue
            if isinstance(obj, (staticmethod, classmethod)):
                obj = obj.__func__
            meta = getattr(obj, EVENT_META_ATTR, None)
            if meta and meta.id:
                handler = getattr(self, name)
                self._decorated_entries.append((name, meta, handler))

    def _resolved_entries(self) -> dict[str, EventMeta]:
        """懒解析：按当前 prefix 计算最终 entry ID"""
        if self._resolved:
            return self._cached_resolved

        result = {}

        # 解析装饰器 entry
        for name, meta, handler in self._decorated_entries:
            eid = f"{self.prefix}:{meta.id}" if self.prefix else meta.id
            resolved_meta = replace(meta, id=eid, handler=handler)
            result[eid] = resolved_meta

        # 合并动态 entry
        for eid, record in self._entries.items():
            full_eid = f"{self.prefix}:{eid}" if self.prefix else eid
            result[full_eid] = record.meta

        self._cached_resolved = result
        self._resolved = True
        return result
```

---

## 5. 动态 Entry 注册

### 5.1 使用场景

```python
# 基于配置动态创建 entry
@lifecycle("on_start")
async def on_start(self, **_):
    config = await self.config.get()
    for item in config.get("items", []):
        self.router.add_entry(
            entry_id=f"process_{item['id']}",
            handler=self._make_handler(item),
            description=f"处理 {item['name']}",
            input_schema={"type": "object", "properties": {...}}
        )
```

### 5.2 add_entry 实现

```python
def add_entry(
    self,
    entry_id: str,
    handler: RouteHandler,
    *,
    description: str = "",
    name: str = "",
    input_schema: dict | None = None,
    output_schema: dict | None = None,
    permission: str = "basic",
    tags: list[str] | None = None,
) -> Result[bool]:
    """动态注册 entry"""
    # 1. 检查是否已存在
    if entry_id in self._entries:
        return Err(code="DUPLICATE", message=f"Entry {entry_id} 已存在")

    # 2. 创建元数据
    meta = EventMeta(
        id=entry_id,
        description=description,
        name=name or entry_id,
        input_schema=input_schema,
        output_schema=output_schema,
        permission=permission,
        tags=tags or [],
        handler=handler,
    )

    # 3. 存储
    self._entries[entry_id] = _EntryRecord(meta=meta, dynamic=True)
    self._resolved = False  # 使缓存失效
    return Ok(True)

def remove_entry(self, entry_id: str):
    """移除动态 entry"""
    if entry_id not in self._entries:
        return
    record = self._entries.pop(entry_id)
    if not record.dynamic:
        self.logger.warning(f"尝试移除非动态 entry: {entry_id}")
        return
    self._resolved = False
```

---

## 6. Entry 分发流程

### 6.1 从 LLM/用户到插件

```
用户输入 / LLM 决策
    │
    ▼
main_server 解析意图
    │
    ▼
查找 GlobalState.entry_registry
    │
    ├── 找到匹配的 entry
    │     │
    │     ▼
    │   通过 ZMQ 发送 CALL_ENTRY 到子进程
    │     │
    │     ▼
    │   子进程的 PluginChildRuntime 分发
    │     │
    │     ├── 查找主插件的 handler
    │     ├── 查找 Router 的 handler
    │     └── 执行 handler(args)
    │           │
    │           ▼
    │         返回 Result[Ok | Err]
    │
    └── 未找到 → 返回错误给 LLM
```

### 6.2 子进程内的分发

```python
# 子进程内的简化分发逻辑
async def dispatch_entry(self, entry_id: str, args: dict):
    # 1. 先查主插件
    handler = self.plugin_instance._entry_handlers.get(entry_id)
    if handler:
        return await handler(_ctx=self.ctx, **args)

    # 2. 查所有 Router
    for router in self.plugin_instance._routers:
        handlers = router.iter_handlers()
        if entry_id in handlers:
            handler = handlers[entry_id]
            return await handler(_ctx=self.ctx, **args)

    # 3. 未找到
    return Err(code="NOT_FOUND", message=f"Entry {entry_id} 不存在")
```

---

## 7. 装饰器叠加机制

### 7.1 双装饰器

```python
@plugin_entry(id="action")
@ui.action(id="ui_action")
async def my_action(self, _ctx=None, *, param: str):
    ...
```

**规则：`@plugin_entry` 必须在 `@ui.action` 之上！**

原因：Python 装饰器从下往上执行，`@plugin_entry` 在最外层，其返回值会被 `@ui.action` 包装。如果顺序反了，`EVENT_META_ATTR` 会被 `@ui.action` 的返回值覆盖。

### 7.2 装饰器链执行顺序

```python
# 实际执行顺序（从下往上）：
@plugin_entry(id="action")      # 3. 最后执行，设置 EVENT_META_ATTR
@ui.action(id="ui_action")      # 2. 第二执行，设置 UI_ACTION_ATTR
async def my_action(...):       # 1. 原始函数
    ...
```

---

## 8. before_entry / after_entry / around_entry 钩子

### 8.1 before_entry

```python
@before_entry("action")
async def before_action(self, _ctx=None, **kwargs):
    """在 entry 执行前调用，可以修改参数或拒绝执行"""
    if not self._is_ready:
        return Err(code="NOT_READY", message="插件未就绪")
    return Ok(kwargs)  # 返回修改后的参数
```

### 8.2 after_entry

```python
@after_entry("action")
async def after_action(self, _ctx=None, result=None, **kwargs):
    """在 entry 执行后调用，可以修改结果或记录日志"""
    self.logger.info(f"Entry action 执行完成: {result}")
    return Ok(result)
```

### 8.3 around_entry

```python
@around_entry("action")
async def around_action(self, _ctx=None, handler=None, **kwargs):
    """包裹 entry 执行，类似中间件"""
    start = time.time()
    result = await handler(**kwargs)
    elapsed = time.time() - start
    self.logger.info(f"Entry action 耗时: {elapsed:.2f}s")
    return result
```

### 8.4 replace_entry

```python
@replace_entry("action")
async def custom_action(self, _ctx=None, **kwargs):
    """完全替换原有 entry 的实现"""
    return Ok({"custom": True})
```

---

## 9. hook 装饰器

### 9.1 使用

```python
@hook("before_all_entries")
async def check_permission(self, _ctx=None, entry_id=None, **kwargs):
    """在所有 entry 执行前检查权限"""
    if entry_id in self._restricted_entries:
        return Err(code="FORBIDDEN", message="无权访问")
    return Ok(kwargs)
```

### 9.2 可用的 hook 点

| Hook 点 | 触发时机 |
|---------|---------|
| `before_all_entries` | 任何 entry 执行前 |
| `after_all_entries` | 任何 entry 执行后 |
| `before_entry:{id}` | 特定 entry 执行前 |
| `after_entry:{id}` | 特定 entry 执行后 |

---

## 10. quick_action 快捷操作

```python
@quick_action(
    id="quick_search",
    label="快速搜索",
    icon="search",
    description="快速搜索文件"
)
async def quick_search(self, _ctx=None):
    """前端直接调用的快捷操作，无需 LLM 决策"""
    return Ok({"action": "open_search"})
```

快捷操作直接显示在前端 UI 中作为按钮，用户点击直接触发，跳过 LLM 决策。

---

## 11. 完整 Router 示例

```python
class MusicRouter(PluginRouter):
    """音乐相关功能的 Router"""

    def __init__(self):
        super().__init__()
        self.set_prefix("music")
        self._playlist = []

    def on_mount(self):
        """挂载到主插件时调用"""
        self.logger.info("MusicRouter 已挂载")

    def on_unmount(self):
        """从主插件卸载时调用"""
        self._playlist.clear()

    @plugin_entry(
        id="play",
        description="播放音乐",
        input_schema={
            "type": "object",
            "properties": {
                "song_name": {"type": "string", "description": "歌曲名"}
            },
            "required": ["song_name"]
        }
    )
    async def play(self, _ctx=None, *, song_name: str):
        # 通过 self.plugins 调用其他插件
        result = await self.plugins.call_entry(
            "music_pusher:search",
            args={"query": song_name}
        )
        if result.is_err():
            return result
        return Ok({"playing": song_name, "url": result.unwrap()["url"]})

    @plugin_entry(id="stop", description="停止播放")
    async def stop(self, _ctx=None):
        return Ok({"stopped": True})

    @plugin_entry(id="playlist", description="查看播放列表")
    async def playlist(self, _ctx=None):
        return Ok({"songs": self._playlist})

    # 动态注册 entry
    async def register_genre_entries(self, genres: list[str]):
        for genre in genres:
            async def genre_handler(_ctx=None, genre=genre):
                return Ok({"genre": genre, "songs": [...]})

            self.add_entry(
                entry_id=f"genre_{genre}",
                handler=genre_handler,
                description=f"播放 {genre} 类型的音乐"
            )


class MyPlugin(NekoPluginBase):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.music = MusicRouter()
        self.include_router(self.music)

    @lifecycle("on_start")
    async def on_start(self, **_):
        # 动态注册 genre entry
        await self.music.register_genre_entries(["pop", "rock", "jazz"])
```

---

## 12. 常见陷阱

### 陷阱 33-1：忘记 set_prefix 导致 entry ID 冲突
```python
# ❌ 错误：两个 Router 有相同 entry ID
self.include_router(RouterA())  # 有 entry id="action"
self.include_router(RouterB())  # 也有 entry id="action"
# → EntryConflictError

# ✅ 正确：设置不同 prefix
ra = RouterA(); ra.set_prefix("a"); self.include_router(ra)
rb = RouterB(); rb.set_prefix("b"); self.include_router(rb)
# entry 变为 "a:action" 和 "b:action"
```

### 陷阱 33-2：动态 entry 的闭包陷阱
```python
# ❌ 错误：闭包捕获了循环变量
for i in range(5):
    async def handler(_ctx=None):
        return Ok({"index": i})  # 所有 handler 返回 i=4
    self.add_entry(f"item_{i}", handler)

# ✅ 正确：使用默认参数捕获
for i in range(5):
    async def handler(_ctx=None, idx=i):
        return Ok({"index": idx})
    self.add_entry(f"item_{i}", handler)
```

### 陷阱 33-3：在 Router.on_mount 中访问 self.plugins
```python
# ❌ 错误：Router 挂载时其他插件可能未就绪
def on_mount(self):
    self.plugins.call_entry("other:entry")  # 可能失败

# ✅ 正确：在插件 on_start 中调用
@lifecycle("on_start")
async def on_start(self, **_):
    await self.router.do_init()  # 此时其他插件已就绪
```
