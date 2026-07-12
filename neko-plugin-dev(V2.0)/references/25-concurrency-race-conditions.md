# 并发与竞态条件

> 基于 `ai_singer` + `qq_auto_reply` 插件实战。覆盖 asyncio 并发、线程安全、请求去重、积压控制。

---

## 一、核心问题

N.E.K.O 插件运行在 asyncio 事件循环中，同时面临：
- 多个 `@plugin_entry` 可能被同时调用
- `@timer_interval` 在独立线程中运行
- 用户通过 UI 和 AI 对话可能同时触发操作
- 外部协议（如 OneBot WebSocket）在后台推送消息

**并发安全 = 数据一致性 + 用户体验 + 资源不泄漏**

---

## 二、线程安全模式

### 2.1 锁外 I/O 模式（Lock Scope Minimization）

> 来源：`ai_singer/__init__.py` L1244-1249

```python
self._lock = threading.Lock()

async def add_song(self, song_record):
    # 锁内：只操作共享数据结构
    with self._lock:
        self._recent_songs.append(song_record)
        snapshot = list(self._recent_songs)  # 快照复制

    # 锁外：执行磁盘 I/O
    await asyncio.to_thread(self._save_songs_sync, snapshot)
```

**为什么这样做**：
- 锁的作用域最小化 → 减少锁竞争
- 在锁内做快照复制 → 确保保存的是一致状态
- 磁盘 I/O 在锁外执行 → 不阻塞其他线程的数据访问

**反例**（锁太大）：
```python
# ❌ 错误：在锁内执行磁盘 I/O
with self._lock:
    self._recent_songs.append(record)
    json.dump(self._recent_songs, open("songs.json", "w"))  # 阻塞其他所有操作！
```

---

### 2.2 冻结/取消模式（Graceful Cancellation）

> 来源：`ai_singer/__init__.py` L493-501

当插件被宿主"冻结"时，取消正在进行的长时间任务：

```python
@lifecycle(id="freeze")
async def on_freeze(self, **_):
    self._frozen = True
    if self._live_sing_task:
        self._live_sing_task.cancel()  # 取消正在进行的演唱
    return Ok({"status": "frozen"})

@lifecycle(id="unfreeze")
async def on_unfreeze(self, **_):
    self._frozen = False
    return Ok({"status": "active"})
```

**在长时间循环中检查冻结标志**：
```python
async def sing(self, *, song_name: str, _ctx=None):
    for i, line in enumerate(lines):
        if self._frozen:
            return Err(code="FROZEN", message="插件已冻结，演唱已取消")
        # ... 处理当前行 ...
```

**模式要点**：
- 循环的每次迭代都检查标志
- 不只在循环开始检查一次（可能在循环中被冻结）
- 取消后返回明确的 Err 而非静默退出

---

### 2.3 防重入刷新（Refresh Guard）

> 来源：`music_pusher/data/static_ui/index.html` L1940-1961

```javascript
const state = {
    refreshing: false,
    // ...
};

async function refreshAll() {
    if (state.refreshing) return;  // 防重入
    state.refreshing = true;

    try {
        const [music, tasks] = await Promise.all([
            fetchMusicItems(),
            fetchTasks(),
        ]);
        state.musicItems = music;
        state.tasks = tasks;
        renderAll();
    } catch (err) {
        console.error("刷新失败:", err);
    } finally {
        state.refreshing = false;
    }
}
```

**为什么需要**：
- `refreshAll` 被定时器（每 5s）和用户操作（上传后）同时触发
- 不加防重入可能导致两个刷新同时进行，数据交错覆盖

---

### 2.4 消息积压上限控制

> 来源：`qq_auto_reply/data/business_config.json`

```python
def add_message(self, conv_key: str, msg: dict):
    conv = self._conversations[conv_key]
    conv["messages"].append(msg)
    conv["unread_count"] += 1

    # 限制积压数量
    limit = self.config.get("backlog_retention_limit", 200)
    if len(conv["messages"]) > limit:
        conv["messages"] = conv["messages"][-limit:]  # 只保留最近 N 条
```

**配置项设计**：
```json
{
    "backlog_retention_limit": 200,           // 每个会话最多保留多少条
    "backlog_summary_threshold": 10,          // 超过多少条未读触发摘要
    "backlog_notify_cooldown_seconds": 900,   // 通知冷却时间（15分钟）
    "backlog_issue_notify_threshold": 1,      // 触发通知的最低积压数
    "max_concurrent_messages": 3              // 最大并发处理消息数
}
```

**防止 OOM 的策略**：
- `backlog_retention_limit` → 硬上限，超出截断
- `backlog_summary_threshold` → 软阈值，触发 AI 摘要
- `backlog_notify_cooldown_seconds` → 防止通知轰炸

---

## 三、请求去重与幂等性

### 3.1 任务级去重

当同一个操作可能被多次触发时（如用户双击按钮、AI 和 UI 同时触发）：

```python
self._pending_tasks: dict[str, asyncio.Task] = {}

async def sing(self, *, song_name: str, _ctx=None):
    task_key = f"sing:{song_name}"

    # 检查是否已有相同任务在运行
    if task_key in self._pending_tasks:
        existing = self._pending_tasks[task_key]
        if not existing.done():
            return Err(code="ALREADY_RUNNING",
                       message=f"歌曲「{song_name}」正在演唱中，请等待完成")

    # 创建并注册任务
    task = asyncio.create_task(self._do_sing(song_name))
    self._pending_tasks[task_key] = task

    try:
        return await task
    finally:
        self._pending_tasks.pop(task_key, None)
```

### 3.2 播放 URL 去重

> 来源：`music_pusher/data/static_ui/index.html` L1876

```javascript
function syncRuntimePlayer(url) {
    // 去重：如果 URL 没变，不重复设置（避免播放中断）
    if (state.lastRuntimeTrackUrl === url) return;
    state.lastRuntimeTrackUrl = url;

    const player = document.getElementById("syncPlayer");
    player.src = url;
    player.play();
}
```

---

## 四、WebSocket 重连策略

> 来源：`qq_auto_reply/data/business_config.json`

```python
class OneBotConnection:
    def __init__(self, config):
        self._ws_url = config["onebot_url"]
        self._reconnect_delay = 1       # 初始重连延迟（秒）
        self._max_reconnect_delay = 60  # 最大重连延迟
        self._should_run = True

    async def connect(self):
        while self._should_run:
            try:
                async with websockets.connect(self._ws_url) as ws:
                    self._reconnect_delay = 1  # 连接成功后重置延迟
                    await self._handle_messages(ws)
            except Exception as e:
                self.logger.warning(f"WebSocket 断开：{e}，{self._reconnect_delay}s 后重连")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2,
                    self._max_reconnect_delay
                )  # 指数退避

    async def shutdown(self):
        self._should_run = False
```

**指数退避策略**：
```
第 1 次断开 → 等 1s
第 2 次断开 → 等 2s
第 3 次断开 → 等 4s
第 4 次断开 → 等 8s
...
第 N 次断开 → 等 min(2^(N-1), 60)s
连接成功后 → 重置为 1s
```

---

## 五、回复概率控制

> 来源：`qq_auto_reply/data/business_config.json`

三种场景使用不同的回复概率：

```python
async def should_reply(self, message: dict) -> bool:
    """根据消息类型决定是否回复。"""
    import random

    # 检查是否被 @ 或点名
    if message.get("is_at_bot") or self._is_mentioned(message):
        return True  # 100% 回复

    # 检查是否是信任用户
    if self._is_trusted(message["sender_id"]):
        prob = self.config["open_reply_probability"]     # 默认 0.1 (10%)
    else:
        prob = self.config["normal_relay_probability"]   # 默认 0.1 (10%)

    return random.random() < prob
```

**概率体系设计**：
```json
{
    "normal_relay_probability": 0.1,   // 普通用户回复概率 10%
    "open_reply_probability": 0.1,     // 信任用户回复概率 10%
    "truth_reply_probability": 0.1     // 诚实模式回复概率 10%
}
```

**为什么需要概率控制**：
- 避免机器人太"话痨"打扰群聊
- 防止 AI 调用过于频繁（API 费用控制）
- 可以通过 UI 调节（用户自行决定活跃度）

---

## 六、并发配置项设计指南

```json
{
    // 超时控制
    "ai_connect_timeout_seconds": 10.0,        // AI 连接超时
    "ai_turn_timeout_seconds": 60.0,           // 单轮对话超时
    "handler_shutdown_timeout_seconds": 10.0,  // 处理器关闭超时

    // 并发限制
    "max_concurrent_messages": 3,              // 最大并发处理数

    // 积压控制
    "backlog_retention_limit": 200,            // 保留上限
    "backlog_summary_threshold": 10,           // 摘要触发阈值
    "backlog_notify_cooldown_seconds": 900,    // 通知冷却
    "backlog_issue_notify_threshold": 1        // 通知触发阈值
}
```

**配置项命名规范**：
- 时间类：`{功能}_seconds` / `{功能}_ms`
- 数量类：`{功能}_limit` / `{功能}_threshold` / `max_{功能}`
- 概率类：`{场景}_probability`
- 开关类：`{功能}_enabled` / `show_{功能}`

---

## 七、速查表

| 并发场景 | 推荐模式 | 来源 |
|----------|----------|------|
| 多入口同时修改共享数据 | `threading.Lock` + 锁内只改数据 | ai_singer |
| 插件被冻结时取消任务 | 循环中检查 `self._frozen` 标志 | ai_singer |
| 定时器 + 用户操作同时刷新 | `refreshing` 防重入标志 | music_pusher |
| 消息积压防止 OOM | `backlog_retention_limit` 硬上限 | qq_auto_reply |
| 相同操作被重复触发 | `_pending_tasks` 去重字典 | 通用 |
| WebSocket 断线重连 | 指数退避 + 成功重置 | qq_auto_reply |
| 控制 AI 回复频率 | 场景化概率控制 | qq_auto_reply |
| 防止重复播放 | URL 去重比较 | music_pusher |
