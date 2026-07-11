# 权限体系设计模式

> 基于 `file_manager` 的两层权限体系：总开关 + 逐操作授权。

---

## 设计模式：两层权限

```python
# 第一层：总开关
self.enable_ops: bool = False

# 第二层：逐操作授权
self.allow_read: bool = False
self.allow_move: bool = False
self.allow_delete: bool = False
self.allow_create: bool = False
self.allow_write: bool = False
self.allow_exec: bool = False
```

**为什么需要两层？**
- 总开关：一键关闭所有危险操作，无需逐个修改
- 逐操作授权：给用户精细化控制，AI 只能执行被授权的操作

---

## 完整实现

### 1. plugin.toml 配置项

```toml
[settings]
enable_file_ops = false
allow_file_read = false
allow_file_move = false
allow_file_delete = false
allow_file_create = false
allow_file_write = false
allow_command_exec = false
```

**所有权限默认 false** — 安全优先，用户主动开启。

### 2. Python 初始化

```python
def __init__(self, ctx):
    super().__init__(ctx)
    # 配置项声明
    self.enable_ops: bool = False
    self.allow_read: bool = False
    self.allow_move: bool = False
    self.allow_delete: bool = False
    self.allow_create: bool = False
    self.allow_write: bool = False
    self.allow_exec: bool = False
```

### 3. 启动时读取配置

```python
@lifecycle(id="startup")
async def on_startup(self, **_):
    cfg = await self.config.dump()
    settings = cfg.get("settings", {})

    self.enable_ops = settings.get("enable_ops", False)
    self.allow_read = settings.get("allow_read", False)
    self.allow_move = settings.get("allow_move", False)
    self.allow_delete = settings.get("allow_delete", False)
    self.allow_create = settings.get("allow_create", False)
    self.allow_write = settings.get("allow_write", False)
    self.allow_exec = settings.get("allow_exec", False)
```

### 4. 统一权限检查入口

```python
def _check_op_allowed(self, action: str, source_path: str,
                      dest_path: str = "", skip_source: bool = False
                      ) -> str | None:
    """返回 None 表示通过，否则返回错误消息。"""
    # 第一层：总开关
    if not self.enable_ops:
        return "喵～操作功能还没打开的说，去设置里开启一下嘛"

    # 第二层：逐操作授权
    if action == "read" and not self.allow_read:
        return "人家还没被允许读文件啦…去设置里开一下喵？"
    if action == "move" and not self.allow_move:
        return "移动文件？不行不行，还没授权的说～"
    if action == "delete" and not self.allow_delete:
        return "删除什么的太危险啦喵！请先在设置里确认开启～"
    if action == "create" and not self.allow_create:
        return "创建文件？还没允许喵～先去设置里开一下吧"
    if action == "write" and not self.allow_write:
        return "修改文件内容？还不行喵～检查一下设置里的权限"
    if action == "exec" and not self.allow_exec:
        return "命令执行超级危险的说…请在设置里三思后开启喵"

    # 第三层：路径范围 + 保护检查
    if source_path and not skip_source:
        source_path = os.path.abspath(source_path)
        if self._is_protected(source_path):
            return "那个地方是禁区啦，不可以碰哦 🐾"
        if not self._path_in_scan_range(source_path):
            return "咦？这个路径不在允许的扫描范围里喵～"

    if dest_path:
        dest_path = os.path.abspath(dest_path)
        if self._is_protected(dest_path):
            return "目标路径是禁区的说，不能放过去喵～"
        if not self._path_in_scan_range(dest_path):
            return "目标路径不在允许范围内喵～"

    return None  # 通过
```

### 5. 在入口方法中调用

```python
async def file_operation(self, action, source_path, dest_path, ...):
    # 根据操作类型路由到对应权限
    if action in ("move", "delete"):
        err = self._check_op_allowed(action, source_path, dest_path)
    elif action == "create":
        err = self._check_op_allowed("create", source_path or "", dest_path,
                                      skip_source=True)  # create 不需要源路径
    elif action in ("copy", "paste"):
        err = self._check_op_allowed("write", source_path, dest_path)
    else:
        err = self._check_op_allowed(action, source_path, dest_path)

    if err:
        return Err(SdkError(err))
    # 继续执行...
```

### 6. 操作到权限的映射

| 操作 | 对应权限 | 原因 |
|------|---------|------|
| `read` | `allow_read` | 读取文件内容 |
| `move` | `allow_move` | 移动文件（同时读写） |
| `delete` | `allow_delete` | 删除文件（危险操作） |
| `create` | `allow_create` | 创建新文件/目录 |
| `copy` | `allow_write` | 复制 = 读取源 + 写入目标 |
| `paste` | `allow_write` | 粘贴 = 读取源 + 写入目标 |
| `exec` | `allow_exec` | 执行命令（高危） |

**copy 和 paste 为什么用 `allow_write` 而不是 `allow_read`？**
因为 copy/paste 的核心风险是**写入目标位置**，而非读取源文件。如果源文件不在扫描范围内，范围检查会拒绝。

---

## UI 端权限控制

```tsx
type State = {
    config: {
        enable_ops: boolean
        allow_read: boolean
        allow_move: boolean
        allow_delete: boolean
        allow_create: boolean
        allow_write: boolean
        allow_exec: boolean
    }
}

export default function SettingsPanel(props: PluginSurfaceProps<State>) {
    const [enableOps, setEnableOps] = useLocalState("eo", () => false)
    const [allowRead, setAllowRead] = useLocalState("ar", () => false)
    // ...

    return (
        <Page>
            <Card title="操作权限">
                <Field label="启用操作">
                    <Switch checked={enableOps} onChange={setEnableOps} />
                </Field>
                {enableOps && (
                    <>
                        <Divider />
                        <Field label="允许读取"><Switch checked={allowRead} onChange={setAllowRead} /></Field>
                        <Field label="允许移动"><Switch checked={allowMove} onChange={setAllowMove} /></Field>
                        <Field label="允许删除"><Switch checked={allowDelete} onChange={setAllowDelete} /></Field>
                        <Field label="允许创建"><Switch checked={allowCreate} onChange={setAllowCreate} /></Field>
                        <Field label="允许修改"><Switch checked={allowWrite} onChange={setAllowWrite} /></Field>
                        <Field label="允许执行命令"><Switch checked={allowExec} onChange={setAllowExec} /></Field>
                    </>
                )}
            </Card>
        </Page>
    )
}
```

**关键模式**：子权限开关只在 `enableOps` 为 true 时才显示，使用条件渲染。

---

## 配置重载时保持权限

```python
@lifecycle(id="reload")
async def on_reload(self, **_):
    cfg = await self.config.dump()
    settings = cfg.get("settings", {})
    # 重新读取所有权限
    self.enable_ops = settings.get("enable_ops", False)
    self.allow_read = settings.get("allow_read", False)
    # ...

@lifecycle(id="config_change")
async def on_config_change(self, old_config, new_config, **_):
    settings = new_config.get("settings", {}) if new_config else {}
    # 使用旧值作为 fallback，避免配置变更时丢失
    self.enable_ops = settings.get("enable_ops", self.enable_ops)
    self.allow_read = settings.get("allow_read", self.allow_read)
    # ...
```

**注意**：`on_reload` 用 `False` 作为 fallback，`on_config_change` 用 `self.xxx` 作为 fallback。因为 `on_reload` 是完整重载，`on_config_change` 可能只传了部分变更。

---

## 安全原则

1. **默认全部拒绝** — 所有权限默认 `false`
2. **总开关优先** — `enable_ops=False` 时拒绝一切操作
3. **路径范围限制** — 即使有权限，也只能访问 `scan_paths` 范围内的文件
4. **保护列表优先** — 即使有权限且在范围内，`protected_files` 中的路径仍不可访问
5. **操作前检查** — 每个入口方法在执行前调用 `_check_op_allowed`
6. **违规日志** — 权限拒绝时记录操作日志

---

## 常见错误

```python
# ❌ 错误 — 忘记检查权限
async def read_file(self, file_path):
    content = open(file_path).read()
    return Ok({"content": content})

# ✅ 正确
async def read_file(self, file_path):
    err = self._check_op_allowed("read", file_path)
    if err:
        return Err(SdkError(err))
    content = open(file_path).read()
    return Ok({"content": content})
```

```python
# ❌ 错误 — 权限检查不完整（只检查了 enable_ops）
if not self.enable_ops:
    return Err(SdkError("操作未启用"))

# ✅ 正确 — 通过统一入口检查所有权限
err = self._check_op_allowed("delete", source_path)
if err:
    return Err(SdkError(err))
```

## 相关文档

- [03-ui-settings.md](03-ui-settings.md) — 权限 UI 的完整实现（Switch + 条件渲染）
- [08-ai-friendly-design.md](08-ai-friendly-design.md) — 权限错误消息的引导性写法
- [01-plugin-toml.md](01-plugin-toml.md) — 配置项在 `[settings]` 节的定义