# 深审问题修复对照表（历史存档）

> 🗄️ **本文件是历史存档，不参与当前规则判定**。自 **4.3.0** 起，本仓库的事实只按官方 `Project-N-E-K-O/N.E.K.O` main `acfbdbc` **单一口径**判定；`SKILL.md`、`references/`、`examples/` 与介绍文件均不再并列旧快照。
>
> 本文件保留旧版复核过程、「曾经错过什么」以及 §9 的版本代差勘误，仅供追溯与回滚。**不要依据本文件里的旧快照结论写插件代码**；当前规则请读 `neko-plugin-dev/SKILL.md`。
>
> 关于「哪些验证没做、为什么没做、需要什么条件」的逐条说明不在本文件，统一见 [`UNVERIFIED.md`](UNVERIFIED.md)（待审）。
>
> 4.3.0 收尾：GitHub [Issue #2](https://github.com/HMUG12/Project_Neko-plugin_skill/issues/2) 的 8 类残留问题已按官方 main 单一口径逐条处理，[Issue #1](https://github.com/HMUG12/Project_Neko-plugin_skill/issues/1) 的自动化规范已落成 `scripts/verify_skill.py` + CI；真跑证据与完整改动见 `CHANGELOG.md` 4.3.0 条目。本文件此后不再追加规则性结论。
>
> 本文件记录 `Project_Neko-plugin_skill-深审-1114193300.md` 中每个问题的处理结果与依据，供复核与回滚。

## 0. 基线与依据

| 项 | 内容 |
|---|---|
| 上游同步 | `HMUG12/Project_Neko-plugin_skill`，main 分支 commit `38fa349`（tag `4.1.1`，最后提交 2026-09-18） |
| 同步方式 | `git` 直连 github.com 走代理 SSL 握手失败，改用 GitHub API zipball 下载快照；原 zip 保留为回滚基线 |
| 回滚 | 用工作区根目录的 `Project_Neko-plugin_skill-main.zip` 还原；同步目录无 `.git` |
| 事实基准 | 本地 `N.E.K.O-main (1)/N.E.K.O-main` 的 `plugin/` 源码、`docs/plugins/`、`.agent/skills/neko-plugin/` |
| 核对原则（4.1.1） | 逐条以**本地旧快照**源码为准，不盲从审查报告；与旧快照不符的条目见 §6，当时一律未采纳 |
| **4.2.0 纠偏** | 2026-11-15 只读查询官方 `Project-N-E-K-O/N.E.K.O` main `acfbdbc`（**未克隆、未下载仓库**）后发现：§6 中多条「不成立」结论**只对旧快照成立**，官方新版中审查报告的说法是对的。逐条勘误见 **§9**；旧快照与官方 main 按 A/B 双口径标注 |
| 上游推送 | 2026-11-15 单 commit `11b2bdef8a4918ee61de5401a755fc6ac10f0eb5` 推到 `main`；Git Data API 一次提交 132 个 tree 条目（71 新增/更新 + 61 删除），远端 71 个文件与本地逐条 blob hash 一致 |
| 本地工作副本 | `Project_Neko-plugin_skill/` 已 `git init` 并跟踪 `origin/main`；`http.version=HTTP/1.1` 解决本地代理下 git 的 HTTP/2 握手失败（**无需**关闭 TLS 校验），`core.autocrlf=input` |

## 1. A 类 · 严重且确定

| 编号 | 深审结论 | 核实 | 处理 |
|---|---|---|---|
| A1 | 依赖声明是内联表，与官方相反 | ✅ 成立 | 铁律 #11、`01`、`07` #23、`12`、`13`、`16`、`28`、示例：`[plugin].dependencies` 改插件 ID 字符串列表（CLI 校验口径），Python 包走 `pyproject.toml [project].dependencies` + `neko-plugin add / sync` + `vendor/`；删除「自动安装」；补充运行时 schema 与 CLI 两套口径不一致的说明 |
| A2 | 定时器要求 `def` + `new_event_loop` 是错的 | ✅ 成立（宿主 `host.py:1147` 用 `asyncio.run(fn())`） | 全仓定时器改 `async def`、删 `new_event_loop()` 三步模板；`07` #19 / #35 两条反向陷阱重写；`02/10/12/24/32/39/46` 等同步 |
| A3 | 29 号整篇生命周期与官方不符 | ✅ 成立（`decorators.py:473` 只有 6 个 id） | `29` 整篇重写；删 `on_init/on_start/on_stop/on_unload`、`trigger_event`、`query_memory`、`self,,`；07 #36 与铁律 #17 同步 |
| A4 | ZMQ 写成 PAIR + inproc + JSON | ✅ 成立（实际 `zmq.PUSH/PULL` + `tcp://127.0.0.1:*` + pickle） | `37` 整篇重写，含 6 种 channel tag；`references/README.md` 索引与 CHANGELOG 历史描述同步 |
| A5 | `push_message` 被写成 async 且多处过时 | ✅ 成立（`context.py:390` 同步；宿主 `core/context.py:846` 返回 `None`） | `30` 整篇重写；全仓去 `await`、去 `content=`；补 v2 `parts`、`coalesce_key`、占位符、`push_message_async`、v1 弃用参数；07 #37、SKILL.md §5 同步 |
| A6 | 裸 `@ui.action` 不产生可调用动作 | ✅ 成立（`host.py:953` 只遍历 `entry_map`） | SKILL.md 完整模板、`03`、示例补 `@plugin_entry` 叠加；前端删除空操作静默兜底 |

## 2. B 类 · 示例插件

| 编号 | 处理 |
|---|---|
| B1 | `WebRouter` 未继承 `PluginRouter` → 目录改名 `examples/minimal_plugin/`，`NotesRouter(PluginRouter)`；`@llm_tool` 移回主类；删掉 Router 上对 `self._reload_config()` 的调用 |
| B2 | 设置面板只存本地 state → 重写为可保存面板：`@ui.action` + `@plugin_entry` 的 `save_settings`，`permissions` 含 `config:write`，`onResult` 显式报错；删 `handleRefresh` 死代码与静默 `catch` |
| B3 | 依赖格式、阻塞 `getaddrinfo`、非法配置崩溃、提示注入、未用变量、缺 `pyproject.toml`/`tests` → 改为**零第三方依赖**示例，补 `pyproject.toml`、`tests/test_plugin_contract.py`、`README.md`、`config.example.toml`；`42` 的 firecrawl 抓取降级为方法论参考并标注未核实 |

## 3. C 类 · 中等

| 编号 | 处理 |
|---|---|
| C1 | `config_change` 统一为 kwargs（`old_config/new_config/mode`）；`29`、`SKILL.md` §3/§5、示例模板一致；Reload 明确为重启进程，`reload` 钩子仅兼容保留 |
| C2 | 铁律 #3 改为「默认不传 ctx，需要时声明 `_ctx` 或 `**_`；`@llm_tool(reply_tail=True)` 必须能接收 `_ctx`」 |
| C3 | `35`、`49`、`14`、`39` 的 `store.get` 裸值改 `unwrap_or`；SKILL.md §5 加易错行 |
| C4 | `20` 的 3 处 `from plugin.sdk.shared.core.router import PluginRouter` 改 `from plugin.sdk.plugin import PluginRouter`；SKILL.md §1 明确禁止新增 `plugin.sdk.shared` 导入 |
| C5 | `01` §2 整段重写：`keywords` 是正则、只做粗筛、非法正则退化为字面匹配；检查清单同步 |
| C6 | 补官方 CLI（`init / init-repo / setup-repo / add / sync / check --strict|--release|--market-release / build / install / inspect / verify`）、`type` 四种取值、`[plugin.host]`、`startup_failure`、面板 `permissions`、`self.memory`、Agent 调度语义、官方自带 skill 与 `init` 脚手架要求。**同时删除报告中不存在的字段与能力**（见 §6） |

## 4. D 类 · 一致性与可用性

- 版本统一为 **4.1.1**：README 标题、徽章（`CHANGELOG.md` 补全扩展名）、CHANGELOG 顶部新增 4.1.1 条目，修正被误替换的 V4.0.0 标题。
- 目录 `neko-plugin-dev(4.1.0)` → `neko-plugin-dev`（与 `SKILL.md` 的 `name` 一致），全仓路径引用同步。
- 示例更名 `web_assistant` → `minimal_plugin`，README 结构图、检查清单、索引同步。
- 速查清单统一为 20 项；`references/README.md` 中不存在的 `#29-1` / `#30-1` / `#31-1` / `#34-1` 引用改为实际编号。
- 死链：`examples/README.md` → `../examples/README.md`；徽章链接补 `.md`；`[N.E.K.O](https://github.com)` 占位链接改指官方文档站；README 不再宣传不存在的 `Slider`。
- 杂文件：`OTHER.md` 与 `n.e.k.o_plugin_example/README.md` 重写为准确说明，纳入 `.gitignore` 白名单并写进仓库结构图；删掉对不存在的 `main.py` / `scripts/verify_plugin.py` 的描述。
- `SKILL.md` 由 920 行精简到约 360 行；`description` 去掉「所有结论已对照官方核实」的夸大表述，补「先读哪几篇」硬性分级、发布前检查与未验证声明；完整类模板补齐导入。

## 5. E / F 类

- **E（可能）**：firecrawl 依赖名与 API、`Input type="range"`、`50` 号 file:line 出处、市场 31 插件统计——均**未核实**，已在 `SKILL.md` §11、`examples/README.md`、`42` 相关处明确标注，不写成事实。
- **F（安全）**：补运行时配置是明文 TOML 的提示、用户可配外部 API 地址会把 Key 发往该地址的风险、抓取内容回灌 LLM 前的截断与提示注入缓解；`14` 的 `update_own_config` 说明同步。

## 6. 审查报告中经**本地旧快照**核对不成立的条目（4.1.1 未采纳）

> ⚠️ **本节只适用于工作区本地旧快照，已被 4.2.0 部分推翻、4.3.0 完全降级为存档**。官方 `main`（`acfbdbc`，2026-11-15）中下表多条说法其实是**真实存在的能力**，属于版本演进而非报告误判。**逐条勘误见 §9**，以 §9 为准。
>
> 下表仍保留作为「旧快照下不可写」的反例；写插件前必须先确认目标版本，并用 `uv run neko-plugin --help` 核对命令集。

| 报告说法 | 源码事实 |
|---|---|
| `push_message` 有 `submitted` 回执 | `plugin/core/context.py:846` 标注 `-> None`，插件侧拿不到回执 |
| 有 `payload_too_large` 结果 | 全仓无该字符串 |
| 载荷上限 512 KiB | `plugin/settings.py:447` 默认 **256 KiB**（`NEKO_MESSAGE_PLANE_PAYLOAD_MAX_BYTES` 可调） |
| 用 `ctx.images.upload()` 传大文件 | 全仓无此 API；图片用 `image` part 的 `data`（SDK 转 `binary_base64`） |
| AI 路径会拒绝任意外部 URL | 无 SSRF 拒绝策略；`ui_action` 的 `media_play_url` 明确支持 url，其余 url 型媒体以实测为准 |
| ZMQ 序列化是 ormsgpack | `plugin/core/zmq_transport.py` 用 **pickle + channel tag**；ormsgpack 属于 `plugin/message_plane/*` 另一条通道 |
| 缺失 `ChatCard` / `bus.frames` 第 6 条总线 | 全仓无 `ChatCard`、无 `bus.frames`；Bus 只有 5 个命名空间，`31` 号写「五条总线」是对的 |
| 缺失 `[plugin.install]` / `[plugin.models]` manifest 字段 | schema 中没有；源码里的同名字符串是某插件的 Python 模块导入路径 |
| CLI 有 `release` / `deps` / `publish` 顶层子命令，以及 `init setup-repo` / `init create-repo` 二级写法 | 实际顶层子命令是 `init / init-repo / setup-repo / add / sync / check / build / install / inspect / verify / analyze`；`setup-repo` 与 `sync` 确实存在但**都是顶层命令**，`release` / `deps` / `publish` 不存在 |
| 官方 `decorators.md` 写明定时器必须 `async def` | 该文档示例用的是同步 `def`，与 `host.py` 实现冲突；结论正确但依据错误，已在 SKILL.md §5 注明「不要照抄该示例」 |
| `docs/plugins/push-message.md` | 本地副本无此文件；相关内容在 `plugin-base.md` / `sdk-reference.md` / `docs/changelog/plugin-push-message-v2.md` |
| `host.py:1383` / `:1174` 等行号 | 本地快照为 `:1147` / `:953`，行号因版本漂移，不作为依据 |

## 7. 验证结果（终验）

| 检查 | 结果 |
|---|---|
| 反向模式扫描（逐条归类） | `deps sync` / `init setup-repo` **0 处**；`nekog.sdk` 1 处（仅修订说明）；`self,,` 4 处（CHANGELOG / 修订说明 / 对照表）；`[plugin.dependencies]` 7 处（**全部**是标注「❌ 错误」的反例或勘误文字）；`await push_message` 4 处（错误现象 / 旧→新映射）；`PAIR / inproc` 8 处（全部是勘误说明）；`ChatCard` / `bus.frames` 3 处（全部是「不要写」清单）；`512KiB` / `submitted` / `payload_too_large` 命中均在勘误语境。`on_start` 的 51 处命中中 44 处是 `on_startup` 的子串误匹配，其余为勘误，**无错误正面示例残留** |
| Markdown 相对链接 | 60 篇 md 全量扫描，**0 处失效** |
| SKILL.md | **360 行**（< 500）；frontmatter description **352 字符**（< 1024） |
| Python 文件语法 | 4 个 `.py` 文件 `py_compile`，**0 失败** |
| 重写代码块语法 | `24` §2.6、`32` §11 的代码块抽取后**编译通过**；`32-3` 的 `async def action(self, ...)` 伪代码已改为合法写法 |
| 静态契约测试 | **7/7 通过**（环境无 pytest，用内置方式逐个调用 `test_*`，与 pytest 断言等价） |
| TOML 可解析 | 3 个 `.toml` 用 `tomllib`，**0 失败** |
| 规模 | 86 个文件 / 60 篇 md / 4 个 py / 3 个 toml |
| 官方 `check --strict` | ✅ **已实测通过**：`[OK] 0 error(s), 1 warning(s)`（exit 0）。用 `uv run --no-project` 隔离环境 + 本地 N.E.K.O 源码调用官方 CLI；据反馈补齐 `tests/test_smoke.py`、`.vscode/*`、`.github/workflows/*`、`[plugin.sdk]` 与 `.gitignore` 规则。唯一 warning「非独立插件仓库」是示例内嵌于技能包的固有属性，非缺陷 |
| **运行时端到端** | ❌ 未跑：真实宿主中加载插件、打开设置面板保存、执行 Reload 需要完整 N.E.K.O 运行环境；已在 README / SKILL.md / CHANGELOG 声明 |

## 8. 后续建议

1. ~~跑一次 `check --strict`~~ **已完成**（见 §7）。剩余：在真实宿主中加载示例并跑通 Reload，把输出记进 CHANGELOG。
2. 实际加载示例、调用入口、打开设置面板保存、执行 Reload，补端到端验证记录。
3. 若上游 N.E.K.O 主仓库有更新，重新核对 `decorators.py`、`context.py`、`zmq_transport.py`、`schema.py` 与 CLI 注册清单，再更新本表「事实基准」版本。
4. 本次修复沿用版本号 `4.1.1` 但未打新 tag；如需在 Release 页可见，补一个 `v4.1.1-fix` 或 `v4.1.2` 标签。（原「无法回推上游」问题已解决，见 §0）
5. `references/` 的 359 个 Python 代码块中有 100 个无法独立编译，均为「类方法摘录」「签名 `...` 占位」「函数签名原文」三类文档体裁，**不是事实错误也不是本次修复的回归**；已在 `references/README.md` 与 `SKILL.md` §11 加全局说明。若要整体改成可编译片段，属于独立的大规模文档重构。


---

## 9. 版本代差勘误（4.2.0 · 2026-11-15）

> **背景**：4.1.1 的事实基准是工作区 `N.E.K.O-main (1)/N.E.K.O-main`（旧版 SDK 0.1.x）。官方 `Project-N-E-K-O/N.E.K.O` 的 `main`（commit `acfbdbc`，2026-11-15，0.9.x 系列）已演进。**用 A 版源码否定 B 版文档是基线选择错误**，导致 §6 把一批针对新版的说法误判为「报告误判」。本次通过 GitHub REST API **只读查询**官方文档与源码（未克隆、未下载仓库文件）逐条复核。

### 9.1 §6 中「不成立」但官方 main **确实存在**的条目

| 审查报告 / §6 原说法 | 官方 main 事实 | 依据 |
|---|---|---|
| `push_message` 有 `submitted` 回执 | 成立。`push_message(...) -> PushMessageResult`，返回 `{"submitted": bool, "reason": ..., "ok": ...}`；`reason` 取 `backpressure` / `transport_error` / `transport_unavailable` / `payload_too_large`。**`submitted=True` 只表示本地已提交，不代表送达** | `plugin/sdk/shared/core/context.py:463`、`docs/plugins/push-message.md` |
| 有 `payload_too_large` 结果 | 成立。超限在**本地**拒绝整条 push，返回 `submitted=False` + 该 reason | `docs/plugins/push-message.md` L102–111 |
| 载荷上限 512 KiB | 成立。`MESSAGE_PLANE_PAYLOAD_MAX_BYTES = 512 * 1024`（旧快照 256 KiB） | `plugin/settings.py:588` |
| 用 `ctx.images.upload()` 传大文件 | 成立。`await ctx.images.upload(bytes, mime=...)`，源 32 MiB / 归一化 8 MiB 上限，失败抛 `ValueError` | `docs/plugins/push-message.md` §Image upload |
| 缺失 `ChatCard` / `bus.frames` 第 6 条总线 | 成立。`ChatCard` / `CardSubmissionError` / `PluginView` 由 `plugin.sdk.plugin` 导出；`bus.frames` 有独立实现 | `plugin/sdk/shared/core/cards.py`、`plugin/sdk/plugin/__init__.py:133-135`、`plugin/core/bus/frames.py`、`docs/plugins/chat-cards.md`、`docs/plugins/sdk-reference.md` §Frames |
| 缺失 `[plugin.install]` / `[plugin.models]` manifest 字段 | 成立。`install: Optional[PluginInstallSchema]`、`models: Dict[PluginModelUsageId, PluginModelRequirementSchema]` | `plugin/config/schema.py:227-228`（类定义在 :100 / :32 / :146） |
| CLI 有 `publish` 顶层子命令 | 成立。`publish <plugin>` / `publish github <plugin>` / `publish market <release-url>` 三模式 | `plugin/neko_plugin_cli/cli.py` 注册 `publish_cmd.register(...)`、`commands/publish_cmd.py:104-175`、`docs/zh-CN/plugins/cli.md` §5 |
| `docs/plugins/push-message.md` | 成立，官方仓库有该文件（约 24K 字符）；旧快照没有 | `docs/plugins/push-message.md` |
| `setup-repo --upgrade-github-actions` / `create-repo` | 成立，均为新版真实顶层命令 | `commands/init_cmd.py:73-135` |

### 9.2 §6 中**仍然成立**的结论（不要写进文档）

- ~~ZMQ 传输是 `PUSH/PULL` + `pickle` + channel tag；`ormsgpack` 属于另一条通道~~ → **4.3.0 更正**：官方 main 的 `plugin/core/zmq_transport.py:3-31` 是 **4 条 PUSH/PULL 通道 / 7 个 tag**；下行 `pickle`、**上行 `ormsgpack`（MessagePack）+ per-host token**，图片上行为独立帧格式。旧结论只对旧快照成立，见 `37` 篇。
- ~~官方 `decorators.md` 给出同步 `def` 示例~~ → **4.3.0 更正**：官方 main `docs/plugins/decorators.md:124` 的 `cleanup` 是 `async def`，不存在该冲突。`@timer_interval` 必须 `async def` 的结论不变。
- `host.py:1383` / `:1174` 等固定行号会随版本漂移，不作为依据。
- **新版也没有**的：`bus.emit()` / `get_recent()` / `union()` / `intersect()` / `difference()`、`on_init` / `on_start` / `on_stop` / `on_unload` 钩子、`[plugin.dependencies]` 内联表、`deps` / `release` 顶层子命令、`init setup-repo` / `init create-repo` 二级写法。`release_cmd.py` / `validate_cmd.py` 仍是内部实现模块。
- `ChatCard` 不是持久化对象、卡片里的脚本/内联事件处理器**不会执行**（script-disabled iframe）；不能当成 JS 运行时。

### 9.3 历史：两版 CLI 命令集（存档，以 `--help` 与官方 `cli.py` 为准）

| 官方 main `acfbdbc` | 本地旧快照 |
|---|---|
| `init` / `setup-repo` / `create-repo` / `check` / `sync` / `lint` / `precheck` / `build` / `install` / `analyze` / **`publish`** | `init` / `init-repo` / `setup-repo` / `add` / `sync` / `check` / `build` / `install` / `inspect` / `verify` / `analyze` |

- 新版**没有** `add`（依赖写 `pyproject.toml` 后 `sync --clean`）、`inspect` / `verify`（合并进 `check -r`）、`init-repo`（改为 `create-repo`）、`init --no-interactive`。
- 新版 `deps_cmd.py` 只注册 `sync`，`lint` / `precheck` / `publish` 是新增的顶层命令。
- 完整工作流、构建包格式、验证分层与审核证据链见 [`neko-plugin-dev/references/51-build-publish-and-market-review.md`](neko-plugin-dev/references/51-build-publish-and-market-review.md) 与 [`OTHER.md`](OTHER.md)。

### 9.4 4.2.0 的处理方式

采用 **A/B 双口径**而不是简单翻转结论：`SKILL.md` 开头声明两条基线；构建/发布/验证/审核统一以官方 main 为准（§7 + 51 篇）；`00`–`50` 篇与示例的 `check --strict` 实测标注为旧快照口径；`30` / `31` / `01` / `07` / `12` / `05` / `06` 等篇在冲突处加版本代差说明。这样既不丢弃 4.1.1 已验证的成果，也不再把新版事实写成错误。

**仍未验证**：官方 `publish → GitHub Release → Market 上架` 全链路、`NEKO_PLUGIN_MARKET_SECURITY_CHECKS=1` 的扫描行为、Market 人工审核标准（未在公开仓库披露）。本表所有官方 main 结论均来自只读查询，未在本机运行新版 CLI。
