---
name: "neko-plugin-dev"
description: "N.E.K.O 插件开发指南。用于创建、修改、调试、打包 N.E.K.O 插件：plugin.toml 契约、依赖声明（pyproject + vendor）、装饰器与生命周期、@plugin_entry 与 @ui.action 叠加、@llm_tool、PluginRouter、Hosted TSX 设置面板、store 持久化、push_message、定时器、权限与部署、官方 neko-plugin CLI 流程。含 20 条铁律、最小可用插件模板、易错 API 速查与 51 篇按需加载的 references。事实以仓库内 N.E.K.O 主程序源码与 docs/plugins 为准，示例未在干净环境跑通端到端。当用户需要开发、修改、调试 N.E.K.O 插件或创建新插件时调用此技能。"
---

# N.E.K.O 插件开发 Skill

> **依据与边界**：本技能的事实层以工作区内的 N.E.K.O 主程序源码（`plugin/`、`docs/plugins/`）与官方 `.agent/skills/neko-plugin/` 为准，核对日期见 CHANGELOG。**示例插件未在干净环境跑通端到端**，凡标注「示意」的代码都要用 `uv run neko-plugin check` 复验。第三方融合类文档（40–50）是方法论参考，不是官方 API 契约。
>
> **不要凭记忆写 API**：`references/` 里带「内部机制」字样的篇章（29–38）描述的是宿主实现，可能随版本变化；写插件代码前请以 `docs/plugins/` 与 `sdk/plugin/` 公开签名为准。

---

## 0. 先读哪几篇（按需加载 · 硬性分级）

| 你要做的事 | 必读 | 按需再读 |
|---|---|---|
| 新建插件 | 本文 §1–§4 + `01-plugin-toml.md` + 官方 `.agent/skills/neko-plugin/references/core-plugin-contract.md` | `39-official-plugin-dev-guide.md` |
| 改 manifest / 依赖 / 包类型 | `01-plugin-toml.md`、`07-gotchas.md` #23 | `plugin/config/schema.py`、`neko_plugin_cli/core/dependencies.py` |
| 写 Python 入口 / 生命周期 / 定时器 | 本文 §4 §5、`02-python-plugin.md` | `29`（仅概念）、`33` |
| Hosted TSX 设置面板 | `03-ui-settings.md`、官方 `hosted-ui-authoring.md` | `15`、`41` |
| 消息推送 | 本文 §5 + `30-push-message-internals.md` | `docs/plugins/plugin-base.md` |
| 打包 / 发布 / 校验 | 本文 §7、`07-gotchas.md` | `06-deployment.md`、`12-master-checklist.md` |
| 排错 | `07-gotchas.md`、`12-master-checklist.md` | `17`、`24` |

> **不要每次触发都通读 51 篇**。`00-development-coordinator.md` 是可选工作流，仅在用户明确要求协作式开发或需求含糊时启用，不是强制前置。

---

## 1. 官方基线与工作边界

- **用脚手架，不要手写目录**：`uv run neko-plugin init <plugin_id> ...` 生成标准骨架与 `plugin.toml`；之后只在 `plugin/plugins/<plugin_id>/` 内改动。
- **用公开 facade**：`plugin.sdk.plugin`、`plugin.sdk.extension`、`plugin.sdk.adapter`。**不要新增 `plugin.sdk.shared.*` 导入**（`20-plugin-router.md` 曾给出这种写法，已废弃）。
- **三种包类型由 manifest 决定**：`plugin`（默认）、`extension`（须声明 `[plugin.host]`）、`adapter`（桥接外部协议/请求流；单纯调外部 HTTP 服务不算 adapter）。
- **身份一致**：目录名、`[plugin].id`、`[plugin].entry`、主类名表达同一个插件概念；打包与生产安装要求对齐。
- **运行时触发的 `@plugin_entry` 必须是 `async def`**；`plugin_runtime.auto_start = false` 表示手动启动，不是「禁用」或「导入安全」。
- **改平台源码（docs/tests/宿主）需要用户明确确认**，插件开发默认只在插件工作区内写文件。

标准骨架（以 `init` 实际产出为准）：

```
plugin/plugins/<plugin_id>/
├── plugin.toml            # 清单：身份、权限、配置、UI、依赖
├── pyproject.toml         # Python 包依赖（需要第三方库时）
├── vendor/                # 依赖实体，由 add / sync 安装，随包发布
├── __init__.py            # 主类 + @plugin_entry / @ui.action / @lifecycle
├── DESIGN.md              # 建议：目的与 out-of-scope 边界
├── ui/settings.tsx        # Hosted TSX（新交互式 UI 首选）
├── i18n/{zh-CN,en}.json
├── static/                # 仅遗留独立页面用
├── docs/                  # 只读 Markdown 页面
└── tests/
```

---

## 2. 20 条铁律（修订版）

1. **文件名全小写 + 下划线**，目录名 / `plugin.id` / `entry` 包名对齐。
2. **Python 文件 UTF-8 无 BOM**，否则 `SyntaxError`。
3. **上下文默认不传参**：框架不会主动把 `ctx` 作为普通参数塞进入口；需要运行时上下文用 `self.ctx`。若确实要接框架注入的 `args._ctx`，显式声明 `_ctx` 或用 `**_` 兜底；`@llm_tool(reply_tail=True)` 的处理函数必须能接收 `_ctx`。
4. **`**_` 是可选 catch-all**：仅在有意容纳额外关键字时加，不是强制要求。
5. **启动就绪默认约 10 秒**：`[plugin_runtime].timeout` 满足 `0 < timeout <= 300`；耗时操作放 `asyncio.create_task()` 并处理取消与异常。
6. **数据库会话无 `executemany`**：逐行 `await session.execute()`。
7. **改完优先官方 Reload**；仅在手改源码 / 已安装包且行为不更新时，才把删 `__pycache__/` 当诊断分支（06 / 17）。
8. **权限默认 `false`**，按最小权限逐项授权。
9. **AI 路径参数要求绝对路径**，拒绝相对路径并在错误信息中引导。
10. **磁盘 I/O 用 `asyncio.to_thread`**，不阻塞事件循环。
11. **依赖分两条通道**：打包 / CLI 校验口径下 `[plugin].dependencies` 是**插件 ID 字符串列表**（运行时 schema 另有一套对象数组口径，见 §3）；Python 包写在 `pyproject.toml [project].dependencies`，再用 `neko-plugin sync <id>` 装进 `vendor/`。**不会自动安装**（详见 §3）。
12. **`@ui.action` 必须与 `@plugin_entry` 叠加**：宿主只从已注册的 entry 收集 UI action，裸 `@ui.action` 不会生成可调用按钮。
13. **`@llm_tool` 用 `*,` 强制 keyword-only**，参数面要窄。
14. **Router 在 `__init__` 中注册**：`self.include_router(...)` 放在 `super().__init__(ctx)` 之后、`__init__` 返回之前；Router 类必须继承 `PluginRouter`。
15. **第三方库惰性导入 + 错误缓存**：`try/except ImportError` 失败后缓存错误，不反复重试 import。
16. **跨插件调用用 `self.plugins.call_entry`**，不要直接 import 其他插件的类。
17. **启动期不要跨插件调用**：`startup` 时其他插件可能尚未就绪；需要时放到首个工作入口里并做失败回退。官方**没有** `on_init` / `on_start` 这类钩子。
18. **推消息用 `parts`，不要 `await`**：`push_message` 是同步方法，返回 `None`（插件侧拿不到回执）；旧参 `content=` 会触发 `DeprecationWarning`。二进制媒体用 `image` / `audio` / `video` part 的 `data`（SDK 转 `binary_base64`）；url 型媒体能否渲染取决于宿主路径，别当成保证可用（详见 §5）。
19. **Router entry 避免 ID 冲突**：用 `prefix` 或不同 `entry_id`，不是「所有 Router 必须设 prefix」。
20. **Bus 是只读门面**：用可重放查询链 `get().filter().sort().limit()`；`get_recent()` / `reload()` / `union()` / `intersect()` / `difference()` / `bus.emit()` 均不存在，它不是发布订阅总线。

---

## 3. `plugin.toml` 与依赖（A1 修订）

```toml
[plugin]
id = "my_plugin"                 # 与目录名一致
name = "我的插件"
description = "给 AI 看的功能描述"
version = "0.1.0"
entry = "plugin.plugins.my_plugin:MyPlugin"
type = "plugin"                  # plugin | extension | adapter
keywords = ["^查.*天气$", "weather"]   # 正则，只用于粗筛候选
dependencies = ["other_plugin_id"]     # 插件 ID 字符串列表；无依赖就省略

[plugin_runtime]
auto_start = true
timeout = 10

[plugin.store]
enabled = true

[[plugin.ui.panel]]
id = "settings"
title = "设置"
context = "settings"
```

**依赖的正确流程**（官方 `neko_plugin_cli/core/dependencies.py`）：

```toml
# plugin.toml —— 只声明插件间依赖
dependencies = ["base_plugin"]

# pyproject.toml —— 声明 Python 包
[project]
dependencies = ["httpx>=0.27"]
```

```bash
uv run neko-plugin add <plugin_id> "httpx>=0.27"   # 装进 vendor/ 并更新 pyproject.toml
uv run neko-plugin sync <plugin_id> [--clean]      # 从 pyproject.toml 重装依赖
uv run neko-plugin check <plugin_id> --strict       # 缺支撑文件 / vendor 不满足会报错
```

要避免的写法：

```toml
# 错误：内联表既不是字符串列表，也不是依赖对象数组，加载/打包会失败
[plugin.dependencies]
openai = ">=1.0.0"
```

- `keywords` 是**正则表达式**，用于粗筛候选；非法正则会退化为字面子串匹配且不保证报错，注意转义。
- **两套口径不一致**：运行时 `plugin/config/schema.py:103` 把 `dependencies` 定义为 `List[PluginDependencySchema]`（对象数组），而打包 CLI `neko_plugin_cli/core/dependencies.py:75` 要求插件 ID 字符串列表。**写插件时以 CLI 校验口径为准**（字符串列表），高级结构化依赖用 `[plugin.dependency]` / `[[plugin.dependency]]`。
- 官方**不会**在插件安装时自动 pip 安装依赖；不支持 `requirements.txt`；`extension` 类型不得声明外部 Python 依赖；缺依赖时代码要做惰性导入与友好报错。
- 字段全集（`type = plugin / extension / script / adapter`、`[plugin.host]`、`[plugin_runtime].startup_failure`、`[[plugin.ui.panel]]` 与 `permissions`（含 `config:write`））以 `plugin/config/schema.py`、`plugin/core/ui_manifest.py`、`docs/plugins/plugin-toml.md` 为准。**`[plugin.install]` / `[plugin.models]` 不是 manifest 字段**（源码里同名字符串是某插件的 Python 模块导入路径），早期审查报告把它们列为「缺失项」属误判。
- `check --strict` 会把「缺仓库支撑文件（pyproject/tests/README 等）」按错误处理，所以示例/新插件要补齐支撑文件。

---

## 4. 最小可用插件模板（可直接改）

```python
"""my_plugin —— 以 plugin.sdk.plugin 公开 facade 为准。"""
import asyncio

from plugin.sdk.plugin import (
    NekoPluginBase, neko_plugin, plugin_entry, lifecycle, timer_interval,
    ui, llm_tool, Ok, Err, SdkError, unwrap, unwrap_or,
)


@neko_plugin
class MyPlugin(NekoPluginBase):
    def __init__(self, ctx):
        super().__init__(ctx)
        self._counter = 0
        self._frozen = False

    # ── 生命周期：只有这 6 个 id，且用关键字参数 ──
    @lifecycle(id="startup")
    async def on_startup(self, **_):
        self._counter = unwrap_or(await self.store.get("counter"), 0)
        return Ok({"status": "ready"})

    @lifecycle(id="shutdown")
    async def on_shutdown(self, **_):
        await self.store.set("counter", self._counter)
        return Ok({"status": "stopped"})

    @lifecycle(id="config_change")
    async def on_config_change(self, *, old_config=None, new_config=None, mode=None, **_):
        # 框架以 kwargs 注入；不要写成必填位置参数
        return Ok({"status": "reloaded"})

    # reload / freeze / unfreeze 仅作兼容保留；管理面板的 Reload 是重启进程
    @lifecycle(id="freeze")
    async def on_freeze(self, **_):
        self._frozen = True
        return Ok({"status": "frozen"})

    @lifecycle(id="unfreeze")
    async def on_unfreeze(self, **_):
        self._frozen = False
        return Ok({"status": "unfrozen"})

    # ── AI 入口 ──
    @plugin_entry(
        id="count",
        name="计数",
        description="把计数器加一并返回当前值",
        input_schema={"type": "object", "properties": {}},
    )
    async def count(self, **_):
        self._counter += 1
        return Ok({"count": self._counter})

    # ── UI action：必须与 @plugin_entry 叠加 ──
    @ui.action(label="保存设置", tone="primary", refresh_context=True)
    @plugin_entry(id="save_settings", name="保存设置", description="保存面板配置")
    async def save_settings(self, config: dict | None = None, **_):
        if not isinstance(config, dict):
            return Err(SdkError("config 必须是对象"))
        await self.config.update(config)   # 具体方法名以目标 SDK 为准
        return Ok({"status": "saved"})

    @ui.context(id="settings")
    async def settings_context(self):
        return {"counter": self._counter, "frozen": self._frozen}

    # ── 定时器：必须 async def，宿主执行 asyncio.run(fn()) ──
    @timer_interval(id="tick", seconds=60, name="定时整理", auto_start=True)
    async def on_tick(self, **_):
        if self._frozen:
            return Ok({"skipped": True})
        await asyncio.to_thread(self._blocking_work)
        return Ok({"status": "done"})

    def _blocking_work(self):
        pass

    # ── push_message 是同步方法，不要 await ──
    def notify(self, text: str):
        receipt = self.ctx.push_message(
            visibility=["chat"],
            ai_behavior="blind",
            parts=[{"type": "text", "text": text}],
            source="my_plugin",
            priority=0,
        )
        return receipt
```

> 模板里的 `config.update` / `store.set` 等方法名请以目标版本的 `sdk/plugin/base.py` 与 `docs/plugins/sdk-reference.md` 复核；本节重点是正确的**调用形态**（异步入口、同步 push、双装饰器、依赖通道）。

---

## 5. 易错 API 速查

| 主题 | 事实 | 错误写法 |
|---|---|---|
| `@lifecycle` | 只允许 `startup / shutdown / reload / freeze / unfreeze / config_change`，用 `id=` 关键字 | `@lifecycle("on_init")`、位置参数 |
| `config_change` | 框架以 kwargs 传 `old_config / new_config / mode` | 写成必填位置参数或声称「框架不传」 |
| Reload | 管理面板的 Reload 是**重启进程**（shutdown → startup）；`reload` 钩子仅为兼容保留 | 依赖 `on_reload` 做同进程热更新 |
| `@timer_interval` | 必须 `async def`，宿主在独立线程里 `asyncio.run(fn())`；`docs/plugins/decorators.md` 的同步 def 示例与实现冲突，不要照抄 | `def` + `new_event_loop()` + `run_until_complete()` |
| `push_message` | **同步**方法，返回 `None`（插件侧无回执）；v2 用 `parts`；v1 的 `content=` 等参数会告警 | `await ctx.push_message(...)`、`content=` 当快捷用法 |
| `push_message` 载荷 | 返回 `None`，**没有** `submitted` / `payload_too_large` 回执给插件；消息平面默认载荷上限是 **256 KiB**（`NEKO_MESSAGE_PLANE_PAYLOAD_MAX_BYTES`，可由环境变量调整），不是审查报告说的 512KiB；`{MASTER_NAME}` / `{LANLAN_NAME}` 由宿主展开 | 检查返回值、把大文件塞 base64、`ctx.images.upload()`（不存在） |
| 媒体 part | `image` / `audio` / `video` 支持 `data`（转 `binary_base64`）或 `url`；`ui_action` 的 `media_play_url` 可带 url。AI 路径对媒体 part 的支持以目标版本实测为准，别假设任意外部 URL 都可用 | 把 `file://` 当成通用通道、断言宿主一定会拦截或放行外部 URL |
| `visibility` / `ai_behavior` | 两轴正交：`["chat" \| "hud"]` × `respond / read / blind` | 把 priority 臆造成 info/warning/紧急分档 |
| `priority` | `0–10` 整数，默认 `0`；官方未定义语义分档 | 自拟 `0-2 低 / 9-10 紧急` |
| `store.get/set` | 返回 `Result`，取值用 `unwrap` / `unwrap_or` | `await store.get(...) or 0` 再 `+1` |
| `keywords` | 正则表达式，只做粗筛 | 当成 AI 关键词堆纯词、不转义 |
| `@ui.action` | 只从已注册 entry 收集，必须与 `@plugin_entry` 叠加 | 裸 `@ui.action`、前端静默兜底按钮 |
| `_ctx` | 默认不传；需要时声明 `_ctx` 或 `**_`，`llm_tool(reply_tail=True)` 必须能接收 | 断言「框架绝不传任何上下文」 |
| Router | 自定义 Router 必须继承 `PluginRouter`；`@llm_tool` 只扫插件主类 | 裸类 + 在 Router 里写 `@llm_tool` |
| Bus | 只读门面，可重放查询链 | `bus.emit()`、`get_recent()` |

---

## 6. 常见错误速查（20 项，与 `07-gotchas.md` 编号对齐）

```
1.☐BOM? 2.☐目录名/ID/entry对齐? 3.☐self.ctx且入口签名正确? 4.☐executemany?
5.☐keywords是正则且已转义? 6.☐store.enabled / store返回值已unwrap?
7.☐改完先Reload? 8.☐行为不更新才删__pycache__? 9.☐绝对路径已校验?
10.☐dependencies是插件ID列表+pyproject/vendor? 11.☐@ui.action叠加了@plugin_entry?
12.☐@llm_tool用*且在主类? 13.☐Router继承PluginRouter且在__init__注册?
14.☐第三方导入有错误缓存? 15.☐跨插件用call_entry?
16.☐startup里不调其他插件? 17.☐push_message未await且用parts?
18.☐Router entry ID无冲突? 19.☐Bus用get().filter().sort().limit()?
20.☐定时器是async def且无new_event_loop?
```

> `07-gotchas.md` 的 45 条长清单与本速查表是**同一套问题的两种粒度**：本表是每次提交前的硬检查，07 是排错时的展开说明。07 中原有的 #19「定时器必须用 def」、#35「定时器里不能直接 await」两条反向陷阱已按官方源码改正。

---

## 7. 官方 CLI 流程与新能力（C6 补齐）

```bash
uv run neko-plugin init <plugin_id> --type plugin --name "My Plugin" --no-interactive
uv run neko-plugin init-repo <plugin_id>       # 创建市场仓库
uv run neko-plugin setup-repo <plugin_id>      # 准备仓库工作流
uv run neko-plugin add <plugin_id> "httpx>=0.27"   # 装进 vendor/ 并更新 pyproject.toml
uv run neko-plugin sync <plugin_id> [--clean]      # 从 pyproject.toml 重装依赖
uv run neko-plugin check <plugin_id> --strict       # 缺支撑文件按错误处理
uv run neko-plugin check <plugin_id> --release --market-release  # 发布前（后者必须与 --release 同用）
uv run neko-plugin build <plugin_id> / install <pkg> / inspect <pkg> / verify <pkg>
```

> 子命令以 `plugin/neko_plugin_cli/cli.py` 的注册清单为准（`init / init-repo / setup-repo / add / sync / check / build / install / inspect / verify / analyze`）；**不存在 `release` 或 `deps` 顶层子命令**。`--market-release` 必须与 `--release` 同用，并检查仓库名 `n.e.k.o_plugin_<id>`、tag 与版本对齐、release workflow 存在。执行前用 `--help` 复核参数。

**上游真实存在、早期版本没讲清的内容**（用前查源码，不要凭本文推断签名）：

- 清单层：`type = plugin / extension / script / adapter`；`extension` 必配 `[plugin.host]`；`[plugin_runtime].startup_failure = warn | fail | ignore`；`[[plugin.ui.panel]]` 的 `permissions` 支持 `state:read / config:read / config:write / action:call / logs:read / runs:read`（**只有面板要写配置时才加 `config:write`**）。
- SDK 层：`self.memory`（`MemoryClient`，`await self.memory.query(...)`）；`self.bus` 是只读 / 订阅门面，**只有 5 个命名空间**：`messages / events / lifecycle / conversations / memory`。
- Agent 调度语义：`agent_hidden` 是 entry metadata（对自动 Agent 路由隐藏）；`needs_confirmation` / `clarify` / `deferred` 是插件 run_data 返回值驱动的**宿主内部调度信号**，不是 SDK 装饰器或 `push_message` 参数。见 `brain/task_executor.py`、`app/agent_server/channels/user_plugin.py`、`docs/architecture/task-hud-system.md`。
- 官方仓库自带 `.agent/skills/neko-plugin/`（含 `core-plugin-contract.md`、`hosted-ui-authoring.md`、`plugin-checks-and-tests.md`），**优先级高于本技能的任何推测性描述**。

> **不要写进文档的东西**：`ChatCard`、`bus.frames` /「第 6 条总线」、manifest 里的 `[plugin.install]` / `[plugin.models]`、`ctx.images.upload()`、`submitted` / `payload_too_large` 回执、512KiB 上限——源码里都不存在（消息平面实际默认上限是 256 KiB 且可由环境变量调整），属早期外部审查报告的误判。`31-bus-system-internals.md` 写「五条总线」是对的。

---

## 8. 进阶融合规则（F1–F9 · 方法论，非 API 契约）

- **F1 先跑通再拆**：最小壳跑通再逐步加抽象（40 §6）。
- **F2 复杂度收进深函数**：entry 只做「取参 → 调深函数 → Ok/Err」（40 §5 / 42 §2）。
- **F3 UI 克制**：≤1 品牌色、无嵌套卡片、对比度 ≥4.5:1（41）。
- **F4 外部输入先预筛**：URL 走 `_is_safe_url`（非完整 SSRF 防护）、命令/SQL 参数化、抓取内容回灌 LLM 前做提示注入缓解（43）。
- **F5 大插件拆 Router / Mixin**（44）；示例见 `examples/`。
- **F6 持久状态放 `store` / `db`**（46）。
- **F7 外部 LLM 先路由再缓存去重**（47）、**F8 提示词先压缩再脱敏**（48）、**F9 复杂插件参考市场骨架**（50）。

> 46–48 偏通用工程方法论，与插件 API 无关；40–45 与 F1–F9 内容有重叠，以 `45-fusion-quick-reference.md` 为压缩入口即可，不必重复读。

---

## 9. `references/` 索引（按需加载）

**基础**：`00` 可选协作工作流 · `01` plugin.toml · `02` Python 插件 · `03` UI 设置面板 · `04` i18n · `05` 测试 · `06` 部署 · `07` 踩坑大全 · `08` AI 友好设计 · `09` 权限 · `10` 性能 · `11` 撤销与日志

**实战**：`12` 汇总清单 · `13` 云 API 集成 · `14` 多面板架构 · `15` 富 UI 组件 · `16` 后端简化 · `17` pyc 缓存陷阱 · `18` 流式输出 · `19` LLM 工作流 · `20` PluginRouter · `21` @llm_tool 注册 · `22` Static UI · `23` 外部协议集成 · `24` 错误处理 · `25` 并发竞态 · `26` 后端设计模式 · `27` 音频流水线 · `28` 插件间通信

**宿主内部机制（仅供理解，勿当作 API 契约）**：`29` 生命周期 · `30` push_message · `31` Bus · `32` NekoPluginBase · `33` Router/Entry · `34` Logger · `35` Store/DB · `36` i18n 引擎 · `37` ZMQ 传输 · `38` 配置系统 · `39` 官方文档总结

**工程与外部融合**：`40` 工程纪律 · `41` UI 设计质量 · `42` 网页数据集成 · `43` 安全加固 · `44` 本地插件架构 · `45` 融合速查 · `46` 持久记忆 · `47` LLM 路由 · `48` 提示词压缩/PII · `49` 角色状态机 · `50` 市场插件逆向

> `README.md`（references 目录下）是逐篇索引与「何时需要」指引。**29–38 曾包含基于旧版本逆向的虚构 API，已在本次修订中按官方源码重写**，引用时以本文 §5 为准。`50` 声称「全部带 file:line 出处」，但其依据的 `_crawled_repos/` 不在仓库内，无法复核，请当作经验性材料。

---

## 10. 发布前检查清单

```
☐ uv run neko-plugin check <id> --strict 通过
☐ 目录名 / id / entry / 主类名一致；无 BOM
☐ 依赖：plugin.toml 是插件 ID 列表；Python 包在 pyproject.toml 且 vendor/ 已用 add / sync 装好
☐ 所有 @plugin_entry / @ui.action / 定时器都是 async def（定时器无 new_event_loop）
☐ @ui.action 都与 @plugin_entry 叠加；面板有保存入口且声明了所需权限
☐ push_message 没有 await，未用 content=，未硬编码称呼
☐ store 取值已 unwrap；Bus 只用只读查询链
☐ keywords 是合法正则；权限默认 false
☐ 运行时配置是明文 TOML：不要在日志/回显中打印密钥
☐ 用户可配的外部 API 地址要在文档里说明 Key 会被发往该地址
☐ 抓取/外部内容回灌 LLM 前有截断与提示注入缓解
☐ README / CHANGELOG / tests / pyproject 齐备（--strict 会检查支撑文件）
☐ 在真实 SDK 上跑 check（静态已通过）；加载插件、打开面板保存、执行 Reload 后把结果记进 CHANGELOG
```

---

## 11. 未验证与免责

- `references/` 中的 Python 代码块是摘录片段（方法体单独成块、签名用 `...` 占位），**不是可独立运行的模块**；可复制的完整骨架只有 `examples/minimal_plugin/`。
- 本技能的示例插件已通过官方 `neko-plugin check --strict`（0 error / 1 个「非独立插件仓库」预期 warning），但**未在真实宿主中加载、打开面板并 Reload**，因此仍不算端到端验证；`30` / `37` 等内部机制描述依据的是本地 N.E.K.O 主程序快照，上游变更可能导致细节不同。
- `42` 中的 firecrawl 依赖名、`fc.scrape(...)` 的位置参数与 `doc.metadata_dict` 是否符合当前 PyPI 版本**未核实**；示例已改为零外部依赖版本以免误导。
- `41` 提到的 `Input type="range"` 能否替代 Slider 未核实；`README.md` 曾宣传 `Slider`，按 `03-ui-settings.md` 的组件表为准。
- 外部 skill 片段（40–50）无逐条许可/署名说明，引用时请自行确认来源许可。
- 31 个市场插件的统计与「全部声明同样 SDK 区间」未复核。
- 遇到与本文冲突的官方源码/文档，**一律以官方为准**并回填到本技能。
