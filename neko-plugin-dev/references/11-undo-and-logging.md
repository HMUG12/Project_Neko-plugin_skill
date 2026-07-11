# 撤销机制与操作日志

> 完整的撤销栈 + 操作日志 + 数据库同步模式。

---

## 撤销栈设计

### 数据结构

```python
def __init__(self, ctx):
    self._undo_stack: list[dict] = []  # 撤销栈
    self._max_undo_steps = 50          # 最多保留 50 步
```

### 入栈

```python
async def _push_undo(self, undo_item: dict):
    self._undo_stack.append(undo_item)
    if len(self._undo_stack) > self._max_undo_steps:
        self._undo_stack.pop(0)  # 超出上限时移除最旧的
```

### 撤销操作类型映射

每种操作需要不同的撤销逻辑：

```python
# 创建 → 撤销 = 删除
await self._push_undo({
    "action": "delete",
    "source_path": created_path,
    "is_dir": is_dir,
})

# 复制 → 撤销 = 删除目标
await self._push_undo({
    "action": "uncopy",
    "source_path": dest_path,
    "is_dir": is_dir_src,
})

# 移动 → 撤销 = 移回去
await self._push_undo({
    "action": "unmove",
    "source_path": moved_path,    # 当前位置
    "dest_path": original_path,   # 原始位置
    "is_dir": is_dir_src,
})

# 删除 → 撤销 = 恢复（使用临时回收站）
await self._push_undo({
    "action": "undelete",
    "source_path": deleted_path,
    "is_dir": is_dir_src,
})
```

### 撤销执行

```python
async def _remove_db_entries(self, paths: list[str]):
    """从索引数据库中删除指定路径及其子路径。"""
    session = unwrap(await self.db.session())
    try:
        for p in paths:
            await session.execute(
                "DELETE FROM files WHERE path = ? OR path LIKE ?",
                (p, p + os.sep + "%"),
            )
        await session.commit()
    finally:
        await session.close()

@ui.action(id="undo_operation")
async def undo_operation(self, _ctx=None, **_):
    if not self._undo_stack:
        return Ok({"success": False, "message": "喵～没有可以撤销的操作了"})

    undo_item = self._undo_stack.pop()
    action = undo_item["action"]
    source_path = undo_item["source_path"]
    is_dir = undo_item.get("is_dir", False)

    try:
        if action == "delete":
            # 撤销创建 = 删除创建的文件
            if is_dir:
                shutil.rmtree(source_path)
            else:
                os.remove(source_path)
            await self._remove_db_entries([source_path])

        elif action == "uncopy":
            # 撤销复制 = 删除目标
            if is_dir:
                shutil.rmtree(source_path)
            else:
                os.remove(source_path)
            await self._remove_db_entries([source_path])

        elif action == "unmove":
            # 撤销移动 = 移回原位
            dest_path = undo_item["dest_path"]
            shutil.move(source_path, dest_path)
            await self._upsert_file_record(dest_path)

        elif action == "undelete":
            # 撤销删除 = 无法恢复（文件已永久删除）
            return Ok({
                "success": False,
                "message": "喵～文件已经被删掉了，没办法恢复啦…抱歉喵",
            })

        return Ok({"success": True, "action": action, "path": source_path})

    except Exception as exc:
        # 撤销失败时推回栈中
        self._undo_stack.append(undo_item)
        return Err(SdkError(f"撤销失败喵: {exc}"))
```

### 撤销栈的边界处理

```python
# 操作失败时不要入栈
try:
    shutil.copy2(src, dst)
    await self._push_undo({"action": "uncopy", "source_path": dst})
except OSError:
    return Err(SdkError("复制失败"))
    # 注意：失败时不入栈

# 撤销失败时推回栈中
try:
    shutil.move(dst, src)
except Exception:
    self._undo_stack.append(undo_item)  # 恢复栈项
    return Err(SdkError("撤销失败"))
```

### UI 中显示撤销步数

```python
@ui.context("settings")
async def settings_context(self):
    return {
        "undo_steps": len(self._undo_stack),  # 传给 UI
    }
```

```tsx
// 在 UI 中显示
{undoAction && undoSteps > 0 && (
    <ActionButton action={undoAction}>撤销 ({undoSteps})</ActionButton>
)}
```

---

## 操作日志

### 日志表结构

```sql
CREATE TABLE IF NOT EXISTS operation_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    action        TEXT    NOT NULL,    -- 操作类型: copy/move/delete/create
    source_path   TEXT    DEFAULT '',  -- 源路径
    dest_path     TEXT    DEFAULT '',  -- 目标路径
    timestamp     REAL    NOT NULL,    -- 时间戳
    success       BOOLEAN DEFAULT 1,  -- 是否成功
    error_msg     TEXT    DEFAULT '',  -- 错误信息
    is_dangerous  BOOLEAN DEFAULT 0,  -- 是否危险操作
    can_undo      BOOLEAN DEFAULT 0,  -- 是否可撤销
    undo_data     TEXT    DEFAULT ''   -- 撤销数据 JSON
)
```

### 日志记录函数

```python
async def _log_operation(
    self, action, source_path="", dest_path="",
    success=True, error_msg="", is_dangerous=False,
    can_undo=False, undo_data=None,
):
    import json
    undo_json = json.dumps(undo_data) if undo_data else ""
    session = unwrap(await self.db.session())
    try:
        await session.execute(
            """INSERT INTO operation_logs
               (action, source_path, dest_path, timestamp, success,
                error_msg, is_dangerous, can_undo, undo_data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (action, source_path, dest_path, time.time(),
             success, error_msg, is_dangerous, can_undo, undo_json),
        )
        await session.commit()
    finally:
        await session.close()

    if is_dangerous:
        self.logger.warning(
            "⚠️ 危险操作: action=%s, source=%s, dest=%s, success=%s",
            action, source_path, dest_path, success,
        )
```

### 在操作中记录日志

```python
async def file_operation(self, action, source_path, dest_path, ...):
    is_dangerous = action in ("delete", "move")
    can_undo = action in ("copy", "move", "delete", "create")

    # 操作前记录
    try:
        shutil.copy2(source_path, dest_path)
    except OSError as e:
        await self._log_operation(action, source_path, dest_path,
                                   False, str(e), is_dangerous)
        return Err(SdkError(f"操作失败: {e}"))

    # 操作后记录
    await self._log_operation(action, source_path, dest_path,
                               True, "", is_dangerous, can_undo)
```

### 日志查询

```python
@plugin_entry(id="get_operation_logs", name="操作日志")
async def get_operation_logs(self, limit=20, only_dangerous=False, _ctx=None, **_):
    session = unwrap(await self.db.session())
    try:
        where = "WHERE is_dangerous=1" if only_dangerous else ""
        cursor = await session.execute(
            f"SELECT * FROM operation_logs {where} ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
    finally:
        await session.close()

    return Ok({
        "logs": [dict(r) for r in rows],
        "total": len(rows),
    })
```

---

## 操作后数据库同步

操作成功后需要同步索引数据库：

```python
# 删除操作 → 删除数据库记录
if action == "delete":
    await session.execute(
        "DELETE FROM files WHERE path = ? OR path LIKE ?",
        (source_path, source_path + os.sep + "%"),
    )

# 移动操作 → 删除旧记录 + 写入新记录
if action == "move":
    await session.execute(
        "DELETE FROM files WHERE path = ? OR path LIKE ?",
        (source_path, source_path + os.sep + "%"),
    )
    await self._upsert_file_record(dest_path)

# 创建/复制操作 → 写入新记录
if action in ("create", "copy", "paste"):
    await self._upsert_file_record(dest_path)
```

**注意**：删除目录时用 `LIKE` 匹配子路径，确保子文件也被删除。

---

## push_message 通知

关键事件应通过 `push_message` 通知用户：

```python
# 成功
self.push_message(
    source="plugin_id",
    visibility=["chat"],
    ai_behavior="blind",
    parts=[{"type": "text", "text": f"索引完成喵～共找到 {count} 个文件 ✨"}],
    priority=3,  # 低优先级
)

# 失败
self.push_message(
    source="plugin_id",
    visibility=["chat"],
    ai_behavior="blind",
    parts=[{"type": "text", "text": f"呜…索引出问题了喵: {exc}"}],
    priority=8,  # 高优先级
)
```

**priority 级别**：
- `1-3`：信息性通知（索引完成、统计更新）
- `4-6`：警告（配置变更、路径跳过）
- `7-9`：错误（操作失败、崩溃）
- `10`：紧急（安全事件）

**visibility**：
- `["chat"]`：显示在聊天中
- `["notification"]`：系统通知
- `["chat", "notification"]`：两者都显示

**ai_behavior**：
- `"blind"`：AI 不处理此消息，只展示给用户

---

## 完整检查清单

- [ ] 撤销栈有最大容量限制（如 50 步）
- [ ] 每种操作类型都有对应的撤销逻辑
- [ ] 操作失败时不入撤销栈
- [ ] 撤销失败时推回栈项
- [ ] 操作日志记录了所有关键信息
- [ ] 危险操作有特殊标记和日志警告
- [ ] 操作后同步更新索引数据库
- [ ] 目录删除时用 LIKE 匹配子路径
- [ ] 关键事件通过 push_message 通知
- [ ] UI 中展示了撤销步数

## 相关文档

- [02-python-plugin.md](02-python-plugin.md) — 数据库模式（日志表操作）
- [08-ai-friendly-design.md](08-ai-friendly-design.md) — `verify_context` 与操作后验证
- [03-ui-settings.md](03-ui-settings.md) — 撤销按钮 + 操作日志表格 UI