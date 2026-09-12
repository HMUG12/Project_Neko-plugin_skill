---
name: "neko-plugin-dev"
description: "N.E.K.O 插件开发完整指南。涵盖 plugin.toml 配置、Python 后端（装饰器/生命周期/数据库/report_status/data_path/双装饰器/@llm_tool/PluginRouter）、UI 设置面板（Select/StatusBadge/ActionForm/api.call）、AI 友好设计、权限体系、性能优化、单元测试、部署同步和 45 个已知陷阱。新增 NEKO 主程序深度逆向分析十篇（生命周期/ZMQ/Push Message/Bus/NekoPluginBase/PluginRouter/Logger/Store-DB/i18n/Config 内部机制）。进一步融合 13 个外部开源 skill（mattpocock/ponytail/impeccable/hallmark/firecrawl/strix/agentskills + token-saviour/subconscious-skill/prompthakcer/NadirClaw/llm-router/neko-skill）的方法论，并直接逆向工作区 plugins/ 真实插件源码提取架构范式（44-local-plugin-architecture）与融合速查（45-fusion-quick-reference / 46–49 二次融合 / 50 市场插件逆向）。可选工作流 `00-development-coordinator`（**非强制前置**）：仅当用户**明确**要求协作/结对编程，或插件规模大、需求含糊时，才进入五阶段工作流（需求澄清→方案规划→约束生成→任务拆解→编码实现），状态只保留最少必要并遵守脱敏/忽略/删除规则；简单/明确任务直接按 01–50 动手。所有结论已对照官方开发者文档 project-neko.online 与 GitHub 仓库 plugins/ 真实代码核实。当用户需要开发、修改、调试 N.E.K.O 插件或创建新插件时调用此技能。"
---

# N.E.K.O 插件开发 Skill

> 基于 `file_manager` + `ai_singer` + `music_pusher` + `qq_auto_reply` 多插件实战 + N.E.K.O-main 主程序深度逆向分析 + 插件市场 31 个已上架插件源码逆向，从零到一，涵盖 51 个主题（含 1 篇可选工作流 00 + 50 个技术主题 01–50），并附 1 个示例插件（examples/，**尚未在干净环境跑通端到端验证**）。结论已对照官方开发者文档（project-neko.online）与 GitHub 仓库 `plugins/` 真实代码逐条核对。

> **已验证目标版本**：SDK `recommended = ">=0.1.0,<0.2.0"` / `supported = ">=0.1.0,<0.3.0"`；官方文档核对日期 **2026-09-12**。超出该区间请先重跑 `uv run neko-plugin check <id> --strict` 与示例验证。文中未标注「已验证」的代码片段均为**示意**。

---

## 可选工作流（来自 00 · 非强制前置，按需启用）

> 当用户**明确**说"启动开发协作""用结对编程模式"，或插件规模大、需求含糊时，进入 [`00-development-coordinator.md`](references/00-development-coordinator.md) 的五阶段工作流（需求澄清→方案规划→约束生成→任务拆解→编码实现）。
> **简单/明确的插件任务不要强制走五阶段访谈**——直接按 01–50 给方案并动手即可。若启用，状态文件只保留最少必要内容，并遵守 00 中的脱敏、`.gitignore` 与删除规则。

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

1. **文件名全小写 + 下划线** — 目录名 / `plugin.id` / `entry` 包名**建议**三者一致；官方加载器可能容忍不一致，但**打包与生产安装要求对齐**，不一致会报错
2. **Python 文件无 BOM** — `UTF-8 without BOM`，否则 `SyntaxError`
3. **上下文用 `self.ctx`** — 框架**不会**给 `@plugin_entry`/`@ui.action`/`@lifecycle` 传入任何 `ctx` 参数（真实插件代码 0 处使用 `_ctx=None`）；需要运行时上下文用 `self.ctx` 属性，不要给方法加 `_ctx=None` 参数
4. **`**_` 可选 catch-all** — `@lifecycle`/`@plugin_entry`/`@ui.action` 想兼容框架未来可能传入的额外关键字可加 `**_`，官方示例普遍使用但**非强制**；Best Practice 建议「仅在有意消费额外参数时」才加
5. **启动就绪默认约 10 秒（可配）** — `[plugin_runtime].timeout` 须满足 `0 < timeout <= 300`；耗时操作丢 `asyncio.create_task()`，并注意关闭时取消与异常收集
6. **无 `executemany`** — 逐行 `await session.execute()`
7. **优先官方开发模式 Reload** — 源码树（`plugin/plugins/`）或开发者模式 Load unpacked 下，改完点 **Reload** 即可生效，日常不必反复复制；仅在手改源码/已安装包或行为不更新时，才删目标目录 `__pycache__/` 作为**诊断分支**（见 06 / 17）
8. **权限默认 `false`** — 安全优先，总开关 + 逐操作授权
9. **AI 需要绝对路径** — 拒绝非绝对路径，错误消息中引导搜索
10. **磁盘 I/O 用 `asyncio.to_thread`** — 不阻塞事件循环
11. **`plugin.toml` dependencies 用内联表** — `openai = ">=1.0.0"` 而非 `python = ["openai>=1.0.0"]`
12. **双装饰器：`@ui.action` 在上，`@plugin_entry` 在下**（官方示例顺序，**本机未运行验证**）— 叠加时 `@ui.action(label=..., tone=..., refresh_context=True)` 在外、`@plugin_entry` 在内；最终以你目标 SDK 的官方示例为准（详见 33 号文档 §7.1 与 39 号文档 §8）
13. **`@llm_tool` 用 `*,` 强制 keyword-only** — `async def my_tool(self, *, param: str)`，万一传进位置参数会立刻报错
14. **Router 在 `__init__` 中注册** — `self.include_router()` 必须在 `super().__init__(ctx)` 之后、`__init__` 返回之前调用
15. **第三方库惰性导入 + 错误缓存** — `try/except ImportError` 失败后缓存错误，后续调用重放错误而不重试 import
16. **跨插件调用用 `call_entry`** — 不要直接 import 其他插件的类，松耦合 + 防御性调用
17. **on_init 不调其他插件** — `on_init` 时其他插件可能尚未加载，跨插件调用应在 `on_start` 中进行
18. **push_message 大文件用 URL** — 大文件 base64 编码后体积膨胀 33%，用 `file://` URL 代替 `data:` 传递
19. **Router entry 设 prefix** — 多个 Router 必须有不同 prefix 避免 entry ID 冲突
20. **Bus 查询用官方可重放链** — `get(...).filter(field=value).sort(by=...).limit()`；旧 `get_recent()` / `reload()` / `union()/intersect()/difference()` / `bus.emit()` 已移除，Bus 不是发布订阅总线

---

## 融合外部最佳实践 · 核心规则（来自 40–45）

> 不与上面 1–20 重复；这是融合 13 个外部开源 skill + 本地 `plugins/` 逆向 + 市场 31 插件逆向后提炼的"精髓九条"。写任何插件前先默念一遍，展开见 `45-fusion-quick-reference.md`（46–49 续、50 市场逆向）。

- **F1 先跑通再拆，别过度工程**：新插件用最小壳（`@neko_plugin` + 一个 hello entry）跑通再逐步加；抽象只在该上 YAGNI 阶梯第 3 级时才上（`40-engineering-discipline.md` §6）。
- **F2 复杂度收进深函数**：entry 只做"取参 → 调深函数 → `Ok`/`Err`"；`@llm_tool` 参数面要窄，内部重试/限流/格式转换藏起来（`40` §5 / `42` §2）。
- **F3 UI 克制即专业**：≤1 品牌色、无嵌套卡片、对比度 ≥ 4.5:1、文案具体、无英雄区/光晕（`41-ui-design-quality.md` §2 + §2.5）。
- **F4 外部调用先防 SSRF/注入**：凡访问用户给的 URL 先 `_is_safe_url`（解析 IP 判内网+云元数据），凡拼命令/SQL 必参数化（`43-security-hardening.md` §4/§5）。
- **F5 大插件照抄真实骨架**：用 Router 子包或 Mixin 合成；配置用 `SettingsField(hot=True)`，动作用 `@ui.action`，不用 `@config` / `[[plugin.ui.action]]`（`44-local-plugin-architecture.md`）。想直接抄完整骨架，见 `examples/web_assistant/`（一个整合 40–45 的可运行插件）。
- **F6 持久状态放 store 跨会话**：记忆/好感/习惯类插件用 `self.store`（或 `self.db`）留存状态，`@timer_interval` 后台"梦境"整理，会话落盘用 `@hook`/`@message`（`46-memory-persistence-subconscious.md`）。
- **F7 外部 LLM 先路由再缓存再去重**：复杂度分类选便宜层→验证不达标升级（cascade，fail-open），语义缓存按 hash/TTL，飞行中请求按 canonical hash 合并（`47-llm-routing-cost-optimization.md`）。
- **F8 外发提示词先压缩再脱敏**：发往外部 LLM/API 前先 regex 精简降 token，再本地正则脱敏信用卡/邮箱/SSN/API Key（`48-prompt-compression-pii-redaction.md`）。
- **F9 写复杂插件先抄真实市场骨架**：系统自动化用「三合一装饰器 + 目标窗口锁定 + 后台轮询」；游戏/决策类用「独立 data 进程 + 状态机」；外部程序桥接用「HTTP 桥 + 健康检查 + 指数退避」；教育/记忆类用「按功能域拆分 entry + store 持久化」。六类范式与可抄片段见 `50-market-plugin-reverse-engineering.md`。

---

## 快速排查

```
1.☐BOM? 2.☐目录名/ID/entry包名对齐? 3.☐self.ctx取上下文(无_ctx参数)? 4.☐executemany?
5.☐keywords? 6.☐database.enabled? 7.☐改完先Reload(而非复制+重启)? 8.☐行为不更新才删__pycache__? 9.☐rstrip(os.sep)?
10.☐dependencies格式? 11.☐双装饰器顺序? 12.☐@llm_tool用*或**_? 13.☐Router在__init__中注册?
14.☐第三方导入有错误缓存? 15.☐跨插件用call_entry而非import?
16.☐on_startup不调其他插件? 17.☐大文件用URL而非base64? 18.☐Router有prefix? 19.☐Bus用get().filter().sort().limit()?
```

---

## plugin.toml 模板

```toml
[plugin]
id = "your_plugin_id"                    # 建议与源码目录名一致（打包/生产安装要求对齐）
name = "插件中文名"
description = "插件功能描述"
short_description = "简短描述（给 AI 看）"
keywords = ["关键词1", "关键词2", ...]      # 中英文都写，覆盖用户所有说法
version = "0.1.0"
type = "plugin"                          # 普通插件；可省略（默认值）
entry = "plugin.plugins.目录名:PluginClassName"  # module.path:ClassName，且必须是 NekoPluginBase 子类

[plugin.author]
name = "作者名"

[plugin.sdk]
recommended = ">=0.1.0,<0.2.0"
supported = ">=0.1.0,<0.3.0"

[plugin_runtime]
enabled = true
auto_start = true
timeout = 10                             # 启动就绪秒数，须 0 < timeout <= 300

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

**注意**：`[plugin].entry` 必须是 `module.path:ClassName` 且解析为 `NekoPluginBase` 子类（`PluginRouter` 不能直接作为入口）。`plugin.id`、源码目录名、`entry` 包名**强烈建议一致**：开发期旧的源码发现机制可能容忍不一致，但**打包与生产安装要求对齐**，不一致会加载/打包失败。

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

    # ═══ 生命周期（可加 **_ 前向兼容）═══
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
    async def on_config_change(self, **_):
        # 框架不传 old/new，配置变更后自行 dump 重新读取
        cfg = await self.config.dump()
        settings = cfg.get("settings", {})
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

    # ═══ AI 入口（不能有 keywords；上下文用 self.ctx）═══
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
    async def my_action(self, param1: str = "", **_):
        if not param1:
            return Err(SdkError("参数不能为空"))
        # 业务逻辑...
        return Ok({"result": "success", "detail": "..."})

    # ═══ UI Action（官方推荐：label + tone + refresh_context）═══
    @ui.action(
        label=tr("actions.update.label", default="保存设置"),
        tone="primary",
        refresh_context=True,   # 修改状态后自动刷新面板 props.state
    )
    async def update_settings(self, config: dict = None, **_):
        if not isinstance(config, dict):
            return Err(SdkError("config 必须是对象"))
        self.my_setting = config.get("my_setting", False)
        self.my_list = config.get("my_list", [])
        return Ok({"status": "saved"})

    # ═══ UI Context（返回面板数据；id 须与 plugin.toml 的 [[plugin.ui.panel]].context 一致）═══
    @ui.context(id="settings")
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
| `@lifecycle(...)` | none（可加 `**_` 前向兼容） | — |
| `@plugin_entry(...)` | none（可加 `**_`） | 不能有 `keywords`；上下文用 `self.ctx` |
| `@ui.action(...)` | none（可加 `**_`） | 支持 `label=tr(...)`、`tone="primary"`、`refresh_context=True`；UI 按钮调用 |
| `@ui.context(...)` | none | 返回 dict |
| `@timer_interval(...)` | none | 独立线程，需 `new_event_loop()` |
| `@llm_tool(...)` | `name=`+`parameters=`（`*,` 或 `**_`） | 返回普通 dict，非 Ok/Err |

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

> 官方组件库 `@neko/plugin-ui` 提供以下组件（对照 project-neko.online 核实）：

| 分类 | 组件 |
|------|------|
| 布局 | `Page` `Card` `Section` `Stack` `Grid` `Heading` `Divider` |
| 文本/展示 | `Text`(color: primary/secondary/muted) `StatCard` `KeyValue` `DataTable` `List` `JsonView` `CodeBlock` `Alert` `Tip` `Warning` `InlineError` `EmptyState` |
| 表单/输入 | `Field` `Input` `Textarea` `Select` `Switch` `Form` `ActionForm` |
| 状态/交互 | `StatusBadge` `ActionButton` `RefreshButton` `Modal` `ConfirmDialog` `AsyncBlock` |
| Hooks | `useLocalState` `useAsync` `useForm` `useToast` `useConfirm` `useDebounce` `useDebouncedState` `useI18n` |

**不可用组件 / 限制**（Hosted TSX 沙箱）：
- `Table`→`DataTable`、`Button`→`ActionButton`、`useState`→`useLocalState`
- `Text` 的 color **不支持** `danger`/`warning`/`default`（仅 primary/secondary/muted）
- **没有 `Slider` 组件**（滑动条请用 `Input`+数字或 `Select`）
- 禁止：npm 包、class 组件、React Context / Portals / Suspense
- `@ui.context(id=...)` 的 id 必须与 plugin.toml 中 `[[plugin.ui.panel]].context` 完全一致

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
    priority=5,  # 0-2=低(信息性), 3-5=中(一般通知), 6-8=高(重要通知), 9-10=紧急
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

## 运行与部署（默认官方开发模式）

按场景选择，**不要把源码手工复制进用户插件目录**：

| 场景 | 代码从哪加载 | 改完怎么生效 |
|------|-------------|-------------|
| 源码树开发（推荐） | `N.E.K.O/plugin/plugins/<id>/` | `uv run neko-plugin check <id> --strict` → 详情页 **Reload**；改依赖后重启该插件 |
| 开发者模式 Load unpacked | 就地注册的源码绝对路径目录 | 编辑后 **Reload**；改依赖后重启 |
| 已安装包 | 安装目录代码只读，运行时状态在用户数据目录 | 重新 `build` 并导入 `.neko-plugin`；仅手工覆盖时删目标 `__pycache__/` |

```bash
uv run neko-plugin check my_plugin --strict     # 静态检查（通过 ≠ 运行通过）
uv run neko-plugin build my_plugin --out my_plugin.neko-plugin   # 交付时打包
```

> 用户运行时配置在用户数据目录（Windows `%LOCALAPPDATA%\N.E.K.O\plugins\<id>\config\plugin.toml`），密钥写这里，不要进源码 manifest。

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
| 2 | 目录名/ID/entry 不一致 | 加载或打包失败（旧发现机制可能容忍） | 三者对齐 = 源码目录名 |
| 3 | keywords 参数 | `unexpected keyword argument` | 移除 `keywords=` |
| 4 | executemany | `no attribute` | 逐行 `execute()` |
| 5 | 启动就绪超时 | 收到 startup timeout 报错 | 调 `[plugin_runtime].timeout`（≤300）；耗时放 `asyncio.create_task()` |
| 6 | database 未启用 | `self.db` 为 None | `enabled = true` |
| 7 | fetchall 加 await | 运行时错误 | 同步 `fetchall()` |
| 8 | 根目录路径 Bug | 路径不匹配 | `rstrip(os.sep)` |
| 9 | 旧文件未生效 | 行为不变 | 源码树/开发者模式用 **Reload**；手工同步场景确认已覆盖 |
| 10 | AI 乱拼路径 | 路径错误 | 拒绝非绝对路径 + 引导 |
| 11 | `__pycache__` 缓存 | 改代码不生效（Reload 后仍不变） | 删目标 `__pycache__/`（诊断分支） |
| 12 | dependencies 格式 | schema 警告 | 内联表格式 |
| 13 | 双装饰器顺序 | 行为异常/UI 不生效 | 以官方示例为准：`@ui.action` 在上、`@plugin_entry` 在下（未本机验证） |
| 14 | LLM 跳过前置检查 | 直接调核心入口 | description 强提示 |
| 15 | 惰性导入无缓存 | 反复 import 失败 | 错误缓存 + 重放 |
| 16 | on_init 调其他插件 | 返回 PluginNotFound | 移到 on_start |
| 17 | 大文件 base64 超时 | ZMQ 消息超限 | 用 file:// URL |
| 18 | Router 无 prefix | Entry ID 冲突 | router.set_prefix() |
| 19 | Bus 用旧 API | `get_recent/reload` 报错或空 | 改 `get(...).filter(...).sort(...).limit()` |
| 20 | BusList watch 条件错 | 迭代返回空/不触发 | 结构化 `filter(field=value)`；仅 messages/events/lifecycle 支持 `watch(ctx)` |

---

## 官方权威补充（基于 project-neko.online 核实）

> 以下结论与官方开发者文档及 `plugins/` 真实代码逐条核对，用于纠正/补全上文实战经验中可能过时的部分。更完整内容见 [39-official-plugin-dev-guide](references/39-official-plugin-dev-guide.md)。

### 1. 装饰器全集（官方）

| 装饰器 | 作用 |
|--------|------|
| `@neko_plugin` | 类装饰器，标记插件类（必须） |
| `@plugin_entry(id, name, description, input_schema/params, kind(action/service/hook/custom), auto_start, persist, model_validate, timeout, llm_result_fields, llm_result_model, fields, metadata)` | 注册 AI 可调用的入口 |
| `@lifecycle(id="startup"/"shutdown"/"reload"/"freeze"/"unfreeze"/"config_change")` | 生命周期钩子 |
| `@timer_interval(id, seconds, name, auto_start)` | 定时器，独立线程 |
| `@ui.action(label=tr(...), tone="primary", refresh_context=True)` / `@ui.context(id=...)` | Hosted UI 的行为与数据 |
| `@llm_tool(name, description, parameters, timeout, role)` | 注册 LLM 自动调用的工具 |
| `@message` / `@on_event` / `@custom_event` | 消息/事件订阅 |
| `@hook` / `before_entry` / `after_entry` / `around_entry` / `replace_entry` | 入口钩子（monkey-patch 式包装） |
| `@quick_action` | 快捷操作 |
| `@plugin.entry` / `@plugin.lifecycle` / `@plugin.hook` / `@plugin.timer` | 等价命名空间写法 |

**关键纠正**：入口/生命周期/UI 方法的签名里**不要加 `_ctx=None`**（框架不传该参数），需要运行时上下文用 `self.ctx`。`**_` 仅作为前向兼容 catch-all，官方示例普遍写但非强制。

### 2. 参数声明的三种方式（任选其一）

```python
# 方式 A：input_schema（JSON Schema，最常用，真实插件主流）
@plugin_entry(id="x", name="X", description="...", input_schema={...})

# 方式 B：params=Pydantic 模型（类型安全）
@plugin_entry(id="x", name="X", description="...", params=MyParams)

# 方式 C：Annotated 类型提示（官方 Quick Start 写法，自动生成 schema）
@plugin_entry(id="greet", name="Greet", description="Say hello")
async def greet(self, name: Annotated[str, "Name to greet"] = "World"):
    return Ok({"message": f"Hello, {name}!"})
```

### 3. `@llm_tool` 正确写法（与 `@plugin_entry` 区别）

```python
from plugin.sdk.plugin import llm_tool
@llm_tool(
    name="get_weather",                 # 注意是 name= 不是 id=
    description="查询天气",
    parameters={"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
    timeout=30.0,
)
async def get_weather(self, *, city: str):   # 框架以 kwargs 传参，推荐 * 强制 keyword-only
    return {"output": {"city": city, "temp": 22}, "is_error": False}
```
返回**普通 dict**（非 `Ok/Err`）；错误用 `{"output": {...}, "is_error": True, "error": "CODE"}`。

### 4. `NekoPluginBase` 可用属性与方法（官方 SDK）

| 属性/方法 | 说明 |
|-----------|------|
| `self.ctx` | 运行时上下文 `PluginContext`（替代不存在的 `_ctx` 参数） |
| `self.config` | 插件配置（`dump()` / `update()` / `save()`） |
| `self.store` | 键值持久化（`get`/`set`/`delete`） |
| `self.db` | SQLite（`[plugin.database] enabled=true` 时可用） |
| `self.logger` | 日志（支持 `loguru` braces 与 stdlib `%`） |
| `self.bus` | **只读/订阅门面（不是 pub/sub 事件总线）**：`messages`/`events`/`lifecycle`/`conversations`/`memory` 五条总线；前三条可 `get().filter().sort().limit()` 并 `watch(ctx)`，`conversations`/`memory` 为只读快照 |
| `self.plugins` | 跨插件调用（`call_entry("other:entry", {...})`） |
| `self.plugin_id` / `self.plugin_dir` / `self.config_dir`(兼容别名) / `self.storage_dir` / `self.runtime_config_path` / `self.metadata` / `self.system_info` | 元信息与路径（官方 10 属性） |
| `report_status(dict)` / `push_message(...)` / `data_path(...)` / `cache_path(*parts)` | 状态/消息/私有目录/缓存目录 |
| `include_router` / `register_static_ui(directory, *, index_file, cache_control)` / `register_dynamic_entry` / `register_llm_tool` / `unregister_llm_tool(name)` / `list_llm_tools()` / `set_list_actions` / `register_list_action` / `clear_list_actions` / `get_list_actions` / `run_update` / `finish` / `export_push` | 注册与运行控制 |

### 5. Best Practices（官方）

- 所有 entry 返回 `Ok`/`Err`；跨插件调用需处理 `Err`
- 生命周期只做真正的初始化/清理；耗时操作丢 `asyncio.create_task`
- 入口参数：推断 schema / 显式 `input_schema` / Pydantic `params` **三选一**
- 处理器签名显式声明用到的字段；`**_` 仅在「有意」消费额外参数时使用
- 普通日志走 `logger`；敏感原文默认不进日志（脱敏正则**非完备**，勿据此断言"已安全"）
- 用定时器时务必用锁保护共享状态
- `plugin.toml` 的 `[plugin].entry` 路径与 SDK 版本约束必须正确

### 6. Bus 查询 API（v0.9 现行）

Bus 是**宿主状态的只读/订阅门面，不是发布订阅总线**（`self.bus.emit()` 之类不存在，输出请用 `push_message` / `report_status` / Bus 之外的通道）。

```python
# 可重放链：get() → 结构化 filter(field=value) → sort(by=, reverse=) → limit()
events = await self.bus.events.get(plugin_id=self.plugin_id, max_count=50)
recent = events.filter(priority_min=1).filter(type="TASK_FINISHED").sort(by="timestamp", reverse=True).limit(20)

# messages 同理：
msgs = await self.bus.messages.get(room_id=room_id, max_count=100)
hot  = msgs.filter(role="user").sort(by="timestamp", reverse=True).limit(10)
```

- 结构化 `filter(field=value)` 可被计划树重放下推；`filter(callable)` 只作用于本地快照，**不能**放在 `watch()` 之前。
- `watch()` 订阅仅 `messages`/`events`/`lifecycle` 支持；`conversations`/`memory` 是只读快照。
- **已移除**：`get_recent()`、`reload()`、`union()/intersect()/difference()`、where_* 辅助、增量 reload 游标、`self.memory`。旧的 `self.memory` 请改用 `await self.bus.memory.get(bucket_id="default", limit=20)`（有界、短 TTL，**不保证**持久事实/人格记忆）。
- 上例为依据官方示例复现的**示意**，未在本机 SDK 逐行运行；升级 SDK 后请以官方示例为准重测。

### 7. 官方 5 个完整示例

官方 Examples 页提供可直接运行的 5 个插件：`hello_world`（最小）、`kv_store`（store）、`config_panel`（UI+配置）、`scheduler`（timer）、`todo`（完整 CRUD）。要点已并入本 Skill 各主题，完整代码见 [39-official-plugin-dev-guide](references/39-official-plugin-dev-guide.md)。

---

## 参考文档

本 Skill 目录下 `references/` 包含 51 篇详细参考文档（含 1 篇可选工作流 00 + 50 个技术主题 01–50），覆盖每个主题的完整实现和代码示例：

### 可选篇（大型新插件按需启用 · 来自用户「AI 开发协作协调器」skill）

- [00-development-coordinator](references/00-development-coordinator.md) — **可选工作流**：五阶段（需求澄清→方案规划→约束生成→任务拆解→编码实现）+ 最小状态持久化 + 错误回滚；适合需求复杂的大型新插件。每阶段挂接 01–50 具体主题、RULES.md 默认注入 20 铁律 + F1–F9

### 基础篇（01–04 必读）
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
- [28-inter-plugin-communication](references/28-inter-plugin-communication.md) — 插件间通信（call_entry 跨插件调用、依赖声明与检查、共享数据模式、版本兼容回退、防御性调用；官方无跨插件 pub/sub，Bus 只是本机只读门面）

### 实战篇·五（基于 N.E.K.O 主程序深度逆向分析 — 框架层）
- [29-plugin-lifecycle-internals](references/29-plugin-lifecycle-internals.md) — 插件生命周期内部机制（7 阶段状态机、ZMQ 进程通信架构、load/init/start/run/stop/unload 全流程、子进程管理、常见生命周期陷阱）
- [30-push-message-internals](references/30-push-message-internals.md) — Push Message 深度解析（visibility/ai_behavior 两轴正交模型、Parts 结构详解、coalesce_key 消息合并、旧版→v2 迁移映射、UI Action 媒体播放、内部 base64 编码机制）
- [31-bus-system-internals](references/31-bus-system-internals.md) — Bus 只读门面深度解析（可重放查询链 `get().filter().sort().limit()`、计划节点树、五条总线 messages/events/lifecycle/conversations/memory、Watch 变更订阅；**已移除 get_recent/reload/union/intersect/difference**）
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
- [39-official-plugin-dev-guide](references/39-official-plugin-dev-guide.md) — **官方开发者文档权威总结**（Quick Start + 装饰器全集 + SDK 属性/方法 + 5 个完整示例 + Best Practices + Hosted UI 组件全表），已对照 project-neko.online 与真实插件代码核实

### 融合外部开源最佳实践（工程与质量）⭐ 新增

> 融合 13 个外部开源仓库的方法论，作为跨主题的工程纪律与质量基线：**mattpocock**（工程纪律）、**ponytail**（YAGNI 反过度工程）、**impeccable + hallmark**（反 AI 味 UI 设计）、**firecrawl**（网页数据集成）、**strix**（安全加固）、**agentskills**（Agent Skills 规范）、**token-saviour**（token 成本模型）、**subconscious-skill**（持久记忆/潜意识整理）、**prompthakcer**（提示词压缩/PII 脱敏）、**NadirClaw + llm-router**（LLM 路由/成本优化/缓存/去重）、**neko-skill**（陪伴型状态机，已剔除越狱）。本 Skill 自身也遵循 agentskills 规范：`SKILL.md` 仅含 `name` + `description` 与按需展开的 `references/` 渐进披露。

- [40-engineering-discipline](references/40-engineering-discipline.md) — 工程纪律：小步提交、TDD、深模块、两轴代码审查、诊断循环 + ponytail 的 YAGNI 阶梯反过度工程
- [41-ui-design-quality](references/41-ui-design-quality.md) — 反"AI 味"的 Hosted UI 设计：impeccable + hallmark 的确定性设计规则映射到 `@neko/plugin-ui` 受限组件与内联样式
- [42-web-data-integration](references/42-web-data-integration.md) — 网页数据集成：以 firecrawl 为例，把联网抓取/搜索封装成 `@llm_tool` / `@plugin_entry` 的深模块模式
- [43-security-hardening](references/43-security-hardening.md) — 插件安全加固：以 strix 攻击者视角覆盖最小权限、密钥来源分层、URL 输入预筛选（**非完整 SSRF 防护**）、注入、路径穿越、XSS、提示注入、错误处理
- [44-本地插件架构逆向](references/44-local-plugin-architecture.md) — 直接逆向 `plugins/` 真实插件：三种拆分范式、生命周期/配置/工具注册真实写法、防御性模式（带 file:line 出处）
- [45-融合速查](references/45-fusion-quick-reference.md) — 40–44 的压缩版：精髓五条 + 决策树 + 可抄片段（YAGNI/反 slop/firecrawl/SSRF 输入预筛选/真实骨架）
- [46-持久记忆与潜意识整理](references/46-memory-persistence-subconscious.md) — 5 阶段记忆管道、3 类记忆、重要性衰减/归档、whisper 极简注入；映射到 store + `@timer_interval` 后台整理（subconscious-skill）
- [47-LLM 路由与成本优化](references/47-llm-routing-cost-optimization.md) — 复杂度分类→三档、验证器门控级联、Jaccard 语义缓存、飞行中去重、健康感知后端（NadirClaw + llm-router）
- [48-提示词压缩与 PII 脱敏](references/48-prompt-compression-pii-redaction.md) — 4 层 token 成本模型（输入是大头）、正则压缩 15–70%、本地正则遮挡信用卡/邮箱/SSN/API Key（覆盖面有限，非完备脱敏）（token-saviour + prompthakcer）
- [49-角色陪伴型状态机](references/49-neko-companion-state-machine.md) — 数值化好感度状态机、聊天指令系统、动作/情绪标签输出、主动聊天（neko-skill，**已剔除越狱内容**）

### 实战篇·七（基于插件市场 31 个已上架插件源码逆向）⭐ 新增
> 从 `https://market.project-neko.cn` 市场 API 爬取全部 31 个已上架插件的 GitHub 源码（`_crawled_repos/`），逆向提炼六类成功插件范式：系统自动化 / 邮件 / 搜索 / 教育 OCR / 游戏控制 / 外部程序桥接。想抄真实成功插件的骨架或写复杂插件前先读这篇。

- [50-市场插件逆向工程](references/50-market-plugin-reverse-engineering.md) — 31 插件全景表 + 跨插件共性范式（三合一装饰器、后台轮询、深模块、异步 I/O）+ 六类最佳实践（含可抄代码片段：目标窗口锁定、IMAP 轮询、多引擎搜索去重、FSRS 间隔重复、独立 data 进程、HTTP 桥+指数退避）+ 踩坑表（rvc_singer 双目录、pvz_agent 缺失等）