# 31 — Bus 总线系统深度解析

> **来源**：N.E.K.O-main `plugin/core/bus/` 全部源码深度逆向分析  
> **适用**：理解插件间事件/消息/生命周期的底层通信机制，排查通信相关 bug

---

## 1. Bus 系统架构总览

N.E.K.O 的总线系统不是传统的 pub/sub（基于 topic），而是一个**反应式查询系统**，支持惰性求值、计划重放和增量变更订阅。

### 五条总线

```
BusHub (总线中枢)
├── messages/      ← 消息总线：聊天消息、插件推送
├── events/        ← 事件总线：系统事件、自定义事件
├── lifecycle/     ← 生命周期总线：插件状态变更
├── conversations/ ← 对话总线：对话上下文管理
└── memory/        ← 记忆总线：五维记忆系统查询
```

### 架构模式

```
[Plugin Process]                    [Server Process]
     │                                   │
     │  ctx.bus.messages.get(...)        │
     │  (returns BusList)                │
     │                                   │
     │  ZeroMQ RPC ──────────────────►   │
     │  op="bus.get_recent"              │
     │                                   │
     │  ◄──────────────────  records     │
     │                                   │
     │  BusList wraps records            │
     │  with _plan (GetNode tree)        │
     │                                   │
     │  .filter(...).sort(...).limit()   │
     │  链式操作只修改 _plan，不重查      │
     │                                   │
     │  .reload(ctx) → 重放 _plan        │
     │  .watch(ctx)  → 订阅变更          │
```

---

## 2. BusList — 惰性查询容器

`BusList` 是总线的核心抽象，它有两种模式：

### 2.1 急切模式 (Eager)
```python
# 直接传入记录列表，没有 _ctx 或 _plan
records = [MessageRecord(...), MessageRecord(...)]
bus_list = BusList(records)
# 此时 BusList 行为类似普通 list
for r in bus_list:
    print(r.content)
```

### 2.2 惰性模式 (Lazy)
```python
# 有 _ctx 和 _plan 时，访问数据时会自动重放计划
bus_list = BusList(
    _ctx=ctx,
    _plan=GetNode(source="messages", filters=[...]),
    _records=[]  # 初始为空，访问时惰性加载
)
# 只有在迭代时才实际查询
for r in bus_list:  # 触发 _ensure_materialized()
    print(r.content)
```

### 2.3 链式操作（构建查询计划）

```python
result = (
    ctx.bus.messages.get_recent(limit=100)
    .filter(lambda m: m.role == "user")           # 添加 FilterNode
    .filter(lambda m: "音乐" in m.content)         # 再添加 FilterNode
    .sort(key=lambda m: m.timestamp, reverse=True) # 添加 SortNode
    .limit(10)                                     # 添加 LimitNode
)
# 此时还没查询！_plan 是一棵树
# 访问数据时一次性执行整个计划
```

### 2.4 计划节点类型

| 节点 | 类型 | 说明 |
|------|------|------|
| `GetNode` | 叶节点 | 从数据源获取数据 |
| `FilterNode` | 一元节点 | 过滤数据 |
| `SortNode` | 一元节点 | 排序 |
| `LimitNode` | 一元节点 | 限制数量 |
| `TransformNode` | 一元节点 | 转换数据 |
| `UnionNode` | 二元节点 | 合并两个数据集 |
| `IntersectNode` | 二元节点 | 取交集 |
| `DifferenceNode` | 二元节点 | 取差集 |

---

## 3. 各总线详解

### 3.1 Messages 总线

```python
# 获取最近消息
recent = await ctx.bus.messages.get_recent(limit=50)

# 获取特定对话的消息
conv_msgs = await ctx.bus.messages.get_by_conversation(conv_id)

# 查询消息（带过滤）
msgs = await ctx.bus.messages.query(
    filters={"role": "user", "content_contains": "音乐"},
    sort_by="timestamp",
    limit=10
)

# 推送消息（插件→聊天）
await ctx.push_message(
    content="你好",
    visibility=["chat"],
    ai_behavior="respond"
)
```

### 3.2 Events 总线

```python
# 获取最近事件
events = await ctx.bus.events.get_recent(limit=20)

# 获取特定类型事件
plugin_events = await ctx.bus.events.get_by_type("plugin_lifecycle")

# 触发自定义事件
await ctx.trigger_event("my_custom_event", data={"key": "value"})

# 监听事件（通过装饰器）
@on_event("my_custom_event")
async def handle_my_event(self, event_data, **_):
    self.logger.info(f"收到事件: {event_data}")
```

### 3.3 Lifecycle 总线

```python
# 获取生命周期事件
lifecycle_events = await ctx.bus.lifecycle.get_recent(limit=10)

# 获取特定插件的生命周期
plugin_lifecycle = await ctx.bus.lifecycle.get_by_plugin("my_plugin")
```

### 3.4 Conversations 总线

```python
# 获取当前对话
current_conv = await ctx.bus.conversations.get_current()

# 获取对话历史
conv_history = await ctx.bus.conversations.get_history(conv_id)

# 创建新对话
new_conv = await ctx.bus.conversations.create(title="新对话")

# 切换对话
await ctx.bus.conversations.switch(conv_id)
```

### 3.5 Memory 总线

```python
# 查询记忆
memories = await ctx.bus.memory.query(
    query="用户喜欢什么音乐",
    limit=5,
    tier="facts"  # Tier 0: embeddings, Tier 1: facts, Tier 2: reflections
)

# 存储记忆
await ctx.bus.memory.store(
    content="用户喜欢古典音乐",
    tier="facts",
    metadata={"source": "plugin:music_pusher"}
)

# 获取人设
persona = await ctx.bus.memory.get_persona("master")
```

---

## 4. BusList 高级操作

### 4.1 懒加载 + 重放

```python
# 第一步：构建查询计划（不执行）
plan = ctx.bus.messages.get_recent(100)

# 第二步：链式过滤（只修改计划）
filtered = plan.filter(lambda m: m.role == "assistant")

# 第三步：实际执行（重放计划）
results = await filtered.reload(ctx)
```

### 4.2 变更订阅 (Watch)

```python
# 订阅消息变更
watcher = ctx.bus.messages.get_recent(10).watch(ctx)

# 当有新消息时，watcher 自动更新
@watcher.on_change
def on_new_message(delta: BusListDelta):
    for added in delta.added:
        print(f"新消息: {added.content}")
    for removed in delta.removed:
        print(f"已删除: {removed.id}")
```

### 4.3 集合操作

```python
# 并集
user_msgs = ctx.bus.messages.query(filters={"role": "user"})
assistant_msgs = ctx.bus.messages.query(filters={"role": "assistant"})
all_chat = user_msgs.union(assistant_msgs)

# 交集
music_msgs = ctx.bus.messages.query(filters={"content_contains": "音乐"})
recent_msgs = ctx.bus.messages.get_recent(50)
recent_music = music_msgs.intersect(recent_msgs)

# 差集
read_msgs = ctx.bus.messages.query(filters={"read": True})
all_msgs = ctx.bus.messages.get_recent(100)
unread_msgs = all_msgs.difference(read_msgs)
```

---

## 5. Bus 内部机制

### 5.1 修订追踪 (Revision Tracking)

每次总线数据变更都会产生一个新的 revision：

```python
# rev.py 中的核心机制
_BUS_LATEST_REV: dict[str, int] = {
    "messages": 0,
    "events": 0,
    "lifecycle": 0,
    "conversations": 0,
    "memory": 0,
}

def dispatch_bus_change(bus_name: str, delta: BusListDelta):
    """总线数据变更时调用，通知所有 watcher"""
    _BUS_LATEST_REV[bus_name] += 1
    for watcher in _watchers[bus_name]:
        watcher.notify(delta, _BUS_LATEST_REV[bus_name])
```

### 5.2 本地缓存 (Local Cache)

Messages 总线在子进程中维护本地缓存以优化性能：

```python
# messages.py 中的 _LocalMessageCache
class _LocalMessageCache:
    """子进程本地消息缓存，减少 ZMQ 往返"""
    _max_size: int = 1000
    _cache: list[MessageRecord]
    _last_sync_rev: int = 0

    def get_recent(self, limit: int) -> list[MessageRecord]:
        """如果本地缓存足够，直接返回"""
        if len(self._cache) >= limit:
            return self._cache[:limit]
        return None  # 缓存不足，需要从服务端获取
```

### 5.3 过滤器的惰性求值

```python
# 所有 filter/sort/limit 只构建计划树
def filter(self, predicate):
    return BusList(
        _ctx=self._ctx,
        _plan=FilterNode(child=self._plan, predicate=predicate),
        _records=[]  # 不立即执行
    )

# 只在 _ensure_materialized() 时才执行
def _ensure_materialized(self):
    if self._plan is None:
        return  # 已经是急切模式
    if self._ctx is None:
        return  # 没有上下文，无法执行

    # 从叶节点开始递归执行计划树
    raw_data = self._plan.execute(self._ctx)
    self._records = list(raw_data)
    self._plan = None  # 执行后转为急切模式
```

---

## 6. 与插件开发的关联

### 6.1 何时使用 Messages 总线
- 获取聊天历史
- 推送插件生成的内容
- 监听用户消息

### 6.2 何时使用 Events 总线
- 监听系统事件（启动、停止、配置变更）
- 触发自定义事件供其他插件消费
- 实现插件间松耦合通信

### 6.3 何时使用 Memory 总线
- 查询用户的长期记忆
- 存储插件提取的事实
- 获取角色人设信息

### 6.4 何时使用 Conversations 总线
- 管理对话上下文
- 切换对话会话
- 获取对话历史

---

## 7. 性能优化建议

### 7.1 使用惰性查询
```python
# ✅ 好：构建计划后一次性执行
results = (
    ctx.bus.messages.get_recent(200)
    .filter(lambda m: m.role == "user")
    .filter(lambda m: "关键词" in m.content)
    .limit(5)
)
# 一次 ZMQ 往返

# ❌ 差：多次查询
all_msgs = await ctx.bus.messages.get_recent(200).reload(ctx)
filtered = [m for m in all_msgs if m.role == "user"]  # 客户端过滤，浪费带宽
```

### 7.2 使用 limit 限制数据量
```python
# ✅ 好：限制返回数量
ctx.bus.messages.get_recent(limit=10)

# ❌ 差：不限制，可能返回大量数据
ctx.bus.messages.get_recent()  # 默认可能返回所有
```

### 7.3 避免频繁 reload
```python
# ✅ 好：复用已加载的数据
plan = ctx.bus.messages.get_recent(50)
data = plan  # 惰性
for item in data:  # 第一次触发加载
    process(item)
# data 已转为急切模式，后续访问不触发重查

# ❌ 差：每次都 reload
for i in range(10):
    data = await ctx.bus.messages.get_recent(50).reload(ctx)
    process(data[i])
```

---

## 8. 常见陷阱

### 陷阱 31-1：Bus 在 on_init 中不可用
```python
# ❌ 错误：on_init 时 Bus 可能未完全初始化
@lifecycle("on_init")
async def on_init(self, **_):
    msgs = await self.ctx.bus.messages.get_recent(10).reload(self.ctx)

# ✅ 正确：在 on_start 中使用
@lifecycle("on_start")
async def on_start(self, **_):
    msgs = await self.ctx.bus.messages.get_recent(10).reload(self.ctx)
```

### 陷阱 31-2：忘记 await reload
```python
# ❌ 错误：没有 reload，plan 不会执行
plan = ctx.bus.messages.get_recent(10).filter(lambda m: m.role == "user")
for m in plan:  # 可能为空或报错
    print(m)

# ✅ 正确：显式 reload
plan = ctx.bus.messages.get_recent(10).filter(lambda m: m.role == "user")
for m in await plan.reload(ctx):
    print(m)
# 或者直接用（__iter__ 会自动触发 _ensure_materialized）
for m in plan:
    print(m)
```

### 陷阱 31-3：Watcher 内存泄漏
```python
# ❌ 错误：注册了 watcher 但从未取消
watcher = ctx.bus.messages.get_recent(10).watch(ctx)
# ... watcher 持续运行

# ✅ 正确：在 on_stop 中取消
@lifecycle("on_stop")
async def on_stop(self, **_):
    if hasattr(self, '_watcher'):
        self._watcher.unsubscribe()
```
