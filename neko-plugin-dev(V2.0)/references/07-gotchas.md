# 踩坑大全 — 已知陷阱与解决方案

> 基于 `file_manager` + `ai_singer` + `music_pusher` + `qq_auto_reply` 多插件实战 + N.E.K.O-main 主程序深度逆向分析，按严重程度排序，共 45 个已知陷阱。

---
## 🔴 致命级（直接导致插件崩溃）

### 1. UTF-8 BOM 导致 SyntaxError

> 详见 [06-deployment.md](06-deployment.md) BOM 移除命令

**现象**：`SyntaxError: invalid character '`' (U+FEFF)`

**原因**：某些编辑器（如 Windows 记事本）保存 UTF-8 文件时会自动添加 BOM（`\xEF\xBB\xBF`）。

**修复**：
```powershell
$content = [System.IO.File]::ReadAllBytes('file.py')
$newContent = $content[3..$content.Length]
[System.IO.File]::WriteAllBytes('file.py', $newContent)
```

**预防**：使用 VS Code 等编辑器，设置 `"files.encoding": "utf8"` 且 `"files.insertFinalNewline": true`。

---

### 2. 目录名大小写不匹配 → PluginEntryDirectoryMismatch

> 详见 [01-plugin-toml.md](01-plugin-toml.md) entry 路径规范

**现象**：`PluginEntryDirectoryMismatch` 错误

**原因**：`plugin.toml` 中 `entry = "plugins.file_manager:..."` 要求目录名为 `file_manager`，但实际目录是 `FileManager`。

**修复**：将目录重命名为与 `entry` 中完全一致的小写名。

**预防**：创建插件时就使用全小写 + 下划线命名。

---

### 3. plugin_entry 不支持 keywords 参数

**现象**：`plugin_entry() got an unexpected keyword argument 'keyword'`

**原因**：SDK 的 `plugin_entry` 装饰器不接受 `keywords` 参数。

**修复**：从 `@plugin_entry(...)` 中移除所有 `keywords=` 参数。关键词应放在 `description` 和 `plugin.toml` 的 `keywords` 字段中。

---

### 4. _SqliteAsyncSession 没有 executemany 方法

> 详见 [02-python-plugin.md](02-python-plugin.md) 数据库模式

**现象**：`'_SqliteAsyncSession' object has no attribute 'executemany'`

**原因**：SDK 封装的异步 SQLite 会话不支持 `executemany()`。

**修复**：
```python
# ❌ 错误
await session.executemany("INSERT INTO t VALUES (?)", [(1,), (2,)])

# ✅ 正确
for row in [(1,), (2,)]:
    await session.execute("INSERT INTO t VALUES (?)", row)
```

---

### 5. 启动超过 10 秒 → 超时

> 详见 [10-performance.md](10-performance.md) 启动优化

**现象**：`Plugin startup timed out after 10.0s`

**原因**：`on_startup` 中执行了耗时操作（如全量扫描目录）。

**修复**：
```python
async def on_startup(self, **_):
    # 快速操作：同步等待
    await self._ensure_tables()

    # 耗时操作：后台任务
    asyncio.create_task(self._heavy_init())

    return Ok({"status": "ready"})
```

---

## 🟡 严重级（导致功能异常）

### 6. 数据库未启用 → PluginDatabase 不可用

**现象**：`self.db` 为 None 或数据库操作失败

**原因**：`plugin.toml` 中 `[plugin.database] enabled = false`。

**修复**：
```toml
[plugin.database]
enabled = true
```

---

### 7. 数据库操作模式错误

**错误模式**：
```python
# ❌ 错误：两层 await
rows = await (await session.execute("SELECT ...")).fetchall()

# ❌ 错误：fetchall 也 await
rows = await cursor.fetchall()
```

**正确模式**：
```python
cursor = await session.execute("SELECT ...", params)
rows = cursor.fetchall()  # ← 同步调用，不 await
```

---

### 8. 根目录路径匹配失败

**现象**：`C:\test.txt` 无法匹配扫描根 `C:\`

**原因**：`os.path.normpath("C:\\") + os.sep` 产生 `C:\\`（双反斜杠），而 `os.path.normpath("C:\\test.txt")` 是 `C:\test.txt`，`startswith("C:\\\\")` 不匹配。

**修复**：
```python
def _path_in_scan_range(self, path: str) -> bool:
    norm = os.path.normpath(path).lower().rstrip(os.sep)
    for sp in self.scan_paths:
        sp_norm = os.path.normpath(sp).lower().rstrip(os.sep)
        if norm == sp_norm or norm.startswith(sp_norm + os.sep):
            return True
    return False
```

---

### 9. 部署目录中旧文件覆盖新代码

**现象**：修改了工作区代码但插件行为不变

**原因**：部署目录 `C:\Users\Admin\AppData\Local\N.E.K.O\plugins\` 中有旧版本文件，N.E.K.O 加载的是旧文件。

**修复**：手动同步工作区文件到部署目录，然后重启 N.E.K.O。

---

### 10. AI 构造无效路径

> 详见 [08-ai-friendly-design.md](08-ai-friendly-design.md) 完整工作流设计

**现象**：`路径不存在: F:\SteamLibrary\...\目标报错日志路径`

**原因**：N.E.K.O AI 将用户描述（如"目标报错日志路径"）当作路径名拼接到当前工作目录后，而不是先调用 `search_files` 查找真实路径。

**修复策略**：
1. 插件必须拒绝非绝对路径
2. 错误消息引导 AI 使用 `search_files` 或 `scan_folder_context`
3. 在 `@plugin_entry` 的 `description` 中明确说明工作流

**最佳实践**：
```python
# 拒绝非绝对路径
if not os.path.isabs(path):
    return Err(SdkError(
        "喵～路径不是绝对路径。请先用 search_files 搜索文件，"
        "获取完整路径后再操作～"
    ))

# 路径不存在时引导 AI
if not os.path.exists(path):
    return Err(SdkError(
        f"路径不存在: {path}。请先用 search_files 搜索确认"
        "文件完整路径，或用 scan_folder_context 扫描目录～"
    ))
```

---

## 🟢 一般级（影响体验）

### 11. UI 按钮首次渲染消失

**现象**：设置面板的 `ActionButton` 偶尔不显示

**原因**：`actions` 数组在首次渲染时可能为空，后续渲染时才填充。

**修复**：
```typescript
const [cachedActions, setCachedActions] = useLocalState("ca", () => [] as HostedAction[])
if (actions.length > 0 && actions.length !== cachedActions.length) {
    setCachedActions(actions)
}
const effectiveActions = cachedActions.length > 0 ? cachedActions : actions
```

---

### 12. 使用了不存在的 UI 组件

**不存在的组件**：`Table`、`Button`、`useState`

**替代方案**：
- `Table` → `DataTable`
- `Button` → `ActionButton`
- `useState` → `useLocalState`

---

### 13. Text 颜色值不支持 danger/warning/default

**仅支持的颜色**：`primary`、`secondary`、`muted`

---

### 14. 配置项未在 plugin.toml 中声明

**现象**：Python 代码中使用了 `self.allow_file_create`，但 `plugin.toml` 中没有这个配置项。

**后果**：配置项不会被持久化，重启后丢失。

**修复**：确保 `plugin.toml` 的 `[settings]` 节包含所有配置项。

---

### 15. 生命周期方法缺少 `**_`

**现象**：`TypeError: on_startup() got an unexpected keyword argument 'xxx'`

**原因**：SDK 会向生命周期方法注入额外参数。

**修复**：所有 `@lifecycle` 方法必须包含 `**_`。

---

### 16. 入口方法缺少 `_ctx=None`

**现象**：`plugin_entry() got an unexpected keyword argument '_ctx'`

**原因**：SDK 自动注入 `_ctx` 关键字参数。

**修复**：所有 `@plugin_entry` 和 `@ui.action` 方法必须包含 `_ctx=None`。

---

### 17. asyncio.create_task 是 fire-and-forget

**问题**：`asyncio.create_task()` 创建的任务如果抛出异常，不会被捕获。

**建议**：
```python
async def _safe_background_task(self):
    try:
        await self._heavy_work()
    except Exception as exc:
        self.logger.error("后台任务失败: %s", exc, exc_info=True)
```

---

### 18. useLocalState key 跨面板/标签页冲突

**现象**：切换到不同标签页后，`useLocalState` 的值互相覆盖或表现异常。

**原因**：不同组件使用了相同的 `useLocalState` key，N.E.K.O 的 local state 是按 key 全局共享的。

**修复**：
```tsx
// ❌ 错误：不同面板/标签页用了同一个 key
// settings.tsx
const [apiKey, setApiKey] = useLocalState("key", ...)

// panel.tsx
const [selectedVoice, setSelectedVoice] = useLocalState("key", ...)

// ✅ 正确：key 全局唯一，使用有意义的前缀
// settings.tsx
const [apiKey, setApiKey] = useLocalState("apiKey", ...)

// panel.tsx
const [selectedVoice, setSelectedVoice] = useLocalState("selectedVoice", ...)

// ✅ 正确：列表项状态用 id 组合 key
const [showLyrics, setShowLyrics] = useLocalState(`lyrics_${song.id}`, false)
```

**关键原则**：所有 `useLocalState` 的 key 在**整个插件范围内**必须唯一，不只是在单个组件内。

---

### 19. timer_interval 必须用 def（非 async def）

**现象**：`timer_interval` 装饰的方法使用了 `async def` 导致行为异常。

**原因**：N.E.K.O 的定时器在独立线程中执行，`async def` 无法直接在线程中运行。

**修复**：
```python
# ❌ 错误
@timer_interval(id="my_timer", seconds=300)
async def _on_timer(self, **_):
    await self._async_work()

# ✅ 正确：def + new_event_loop
@timer_interval(id="my_timer", seconds=300, name="定时任务", auto_start=True)
def _on_timer(self, **_):
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(self._async_work())
    finally:
        loop.close()
```

---

### 20. 保存配置只更新了部分字段

**现象**：`save_api_config` 调用后，部分配置项没有生效。

**原因**：`update_own_config` 传入的 `settings` 只包含被修改的字段，但 `on_config_change` 中可能假设所有字段都存在。

**修复**：
```python
# ✅ 正确：update_own_config 传入的 settings 只包含变更项即可
# N.E.K.O 会自动合并到完整配置中
await self.ctx.update_own_config({"settings": {
    "api_key": new_api_key,        # 只传变更项
    "workspace": new_workspace,
}})

# ✅ 正确：在 on_config_change 中用 .get() 读取，提供默认值
@lifecycle(id="config_change")
async def on_config_change(self, new_config=None, **_):
    if new_config:
        settings = new_config.get("settings", {})
        for key in self.DEFAULT_CONFIG:      # 遍历所有已知 key
            if key in settings:               # 只更新传入的
                self._config[key] = settings[key]
```

---

### 21. @ui.action 的 save 操作数值型参数默认值陷阱

**现象**：`@ui.action` 的 `float` 参数默认值为 `0` 时，UI 传入 `0` 会被判断为"未设置"而跳过。

**原因**：`if cosyvoice_speech_rate > 0` 这种判断逻辑会把 `0`（有效值）和未传入（默认值 `0`）混淆。

**修复**：
```python
# ❌ 错误：无法区分"未传入"和"传入 0"
async def save_config(self, speech_rate: float = 0, **_):
    if speech_rate > 0:          # 0 是有效值但被跳过了！
        self._config["speech_rate"] = speech_rate

# ✅ 正确：使用 sentinel 值区分
async def save_config(self, speech_rate: float = -1, **_):
    if speech_rate >= 0:         # -1 表示未传入，0 及以上都是有效值
        self._config["speech_rate"] = speech_rate

# 或者使用 None 作为默认值
async def save_config(self, speech_rate: float = None, **_):
    if speech_rate is not None:
        self._config["speech_rate"] = speech_rate
```

---

### 22. __pycache__ 缓存导致代码修改不生效 ⭐ 新增

> 详见 [17-pyc-cache-trap.md](17-pyc-cache-trap.md)

**现象**：修改了 `__init__.py`，同步到部署目录，重启 N.E.K.O，但日志显示旧代码仍在运行，已删除的 entry 仍然存在，已删除的配置项仍被持久化。**没有任何报错**。

**原因**：Python 加载的是 `__pycache__/__init__.cpython-3xx.pyc` 缓存文件，而不是 `.py` 源文件。

**诊断**：
```
# 日志中搜索 collect_entries，如果包含已删除的 entry → pyc 缓存问题
Plugin entries collected: ['...', 'clone_neko_voice', ...]  ← 这个 entry 源码中已删除！

# 日志中搜索 配置已持久化，如果包含已删除的配置项 → pyc 缓存问题
配置已持久化: ['cosyvoice_api_key', ...]  ← 这个配置项源码中已删除！
```

**修复**：
```powershell
# 删除 __pycache__ 目录
Remove-Item -Path "部署目录\__pycache__" -Recurse -Force
```

**预防**：每次修改 Python 文件后，同步脚本必须包含 `__pycache__` 清理步骤。

---

### 23. plugin.toml dependencies 格式错误 ⭐ 新增

**现象**：`config schema validation warnings: [{'loc': 'plugin.dependencies', 'msg': 'Input should be a valid list', 'type': 'list_type'}]`

**原因**：`plugin.toml` 中 `[plugin.dependencies]` 的格式不对。N.E.K.O 期望内联表格式：

```toml
# ❌ 错误：列表格式（虽然某些版本兼容但会报警告）
[plugin.dependencies]
python = ["openai>=1.0.0", "dashscope>=1.20.0"]

# ✅ 正确：内联表格式
[plugin.dependencies]
openai = ">=1.0.0"
```

---

### 24. 后端迁移后旧配置漂移 ⭐ 新增

> 详见 [16-backend-simplification.md](16-backend-simplification.md) 16.5 节

**现象**：新代码只写入 `mimo_api_key` 和 `mimo_voice`，但 `config.dump()` 仍返回旧版 `cosyvoice_*` 配置项。

**原因**：`update_own_config` 是合并操作，不会清除 settings 系统中的旧字段。

**修复**：
```python
# on_startup / on_reload / on_config_change 中用 DEFAULT_CONFIG 过滤
for key in self.DEFAULT_CONFIG:
    if key in settings:
        self._config[key] = settings[key]
# 旧字段（不在 DEFAULT_CONFIG 中）被自然忽略
```

---

### 25. LLM 跳过 check_setup 直接调用核心入口 ⭐ 新增

> 详见 [19-llm-workflow-design.md](19-llm-workflow-design.md)

**现象**：用户说"唱歌"，LLM 不先调用 `check_setup` 检查配置，直接调用 `sing` 然后报错"后端不可用"。

**原因**：`check_setup` 的 `description` 不够明确，没有用 ⚠️ 和"必须先调用"等强提示词。

**修复**：
```python
description=(
    "⚠️ 当用户说「唱歌」「唱首歌」「我想听你唱歌」「来一首」等任何唱歌相关请求时，"
    "必须先调用此入口检查配置是否就绪。"  # ← "必须先调用"
    "如果未就绪，引导用户在设置面板中配置 API Key 和音色。"
)
```

---

### 26. PluginRouter 入口 ID 重复 ⭐ 新增

> 详见 [20-plugin-router.md](20-plugin-router.md)

**现象**：多个 Router 注册后，部分入口点不显示或行为异常。

**原因**：不同 Router 中定义了相同 `id` 的 `@plugin_entry`，后注册的覆盖了前面的。

**修复**：
```python
# 方案 A：确保所有 Router 的 entry id 全局唯一
class WeatherRouter(PluginRouter):
    @plugin_entry(id="weather_current", ...)  # 带模块前缀
    async def current(self, ...): ...

class CountdownRouter(PluginRouter):
    @plugin_entry(id="time_countdown", ...)   # 带模块前缀
    async def countdown(self, ...): ...

# 方案 B：使用 prefix 参数
self.include_router(WeatherRouter(), prefix="weather_")
self.include_router(CountdownRouter(), prefix="time_")
```

---

### 27. @llm_tool 方法缺少 `*` 导致位置参数错误 ⭐ 新增

> 详见 [21-llm-tool-registration.md](21-llm-tool-registration.md)

**现象**：LLM 调用工具时出现 `TypeError: got multiple values for argument`。

**原因**：`@llm_tool` 装饰的方法签名没有用 `*` 强制 keyword-only，LLM 可能传入位置参数。

**修复**：
```python
# ❌ 错误
@llm_tool(name="search", ...)
async def search(self, query: str, limit: int = 10):
    ...

# ✅ 正确：强制 keyword-only
@llm_tool(name="search", ...)
async def search(self, *, query: str, limit: int = 10):
    ...
```

---

### 28. 纯前端插件的 Static UI 文件路径错误 ⭐ 新增

> 详见 [22-static-ui-plugin.md](22-static-ui-plugin.md)

**现象**：纯前端插件（无 `__init__.py`）的 `index.html` 无法加载，404 错误。

**原因**：`plugin.toml` 中 `entry` 路径错误，或文件未放在正确的 `static/` 目录中。

**修复**：
```toml
# ✅ 正确：.html 文件放在 static/ 目录
[[plugin.ui.panel]]
id = "main"
title = "My Dashboard"
entry = "static/index.html"      # .html → Static UI 模式
context = "dashboard"
permissions = ["state:read", "action:call"]
```

```toml
# ❌ 错误：.html 放在 ui/ 目录
entry = "ui/index.html"          # ui/ 是给 Hosted TSX 的
```

---

### 29. RPC 调用没有超时导致页面卡死 ⭐ 新增

> 详见 [22-static-ui-plugin.md](22-static-ui-plugin.md)

**现象**：纯前端插件的 RPC 调用后页面一直 loading，永不恢复。

**原因**：`fetch` 请求没有设置超时，后端任务卡住时前端无限等待。

**修复**：
```javascript
async function callEntry(entryId, args = {}, timeoutSec = 90) {
    const deadline = Date.now() + timeoutSec * 1000;

    // 创建任务...
    while (Date.now() < deadline) {
        const run = await fetch(`${RUNS_URL}/${run_id}`).then(r => r.json());
        if (run.status === "completed") return run;
        if (run.status === "failed") throw new Error(run.error);
        await sleep(230);
    }
    throw new Error(`Timeout after ${timeoutSec}s`);  // ← 必须超时退出
}
```

---

### 30. 积压消息无限增长导致内存溢出 ⭐ 新增

> 详见 [23-external-protocol-integration.md](23-external-protocol-integration.md)

**现象**：外部协议插件运行一段时间后内存持续增长，最终 OOM。

**原因**：消息积压队列没有上限控制，长时间运行后消息数无限增长。

**修复**：
```python
def add_message(self, msg: dict):
    conv["messages"].append(msg)

    # 限制积压数量
    limit = self.config.get("backlog_retention_limit", 200)
    if len(conv["messages"]) > limit:
        conv["messages"] = conv["messages"][-limit:]  # 只保留最近 N 条
```

---

### 31. 锁内执行磁盘 I/O 阻塞其他操作 ⭐ 新增

> 详见 [25-concurrency-race-conditions.md](25-concurrency-race-conditions.md) §2.1

**现象**：插件操作响应极慢，多个操作串行等待。

**原因**：在 `threading.Lock` 持有期间执行了磁盘 I/O，导致所有需要锁的操作被阻塞。

**修复**：
```python
# ❌ 错误：锁内做磁盘 I/O
with self._lock:
    self._data.append(record)
    json.dump(self._data, open("data.json", "w"))  # 阻塞所有操作！

# ✅ 正确：锁内只改数据，锁外 I/O
with self._lock:
    self._data.append(record)
    snapshot = list(self._data)  # 快照
await asyncio.to_thread(json.dump, snapshot, open("data.json", "w"))
```

---

### 32. 冻结标志只在循环开始检查一次 ⭐ 新增

> 详见 [25-concurrency-race-conditions.md](25-concurrency-race-conditions.md) §2.2

**现象**：插件被冻结后，正在执行的长任务没有停止。

**原因**：冻结标志 `self._frozen` 只在循环开始前检查了一次，循环内部不检查。

**修复**：
```python
# ❌ 错误：只检查一次
async def sing(self, ...):
    if self._frozen: return Err(...)
    for line in lines:
        await process(line)  # 冻结后继续执行

# ✅ 正确：每次迭代都检查
async def sing(self, ...):
    for line in lines:
        if self._frozen:
            return Err(code="FROZEN", message="已取消")
        await process(line)
```

---

### 33. 第三方库惰性导入无错误缓存 ⭐ 新增

> 详见 [26-backend-design-pattern.md](26-backend-design-pattern.md) §2.1

**现象**：`try/except ImportError` 失败后，每次调用都会重新尝试 import，在网络不可用时反复触发昂贵的操作。

**修复**：使用模块级变量缓存错误，失败后重放错误而不重试 import。详见 [24-error-handling-patterns.md](24-error-handling-patterns.md) §2.1。

---

### 34. 跨插件调用直接 import 其他插件类 ⭐ 新增

> 详见 [28-inter-plugin-communication.md](28-inter-plugin-communication.md) §6.1

**现象**：插件 A 升级后插件 B 崩溃。

**原因**：插件 B 直接 `from plugin_a import BackendClass` 导入了插件 A 的内部类，插件 A 重构后类名/接口改变。

**修复**：始终使用 `self.plugins.call_entry("plugin_a:entry_id", args={})` 跨插件调用，不直接导入。

---

### 35. 定时器中直接 await async 方法 ⭐ 新增

> 详见 [24-error-handling-patterns.md](24-error-handling-patterns.md) §2.6

**现象**：`@timer_interval` 装饰的 `def` 方法中直接 `await` 导致 `SyntaxError`。

**修复**：
```python
@timer_interval(id="check", seconds=300)
def _on_check(self, **_):
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(self._async_check())
    finally:
        loop.close()
```

---

### 36. on_init 中调用其他插件 ⭐ 新增

> 详见 [29-plugin-lifecycle-internals.md](29-plugin-lifecycle-internals.md) §11

**现象**：`on_init` 中 `call_entry` 返回 `PluginNotFound` 或超时。

**原因**：`on_init` 时其他插件可能尚未加载完成。

**修复**：跨插件调用放在 `on_start` 中。

---

### 37. push_message 大文件 base64 导致超时 ⭐ 新增

> 详见 [30-push-message-internals.md](30-push-message-internals.md) §10

**现象**：推送大文件（>5MB）时消息发送超时。

**原因**：`data: bytes` 会被 base64 编码，体积膨胀 33%，且 ZMQ 消息有大小限制。

**修复**：大文件使用 `{"type": "audio", "url": "file:///path/to/file", "mime": "..."}` 传递 URL。

---

### 38. Router 无 prefix 导致 Entry ID 冲突 ⭐ 新增

> 详见 [33-pluginrouter-entry-internals.md](33-pluginrouter-entry-internals.md) §12

**现象**：`EntryConflictError: Entry 'action' already registered`。

**原因**：多个 Router 中有相同 entry ID，且未设置 prefix。

**修复**：每个 Router 调用 `router.set_prefix("unique_prefix")`。

---

### 39. Bus 查询多次 reload 浪费带宽 ⭐ 新增

> 详见 [31-bus-system-internals.md](31-bus-system-internals.md) §7

**现象**：插件响应慢，ZMQ 往返次数多。

**原因**：每次调用 `.reload(ctx)` 都触发一次 ZMQ RPC 往返。

**修复**：使用惰性链式调用 `.filter().limit()` 一次性构建查询计划，只触发一次重放。

---

### 40. 忘记 await BusList 导致空结果 ⭐ 新增

> 详见 [31-bus-system-internals.md](31-bus-system-internals.md) §8

**现象**：`BusList` 迭代返回空或报错。

**原因**：`BusList` 是惰性的，需要显式 `await plan.reload(ctx)` 或触发 `_ensure_materialized()`。

**修复**：要么 `await plan.reload(ctx)`，要么在迭代前确保 `_ctx` 已设置。

---

### 41. 使用 loguru 代替框架 Logger ⭐ 新增

> 详见 [34-logger-system-internals.md](34-logger-system-internals.md) §7

**现象**：CI 拒绝 PR，日志不落地。

**原因**：框架底层使用 stdlib `logging`，`loguru` 被 CI 强制禁止。

**修复**：使用 `self.logger.info()` 而非 `from loguru import logger`。

---

### 42. store 中存储大量数据 ⭐ 新增

> 详见 [35-store-database-internals.md](35-store-database-internals.md) §2

**现象**：插件启动慢，配置加载卡顿。

**原因**：`self.store` 每次 `set()` 都写整个 JSON 文件到磁盘，全量加载到内存。

**修复**：大量结构化数据用 `self.db`（SQLite），少量配置/状态用 `self.store`。

---

### 43. i18n key 在各语言文件中不一致 ⭐ 新增

> 详见 [36-i18n-internals.md](36-i18n-internals.md) §7

**现象**：切换语言后部分文本显示为 key 本身或 default 值。

**原因**：`zh-CN.json` 和 `en.json` 的 key 不完全一致。

**修复**：确保所有语言文件的 key 完全一致，用脚本校验。

---

### 44. 通过 ZMQ 传输大文件 ⭐ 新增

> 详见 [37-zmq-transport-internals.md](37-zmq-transport-internals.md) §8

**现象**：`push_message` 超时或 ZMQ 消息被截断。

**原因**：ZMQ 消息大小有限制，base64 编码后体积膨胀 33%。

**修复**：大文件使用 `file://` URL 传递路径，不传 `data:` base64。

---

### 45. update_own_config 覆盖整个 settings ⭐ 新增

> 详见 [38-config-system-internals.md](38-config-system-internals.md) §8

**现象**：用户保存设置后，其他配置项丢失。

**原因**：`update_own_config({"settings": {...}})` 覆盖了整个 settings 对象。

**修复**：使用点号路径 `update_own_config({"settings.enable_ops": True})` 只传变更项。

---

## 快速排查清单

遇到问题时按顺序检查：

1. ☐ `__init__.py` 有 BOM 吗？
2. ☐ 目录名与 `plugin.toml` 的 `entry` 一致吗？
3. ☐ 所有 `@plugin_entry` 有 `_ctx=None` 吗？
4. ☐ 所有 `@lifecycle` 有 `**_` 吗？
5. ☐ 有 `executemany` 调用吗？
6. ☐ 有 `keywords=` 参数吗？
7. ☐ `plugin.toml` 中 `database.enabled = true` 吗？
8. ☐ 文件同步到部署目录了吗？**部署目录的 `__pycache__` 删了吗？** ⭐
9. ☐ 重启 N.E.K.O 了吗？
10. ☐ 路径匹配用了 `rstrip(os.sep)` 吗？
11. ☐ `useLocalState` 的 key 在整个插件范围内唯一吗？
12. ☐ `@timer_interval` 用了 `def`（非 `async def`）吗？
13. ☐ `save` 操作的数值参数默认值能区分"未传入"和"传入0"吗？
14. ☐ `update_own_config` 只传变更项，`on_config_change` 用 `.get()` + 默认值了吗？
15. ☐ `plugin.toml` dependencies 用了内联表格式（`key = "value"`）而非列表格式吗？ ⭐
16. ☐ 双装饰器叠加时 `@plugin_entry` 在上、`@ui.action` 在下吗？ ⭐
17. ☐ 核心入口的 `description` 明确写了前置条件（"必须先调用 check_setup"）吗？ ⭐
18. ☐ 不同 Router 的 entry id 全局唯一吗？（或用 `prefix` 隔离） ⭐
19. ☐ `@llm_tool` 方法签名用了 `*,` 强制 keyword-only 吗？ ⭐
20. ☐ 纯前端插件的 RPC 调用有超时控制吗？ ⭐
21. ☐ 消息积压队列有上限限制吗？ ⭐
22. ☐ 锁内只操作内存数据，磁盘 I/O 在锁外执行吗？ ⭐
23. ☐ 长循环每次迭代都检查 `self._frozen` 吗？ ⭐
24. ☐ 第三方库惰性导入有错误缓存吗？ ⭐
25. ☐ 跨插件调用用 `call_entry` 而非直接 import 吗？ ⭐
26. ☐ 定时器中 `await` 用 `run_until_complete` 桥接了吗？ ⭐
27. ☐ `on_init` 中调用了其他插件吗？ ⭐
28. ☐ 推送大文件用了 URL 而非 base64 吗？ ⭐
29. ☐ 多个 Router 都设置了不同 prefix 吗？ ⭐
30. ☐ Bus 查询用了惰性链式而非多次 reload 吗？ ⭐
31. ☐ BusList 迭代前已 await reload 或设置了 _ctx 吗？ ⭐
32. ☐ 用了 loguru 而非 self.logger 吗？ ⭐
33. ☐ store 中存储了大量数据吗？ ⭐
34. ☐ 所有 i18n 语言文件的 key 完全一致吗？ ⭐
35. ☐ update_own_config 用了点号路径而非整个 settings 对象吗？ ⭐