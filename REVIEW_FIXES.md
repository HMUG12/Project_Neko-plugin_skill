# 深审问题修复对照表（4.1.1）

> 本文件记录 `Project_Neko-plugin_skill-深审-1114193300.md` 中每个问题的处理结果与依据，供复核与回滚。

## 0. 基线与依据

| 项 | 内容 |
|---|---|
| 上游同步 | `HMUG12/Project_Neko-plugin_skill`，main 分支 commit `38fa349`（tag `4.1.1`，最后提交 2026-09-18） |
| 同步方式 | `git` 直连 github.com 走代理 SSL 握手失败，改用 GitHub API zipball 下载快照；原 zip 保留为回滚基线 |
| 回滚 | 用工作区根目录的 `Project_Neko-plugin_skill-main.zip` 还原；同步目录无 `.git` |
| 事实基准 | 本地 `N.E.K.O-main (1)/N.E.K.O-main` 的 `plugin/` 源码、`docs/plugins/`、`.agent/skills/neko-plugin/` |
| 核对原则 | **逐条以源码为准，不盲从审查报告**。报告里与源码不符的条目见 §6，一律未采纳 |
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

## 6. 审查报告中经源码核对**不成立**的条目（未采纳）

> 这些说法如果照抄进技能包，会变成新的错误。全部保留在文档中作为「不要写」的反例。

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
| **端到端** | ❌ 未跑：`init → check → Reload` 需要真实 N.E.K.O 运行环境，已在 README / SKILL.md / CHANGELOG 声明 |

## 8. 后续建议

1. 在真实 SDK 上跑一次 `uv run neko-plugin check minimal_plugin --strict`，把输出记进 CHANGELOG。
2. 实际加载示例、调用入口、打开设置面板保存、执行 Reload，补端到端验证记录。
3. 若上游 N.E.K.O 主仓库有更新，重新核对 `decorators.py`、`context.py`、`zmq_transport.py`、`schema.py` 与 CLI 注册清单，再更新本表「事实基准」版本。
4. 本次修复沿用版本号 `4.1.1` 但未打新 tag；如需在 Release 页可见，补一个 `v4.1.1-fix` 或 `v4.1.2` 标签。（原「无法回推上游」问题已解决，见 §0）
5. `references/` 的 359 个 Python 代码块中有 100 个无法独立编译，均为「类方法摘录」「签名 `...` 占位」「函数签名原文」三类文档体裁，**不是事实错误也不是本次修复的回归**；已在 `references/README.md` 与 `SKILL.md` §11 加全局说明。若要整体改成可编译片段，属于独立的大规模文档重构。
