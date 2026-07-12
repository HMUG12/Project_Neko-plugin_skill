---
name: "neko-plugin-dev"
description: "N.E.K.O 插件开发完整指南。涵盖 plugin.toml 配置、Python 后端（装饰器/生命周期/数据库/report_status/data_path/双装饰器/@llm_tool/PluginRouter）、UI 设置面板（Slider/Select/StatusBadge/ActionForm/api.call）、AI 友好设计、权限体系、性能优化、单元测试、部署同步和 45 个已知陷阱。新增 NEKO 主程序深度逆向分析十篇（生命周期/ZMQ/Push Message/Bus/NekoPluginBase/PluginRouter/Logger/Store-DB/i18n/Config 内部机制）。当用户需要开发、修改、调试 N.E.K.O 插件或创建新插件时调用此技能。"
---

# N.E.K.O 插件开发 Skill

> 基于 `file_manager` + `ai_singer` + `music_pusher` + `qq_auto_reply` 多插件实战 + N.E.K.O-main 主程序深度逆向分析，从零到一，涵盖 38 个主题。

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

## 20 条铁律

1. **文件名全小写 + 下划线** — 目录名与 `entry` 的包名严格一致
2. **Python 文件无 BOM** — `UTF-8 without BOM`，否则 `SyntaxError`
3. **`_ctx=None`** — 所有 `@plugin_entry` 和 `@ui.action` 必须包含
4. **`**_`** — 所有 `@lifecycle` 必须包含
5. **启动 < 10 秒** — 耗时操作丢 `asyncio.create_task()`
6. **无 `executemany`** — 逐行 `await session.execute()`
7. **手动同步 + 删 `__pycache__`** — 工作区改完必须同步到部署目录，**并删除目标目录的 `__pycache__/`**，否则旧代码继续运行且无报错！
8. **权限默认 `false`** — 安全优先，总开关 + 逐操作授权
9. **AI 需要绝对路径** — 拒绝非绝对路径，错误消息中引导搜索
10. **磁盘 I/O 用 `asyncio.to_thread`** — 不阻塞事件循环
11. **`plugin.toml` dependencies 用内联表** — `openai = ">=1.0.0"` 而非 `python = ["openai>=1.0.0"]`
12. **`@plugin_entry` 在上，`@ui.action` 在下** — 双装饰器叠加时顺序不能反
13. **`@llm_tool` 用 `*,` 强制 keyword-only** — `async def my_tool(self, *, param: str)`，万一传进位置参数会立刻报错
14. **Router 在 `__init__` 中注册** — `self.include_router()` 必须在 `super().__init__(ctx)` 之后、`__init__` 返回之前调用
15. **第三方库惰性导入 + 错误缓存** — `try/except ImportError` 失败后缓存错误，后续调用重放错误而不重试 import
16. **跨插件调用用 `call_entry`** — 不要直接 import 其他插件的类，松耦合 + 防御性调用
17. **on_init 不调其他插件** — `on_init` 时其他插件可能尚未加载，跨插件调用应在 `on_start` 中进行
18. **push_message 大文件用 URL** — 大文件 base64 编码后体积膨胀 33%，用 `file://` URL 代替 `data:` 传递
19. **Router entry 设 prefix** — 多个 Router 必须有不同 prefix 避免 entry ID 冲突
20. **Bus 查询用惰性链式** — `get_recent().filter().limit()` 而非多次 `reload()`，减少 ZMQ 往返

---

## 快速排查

```
1.☐BOM? 2.☐目录名一致? 3.☐_ctx=None? 4.☐**_? 5.☐executemany?
6.☐keywords? 7.☐database.enabled? 8.☐同步+删__pycache__了? 9.☐重启了? 10.☐rstrip(os.sep)?
11.☐dependencies格式? 12.☐双装饰器顺序? 13.☐@llm_tool签名有*? 14.☐Router在__init__中注册?
15.☐第三方导入有错误缓存? 16.☐跨插件用call_entry而非import?
17.☐on_init不调其他插件? 18.☐大文件用URL而非base64? 19.☐Router有prefix? 20.☐Bus用惰性链式?
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
| 11 | `__pycache__` 缓存 | 改代码不生效 | 删除 `__pycache__/` |
| 12 | dependencies 格式 | schema 警告 | 内联表格式 |
| 13 | 双装饰器顺序 | 行为异常 | `@plugin_entry` 在上 |
| 14 | LLM 跳过前置检查 | 直接调核心入口 | description 强提示 |
| 15 | 惰性导入无缓存 | 反复 import 失败 | 错误缓存 + 重放 |
| 16 | on_init 调其他插件 | 返回 PluginNotFound | 移到 on_start |
| 17 | 大文件 base64 超时 | ZMQ 消息超限 | 用 file:// URL |
| 18 | Router 无 prefix | Entry ID 冲突 | router.set_prefix() |
| 19 | Bus 多次 reload | 响应慢/ZMQ 往返多 | 惰性链式 filter().limit() |
| 20 | BusList 忘 await | 迭代返回空 | await reload() 或设置 _ctx |

---

## 参考文档

本 Skill 目录下 `references/` 包含 38 篇详细参考文档，覆盖每个主题的完整实现和代码示例：

### 基础篇（必读）
- [01-plugin-toml](references/01-plugin-toml.md) — plugin.toml 完整参考
- [02-python-plugin](references/02-python-plugin.md) — Python 后端核心指南
- [03-ui-settings](references/03-ui-settings.md) — UI 设置面板开发
- [04-i18n](references/04-i18n.md) — 国际化指南

### 进阶篇（推荐）
- [08-ai-friendly-design](references/08-ai-friendly-design.md) — AI 友好设计
- [09-permission-system](references/09-permission-system.md) — 权限体系
- [10-performance](references/10-performance.md) — 性能优化
- [11-undo-and-logging](references/11-undo-and-logging.md) — 撤销与日志

### 实战篇（基于 ai_singer 插件）
- [13-cloud-api-integration](references/13-cloud-api-integration.md) — 云端 API 集成（SDK 导入、端点配置、错误诊断、健康检查、保存后验证）
- [14-multi-panel-architecture](references/14-multi-panel-architecture.md) — 多面板架构（双面板+双Context、配置共享、标签页组织）
- [15-rich-ui-components](references/15-rich-ui-components.md) — 富交互 UI 组件（LyricPlayer、ActionForm、内联样式、条件渲染）

### 实战篇·二（基于 ai_singer V0.6 重构）
- [16-backend-simplification](references/16-backend-simplification.md) — 后端精简与迁移（双后端→单后端迁移策略、代码清理清单、配置漂移防范、向后兼容处理）
- [17-pyc-cache-trap](references/17-pyc-cache-trap.md) — `__pycache__` 缓存陷阱（代码改了但不生效的根本原因、日志诊断法、预防方案）
- [18-streaming-output](references/18-streaming-output.md) — 流式输出与进度推送（逐句处理循环、push_message/report_status、音频合并、viseme 口型同步）
- [19-llm-workflow-design](references/19-llm-workflow-design.md) — LLM 对话工作流设计（check_setup 前置检查、多入口编排、next_action 指导、description 三要素）

### 实战篇·三（基于原指南 + 第三方插件分析）
- [20-plugin-router](references/20-plugin-router.md) — PluginRouter 拆分大型插件（多入口点模块化、共享逻辑、Router 能力访问、前缀命名、完整示例）
- [21-llm-tool-registration](references/21-llm-tool-registration.md) — @llm_tool LLM 工具注册（装饰器详解、架构分层、错误返回、命令式 API、生命周期与时序、main_server 重启应对）
- [22-static-ui-plugin](references/22-static-ui-plugin.md) — 纯前端/Static UI 插件（RPC 通信机制、状态管理、后台轮询、文件上传、Three.js 3D 集成、音频可视化、Toast 系统）
- [23-external-protocol-integration](references/23-external-protocol-integration.md) — 外部协议集成与消息积压管理（OneBot/NapCat 连接、积压数据结构、回复概率控制、引导式安装、信任体系、WebSocket 重连）

### 实战篇·四（基于三插件深度逆向分析）
- [24-error-handling-patterns](references/24-error-handling-patterns.md) — 错误处理与诊断模式大全（惰性导入+错误缓存、多级关键字诊断、轮询重试、分层 UI 渲染、Ok/Err 分层返回、按钮防重复、Toast 通知、RPC 超时、错误码设计规范）
- [25-concurrency-race-conditions](references/25-concurrency-race-conditions.md) — 并发与竞态条件（锁外 I/O、冻结取消、防重入刷新、消息积压上限、请求去重、WebSocket 指数退避重连、回复概率控制）
- [26-backend-design-pattern](references/26-backend-design-pattern.md) — Backend 对象设计模式（惰性导入+错误缓存、配置传播与_log注入、健康检查多时机、同步/异步桥接、多后端共存、完整模板）
- [27-audio-processing-pipeline](references/27-audio-processing-pipeline.md) — 音频处理管线（纯 Python WAV 合并无 ffmpeg 依赖、Viseme 口型同步数据生成、时长估算三级回退、双轨播放架构、句间换气停顿算法）
- [28-inter-plugin-communication](references/28-inter-plugin-communication.md) — 插件间通信（call_entry 跨插件调用、依赖声明与检查、事件总线 pub/sub、共享数据模式、版本兼容回退、防御性调用）

### 实战篇·五（基于 N.E.K.O 主程序深度逆向分析 — 框架层）
- [29-plugin-lifecycle-internals](references/29-plugin-lifecycle-internals.md) — 插件生命周期内部机制（7 阶段状态机、ZMQ 进程通信架构、load/init/start/run/stop/unload 全流程、子进程管理、常见生命周期陷阱）
- [30-push-message-internals](references/30-push-message-internals.md) — Push Message 深度解析（visibility/ai_behavior 两轴正交模型、Parts 结构详解、coalesce_key 消息合并、旧版→v2 迁移映射、UI Action 媒体播放、内部 base64 编码机制）
- [31-bus-system-internals](references/31-bus-system-internals.md) — Bus 总线系统深度解析（惰性查询容器 BusList、计划节点树 GetNode/FilterNode/SortNode、五条总线 messages/events/lifecycle/conversations/memory、Revision 追踪、Watch 变更订阅、集合操作 union/intersect/difference）
- [32-nekopluginbase-internals](references/32-nekopluginbase-internals.md) — NekoPluginBase 内部机制（双层继承 shared/sdk、构造函数全流程、Entry 收集、Router 绑定、SDK 上下文封装、LLM Tool 注册流程、Static UI、PluginStore/PluginDatabase/PluginStatePersistence）
- [33-pluginrouter-entry-internals](references/33-pluginrouter-entry-internals.md) — PluginRouter 与 Entry 系统（懒解析策略、动态 Entry 注册、before/after/around_entry 钩子、hook 系统、quick_action 快捷操作、Entry 分发全流程、装饰器叠加规则、闭包陷阱）

### 实战篇·六（基于 N.E.K.O 主程序深度逆向分析 — 基础设施层）⭐ 新增
- [34-logger-system-internals](references/34-logger-system-internals.md) — Logger 日志系统内部机制（PluginLoggerAdapter 双风格兼容、loguru braces/stdlib % 格式、RobustLoggerConfig 落地、Root Bridge 第三方日志捕获、敏感信息脱敏、懒解析机制）
- [35-store-database-internals](references/35-store-database-internals.md) — PluginStore 与 PluginDatabase 内部机制（JSON 键值存储 vs SQLite 关系存储、全量加载/每次写入持久化、CRUD 完整模式、批量插入分批提交、PluginStatePersistence、data_path 私有目录、持久化策略选择决策树）
- [36-i18n-internals](references/36-i18n-internals.md) — i18n 国际化引擎内部机制（回退链：用户语言→默认语言→default→key、参数插值 str.format()、懒加载翻译文件、tr 函数在装饰器中的使用、命名规范与最佳实践）
- [37-zmq-transport-internals](references/37-zmq-transport-internals.md) — ZMQ 进程通信协议内部机制（PAIR socket 双向通信、JSON 序列化协议、12 种命令类型及超时配置、HostTransport/ChildTransport 实现、CALL_ENTRY 完整调用链路、子进程崩溃与自动重启、大数据传输优化）
- [38-config-system-internals](references/38-config-system-internals.md) — 插件配置系统内部机制（plugin.toml [settings] / self.config / self.store 三层关系、合并优先级、update_own_config 点号路径、配置漂移防范与迁移策略、DEFAULT_CONFIG 完整模板、config_change 钩子注意事项）

### 工程篇（开发流程）
- [05-testing](references/05-testing.md) — 单元测试
- [06-deployment](references/06-deployment.md) — 部署同步
- [07-gotchas](references/07-gotchas.md) — 踩坑大全（45个已知陷阱）
- [12-master-checklist](references/12-master-checklist.md) — 汇总检查清单