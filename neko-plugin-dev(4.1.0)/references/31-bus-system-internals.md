# 31 — Bus 门面深度解析

> **来源**：官方文档（[SDK 迁移清单](https://project-neko.online/plugins/migration-v0.9)）+ N.E.K.O-main `plugin/core/bus/` 历史源码逆向。
> **适用**：理解宿主状态（消息/事件/生命周期/对话/记忆）的读取与订阅机制，排查通信相关 bug。
>
> ⚠️ **一句话定性**：Bus 是**宿主状态的只读/订阅门面（facade），不是发布订阅总线**。没有 `bus.emit()` / `bus.publish()` / `ctx.trigger_event()`。插件对外产出请用 `push_message` / `report_status` / UI Action / 跨插件 `call_entry`。
>
> **版本**：核对日期 2026-09-12，SDK `>=0.1.0,<0.2.0`。标 ✅ 的写法来自官方文档示例；标 🟡 的片段为**示意**（依据官方 API 复现，未在本机逐行运行）；标 ❌ 的为**已移除接口**，仅供阅读历史代码。

### v0.9 迁移速查表

| 旧 API（❌ 已移除） | 现行 API（✅ 官方文档） |
|-------------------|----------------------|
| `bus.messages.get_recent(50)` | `await bus.messages.get(max_count=50)` |
| `bus.messages.query(filters=..., sort_by=..., limit=...)` | `get(...)` → 链式 `.filter(field=value)` → `.sort(by=..., reverse=...)` → `.limit(n)` |
| `busList.reload(ctx)` | 移除了增量游标；查询尽量**一次**规划完成，链式操作在单次请求内下推 |
| `busList.union(o)` / `intersect` / `difference` | 集合操作已移除，改写为结构化 `filter` |
| `where_eq/where_in/...` 辅助 | 一律用 `filter(field=value)` |
| `ctx.trigger_event(...)` / `bus.emit(...)` | **不存在**：事件通过 `@on_event` / `@message` / `@custom_event` 装饰器接收 |
| `self.memory`（读写记忆） | 改用只读 `await self.bus.memory.get(bucket_id="default", limit=20)`（有界、短 TTL） |

---

## 1. Bus 门面架构总览

官方对 Bus 的定义是"**宿主状态的只读/订阅门面**"，而不是基于 topic 的 pub/sub。它支持惰性求值与变更订阅。

### 五条总线

```
BusHub (门面中枢)
├── messages/      ← 消息：聊天消息、插件推送   （可 get 查询 + watch 订阅）
├── events/        ← 事件：系统/自定义事件        （可 get 查询 + watch 订阅）
├── lifecycle/     ← 生命周期：插件状态变更        （可 get 查询 + watch 订阅）
├── conversations/ ← 对话上下文                   （只读快照）
└── memory/        ← 记忆                         （只读、有界、短 TTL 快照）
```

### 数据流（子进程 → 宿主）

```text
[Plugin Process]                         [Host/Server Process]
     │                                        │
     │  await ctx.bus.messages.get(...)       │
     │  ZeroMQ RPC ─────────────────────────► │
     │  ◄──────────────────────────── records │
     │                                        │
     │  返回 BusList                           │
     │  .filter(field=value)   → 结构化下推    │
     │  .sort(by=..., reverse=) → 计划节点     │
     │  .limit(n)              → 截断          │
     │  .watch(ctx)            → 订阅后继变更  │
```

---

## 2. 查询链（✅ 官方文档示例）

链式顺序建议：**`get()` → 结构化 `filter(field=value)` → `sort(by=..., reverse=...)` → `limit(n)`**。

```python
# 事件：取本插件相关事件，过滤 + 排序 + 截断
events = await self.bus.events.get(plugin_id=self.plugin_id, max_count=50)
recent = (
    events
    .filter(priority_min=1)
    .filter(type="TASK_FINISHED")
    .sort(by="timestamp", reverse=True)
    .limit(20)
)

# 消息
msgs = await self.bus.messages.get(room_id=room_id, max_count=100)
hot = msgs.filter(role="user").sort(by="timestamp", reverse=True).limit(10)
```

规则：

- **结构化 `filter(field=value)`** 可被计划树下推、可重放；**`filter(callable)`** 只作用于本地快照，**不能**放在 `watch()` 之前（会被忽略或报错）。
- `conversations` / `memory` **只读**，不支持 `watch()`，只提供有限快照读取。
- 官方参数命名以 `max_count`（`get`）和 `by`/`reverse`（`sort`）为准；具体字段名以你目标版本的官方示例为最终依据。

🟡 示意（组合示例，未本机运行）：

```python
async def on_start(self, **_):
    self._w = (
        self.bus.messages
        .get(room_id="default", max_count=10)
        .filter(role="user")
        .watch(self.ctx)
    )

    @self._w.subscribe(on="add")
    def _on_add(delta):
        for m in delta.added:
            self.logger.info("新消息: {}", m.content)

    self._w.start()
    return Ok({})
```

---

## 3. 变更订阅 Watch（✅ messages/events/lifecycle 支持）

```python
watcher = self.bus.events.get(plugin_id=self.plugin_id, max_count=20).watch(self.ctx)

@watcher.subscribe(on="add")       # on ∈ {"add", "del", "change"}
def on_new(delta):
    for item in delta.added:
        ...

watcher.start()                     # 开始接收

# 生命周期结束/停止时务必释放，避免泄漏
@lifecycle("shutdown")
async def on_shutdown(self, **_):
    try:
        watcher.stop()             # 或 unsubscribe()，以目标版本文档为准
    except Exception:
        pass
```

> ⚠️ 具体方法名（`stop` / `unsubscribe` / `close`）与 `delta` 结构请以目标 SDK 官方示例为准；上例为**示意**。

---

## 4. 各总线用法

### 4.1 messages（读 + watch）

```python
room = await self.bus.messages.get(room_id="default", max_count=50)
recent_users = room.filter(role="user").sort(by="timestamp", reverse=True).limit(10)
```

推送回聊天（**不是**往 Bus 写）：`await self.push_message(content="...", visibility=["chat"], ai_behavior="respond")`。

### 4.2 events（读 + watch）

```python
events = await self.bus.events.get(plugin_id=self.plugin_id, max_count=50)
```

接收自定义/系统事件用装饰器，**没有** `ctx.trigger_event`：

```python
from plugin.sdk.plugin import on_event

@on_event("my_custom_event")
async def handle(self, event_data, **_):
    self.logger.info("收到事件: {}", event_data)
    return Ok({})
```

### 4.3 lifecycle（读 + watch）

```python
life = await self.bus.lifecycle.get(plugin_id="my_plugin", max_count=50)
```

### 4.4 conversations（只读快照）

🟡 官方仅说明其为只读接口，未给出稳定的读写方法全集。**不要**假定 `create()` / `switch()` / `get_history()` 存在——需要对话管理能力时，先用 `self.plugins.call_entry(...)` 调用宿主相关入口，并在目标 SDK 上验证。

### 4.5 memory（只读、有界、短 TTL）

官方明确：**`self.memory` 已被移除**；`await self.bus.memory.get(bucket_id="default", limit=20)` 返回的是**有界的、内存中的短期 TTS 事件**（约 1 小时 TTL），**不是**持久事实或人格记忆库。

```python
recent_tts = await self.bus.memory.get(bucket_id="default", limit=20)
```

- ❌ 不存在 `memory.store(...)`、`memory.get_persona(...)`、`tier="facts"` 之类持久化/分层写入接口。
- `ctx.query_memory` 是**已弃用的占位**，不自带语义检索。
- **公开插件 SDK 目前没有结构化持久记忆召回接口**。需要长期记忆请自行用 `self.store` / `self.db` 设计（见 [35-store-database-internals](35-store-database-internals.md)）。

---

## 5. 内部机制（历史源码逆向 · 未在本机验证）

> 本节解释"为什么这样设计"，便于排查历史代码。相关命名可能随版本演进变化。

### 5.1 修订追踪（Revision）

```python
_BUS_LATEST_REV: dict[str, int] = {"messages": 0, "events": 0, "lifecycle": 0,
                                   "conversations": 0, "memory": 0}

def dispatch_bus_change(bus_name: str, delta):
    _BUS_LATEST_REV[bus_name] += 1
    for w in _watchers[bus_name]:
        w.notify(delta, _BUS_LATEST_REV[bus_name])
```

### 5.2 子进程本地缓存

```python
class _LocalMessageCache:          # 减少 ZMQ 往返
    _max_size: int = 1000
    _cache: list
    _last_sync_rev: int = 0
```

### 5.3 链式操作只建计划树，物化时才执行

```python
def filter(self, predicate):
    return BusList(_ctx=self._ctx, _plan=FilterNode(child=self._plan, predicate=predicate))

def _ensure_materialized(self):
    if self._plan is None or self._ctx is None:
        return
    self._records = list(self._plan.execute(self._ctx))
    self._plan = None                    # 执行后转急切模式
```

---

## 6. 何时用哪条总线

| 需求 | 用哪条 | 备注 |
|------|--------|------|
| 读聊天历史 / 监听用户消息 | messages | 支持 watch |
| 监听系统/自定义事件 | events | 支持 watch；发送侧无 emit |
| 观察插件状态变更 | lifecycle | 支持 watch |
| 读对话上下文 | conversations | 只读快照 |
| 读短期 TTS 事件 | memory | 只读、有界、短 TTL |

**跨插件通信**（A 插件通知 B 插件）请走 `self.plugins.call_entry("b:entry", {...})`，见 [28-inter-plugin-communication](28-inter-plugin-communication.md)。Bus **不承担**跨插件消息投递。

---

## 7. 性能建议（现行 API 版）

```python
# ✅ 一次规划：结构化 filter 可下推，配合 sort/limit 减少数据量
candidates = await self.bus.messages.get(room_id="default", max_count=200)
top = candidates.filter(role="user").sort(by="timestamp", reverse=True).limit(5)

# ❌ 旧写法（已移除）：get_recent(...).reload(ctx)
```

- 用 `max_count` / `limit` 限制数据量，避免拉全量再客户端过滤。
- 结构化 `filter(field=value)` 优于 `filter(lambda ...)`（后者只在本地快照生效，无法下推）。
- 复用同一次查询结果，不要为了刷新反复重建查询。

---

## 8. 常见陷阱

### 31-1：以为 Bus 能"发事件给别的插件"
**现象**：找不到 `emit/publish/trigger_event`。
**正解**：Bus 是只读门面。跨插件通知用 `call_entry`，对宿主产出用 `push_message` / `report_status`。

### 31-2：在 `on_init` 里查 Bus
**现象**：Bus/上下文尚未就绪。
**正解**：移到 `on_start` 之后。

### 31-3：把 `filter(callable)` 放在 `watch()` 之前
**现象**：watch 不按预期触发。
**正解**：watch 前的过滤必须用结构化 `filter(field=value)`。

### 31-4：以为 `bus.memory` 能存长期记忆
**现象**：写入的内容很快消失或读不到。
**正解**：`memory` 只读且有界、短 TTL；持久化用 `self.store` / `self.db`。

### 31-5：Watcher 泄漏
**现象**：多次 reload 后回调重复触发、内存增长。
**正解**：在 `shutdown`/`reload` 钩子里显式释放 watcher。
