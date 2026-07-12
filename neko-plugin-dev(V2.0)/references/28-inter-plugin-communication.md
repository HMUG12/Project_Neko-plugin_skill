# 插件间通信

> 基于 N.E.K.O 插件系统设计。覆盖跨插件调用、数据共享、依赖声明、事件总线模式。

---

## 一、通信机制概述

N.E.K.O 插件间的通信有三种方式：

| 方式 | 机制 | 适用场景 |
|------|------|----------|
| `self.plugins.call_entry()` | 直接调用其他插件的 `@plugin_entry` | 功能委托（如"用 ai_singer 唱歌"） |
| `self.bus` 事件总线 | 发布/订阅模式 | 广播事件（如"文件已创建"） |
| 共享存储 | 通过数据库或文件 | 持久化数据共享 |

---

## 二、call_entry 跨插件调用

### 2.1 基本用法

```python
# 插件 A 调用插件 B 的入口点
@plugin_entry(id="play_music", description="播放音乐")
async def play_music(self, *, song_name: str, _ctx=None):
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
async def handle_sing_request(self, *, song_name: str, _ctx=None):
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

```toml
[plugin]
name = "my_plugin"
version = "1.0.0"

# 声明对其他插件的依赖
[[plugin.dependencies.plugins]]
name = "ai_singer"
version = ">=0.6.0"
required = true   # 必需依赖

[[plugin.dependencies.plugins]]
name = "music_pusher"
version = ">=1.0.0"
required = false  # 可选依赖
```

### 3.2 运行时检查依赖

```python
@lifecycle(id="startup")
async def on_startup(self, **_):
    # 检查必需依赖
    required_plugins = ["ai_singer"]
    missing = []

    for name in required_plugins:
        try:
            # 尝试获取插件信息
            info = await self.plugins.get_info(name)
            self.logger.info(f"依赖插件 {name} v{info.version} 已就绪")
        except Exception:
            missing.append(name)

    if missing:
        self.logger.warning(f"缺少必需插件：{', '.join(missing)}")
        return Err(code="DEPENDENCY_MISSING",
                   message=f"缺少必需插件：{', '.join(missing)}")

    return Ok({"status": "ready"})
```

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

## 四、事件总线模式

### 4.1 发布事件

```python
# 文件管理插件：文件创建后发布事件
@plugin_entry(id="create_file", ...)
async def create_file(self, *, path: str, content: str, _ctx=None):
    # ... 创建文件 ...

    # 发布事件
    await self.bus.emit("file:created", {
        "path": path,
        "size": len(content),
        "plugin": self.name,
    })

    return Ok({"path": path})
```

### 4.2 订阅事件

```python
@lifecycle(id="startup")
async def on_startup(self, **_):
    # 订阅文件创建事件
    await self.bus.on("file:created", self._on_file_created)
    return Ok({})

async def _on_file_created(self, event_data: dict):
    """当任何插件创建文件时触发。"""
    path = event_data["path"]
    source_plugin = event_data["plugin"]

    if source_plugin == self.name:
        return  # 忽略自己发布的事件

    self.logger.info(f"检测到新文件：{path}（来自 {source_plugin}）")
    # ... 处理 ...
```

### 4.3 事件命名规范

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

### 5.1 通过数据库共享

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
async def play_song(self, *, song_name: str, _ctx=None):
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
