# Python 插件开发指南

## 核心导入

```python
from plugin.sdk.plugin import (
    NekoPluginBase,    # 基类
    neko_plugin,       # 类装饰器
    lifecycle,         # 生命周期方法装饰器
    plugin_entry,      # AI 入口装饰器
    timer_interval,    # 定时器装饰器
    ui,                # UI 相关（ui.action, ui.context）
    tr,                # 占位翻译函数
    Ok, Err,           # 返回值构造
    unwrap,            # 解包 Result
    SdkError,          # 错误类型
)
```

## 类结构

```python
@neko_plugin
class MyPlugin(NekoPluginBase):
    """插件描述"""

    def __init__(self, ctx):
        super().__init__(ctx)
        # 配置项：直接从 settings 映射
        self.my_setting: bool = False
        # 运行状态
        self._running = False

    # ══════════════════════════════════════════
    # 生命周期方法（必须包含 **_）
    # ══════════════════════════════════════════

    @lifecycle(id="startup")
    async def on_startup(self, **_):
        """启动时调用，必须在 10 秒内完成"""
        cfg = await self.config.dump()
        settings = cfg.get("settings", {})
        self.my_setting = settings.get("my_setting", False)
        await self._init_tables()           # 同步等待建表
        asyncio.create_task(self._init())   # 耗时操作放后台
        return Ok({"status": "ready"})

    @lifecycle(id="shutdown")
    async def on_shutdown(self, **_):
        """关闭时清理资源"""
        return Ok({"status": "shutdown"})

    @lifecycle(id="reload")
    async def on_reload(self, **_):
        """配置重载时调用"""
        cfg = await self.config.dump()
        settings = cfg.get("settings", {})
        self.my_setting = settings.get("my_setting", False)
        return Ok({"status": "reloaded"})

    @lifecycle(id="config_change")
    async def on_config_change(self, old_config=None, new_config=None, **_):
        """配置变更时调用（含新旧配置）"""
        if new_config:
            settings = new_config.get("settings", {})
            self.my_setting = settings.get("my_setting", False)
        return Ok({"status": "config_updated"})

    @lifecycle(id="freeze")
    async def on_freeze(self, **_):
        """插件被冻结时调用"""
        self._frozen = True
        return Ok({"status": "frozen"})

    @lifecycle(id="unfreeze")
    async def on_unfreeze(self, **_):
        """插件解冻时调用"""
        self._frozen = False
        return Ok({"status": "unfrozen"})

    # ══════════════════════════════════════════
    # AI 入口方法（必须包含 _ctx=None）
    # ══════════════════════════════════════════

    @plugin_entry(
        id="my_action",
        name="操作名称",
        description="描述给 AI 看，帮助 AI 理解何时调用此方法",
        input_schema={
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "参数1的描述",
                },
            },
            "required": ["param1"],
        },
    )
    async def my_action(self, param1: str = "", _ctx=None, **_):
        """改方法被 AI 调用时执行"""
        if not param1:
            return Err(SdkError("参数不能为空"))
        # 业务逻辑...
        return Ok({"result": "success"})

    # ══════════════════════════════════════════
    # UI Action 方法（必须包含 _ctx=None）
    # ══════════════════════════════════════════

    @ui.action(id="my_ui_action")
    async def my_ui_action(self, param1: str = "", _ctx=None, **_):
        """被 UI 面板的 ActionButton 调用"""
        return Ok({"result": "done"})

    # ══════════════════════════════════════════
    # UI Context 方法
    # ══════════════════════════════════════════

    @ui.context("settings")
    async def settings_context(self):
        """返回 settings 面板需要的数据"""
        return {
            "config": {
                "my_setting": self.my_setting,
            },
            "status": {"running": self._running},
        }

    # ══════════════════════════════════════════
    # 定时器方法
    # ══════════════════════════════════════════

    @timer_interval(id="my_timer", seconds=60, name="定时任务", auto_start=True)
    def _periodic_task(self, **_):
        """定时器在独立线程中执行，需要自己创建事件循环。"""
        if getattr(self, '_frozen', False):
            return Ok({"skipped": True})
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._async_periodic_work())
        finally:
            loop.close()
        return Ok({"done": True})
```

## 返回值模式

所有入口方法返回 `Ok(value)` 或 `Err(SdkError(message))`：

```python
# 成功
return Ok({"files": [...], "count": 5})

# 失败
return Err(SdkError("操作失败的原因"))

# 在调用处解包
result = await self.some_method()
if isinstance(result, Err):   # 注意：Err 是函数，要检查 _Err 实例
    return result
data = result.value
```

## 数据库模式

```python
# 建表 — 必须同步等待
async def _init_tables(self):
    session = unwrap(await self.db.session())
    try:
        await session.execute("""
            CREATE TABLE IF NOT EXISTS my_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        """)
        await session.commit()
    finally:
        await session.close()

# 查询
async def _query(self, name: str):
    session = unwrap(await self.db.session())
    try:
        cursor = await session.execute(
            "SELECT * FROM my_table WHERE name = ?", (name,)
        )
        rows = cursor.fetchall()   # ← 同步调用，不是 await
        return [dict(r) for r in rows]
    finally:
        await session.close()

# 批量插入 — 必须逐行 execute，不支持 executemany
async def _batch_insert(self, items: list):
    session = unwrap(await self.db.session())
    try:
        for item in items:
            await session.execute(
                "INSERT INTO my_table (name) VALUES (?)",
                (item["name"],)
            )
        await session.commit()
    finally:
        await session.close()

# 更新
async def _update(self, id: int, name: str):
    session = unwrap(await self.db.session())
    try:
        await session.execute(
            "UPDATE my_table SET name = ? WHERE id = ?",
            (name, id)
        )
        await session.commit()
        return True
    finally:
        await session.close()
```

## 关键模式

### 启动分离：快速同步 + 后台异步

```python
@lifecycle(id="startup")
async def on_startup(self, **_):
    # 1. 同步等待：读取配置、建表（必须快速）
    cfg = await self.config.dump()
    self._load_settings(cfg)
    await self._init_tables()

    # 2. 后台任务：耗时操作（扫描、索引、网络请求）
    asyncio.create_task(self._heavy_init())

    return Ok({"status": "ready"})
```

### 冻结保护

```python
@timer_interval(seconds=60)
    def _scheduled_task(self, **_):
        """定时器在独立线程中运行，需要自己创建事件循环。"""
        if self._frozen:
            return Ok({"skipped": True})
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._async_scheduled_work())
        finally:
            loop.close()
        return Ok({"done": True})
```

### 路径处理（文件操作类插件）

```python
# 路径必须绝对化
if not os.path.isabs(path):
    return Err(SdkError("请提供绝对路径"))

# 范围检查
def _path_in_scan_range(self, path: str) -> bool:
    if not self.scan_paths:
        return False
    norm = os.path.normpath(path).lower().rstrip(os.sep)
    for sp in self.scan_paths:
        sp_norm = os.path.normpath(sp).lower().rstrip(os.sep)
        if norm == sp_norm or norm.startswith(sp_norm + os.sep):
            return True
    return False
```

### 推送消息

```python
# 报告给 N.E.K.O 主界面（状态栏）
self.report_status({
    "status": "scanning",
    "progress": 50,
    "message": "扫描中... 50/100",
})

# 推送通知（聊天消息）
self.push_message(
    source="plugin_id",           # 插件标识
    visibility=["chat"],          # ["chat"] / ["notification"] / 两者
    ai_behavior="blind",          # "blind" = AI 不处理，只展示
    parts=[{"type": "text", "text": f"索引完成喵～共找到 {count} 个文件 ✨"}],
    priority=3,                   # 1-3=info, 4-6=warning, 7-9=error, 10=紧急
)
```

### 线程安全

```python
import threading

class MyPlugin:
    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._progress = {}

    def _update_progress(self, phase, current, total, msg):
        with self._lock:  # 线程安全写入
            self._progress = {"scanned": current, "total": total, "phase": phase}

    async def _do_work(self):
        with self._lock:  # 防止重复触发
            if self._running:
                return {"skipped": True}
            self._running = True
        try:
            # ... 耗时操作 ...
        finally:
            with self._lock:  # 确保锁释放
                self._running = False
```

### asyncio.to_thread（磁盘 I/O 不阻塞事件循环）

```python
import asyncio

# 分离同步函数
def _sync_disk_work(self, root: str) -> list[tuple]:
    """纯同步函数，在线程池中执行。"""
    result = []
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            st = os.stat(os.path.join(dirpath, fname))
            result.append((fname, st.st_size, st.st_mtime))
    return result

# 异步入口
async def _async_scan(self, root: str):
    entries = await asyncio.to_thread(self._sync_disk_work, root)
    # 回到主线程处理结果
    return entries
```

### i18n 安全调用

```python
def _t(self, key: str, default: str, **kwargs) -> str:
    """安全调用 self.i18n.t()，异常时自动回退到 default。"""
    try:
        return self.i18n.t(key, default=default, **kwargs)
    except Exception:
        return kwargs.get("default", default) if kwargs else default
```

### 配置自检

```python
async def _self_check(self):
    """后台自检：验证配置合法性并记录警告。"""
    if self.scan_paths:
        for p in self.scan_paths:
            if not os.path.isdir(p):
                self.logger.warning("自检: scan_path 不存在 -> %s", p)
```

### report_status — 向 UI 报告任务进度

```python
# ai_singer 使用 report_status 向 N.E.K.O 主界面报告处理进度
# 这是一种轻量级的状态推送机制，不需要 push_message 的聊天消息形式

self.report_status({
    "status": "processing",      # pending / processing / completed / failed
    "progress": 30,               # 0-100 整数
    "message": "正在连接云端声音克隆引擎...",
})

self.report_status({
    "status": "completed",
    "progress": 100,
    "message": "演唱完成！",
})
```

**使用原则**：
- 适用于耗时任务的进度展示（API 调用、文件处理等）
- `status` 推荐取值：`pending` / `processing` / `completed` / `failed`
- `progress` 为 0-100 整数，帮助用户感知等待时间
- `message` 用于描述当前阶段，用户可读

### data_path — 插件私有数据目录

```python
# N.E.K.O 为每个插件分配私有数据目录，用于存储插件运行时生成的文件
# ai_singer 使用它来存放合成的音频文件

output_path = str(self.data_path("songs") / f"{song_name}_{timestamp}.mp3")

# data_path 返回 pathlib.Path 对象，可以直接 / 拼接路径
# 自动创建不存在的目录（取决于实现，建议手动确保）
```

### file:/// URL 路径转换（本地文件可访问 URL）

```python
# 当需要在 UI 中播放/下载插件数据目录中的文件时，
# 将本地路径转为 file:/// URL

audio_url = f"file:///{output_path.replace(os.sep, '/')}"

# Windows 路径: C:\Users\...\songs\song.mp3
# 转为: file:///C:/Users/.../songs/song.mp3
```

### @plugin_entry + @ui.action 双装饰器模式

```python
# ✅ 同一方法同时作为 AI 入口和 UI action
# 这避免了代码重复，确保 AI 和 UI 调用的行为一致

@plugin_entry(
    id="sing",
    name="AI 演唱",
    description="使用云端声音克隆演唱歌词...",
    input_schema={...},
    llm_result_fields=["success", "audio_url"],
)
@ui.action(label=tr("actions.sing.label", default="🎤 开始演唱"), tone="primary", refresh_context=True)
async def sing(self, song_name: str = "", lyrics: str = "", **_):
    # AI 和 UI 都可以调用此方法
    ...
```

**`@ui.action` 的 `tone` 参数**：
- `"primary"` — 主色调按钮（推荐用于主要操作）
- 不指定则为默认样式

**`@ui.action` 的 `refresh_context` 参数**：
- `refresh_context=True` — 操作完成后自动刷新关联面板的 Context 数据
- 几乎所有会修改状态/数据的 action 都应该加此参数

### 定时器中的 asyncio（定时器在独立线程中执行）

```python
@timer_interval(id="my_timer", seconds=3600, name="定时任务", auto_start=True)
def _on_timer(self, **_):
    """定时器在独立线程中执行，需要自己创建事件循环。"""
    if getattr(self, '_frozen', False):
        return Ok({"skipped": True, "reason": "frozen"})

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(self._async_work())
    finally:
        loop.close()
    return Ok({"status": "done"})
```

## 方法签名速查表

| 装饰器 | 必须参数 | 特殊约束 | 说明 |
|--------|---------|---------|------|
| `@lifecycle(...)` | `**_` | — | 吸收 SDK 额外 kwargs |
| `@plugin_entry(...)` | `_ctx=None` | 不能有 `keywords` | AI 入口 |
| `@ui.action(...)` | `_ctx=None` | 可设 `tone="primary"`, `refresh_context=True` | UI 按钮调用 |
| `@ui.context(...)` | 无特殊要求 | 返回 dict | UI 数据提供 |
| `@timer_interval(...)` | 无特殊要求 | 独立线程，需 `new_event_loop()` | 定时任务 |

### @plugin_entry + @ui.action 叠加使用

可以同时挂载两个装饰器到同一方法，让 AI 和 UI 共享同一个实现。装饰器顺序：`@plugin_entry` 在上，`@ui.action` 在下。详见下方"双装饰器模式"章节。

## 完整模式速查

| 模式 | 适用场景 | 关键点 |
|------|---------|--------|
| 启动分离 | on_startup 超时 | 同步等待建表 + `asyncio.create_task` 后台任务 |
| 冻结保护 | 定时器 + 耗时操作 | `if self._frozen: return {"skipped": True}` |
| 线程安全 | 多线程共享状态 | `threading.Lock` + `finally` 释放 |
| 磁盘 I/O | 文件扫描/复制 | `asyncio.to_thread` 分离同步逻辑 |
| 批量处理 | 数据库写入 | `BATCH_SIZE=500` 分批 + 每批 commit |
| 多编码回退 | 读取文本文件 | 按频率尝试编码 + `latin-1` 兜底 |
| 路径验证 | 文件操作 | `os.path.isabs` + `rstrip(os.sep)` 范围检查 |
| 后台自检 | 配置验证 | `asyncio.create_task` 异步检查配置合法性 |
| i18n 安全调用 | 翻译 | try/except 包裹 + default 回退 |
| 进度报告 | 耗时任务进度展示 | `self.report_status({status, progress, message})` |
| 私有数据目录 | 插件运行时文件存储 | `self.data_path("subdir")` 返回 pathlib.Path |
| file:/// URL | UI 中访问本地文件 | `f"file:///{path.replace(os.sep, '/')}"` |
| 双装饰器 | 同一方法 AI+UI 共用 | `@plugin_entry` 在上 + `@ui.action` 在下 |

## 相关文档

- [08-AI友好设计](08-ai-friendly-design.md) — `@plugin_entry` 的 description 和错误消息设计
- [09-权限体系](09-permission-system.md) — 权限检查集成到入口方法
- [10-性能优化](10-performance.md) — `asyncio.to_thread`、批量处理、启动分离
- [11-撤销与日志](11-undo-and-logging.md) — 撤销栈、操作日志、push_message