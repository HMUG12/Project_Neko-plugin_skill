# 踩坑大全 — 已知陷阱与解决方案

> 基于 `file_manager` 插件开发全过程，按严重程度排序。

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

## 快速排查清单

遇到问题时按顺序检查：

1. ☐ `__init__.py` 有 BOM 吗？
2. ☐ 目录名与 `plugin.toml` 的 `entry` 一致吗？
3. ☐ 所有 `@plugin_entry` 有 `_ctx=None` 吗？
4. ☐ 所有 `@lifecycle` 有 `**_` 吗？
5. ☐ 有 `executemany` 调用吗？
6. ☐ 有 `keywords=` 参数吗？
7. ☐ `plugin.toml` 中 `database.enabled = true` 吗？
8. ☐ 文件同步到部署目录了吗？
9. ☐ 重启 N.E.K.O 了吗？
10. ☐ 路径匹配用了 `rstrip(os.sep)` 吗？