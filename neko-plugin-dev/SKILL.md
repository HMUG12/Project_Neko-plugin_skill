---
name: "neko-plugin-dev"
description: "N.E.K.O 插件开发完整指南。涵盖 plugin.toml 配置、Python 后端（装饰器/生命周期/数据库）、UI 设置面板、AI 友好设计、权限体系、性能优化、单元测试、部署同步和 17 个已知陷阱。当用户需要开发、修改、调试 N.E.K.O 插件或创建新插件时调用此技能。"
---

# N.E.K.O 插件开发 Skill

> 基于 `file_manager` 插件实战踩坑总结，从零到一，涵盖所有核心模式。

---

## 目录结构

```
my_plugin/
├── plugin.toml               # 插件元信息 + 配置项
├── __init__.py               # 主入口：插件类 + @plugin_entry
├── ui/
│   ├── settings.tsx          # 设置面板 UI
│   └── types.d.ts            # TypeScript 类型声明
├── i18n/
│   ├── zh-CN.json            # 中文翻译
│   └── en.json               # 英文翻译
├── docs/
│   └── guide.md              # 使用指南（Markdown，给用户看）
├── tsconfig.json             # TypeScript 配置
└── README.md                 # 说明文档
```

---

## 10 条铁律

1. **文件名全小写 + 下划线** — 目录名与 `entry` 的包名严格一致
2. **Python 文件无 BOM** — `UTF-8 without BOM`，否则 `SyntaxError`
3. **`_ctx=None`** — 所有 `@plugin_entry` 和 `@ui.action` 必须包含
4. **`**_`** — 所有 `@lifecycle` 必须包含
5. **启动 < 10 秒** — 耗时操作丢 `asyncio.create_task()`
6. **无 `executemany`** — 逐行 `await session.execute()`
7. **手动同步** — 工作区改完必须同步到部署目录
8. **权限默认 `false`** — 安全优先，总开关 + 逐操作授权
9. **AI 需要绝对路径** — 拒绝非绝对路径，错误消息中引导搜索
10. **磁盘 I/O 用 `asyncio.to_thread`** — 不阻塞事件循环

---

## 快速排查

```
1.☐BOM? 2.☐目录名一致? 3.☐_ctx=None? 4.☐**_? 5.☐executemany?
6.☐keywords? 7.☐database.enabled? 8.☐同步了? 9.☐重启了? 10.☐rstrip(os.sep)?
```

---

## plugin.toml 模板

```toml
[plugin]
id = "your_plugin_id"                    # 必须与目录名一致
name = "插件中文名"
description = "插件功能描述"
short_description = "简短描述（给 AI 看）"
keywords = ["关键词1", "关键词2", ...]      # 中英文都写，覆盖用户所有说法
version = "0.1.0"
entry = "plugins.插件目录名:PluginClassName"  # 必须与目录名完全一致！

[plugin.author]
name = "作者名"

[plugin.sdk]
recommended = ">=0.1.0,<0.2.0"
supported = ">=0.1.0,<0.3.0"

[plugin_runtime]
enabled = true
auto_start = true

[plugin.store]
enabled = true

[plugin.database]
enabled = true       # 需要数据库时必须开启

[plugin.i18n]
default_locale = "zh-CN"
locales_dir = "i18n"

[plugin.ui]
enabled = true

[[plugin.ui.panel]]
id = "settings"
title = "设置面板标题"
entry = "ui/settings.tsx"
context = "settings"
permissions = ["state:read", "action:call", "config:read"]

[[plugin.ui.guide]]
id = "guide"
title = "使用指南"
entry = "docs/guide.md"
permissions = ["state:read"]

# 业务配置项
[settings]
my_setting = false
my_text = ""
my_list = []
```

**注意**：`entry` 路径中的包名必须与目录名完全一致（大小写敏感），否则报 `PluginEntryDirectoryMismatch`。

---

## Python 后端核心导入

```python
from plugin.sdk.plugin import (
    NekoPluginBase, neko_plugin, lifecycle, plugin_entry,
    timer_interval, ui, tr, Ok, Err, unwrap, SdkError,
)
```

---

## 完整类模板

```python
@neko_plugin
class MyPlugin(NekoPluginBase):
    """插件描述"""

    def __init__(self, ctx):
        super().__init__(ctx)
        # 配置项（直接从 settings 映射）
        self.my_setting: bool = False
        self.my_list: list[str] = []
        # 运行状态
        self._frozen = False
        self._lock = threading.Lock()

    # ═══ 生命周期（必须包含 **_）═══
    @lifecycle(id="startup")
    async def on_startup(self, **_):
        cfg = await self.config.dump()
        settings = cfg.get("settings", {})
        self.my_setting = settings.get("my_setting", False)
        await self._ensure_tables()          # 同步等待建表
        asyncio.create_task(self._init())    # 耗时操作放后台
        return Ok({"status": "ready"})

    @lifecycle(id="shutdown")
    async def on_shutdown(self, **_):
        return Ok({"status": "shutdown"})

    @lifecycle(id="reload")
    async def on_reload(self, **_):
        cfg = await self.config.dump()
        settings = cfg.get("settings", {})
        self.my_setting = settings.get("my_setting", False)
        return Ok({"status": "reloaded"})

    @lifecycle(id="config_change")
    async def on_config_change(self, old_config=None, new_config=None, **_):
        if new_config:
            settings = new_config.get("settings", {})
            self.my_setting = settings.get("my_setting", self.my_setting)
        return Ok({"status": "config_updated"})

    @lifecycle(id="freeze")
    async def on_freeze(self, **_):
        self._frozen = True
        return Ok({"status": "frozen"})

    @lifecycle(id="unfreeze")
    async def on_unfreeze(self, **_):
        self._frozen = False
        return Ok({"status": "unfrozen"})

    # ═══ AI 入口（必须包含 _ctx=None，不能有 keywords）═══
    @plugin_entry(
        id="my_action",
        name="操作名称",
        description="⚠️ 描述给 AI 看：何时调用 + 前置条件 + 注意事项",
        input_schema={
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "参数描述"},
            },
            "required": ["param1"],
        },
        llm_result_fields=["result", "detail"],
    )
    async def my_action(self, param1: str = "", _ctx=None, **_):
        if not param1:
            return Err(SdkError("参数不能为空"))
        # 业务逻辑...
        return Ok({"result": "success", "detail": "..."})

    # ═══ UI Action（必须包含 _ctx=None）═══
    @ui.action(id="update_settings")
    async def update_settings(self, config: dict = None, _ctx=None, **_):
        if not isinstance(config, dict):
            return Err(SdkError("config 必须是对象"))
        self.my_setting = config.get("my_setting", False)
        self.my_list = config.get("my_list", [])
        return Ok({"status": "saved"})

    # ═══ UI Context（返回面板数据）═══
    @ui.context("settings")
    async def settings_context(self):
        return {
            "config": {"my_setting": self.my_setting, "my_list": self.my_list},
            "status": {"frozen": self._frozen},
        }

    # ═══ 定时器（独立线程，需 new_event_loop）═══
    @timer_interval(id="my_timer", seconds=3600, name="定时任务", auto_start=True)
    def _on_timer(self, **_):
        if self._frozen:
            return Ok({"skipped": True})
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._async_work())
        finally:
            loop.close()
        return Ok({"status": "done"})

    # ═══ 数据库模式 ═══
    async def _ensure_tables(self):
        session = unwrap(await self.db.session())
        try:
            await session.execute("""
                CREATE TABLE IF NOT EXISTS my_table (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                )
            """)
            await session.execute("CREATE INDEX IF NOT EXISTS idx_name ON my_table(name)")
            await session.commit()
        finally:
            await session.close()

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

    # ❌ 不支持 executemany，必须逐行
    async def _batch_insert(self, items: list):
        session = unwrap(await self.db.session())
        try:
            for item in items:
                await session.execute(
                    "INSERT INTO my_table (name) VALUES (?)", (item["name"],)
                )
            await session.commit()
        finally:
            await session.close()

    # ═══ 线程安全 ═══
    def _update_progress(self, phase, current, total, msg):
        with self._lock:
            self._progress = {"scanned": current, "total": total, "phase": phase}

    # ═══ asyncio.to_thread（磁盘 I/O 不阻塞）═══
    def _sync_disk_work(self, root: str) -> list[tuple]:
        """纯同步函数，在线程池中执行。"""
        result = []
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                st = os.stat(os.path.join(dirpath, fname))
                _, ext = os.path.splitext(fname)
                result.append((fname, ext, st.st_size, st.st_mtime))
        return result

    async def _async_scan(self, root: str):
        return await asyncio.to_thread(self._sync_disk_work, root)

    # ═══ i18n 安全调用 ═══
    def _t(self, key: str, default: str, **kwargs) -> str:
        try:
            return self.i18n.t(key, default=default, **kwargs)
        except Exception:
            return kwargs.get("default", default) if kwargs else default
```

---

## 方法签名速查

| 装饰器 | 必须参数 | 特殊约束 |
|--------|---------|---------|
| `@lifecycle(...)` | `**_` | — |
| `@plugin_entry(...)` | `_ctx=None` | 不能有 `keywords` |
| `@ui.action(...)` | `_ctx=None` | — |
| `@ui.context(...)` | none | 返回 dict |
| `@timer_interval(...)` | none | 独立线程，需 `new_event_loop()` |

---

## 数据库关键模式

```python
# ✅ 正确：await session.execute() + 同步 fetchall()
cursor = await session.execute("SELECT * FROM t WHERE id = ?", (id,))
rows = cursor.fetchall()  # 同步，不是 await

# ❌ 错误：两层 await
rows = await (await session.execute("SELECT ...")).fetchall()

# ❌ 错误：fetchall 也 await
rows = await cursor.fetchall()

# ❌ 错误：SDK 没有 executemany
await session.executemany("INSERT ...", batch)

# ✅ 正确：逐行 execute
for row in batch:
    await session.execute("INSERT INTO t VALUES (?)", row)
```

---

## 权限体系设计

### 两层权限模式

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

def _check_op_allowed(self, action: str, source_path: str,
                      dest_path: str = "", skip_source: bool = False
                      ) -> str | None:
    """返回 None 通过，否则返回错误消息。"""
    if not self.enable_ops:
        return "操作未启用"

    if action == "read" and not self.allow_read: return "未授权读取"
    if action == "move" and not self.allow_move: return "未授权移动"
    if action == "delete" and not self.allow_delete: return "未授权删除"
    if action == "create" and not self.allow_create: return "未授权创建"
    if action == "write" and not self.allow_write: return "未授权修改"
    if action == "exec" and not self.allow_exec: return "未授权执行"

    if source_path and not skip_source:
        source_path = os.path.abspath(source_path)
        if self._is_protected(source_path): return "受保护路径"
        if not self._path_in_scan_range(source_path): return "不在扫描范围"

    if dest_path:
        dest_path = os.path.abspath(dest_path)
        if self._is_protected(dest_path): return "目标受保护"
        if not self._path_in_scan_range(dest_path): return "目标不在范围"

    return None
```

### 路径范围检查（修复根目录 Bug）

```python
def _path_in_scan_range(self, path: str) -> bool:
    if not self.scan_paths:
        return False
    norm = os.path.normpath(path).lower().rstrip(os.sep)  # ← rstrip 是关键
    for sp in self.scan_paths:
        sp_norm = os.path.normpath(sp).lower().rstrip(os.sep)
        if norm == sp_norm or norm.startswith(sp_norm + os.sep):
            return True
    return False
```

---

## AI 友好设计（核心）

### 强制「搜索先行」工作流

AI 会自己拼路径，所以插件必须：
1. 所有入口拒绝非绝对路径
2. 路径不存在时引导 AI 用 `search_files`
3. 错误消息包含三要素：发生了什么 + 为什么 + 怎么做

```python
@plugin_entry(
    id="file_operation",
    name="文件操作",
    description="⚠️ source_path 和 dest_path 必须是绝对路径，你必须先用 search_files 或 scan_folder_context 获取完整路径！",
    input_schema={
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "操作类型"},
            "source_path": {"type": "string", "description": "源路径（绝对路径）"},
            "dest_path": {"type": "string", "description": "目标路径（绝对路径）"},
        },
        "required": ["action", "source_path"],
    },
    llm_result_fields=["action", "result_exists", "verify_context"],
)
async def file_operation(self, source_path, dest_path, ...):
    # 拒绝非绝对路径
    if source_path and not os.path.isabs(source_path):
        return Err(SdkError(
            f"喵～源路径 '{source_path}' 不是绝对路径的说。"
            "请先用 search_files 或 scan_folder_context 找到文件的完整路径，再操作哦～"
        ))

    # 路径不存在时引导
    if not os.path.exists(source_path):
        return Err(SdkError(
            f"喵～路径不存在: {source_path}。"
            "请先用 search_files 搜索确认文件完整路径喵～"
        ))
```

### description 三要素

| 要素 | 说明 | 示例 |
|------|------|------|
| 何时调用 | 什么场景触发 | "用于'帮我看看这个文件'等场景" |
| 前置条件 | 调用前需要做什么 | "⚠️ 必须先用 search_files 获取完整绝对路径" |
| 注意事项 | 限制和边界 | "仅支持文本文件，二进制返回 is_binary: true" |

### 返回值中的 verify_context

```python
# 操作成功后返回目录快照供 AI 验证
verify_dir = os.path.dirname(result_path)
entries = os.listdir(verify_dir)
return Ok({
    "action": action,
    "result_exists": os.path.exists(result_path),
    "verify_context": {
        "dir": verify_dir,
        "entries": [{"name": e, "is_dir": os.path.isdir(...)} for e in entries[:50]],
    },
})
```

---

## UI 设置面板模板

```tsx
import {
  Page, Card, Section, Stack, Grid, Text, Divider,
  Switch, Input, Textarea, StatCard, ActionButton, Field, Alert, DataTable,
} from "@neko/plugin-ui"
import type { HostedAction, PluginSurfaceProps } from "@neko/plugin-ui"
import { useLocalState } from "@neko/plugin-ui"

type State = {
  config: { my_setting: boolean; my_list: string[] }
  status: { frozen: boolean }
}

export default function SettingsPanel(props: PluginSurfaceProps<State>) {
  const { state, actions } = props

  // ⚠️ 缓存 actions 避免首次渲染按钮消失
  const [cachedActions, setCachedActions] = useLocalState("ca", () => [] as HostedAction[])
  if (actions.length > 0 && actions.length !== cachedActions.length) {
    setCachedActions(actions)
  }
  const effectiveActions = cachedActions.length > 0 ? cachedActions : actions

  const [mySetting, setMySetting] = useLocalState("ms", () => state.config?.my_setting ?? false)
  const [myList, setMyList] = useLocalState("ml", () => (state.config?.my_list || []).join("\n"))

  const saveAction = effectiveActions.find((a: HostedAction) => a.id === "update_settings")

  function buildConfig(): Record<string, unknown> {
    return {
      my_setting: mySetting,
      my_list: myList.split("\n").map(s => s.trim()).filter(Boolean),
    }
  }

  return (
    <Page title="我的插件">
      <Card title="配置">
        <Stack>
          <Field label="开关设置">
            <Switch checked={mySetting} onChange={(v: boolean) => setMySetting(v)} />
          </Field>
          <Field label="多行列表">
            <Textarea value={myList} onChange={(v: string) => setMyList(v)} />
          </Field>
        </Stack>
      </Card>
      <Section>
        <Stack>
          {saveAction ? (
            <ActionButton action={saveAction} values={{ config: buildConfig() }}>保存设置</ActionButton>
          ) : (
            <ActionButton action={{ id: "update_settings", call: async () => {} } as HostedAction} values={{ config: buildConfig() }}>保存设置 (加载中…)</ActionButton>
          )}
        </Stack>
      </Section>
    </Page>
  )
}
```

### 可用组件

| 组件 | 用途 | 已验证 |
|------|------|--------|
| `Page` `Card` `Section` `Stack` `Grid` | 布局 | ✅ |
| `Text`（color: primary/secondary/muted） | 文本 | ✅ |
| `Divider` | 分割线 | ✅ |
| `Switch` `Input` `Textarea` `Field` | 表单 | ✅ |
| `StatCard` `DataTable` `Alert` | 展示 | ✅ |
| `ActionButton` `useLocalState` | 交互 | ✅ |

**不可用组件**：`Table`→`DataTable`、`Button`→`ActionButton`、`useState`→`useLocalState`、`Text` color 不支持 `danger/warning/default`

---

## 性能优化

### 启动分离
```python
async def on_startup(self, **_):
    cfg = await self.config.dump()
    self._load_settings(cfg)
    await self._ensure_tables()          # 同步等待（<1s）
    asyncio.create_task(self._init())    # 后台任务
    return Ok({"status": "ready"})
```

### 批量处理
```python
BATCH_SIZE = 500
for i in range(0, total, BATCH_SIZE):
    batch = entries[i:i + BATCH_SIZE]
    for row in batch:
        await session.execute("INSERT INTO t VALUES (?,?,...)", row)
    await session.commit()
```

### 编码检测
```python
for enc in ("utf-8", "gbk", "gb2312", "shift_jis", "big5", "euc-kr", "latin-1"):
    try:
        with open(path, "r", encoding=enc, errors="surrogateescape") as f:
            return f.read()
    except (UnicodeDecodeError, UnicodeError):
        continue
```

### 增量索引
只存路径→mtime 映射，减少内存：
```python
disk_mtimes: dict[str, float] = {}
for entry in entries:
    disk_mtimes[entry[0]] = entry[4]  # path→mtime
```

---

## 撤销与日志

### 撤销栈
```python
self._undo_stack: list[dict] = []
self._max_undo_steps = 50

# 操作映射：create→delete, copy→uncopy, move→unmove, delete→undelete
# 失败不入栈，撤销失败推回栈项
```

### push_message
```python
self.push_message(
    source="plugin_id", visibility=["chat"], ai_behavior="blind",
    parts=[{"type": "text", "text": "消息内容"}],
    priority=3,  # 1-3=info, 4-6=warning, 7-9=error, 10=紧急
)
```

---

## 单元测试

### Mock SDK 核心

```python
# 1. 模拟 SDK
class _FakeSDK:
    neko_plugin = staticmethod(lambda cls: cls)
    lifecycle = staticmethod(lambda **kw: lambda fn: fn)
    plugin_entry = staticmethod(lambda **kw: lambda fn: fn)
    Ok = lambda val: _Ok(val)
    Err = lambda err: _Err(err)
    SdkError = type("SdkError", (Exception,), {
        "__init__": lambda self, msg: setattr(self, "message", msg)
    })

# 2. 注入
sys.modules["plugin.sdk.plugin"] = _FakeSDK

# 3. Err 是函数不是类型，用 _Err 做 isinstance
ErrClass = _Err

# 4. Fake DB
class FakeDB:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
    async def session(self):
        return FakeSession(self.conn)
```

---

## 部署同步

工作区改完必须手动同步到 `C:\Users\...\AppData\Local\N.E.K.O\plugins\` 并重启 N.E.K.O。

### BOM 移除
```powershell
$c = [System.IO.File]::ReadAllBytes('__init__.py')
[System.IO.File]::WriteAllBytes('__init__.py', $c[3..$c.Length])
```

---

## 致命陷阱速查

| # | 陷阱 | 现象 | 修复 |
|---|------|------|------|
| 1 | BOM | `SyntaxError` | 移除 BOM 字节 |
| 2 | 目录名大小写 | `PluginEntryDirectoryMismatch` | 目录名 = entry 包名 |
| 3 | keywords 参数 | `unexpected keyword argument` | 移除 `keywords=` |
| 4 | executemany | `no attribute` | 逐行 `execute()` |
| 5 | 启动超时 | `timed out after 10s` | `asyncio.create_task()` |
| 6 | database 未启用 | `self.db` 为 None | `enabled = true` |
| 7 | fetchall 加 await | 运行时错误 | 同步 `fetchall()` |
| 8 | 根目录路径 Bug | 路径不匹配 | `rstrip(os.sep)` |
| 9 | 旧文件覆盖 | 行为不变 | 同步到部署目录 |
| 10 | AI 乱拼路径 | 路径错误 | 拒绝非绝对路径 + 引导 |

---

## 参考文档

本 Skill 目录下 `references/` 包含 12 篇详细参考文档，覆盖每个主题的完整实现和代码示例。详见各文档的检查清单和实战代码。