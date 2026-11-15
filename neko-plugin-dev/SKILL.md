---
name: "neko-plugin-dev"
description: "N.E.K.O 插件开发指南。用于创建、修改、调试、打包与发布 N.E.K.O 插件：plugin.toml 契约、依赖声明（pyproject + vendor）、装饰器与生命周期、@plugin_entry 与 @ui.action 叠加、@llm_tool、PluginRouter、Hosted TSX 设置面板、store 持久化、push_message、chat cards / create_card、定时器、权限与部署；官方 neko-plugin CLI 构建方法（.neko-plugin / .neko-bundle）、发布工作流（init → check/lint/precheck → publish）、验证分层与 Market 首次审核 / Revision / 构建来源证据。含 20 条铁律、最小可用插件模板、易错 API 速查与 52 篇按需加载的 references。以官方 N.E.K.O main 为唯一基线，事实依据为主程序源码与 docs/plugins；旧版修订记录仅存档、不参与规则判定。示例未在干净环境跑通端到端。当用户需要开发、修改、调试、打包、发布 N.E.K.O 插件或创建新插件时调用此技能。"
---

# N.E.K.O 插件开发 Skill

> **依据与边界 · 单一基线（重要）**：本技能包全部事实只按官方 `Project-N-E-K-O/N.E.K.O` 的 `main`（commit `acfbdbc`，2026-11-15 只读核对）判定，**不再并列任何旧快照口径**。`REVIEW_FIXES.md` / `CHANGELOG.md` 中关于旧版本的记录是历史存档，用来解释「曾经错过什么」，**不参与当前规则判定，也不要据此写插件代码**。
>
> 动手前先 `uv run neko-plugin --help` 确认目标版本的命令集，不要凭记忆写 API；命令名以官方 CLI 注册清单为准。
>
> **示例插件未在干净环境跑通端到端**，凡标注「示意」的代码都要用 `uv run neko-plugin check` 复验。第三方融合类文档（40–50）是方法论参考，不是官方 API 契约。带「内部机制」字样的篇章（29–38）描述宿主实现，可能随版本变化；写插件代码前以 `docs/plugins/` 与 `plugin/sdk/plugin/` 公开签名为准。

---

## 0. 先读哪几篇（按需加载 · 硬性分级）

| 你要做的事 | 必读 | 按需再读 |
|---|---|---|
| 新建插件 | 本文 §1–§4 + `01-plugin-toml.md` + 官方 `.agent/skills/neko-plugin/references/core-plugin-contract.md` | `39-official-plugin-dev-guide.md` |
| 改 manifest / 依赖 / 包类型 | `01-plugin-toml.md`、`07-gotchas.md` #23 | `plugin/config/schema.py`、`neko_plugin_cli/core/dependencies.py` |
| 写 Python 入口 / 生命周期 / 定时器 | 本文 §4 §5、`02-python-plugin.md` | `29`（仅概念）、`33` |
| Hosted TSX 设置面板 | `03-ui-settings.md`、官方 `hosted-ui-authoring.md` | `15`、`41` |
| 消息推送 | 本文 §5 + `30-push-message-internals.md` | `docs/plugins/plugin-base.md` |
| 打包 / 构建 `.neko-plugin` | **`51-build-publish-and-market-review.md` §1**、本文 §7 | `06-deployment.md` |
| 官方发布工作流 / 投稿审核 | **`51-build-publish-and-market-review.md` §2 §4**、`OTHER.md` | `docs/zh-CN/plugins/cli.md`（官方） |
| 验证分层 / CI 门禁 | **`51-build-publish-and-market-review.md` §3** | `05-testing.md`、`12-master-checklist.md` |
| 排错 | `07-gotchas.md`、`12-master-checklist.md` | `17`、`24` |

> **不要每次触发都通读 52 篇**。`00-development-coordinator.md` 是可选工作流，仅在用户明确要求协作式开发或需求含糊时启用，不是强制前置。

---

## 1. 官方基线与工作边界

- **用脚手架，不要手写目录**：`uv run neko-plugin init <plugin_id> --type plugin --name "My Plugin"` 生成标准骨架（自带 `.git/`、`ruff.toml`、`tests/`、`.github/workflows/verify.yml` + `release.yml`，见 `51` §2.2）；之后只在 `plugin/plugins/<plugin_id>/` 内改动。CLI 没有 `add` 顶层命令，Python 依赖写进 `pyproject.toml` 后直接 `sync <id> --clean`。
- **用公开 facade**：`plugin.sdk.plugin`、`plugin.sdk.adapter`。`plugin.sdk.extension` 已随 Extension 包类型移除、无兼容路径（`docs/plugins/migration-v0.9.md:15`）。**不要新增 `plugin.sdk.shared.*` 导入**（`20-plugin-router.md` 曾给出这种写法，已废弃）。
- **两种包类型由 manifest 决定**：`plugin`（默认）、`adapter`（桥接外部协议/请求流；单纯调外部 HTTP 服务不算 adapter）。`plugin/_types/plugin_types.py:8` 定义 `PluginType = Literal["plugin", "adapter"]`；`extension` 类型与 `[plugin.host]` 已被移除，`schema.py:233` 的 `reject_removed_host_config` 会显式拒绝。
- **身份一致**：目录名、`[plugin].id`、`[plugin].entry`、主类名表达同一个插件概念；打包与生产安装要求对齐。
- **运行时触发的 `@plugin_entry` 必须是 `async def`**；`plugin_runtime.auto_start = false` 表示手动启动，不是「禁用」或「导入安全」。
- **改平台源码（docs/tests/宿主）需要用户明确确认**，插件开发默认只在插件工作区内写文件。

标准骨架（以 `init` 实际产出为准）：

```
plugin/plugins/<plugin_id>/
├── plugin.toml            # 清单：身份、权限、配置、UI、依赖
├── pyproject.toml         # Python 包依赖（需要第三方库时）
├── vendor/                # 依赖实体，由 sync 安装，随包发布
├── __init__.py            # 主类 + @plugin_entry / @ui.action / @lifecycle
├── DESIGN.md              # 官方建议：Identity Lock / 首版范围 / out-of-scope
├── ruff.toml              # 与 Market CI 相同的固定 lint 规则
├── .github/workflows/     # verify.yml（push/PR）+ release.yml（v* tag）
├── .git/                  # 插件自己的 Git 仓库（publish 的前置条件）
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
11. **依赖分两条通道**：`[plugin].dependencies` 是**插件 ID 字符串列表**（CLI 校验口径见 `validate_cmd.py:200`）；Python 包写在 `pyproject.toml [project].dependencies`，再用 `neko-plugin sync <id> --clean` 装进 `vendor/`。**不会自动安装**，CLI **没有 `add` 命令**（详见 §3、§7）。
12. **`@ui.action` 必须与 `@plugin_entry` 叠加**：宿主只从已注册的 entry 收集 UI action，裸 `@ui.action` 不会生成可调用按钮。
13. **`@llm_tool` 用 `*,` 强制 keyword-only**，参数面要窄。
14. **Router 在 `__init__` 中注册**：`self.include_router(...)` 放在 `super().__init__(ctx)` 之后、`__init__` 返回之前；Router 类必须继承 `PluginRouter`。
15. **第三方库惰性导入 + 错误缓存**：`try/except ImportError` 失败后缓存错误，不反复重试 import。
16. **跨插件调用用 `self.plugins.call_entry`**，不要直接 import 其他插件的类。
17. **启动期不要跨插件调用**：`startup` 时其他插件可能尚未就绪；需要时放到首个工作入口里并做失败回退。官方**没有** `on_init` / `on_start` 这类钩子。
18. **推消息用 `parts`，不要 `await`，要判回执**：`push_message` 是同步方法，返回 `PushMessageResult`（`submitted` / `reason`）；`submitted=True` 只表示本地已提交，不是送达保证。旧参 `content=` 等 v1 字段是 compatibility-only，会触发静态检查与运行时警告。二进制媒体用 `image` / `audio` / `video` part 的 `data`；大图用 `await ctx.images.upload()`，HTML 卡片用 `await ctx.create_card()`（详见 §5、`30` 篇）。
19. **Router entry 避免 ID 冲突**：用 `prefix` 或不同 `entry_id`，不是「所有 Router 必须设 prefix」。
20. **Bus 是只读门面**：用可重放查询链 `get().filter().sort().limit()`；`get_recent()` / `reload()` / `union()` / `intersect()` / `difference()` / `bus.emit()` 均不存在，它不是发布订阅总线。共 6 个命名空间，含 `bus.frames`（`plugin/core/bus/frames.py`，`docs/plugins/sdk-reference.md` §Frames）。

---

## 3. `plugin.toml` 与依赖（A1 修订）

```toml
[plugin]
id = "my_plugin"                 # 与目录名一致
name = "我的插件"
description = "给 AI 看的功能描述"
version = "0.1.0"
entry = "plugin.plugins.my_plugin:MyPlugin"
type = "plugin"                  # plugin | adapter（extension 已移除）
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

**依赖的正确流程**（官方 `neko_plugin_cli/commands/validate_cmd.py:200` 校验、`templates/generator.py:520` 生成 `pyproject.toml`）：

```toml
# plugin.toml —— 只声明插件间依赖
dependencies = ["base_plugin"]

# pyproject.toml —— 声明 Python 包
[project]
dependencies = ["httpx>=0.27"]
```

```bash
# 手写 pyproject.toml 后直接 sync；CLI 没有 add 顶层命令
uv run neko-plugin sync <plugin_id> --clean        # 从 pyproject.toml 重装依赖进 vendor/
uv run neko-plugin check <plugin_id> --strict       # 缺支撑文件 / vendor 不满足会报错
uv run neko-plugin lint <plugin_id>                 # pinned ruff 0.12.4
uv run neko-plugin precheck <plugin_id>             # lint → sync --clean → check -r
```

要避免的写法：

```toml
# 错误：内联表既不是字符串列表，也不是依赖对象数组，加载/打包会失败
[plugin.dependencies]
openai = ">=1.0.0"
```

- `keywords` 是**正则表达式**，用于粗筛候选；非法正则会退化为字面子串匹配且不保证报错，注意转义。
- **写 manifest 只认 CLI 校验口径**：`validate_cmd.py:200` 的 `_check_plugin_dependency_id_list` 要求 `[plugin].dependencies` 是**插件 ID 字符串列表**。`plugin/config/schema.py:229` 的 `Optional[List[PluginDependencySchema]]` 是宿主运行时内部模型，不是给插件作者照抄的 manifest 写法；把它写成对象数组会在 CLI 校验阶段失败。
- 官方**不会**在插件安装时自动 pip 安装依赖；不支持 `requirements.txt`；缺依赖时代码要做惰性导入与友好报错。Python 包只能走 `pyproject.toml` → `sync --clean` → `vendor/`。
- 字段全集以 `plugin/config/schema.py`、`plugin/core/ui_manifest.py`、`docs/plugins/plugin-toml.md` 为准。`schema.py:227-228` 声明了 `install: Optional[PluginInstallSchema]` 与 `models: Dict[PluginModelUsageId, PluginModelRequirementSchema]`，对应 `[plugin.install]`（宿主管理的安装动作）和 `[plugin.models.<usage_id>]`（模型用途声明）。反向地，`[plugin.host]` 在 `schema.py:233` 被 `reject_removed_host_config` **显式拒绝**，不要写。
- `check --strict` 会把「缺仓库支撑文件（pyproject/tests/README 等）」按错误处理，所以示例/新插件要补齐支撑文件。

---

## 4. 最小可用插件模板（可直接改）

```python
"""my_plugin —— 以 plugin.sdk.plugin 公开 facade 为准。"""
import asyncio

from plugin.sdk.plugin import (
    NekoPluginBase, neko_plugin, plugin_entry, lifecycle, timer_interval,
    ui, llm_tool, Ok, Err, SdkError, unwrap_or,
)

DEFAULT_GREETING = "你好"


@neko_plugin
class MyPlugin(NekoPluginBase):
    def __init__(self, ctx):
        super().__init__(ctx)
        self._counter = 0
        self._frozen = False
        self._greeting = DEFAULT_GREETING

    # ── 配置：从运行时 TOML 读回，Reload 后不丢 ──
    async def _reload_config(self):
        cfg = await self.config.dump(timeout=5.0)
        section = cfg.get("my_plugin", {}) if isinstance(cfg, dict) else {}
        value = section.get("greeting", DEFAULT_GREETING) if isinstance(section, dict) else DEFAULT_GREETING
        self._greeting = str(value)

    # ── 生命周期：只有这 6 个 id，且用关键字参数 ──
    @lifecycle(id="startup")
    async def on_startup(self, **_):
        await self._reload_config()
        self._counter = unwrap_or(await self.store.get("counter"), 0)
        return Ok({"status": "ready"})

    @lifecycle(id="shutdown")
    async def on_shutdown(self, **_):
        await self.store.set("counter", self._counter)
        return Ok({"status": "stopped"})

    @lifecycle(id="config_change")
    async def on_config_change(self, **_):
        await self._reload_config()
        return Ok({"status": "reloaded"})

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

    # ── UI action：必须与 @plugin_entry 叠加；保存要落盘 ──
    @ui.action(label="保存设置", tone="primary", refresh_context=True)
    @plugin_entry(id="save_settings", name="保存设置", description="保存面板配置")
    async def save_settings(self, config: dict | None = None, **_):
        if not isinstance(config, dict):
            return Err(SdkError("config 必须是对象"))
        await self.config.update({"my_plugin": config})   # 只改内存会在 Reload 后丢失
        await self._reload_config()
        return Ok({"status": "saved", "greeting": self._greeting})

    @ui.context(id="settings")
    async def settings_context(self):
        return {"config": {"greeting": self._greeting},
                "counter": self._counter, "frozen": self._frozen}

    # ── 定时器：必须 async def，宿主执行 asyncio.run(fn()) ──
    @timer_interval(id="tick", seconds=60, name="定时整理", auto_start=True)
    async def on_tick(self, **_):
        if self._frozen:
            return Ok({"skipped": True})
        await asyncio.to_thread(self._blocking_work)
        return Ok({"status": "done"})

    def _blocking_work(self):
        pass

    # ── push_message：同步方法，返回 PushMessageResult ──
    def notify(self, text: str):
        result = self.ctx.push_message(
            visibility=["chat"],
            ai_behavior="blind",
            parts=[{"type": "text", "text": text}],
            source="my_plugin",
            priority=0,
        )
        if not result["submitted"]:
            return Err(SdkError(f"push_message 未提交: {result.get('reason')}"))
        return Ok({"status": "submitted"})
```

> 配置读写参照官方 `plugin/plugins/lifekit/__init__.py` 的公开用法（`config.dump(timeout=...)` / `config.update({...})`）；本节重点是正确的**调用形态**（异步入口、同步 push 并判回执、双装饰器、配置落盘、依赖通道）。可复制的完整骨架见 `examples/minimal_plugin/`。

---

## 5. 易错 API 速查

| 主题 | 事实 | 错误写法 |
|---|---|---|
| `@lifecycle` | 只允许 `startup / shutdown / reload / freeze / unfreeze / config_change`，用 `id=` 关键字 | `@lifecycle("on_init")`、位置参数 |
| `config_change` | 框架以 kwargs 传 `old_config / new_config / mode` | 写成必填位置参数或声称「框架不传」 |
| Reload | 管理面板的 Reload 是**重启进程**（shutdown → startup）；`reload` 钩子仅为兼容保留 | 依赖 `on_reload` 做同进程热更新 |
| `@timer_interval` | 必须 `async def`，宿主在独立线程里 `asyncio.run(fn())`；`docs/plugins/decorators.md:124` 的 `cleanup` 也是 `async def` | `def` + `new_event_loop()` + `run_until_complete()` |
| `push_message` | **同步**方法（不要 `await`）；v2 用 `parts`；返回 `PushMessageResult`，含 `submitted` 与 `reason`（`backpressure` / `transport_error` / `transport_unavailable` / `payload_too_large`）。v1 的 `content=` 等字段是 compatibility-only，必须迁移 | `await ctx.push_message(...)`、`content=` 当快捷用法、忽略回执 |
| `push_message` 载荷 | `MESSAGE_PLANE_PAYLOAD_MAX_BYTES = 512 * 1024`（`plugin/settings.py:588`，`NEKO_MESSAGE_PLANE_PAYLOAD_MAX_BYTES` 可调）；超限**本地整条拒绝**并返回 `reason=payload_too_large`。`submitted=True` **只表示本地已提交**，不代表宿主已消费或已显示；`{MASTER_NAME}` / `{LANLAN_NAME}` 由宿主展开。大图用 `await ctx.images.upload(bytes, mime=...)`（源 32 MiB / 归一化 8 MiB 上限，失败抛异常），chat 侧另有每推 8 图 / 8 MiB 上限 | 把 `submitted=True` 当成送达保证、把大文件塞 base64 |
| 媒体 part | `image` / `audio` / `video` 支持 `data`（转 `binary_base64`）或 `url`；`ui_action` 的 `media_play_url` 可带 url。AI 路径对媒体 part 的支持以目标版本实测为准，别假设任意外部 URL 都可用 | 把 `file://` 当成通用通道、断言宿主一定会拦截或放行外部 URL |
| `visibility` / `ai_behavior` | 两轴正交：`["chat" \| "hud"]` × `respond / read / blind` | 把 priority 臆造成 info/warning/紧急分档 |
| `priority` | `0–10` 整数，默认 `0`；官方未定义语义分档 | 自拟 `0-2 低 / 9-10 紧急` |
| `store.get/set` | 返回 `Result`，取值用 `unwrap` / `unwrap_or` | `await store.get(...) or 0` 再 `+1` |
| `keywords` | 正则表达式，只做粗筛 | 当成 AI 关键词堆纯词、不转义 |
| `@ui.action` | 只从已注册 entry 收集，必须与 `@plugin_entry` 叠加 | 裸 `@ui.action`、前端静默兜底按钮 |
| `_ctx` | 默认不传；需要时声明 `_ctx` 或 `**_`，`llm_tool(reply_tail=True)` 必须能接收 | 断言「框架绝不传任何上下文」 |
| Router | 自定义 Router 必须继承 `PluginRouter`；`@llm_tool` 只扫插件主类 | 裸类 + 在 Router 里写 `@llm_tool` |
| Bus | 只读门面，可重放查询链；共 6 个命名空间，含第 6 个 `bus.frames`（`plugin/core/bus/frames.py`，`docs/plugins/sdk-reference.md` §Frames） | `bus.emit()`、`get_recent()`、把 frames 当日志/队列 |
| HTML chat cards | `await ctx.create_card(html=, summary=, css=, actions=)` → `card.update(...)`；`create_view()` 出 AgentHUD 标签页；`ChatCard` / `CardSubmissionError` / `PluginView` 由 `plugin.sdk.plugin` 导出。需 `@ui.action` + `@plugin_entry` 叠加处理 `data-neko-action`。见 `docs/plugins/chat-cards.md` | 旧版照抄这些 API、把 card 当持久化对象、假设按钮脚本会执行 |

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

## 7. 构建、官方工作流与验证审核（官方 main · 2026-11-15 核对）

> **完整版见 [`51-build-publish-and-market-review.md`](references/51-build-publish-and-market-review.md)**。本节是速查；命令集以 `uv run neko-plugin --help` 为准。

### 7.1 官方命令集（照抄前先 `uv run neko-plugin --help` 确认）

| 用途 | 命令 |
|---|---|
| 建骨架 | `init <id> --type plugin --name "..."` |
| 补支撑文件 | `setup-repo <id> [--github-actions] [--upgrade-github-actions] [--dry-run]` |
| 建 GitHub 仓库 | `create-repo <id>`（用 gh） |
| 依赖 | 手写 `pyproject.toml` → `sync <id> --clean` |
| 检查 | `check` / `-s` / `-r` / `-r --market-release` |
| 固定 lint | `lint <id>` |
| 本地 CI 门禁 | `precheck <id> [--json]`（lint → sync --clean → check -r） |
| 包检查 | `check -r` 内含 inspect + payload hash 验证 |
| 构建 | `build <id> [-o] [-t] [--all] [--bundle]` |
| 分析 | `analyze <id>...` |
| **发布** | **`publish <id>` / `publish github <id>` / `publish market <url>`** |

**命令边界**：`release_cmd.py` / `validate_cmd.py` 是内部实现模块；`deps` 不是顶层命令（`deps_cmd.py` 注册的是 `sync`）；没有 `release`、也没有 `add` 顶层命令；`init setup-repo` / `init create-repo` 这类二级写法不存在——它们都是顶层命令。`install` 只是兼容命令，拒绝直接写运行时目录。

### 7.2 构建方法（官方 main）

`.neko-plugin`（单插件）/ `.neko-bundle`（整合包）都是标准 ZIP：`manifest.toml`（必需）、`metadata.toml`（建议，含 payload hash）、`sign.toml`（可选）、`payload/{dependencies.toml,plugins/<id>/,profiles/}`。`dependencies.toml` 由 `build` 自动生成，开发者不要手写。`metadata.payload.hash` 是对**规范化后的 `payload/`** 算 sha256，`check -r` 会验证。

`install` 只是兼容命令，**拒绝直接写运行时目录**；真实安装走 N.E.K.O 插件中心的「导入」。包内禁止 `__pycache__` / `.pytest_cache` / `.venv` / `dist` / `build`。

### 7.3 官方发布工作流（首次上架）

```bash
uv run neko-plugin init hello_world --type plugin --name "Hello World"   # 自带 .git/ + workflows + ruff.toml
uv run neko-plugin check hello_world --strict
uv run neko-plugin lint hello_world            # pinned ruff 0.12.4: E4,E7,E9,F,I / py311 / 120
uv run neko-plugin precheck hello_world        # 本地跑完整三道 CI 门禁
uv run neko-plugin create-repo hello_world     # 或手动建 n.e.k.o_plugin_<id> 公开空仓库
# 在插件自己的目录 commit + push → 等 Actions「Verify N.E.K.O Plugin」通过
# → market.project-neko.cn/#/upload 提交首次审核 → 按意见提交 Revision → 审核通过
uv run neko-plugin publish hello_world         # 检查→打 v<version> tag→Release 三资产→通知 Market stable
```

`publish` 前置：插件目录有自己的 `.git/`、`git status --short` 为空、当前 commit 已推到 `origin`、标准 `release.yml` 是当前版本。后续版本只需改源码 → 换**未发布过**的新版本号 → check → commit/push → publish（审核已通过则无需重新申请）。beta 用 `publish github <id>` 后在 Market 版本页手动选渠道。**审核通过 ≠ 可安装**，`publish` 不能替代首次审核。

### 7.4 验证分层（不要把 check 通过当运行通过）

| 层 | 命令 | 增加什么 |
|---|---|---|
| 日常 | `check <id>` | manifest / 入口 / 装饰器 AST / 依赖 / 支撑文件 |
| 严格 | `check -s <id>` | 缺支撑文件升为 error |
| 发布 | `check -r <id>` | + 插件测试 + 构建 + 包检查 + **payload hash 验证** |
| 市场 | `check -r --market-release <id>` | + 仓库名 / origin / tag-version 对齐 / release.yml / 工作区干净 |
| CI | `verify.yml` | ruff → `sync --clean` → `check -r` → 生成 `market-evidence.json` |

`check` 的盲点：不保证运行时触发的 entry 是 `async def`、不覆盖 lifecycle/timer/message/UI 装饰器语义、`auto_start=false` 不阻止父进程导入、UI action 暴露需运行时检查。`precheck` 就是官方给出的「本地等价 CI」入口。安全扫描默认**暂停**，设 `NEKO_PLUGIN_MARKET_SECURITY_CHECKS=1` 才启用（源码 32 MiB / 单文件 2 MiB / 5000 条目 / 展开 128 MiB 上限）。

### 7.5 审核与证据链（官方 main）

- **人工**：Market 首次申请提交的是**固定 commit 快照**；一个插件只申请一次，改动通过原申请的 **Revision**（填完整 commit SHA）提交，不产生 Market Version；申请关闭后需审核员重开。
- **自动门禁**：id 匹配 `^[a-z][a-z0-9_]*$` 且 ≤100 字符、version ≤50 字符、仓库名推荐 `n.e.k.o_plugin_<id>`、`v<version>` tag 与 `plugin.toml.version` 一致、`.github/workflows/release.yml` 存在、工作区无未提交文件。
- **证据链**：`market-evidence.json` 记录 `source_commit` / `workflow_run_id` / `neko_commit` / 包 `sha256` / `payload_hash`；release workflow 拆成 `release → evidence → attest` 三 job，只有 `attest` 有 `id-token/attestations: write` 且全用 40 位 SHA pinned actions，防止插件代码篡改证据。Release 三资产：`<id>.neko-plugin`、`<id>.market-release-check.txt`、`market-evidence.json`。
- **人工审核标准不在公开仓库**，只能覆盖可查到的自动门禁与流程语义。

### 7.6 官方 main 已确认的能力（不要再当成幻觉）

以下条目均已在官方 main 源码中确认存在（核对记录见 `REVIEW_FIXES.md §9` 存档）：

| 条目 | 官方 main 事实 |
|---|---|
| `submitted` 回执 / `payload_too_large` | `push_message(...) -> PushMessageResult`；`docs/plugins/push-message.md` 明确 `submitted` 与 `reason` |
| 512 KiB 上限 | `plugin/settings.py:588` 默认 `512 * 1024` |
| `ctx.images.upload()` | `docs/plugins/push-message.md` §Image upload，源 32 MiB / 归一化 8 MiB |
| `ChatCard` / HTML chat cards | `plugin/sdk/shared/core/cards.py`；`ChatCard` / `CardSubmissionError` / `PluginView` 由 `plugin.sdk.plugin` 导出 |
| `bus.frames` 第 6 条总线 | `plugin/core/bus/frames.py`、`docs/plugins/sdk-reference.md` §Frames |
| `[plugin.install]` / `[plugin.models]` | `plugin/config/schema.py:227-228` 的 `PluginInstallSchema` / `PluginModelRequirementSchema` |
| `publish` 顶层命令 | `cli.py` 注册 `publish_cmd.register(...)`，三种模式见 §7.1；`init` 生成物见 `generator.py:174-176` |
| `docs/plugins/push-message.md` | 官方完整规范（348 行），含回执、图片上传与预算表 |
| `setup-repo --upgrade-github-actions` / `create-repo` | `cli.py` 注册的顶层命令选项 |

**仍然成立、不要写进文档的**：`bus.emit()` / `get_recent()` / `union()` 等只读门面之外的 API、`on_init` / `on_start` / `on_stop` 等虚构生命周期钩子、`[plugin.dependencies]` 内联表、`deps` / `release` / `add` 顶层子命令、把 ZMQ 说成 PAIR/JSON/12 种命令、把 `ChatCard` 当成持久化对象或可执行 JS 的运行时。`30` / `31` / `37` 三篇已按官方 main 重写。

> 官方仓库自带 `.agent/skills/neko-plugin/`（`core-plugin-contract.md`、`hosted-ui-authoring.md`、`plugin-checks-and-tests.md`、`plugin-creation-workflow.md` 等），**优先级高于本技能的任何推测性描述**。

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

**官方构建 / 发布 / 审核**：`51` 构建方法（`.neko-plugin` 包格式、`build`）、官方工作流（`init → lint/precheck → publish`）、验证分层（`check -s/-r/--market-release`、CI 门禁、安全扫描）、Market 首次审核 / Revision / 构建来源证据链、官方命令集

> `README.md`（references 目录下）是逐篇索引与「何时需要」指引。**29–38 是宿主内部机制说明，全部按官方 main 源码核对**；`30` / `31` / `37` 已整篇按官方 main 重写。`50` 声称「全部带 file:line 出处」，但其依据的 `_crawled_repos/` 不在仓库内，无法复核，请当作经验性材料。

---

## 10. 发布前检查清单

**A. 代码与清单**
```
☐ 目录名 / id / entry / 主类名一致；无 BOM
☐ 依赖：[plugin].dependencies 是插件 ID 列表；Python 包在 pyproject.toml 且 vendor/ 已 sync --clean
☐ 所有 @plugin_entry / @ui.action / 定时器都是 async def（定时器无 new_event_loop）
☐ @ui.action 都与 @plugin_entry 叠加；面板有保存入口且声明了所需权限
☐ push_message 没有 await、用 parts、未用 content=、未硬编码称呼
☐ push_message 判了 submitted 回执，且按「仅本地已提交」处理，不当中送达保证
☐ store 取值已 unwrap；Bus 只用只读查询链（新版可用 bus.frames，但仍是只读）
☐ keywords 是合法正则；权限默认 false
☐ 运行时配置明文 TOML，密钥不进源码仓库、不进日志
☐ 外部 API 地址 / 抓取回灌 LLM 前都有说明、截断与提示注入缓解
```

**B. 构建与验证（官方 main，详见 `51` §1 §3）**
```
☐ check <id> / check -s <id> / lint <id> / precheck <id> 全部通过
☐ build 产物为 .neko-plugin；包内无 __pycache__ / .pytest_cache / .venv / dist
☐ check -r 的 payload_hash_verified=True，包内 manifest id/version 与源码一致
☐ GitHub Actions「Verify N.E.K.O Plugin」通过
☐ Hosted TSX 改动跑过 check-hosted-tsx；entry / UI 改动有触发测试
☐ 明确 check 的盲点，在真实宿主里加载、触发入口、打开面板保存、Reload
```

**C. 投稿与审核（官方 main，详见 `51` §2 §4）**
```
☐ 插件目录有自己的 .git/，origin 指向 n.e.k.o_plugin_<id> 的公开仓库
☐ git status --short 为空，当前 commit 已 push
☐ verify.yml / release.yml 是当前标准模板，ruff.toml 未被自定义破坏
☐ plugin.toml.version 是从未发布过的新版本号，tag 为 v<version>
☐ 首次审核已提交（一个插件只一次）；按审核意见用 Revision 提交完整 commit SHA
☐ 审核已通过（不只是已申请）；publish 完整跑到「Market 发布成功」
☐ Release 三资产齐全可下载；market-evidence.json 与 attestation 已生成
☐ Market 版本列表出现该版本，stable latest 已更新
```

> `examples/minimal_plugin/` 的静态契约测试只覆盖 A 组的静态部分；B 组的真宿主加载与 C 组的 Market 上架必须在目标环境里实跑，不能用文档结论代替。

---

## 11. 未验证与免责

- `references/` 中的 Python 代码块是摘录片段（方法体单独成块、签名用 `...` 占位），**不是可独立运行的模块**；可复制的完整骨架只有 `examples/minimal_plugin/`。
- 本技能示例的**本机真跑**部分：官方 main `generator.py` 的 `generate_plugin()` / `generate_repo_support_files()` 已实际执行，7 份支撑文件与产出字节一致；pinned `ruff==0.12.4` 两种入口（本地 `--config ruff.toml` 与官方 CI `--isolated` 原命令）均通过；`uvx pytest -q -c tests/pytest.ini tests` 11 项通过；5 个 `.py` 编译通过。静态契约测试、语法与链接检查也通过。4.1.1 曾在**本地旧快照** CLI 上跑过 `check --strict`（0 error / 1 预期 warning），**不能当作官方 main 的验证结果**。
- 但**未在真实宿主中加载、打开面板保存并 Reload**，也未跑过官方 main 的 `check` / `lint` / `precheck` / `publish`，因此仍不算端到端验证。可复现的真宿主验证清单见 `examples/minimal_plugin/README.md`。
- `42` 中的 firecrawl 依赖名、`fc.scrape(...)` 的位置参数与 `doc.metadata_dict` 是否符合当前 PyPI 版本**未核实**；示例已改为零外部依赖版本以免误导。
- `41` 提到的 `Input type="range"` 能否替代 Slider 未核实；`README.md` 曾宣传 `Slider`，按 `03-ui-settings.md` 的组件表为准。
- 外部 skill 片段（40–50）无逐条许可/署名说明，引用时请自行确认来源许可。
- 31 个市场插件的统计与「全部声明同样 SDK 区间」未复核。
- 遇到与本文冲突的官方源码/文档，**一律以官方为准**并回填到本技能；核对时锁定到具体 commit（本版为 `acfbdbc`）。`REVIEW_FIXES.md` 与 `CHANGELOG.md` 是历史存档，不作为规则来源。
- **真机验证是当前最大缺口**：`init → check/lint/precheck → 宿主加载 → 面板保存 → Reload → publish` 全链路需要完整 N.E.K.O 宿主与 Market 平台。4.3.0 已把「官方 init 生成器实际执行 + pinned ruff + pytest」这三层在本机跑通（见上），但文档、静态契约测试、lint 都**不能替代一次真实宿主运行**，本技能包不声称已完成。逐条阻塞原因、解除条件与审核决策见仓库根目录 [`../UNVERIFIED.md`](../UNVERIFIED.md)（待审）。
- 官方 `publish → GitHub Release → Market 上架` 全链路、`NEKO_PLUGIN_MARKET_SECURITY_CHECKS=1` 的扫描行为、Market 人工审核标准均**未在真机验证**；人工审核标准未在公开仓库披露。
