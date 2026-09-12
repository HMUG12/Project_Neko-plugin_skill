# 插件间通信

> 基于 N.E.K.O 插件系统设计。覆盖跨插件调用、数据共享、依赖声明、事件订阅模式。
>
> **版本**：核对日期 2026-09-12，SDK `>=0.1.0,<0.2.0`。本文正文（`call_entry` / 装饰器订阅 / 无 emit 结论）已对照官方文档；标注 🟡 的代码为**示意**（未在本机逐行运行）。

---

## 一、通信机制概述

N.E.K.O 插件间的通信有三种方式：

| 方式 | 机制 | 适用场景 |
|------|------|----------|
| `self.plugins.call_entry()` | 直接调用其他插件的 `@plugin_entry` | 功能委托（如"用 ai_singer 唱歌"） |
| `@message` / `@on_event` / `@custom_event` | 消息/事件订阅（仅订阅，**无 publish/emit API**） | 接收系统消息或自定义事件回调 |
| 共享存储 | 通过数据库或文件 | 持久化数据共享 |

> ⚠️ **关于 `self.bus.emit` / `self.bus.on`**：这两个调用方式在当前 SDK 不存在。Bus 是**只读查询 + watch 订阅**容器（见 [31-bus-system-internals](31-bus-system-internals.md)），没有 publish/emit API；插件间"广播事件"应通过 `@message` / `@on_event` 装饰器声明订阅，由框架派发。

---

## 二、call_entry 跨插件调用

### 2.1 基本用法

```python
# 插件 A 调用插件 B 的入口点
@plugin_entry(id="play_music", description="播放音乐")
async def play_music(self, *, song_name: str,):
    # 调用 music_pusher 插件的 push_music 入口
    result = await self.plugins.call_entry(
        "music_pusher:push_music",     # "插件名:入口ID"
        args={"song_name": song_name}  # 参数
    )
    return result
```

### 2.2 完整示例：ai_singer 被其他插件调用

```python
# 调用方：聊天插件
@plugin_entry(id="handle_sing_request", ...)
async def handle_sing_request(self, *, song_name: str,):
    # 1. 先检查 ai_singer 是否可用
    check = await self.plugins.call_entry(
        "ai_singer:check_setup",
        args={}
    )

    if not check.get("mimo_ok"):
        return Ok({"reply": f"唱歌功能未配置：{check.get('mimo_warning', '')}"})

    # 2. 委托演唱
    result = await self.plugins.call_entry(
        "ai_singer:sing",
        args={"song_name": song_name}
    )

    return Ok({"reply": f"已开始演唱「{song_name}」"})
```

### 2.3 错误处理

```python
try:
    result = await self.plugins.call_entry("other_plugin:some_entry", args={})
except PluginNotFoundError:
    return Err(code="PLUGIN_MISSING", message="所需插件未安装")
except EntryNotFoundError:
    return Err(code="ENTRY_MISSING", message="插件版本不兼容")
except Exception as e:
    return Err(code="CALL_FAILED", message=f"跨插件调用失败：{e}")
```

---

## 三、插件依赖声明

### 3.1 plugin.toml 中的依赖

`plugin.toml` 中被官方文档记录的 `[plugin.dependencies]` 是 **Python 第三方包**声明（内联表格式）：

```toml
[plugin.dependencies]
openai = ">=1.0.0"      # ✅ 内联表；不是 openai = [">=1.0.0"]
```

> ⚠️ **没有公开记录的"插件间依赖"声明格式**。不要写 `[[plugin.dependencies.plugins]]` 这类结构——它不在官方文档中，可能被 schema 校验拒绝。插件间依赖请在**运行时**探测并按可用性降级（见下）。

### 3.2 运行时检查依赖（🟡 示意）

插件 B 是否可用，最稳妥的方式是直接 `call_entry` 一个轻量"健康检查"入口并捕获异常：

```python
from plugin.sdk.plugin import lifecycle

@lifecycle(id="startup")
async def on_startup(self, **_):
    required = ["ai_singer"]          # 必需依赖
    missing = []
    for name in required:
        try:
            # 调对方一个约定好的只读入口确认存活/版本
            await self.plugins.call_entry(f"{name}:check_setup", args={})
        except Exception as e:
            self.logger.warning("依赖插件 {} 不可用: {}", name, e)
            missing.append(name)

    if missing:
        return Err(code="DEPENDENCY_MISSING",
                   message=f"缺少必需插件：{', '.join(missing)}")
    return Ok({"status": "ready"})
```

> 是否需要"启动即失败"取决于产品策略；很多插件选择**软降级**（缺依赖时相关功能禁用，不影响其余入口）。`self.plugins` 的完整方法集（是否有 `get_info` / 列出已安装插件等）以目标 SDK 文档为准，未验证前不要依赖。

### 3.3 可选依赖模式

```python
async def _try_use_music_pusher(self, song_data: dict):
    """尝试使用 music_pusher，不可用时静默跳过。"""
    try:
        await self.plugins.call_entry(
            "music_pusher:add_music",
            args={"song": song_data}
        )
    except Exception:
        self.logger.debug("music_pusher 不可用，跳过")
        # 静默失败，不影响主流程
```

---

## 四、消息/事件订阅（@message / @on_event / @custom_event）

> ⚠️ **本节替换旧的"self.bus.emit/on"示例**：Bus 不提供 publish/emit，跨插件广播事件通过装饰器声明订阅，框架派发。

### 4.1 订阅消息

```python
# 接收系统消息（其他插件的 push_message 或聊天）
from plugin.sdk.plugin import message

@message
async def on_incoming_message(self, msg):
    """msg 由框架注入，已是结构化对象。"""
    self.logger.info(f"收到消息: {msg.content}")
    # ... 处理 ...
    return Ok({})
```

### 4.2 订阅生命周期/系统事件

```python
from plugin.sdk.plugin import on_event, custom_event

@on_event("system:plugin_loaded")
async def on_plugin_loaded(self, event):
    self.logger.info(f"插件 {event['plugin']} 加载完成")
    return Ok({})

# 自定义事件（其他插件可通过 call_entry / 框架派发触发）
@custom_event("file:created")
async def on_file_created(self, payload: dict):
    path = payload.get("path", "")
    self.logger.info(f"文件已创建: {path}")
    return Ok({})
```

### 4.3 跨插件"通知"的正确做法

如果需要把"我刚做完一件事"告诉其他插件，**不要**直接 emit，正确做法是：

```python
@plugin_entry(id="create_file", ...)
async def create_file(self, *, path: str, content: str):
    # 1. 真正干活
    write_file(path, content)

    # 2. 通知：调用对方插件的入口点（call_entry 是唯一的"广播"途径）
    await self.plugins.call_entry(
        "downstream_plugin:on_file_created",
        args={"path": path, "size": len(content)},
    )
    return Ok({"path": path})
```

下游插件侧：

```python
@plugin_entry(id="on_file_created", name="接收文件创建事件",
              description="由其他插件通过 call_entry 调用")
async def on_file_created(self, path: str, size: int = 0, **_):
    self.logger.info(f"收到文件创建通知: {path} ({size} 字节)")
    return Ok({})
```

### 4.4 事件命名规范

```
{领域}:{动作}

示例：
file:created
file:deleted
music:playing
music:stopped
chat:message_received
system:plugin_loaded
```

**命名规则**：
- 小写 + 冒号分隔
- 领域在前，动作在后
- 动作使用过去式（created 而非 create）

---

## 五、共享数据模式

> 共享数据属于**强耦合**，优先考虑用 `call_entry` 让对方自己读写自己的数据。确需共享时才用下面的方式。

### 5.1 通过数据库共享（🟡 示意）

```python
# 插件 A：写入数据
async def save_shared_data(self, key: str, value: dict):
    async with self.db.session() as session:
        await session.execute(
            text("INSERT OR REPLACE INTO shared_data (key, value, plugin) VALUES (:k, :v, :p)"),
            {"k": key, "v": json.dumps(value), "p": self.name}
        )

# 插件 B：读取数据
async def read_shared_data(self, key: str):
    async with self.db.session() as session:
        result = await session.execute(
            text("SELECT value FROM shared_data WHERE key = :k"),
            {"k": key}
        )
        row = result.fetchone()
        return json.loads(row[0]) if row else None
```

### 5.2 通过 data_path 共享文件

```python
# 插件 A：写入共享文件
shared_dir = os.path.join(self.data_path, "..", "shared")
os.makedirs(shared_dir, exist_ok=True)
with open(os.path.join(shared_dir, "config.json"), "w") as f:
    json.dump(config, f)

# 插件 B：读取共享文件
shared_dir = os.path.join(self.data_path, "..", "shared")
with open(os.path.join(shared_dir, "config.json"), "r") as f:
    config = json.load(f)
```

---

## 六、跨插件通信设计原则

### 6.1 最小化耦合

```python
# ❌ 紧耦合：直接导入其他插件的类
from other_plugin import SomeBackend
backend = SomeBackend(config)

# ✅ 松耦合：通过 call_entry 调用
result = await self.plugins.call_entry("other_plugin:do_thing", args={})
```

### 6.2 防御性调用

```python
async def call_other_safely(self, entry: str, args: dict, default=None):
    """安全调用其他插件，失败时返回默认值。"""
    try:
        result = await self.plugins.call_entry(entry, args=args)
        return result
    except Exception as e:
        self.logger.warning(f"跨插件调用失败 {entry}: {e}")
        return default
```

### 6.3 版本兼容性

```python
async def call_with_fallback(self, entry: str, args: dict):
    """先尝试新版入口，失败回退到旧版。"""
    try:
        return await self.plugins.call_entry(f"other_plugin:{entry}_v2", args=args)
    except EntryNotFoundError:
        self.logger.debug(f"{entry}_v2 不存在，回退到 {entry}")
        return await self.plugins.call_entry(f"other_plugin:{entry}", args=args)
```

---

## 七、完整示例：音乐推送 + AI 唱歌联动

```python
# 聊天插件中实现"放首歌"功能
@plugin_entry(id="play_song", description="播放指定歌曲")
async def play_song(self, *, song_name: str,):
    # 1. 尝试用 ai_singer 演唱
    check = await self._safe_call("ai_singer:check_setup", {})
    if check and check.get("mimo_ok"):
        result = await self._safe_call("ai_singer:sing", {"song_name": song_name})
        return Ok({"reply": f"正在演唱「{song_name}」"})

    # 2. 回退：尝试从 music_pusher 的库中播放
    music = await self._safe_call("music_pusher:search_library",
                                   {"keyword": song_name})
    if music and music.get("found"):
        await self._safe_call("music_pusher:push_music",
                              {"track_id": music["track_id"]})
        return Ok({"reply": f"正在播放「{music['title']}」"})

    # 3. 都不可用
    return Ok({"reply": f"抱歉，没有找到「{song_name}」的可用来源"})
```

---

## 八、检查清单

- [ ] 跨插件调用使用 `self.plugins.call_entry()` 而非直接导入
- [ ] plugin.toml 中声明了必需/可选插件依赖
- [ ] 启动时检查必需依赖是否可用
- [ ] 可选依赖的调用有 try/except 保护
- [ ] 事件命名遵循 `{领域}:{动作}` 规范
- [ ] 事件处理中检查 `source_plugin` 避免循环
- [ ] 共享数据有 schema 文档说明
- [ ] 有版本兼容性回退策略
