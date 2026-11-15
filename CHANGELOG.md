## 4.3.0 · 2026-11-15（单一口径 + 官方 init 生成物）

> 依据 GitHub [Issue #2](https://github.com/HMUG12/Project_Neko-plugin_skill/issues/2) 的增量复核清单与复核意见。通过 GitHub Contents API **只读查询**官方 `Project-N-E-K-O/N.E.K.O` main `acfbdbc` 逐条验证，**未克隆、未下载仓库**。

### 事实核对（全部只读查询后确认）
- `plugin/_types/plugin_types.py:8`：`PluginType = Literal["plugin", "adapter"]`；`docs/plugins/migration-v0.9.md:15` 明确 Extension 类型 / `[plugin.host]` / `plugin.sdk.extension` 已移除且无兼容路径；`schema.py:233` 的 `reject_removed_host_config` 会拒绝 `[plugin.host]`。
- `validate_cmd.py:200` 的 `_check_plugin_dependency_id_list` 要求 `[plugin].dependencies` 是插件 ID 字符串列表；`schema.py:229` 的 `List[PluginDependencySchema]` 是宿主运行时内部模型，不作为 manifest 写法依据。
- `plugin/core/zmq_transport.py:1-70`：4 条 PUSH/PULL 通道、7 个 channel tag（含 `msg_batch`）、下行 `pickle` / 上行 `ormsgpack` + per-host token、独立图片上行。
- `plugin/sdk/shared/core/context.py:463-487` 返回 `PushMessageResult`；`settings.py:588` 为 512 KiB；`docs/plugins/push-message.md` 给出 `reason` 枚举、`images.upload()` 与预算表；`docs/plugins/decorators.md:124` 是 `async def cleanup`，`:186` 说明 priority 只影响展示顺序。
- `plugin/neko_plugin_cli/templates/generator.py:20-26,174-176,803-861`：pinned `ruff==0.12.4` 与 `init` 生成的 `ruff.toml` / `verify.yml` / `release.yml` 模板；`precheck_cmd.py:7-9` 的三门禁。
- 官方 `plugin/plugins/lifekit/__init__.py:165,192,531`：`config.dump(timeout=...)` / `config.update({...})` / `config_change` 重读配置的公开写法。

### 主要改动
- **单一口径**：`SKILL.md`、`references/`（含索引与 20 条铁律）、`OTHER.md`、README、示例介绍全部删除 A/B 双口径与旧快照并列，只按官方 main 判定；旧快照信息压缩到 `REVIEW_FIXES.md` / `CHANGELOG.md` 存档，并在存档顶部声明「不参与规则判定」。
- **Extension 清除**：`SKILL.md` §1 改为两种包类型并移除 `plugin.sdk.extension`；`01` / `16` / `51` 篇删除 `extension` 类型的正面描述与 check 覆盖项。
- **重写三篇内部机制**：`30` 按 `PushMessageResult` / 512 KiB / `images.upload()` 整篇重写；`37` 按 4 通道 / 7 tag / ormsgpack 整篇重写；`31` 改为 6 个命名空间。
- **契约统一**：`13` / `16` / `28` 等篇的 `neko-plugin add` → `sync --clean`；`11` / `13` / `14` / `36` / `46` / `49` 的裸 `@ui.action` 补 `@plugin_entry`；全仓 `config_change` 签名统一为 `async def on_config_change(self, **_)`（9 处）；`46` / `49` / `39` 修 `store.get/set` 的 `Result` 与 `await`；删除 `02` / `18` / `11` 的 priority 自拟分档；`01` 模板把 `dependencies` 移进 `[plugin]` 段内。
- **示例按官方 init 生成物重建**：把官方 `generator.py` / `plugin_types.py` / `source_paths.py` 只读取出并组成最小可运行包，**实际执行** `generate_plugin()` 与 `generate_repo_support_files()`（用官方支持的 `entry_point_override` 对齐示例类名）；`ruff.toml` / `verify.yml` / `release.yml` / `.gitignore` / `.vscode/*` / `test_smoke.py` 共 7 份产出与示例**字节一致**（sha256 见示例 README），旧的「挂进 N.E.K.O 树再 check -r」workflow 与旧式 `python -m plugin.neko_plugin_cli.cli ...` VS Code task 已废弃；`__init__.py` 的面板保存改为 `config.update()` 落盘并在 `startup` / `config_change` 用 `config.dump()` 读回，`config.example.toml` 改用 `[minimal_plugin]` 命名空间；`push_message` 判 `submitted` 回执；契约测试由 7 项扩到 10 项。
- **仓库介绍同步**：README / 徽章升至 4.3.0，新增 4.3.0 修订说明，`OTHER.md` 与 `n.e.k.o_plugin_example/README.md` 改单口径。
- **仓库自检 CI（关闭 [Issue #1](https://github.com/HMUG12/Project_Neko-plugin_skill/issues/1)）**：新增 `scripts/verify_skill.py`（纯标准库，7 项硬门禁：相对链接 / py·toml·json 语法 / SKILL.md frontmatter / 官方 init 生成物 sha256 / 示例必备文件 / 静态契约测试 / 旧口径残留报告）与 `.github/workflows/verify-skill.yml`（push / PR 跑自检 + pinned `ruff==0.12.4` 官方 CI 原命令 + `uvx pytest`）；根 `.gitignore` 白名单放行 `scripts/` 与 `.github/`。把「代码空间自动化规范几乎为 0」落成可执行门禁，而不是再写一篇说明。

### 本机真跑记录（4.3.0 收尾新增）
- 官方 CI 的 lint 原命令 `uvx ruff==0.12.4 check --ignore-noqa --isolated --no-respect-gitignore --target-version py311 --line-length 120 --select E4,E7,E9,F,I --exclude vendor .` → `All checks passed!`；本地 `--config ruff.toml` 入口同样通过。
- 真跑抓到并修掉 `routers/notes.py` 的 `I001`（import 顺序）；Issue #2 猜测的 `test_plugin_contract.py` import 顺序实际未命中。
- `uvx pytest -q`（不带 `-c`）首轮因插件根 `__init__.py` 且本机无 `plugin.sdk` 报 `ModuleNotFoundError`（官方 CI 把插件 checkout 进 N.E.K.O 源码树，那里有 SDK）；补 `tests/pytest.ini`（`--import-mode=importlib`）后，用 `uvx pytest -q -c tests/pytest.ini tests` 跑出 **11 passed**，静态契约测试在裸环境也可跑。
- 5 个 `.py` 全部 `compile` 通过；全仓相对链接 0 失效、py/toml/json 语法 0 失败；`SKILL.md` 468 行 / description 527 字符；规则区残留扫描 20 处命中均为「不要 await / 已废弃 / 不再并列旧快照」等反例或声明语境，无真实残留。
- 官方 `plugin-market-verify.yml` 已只读核对：用 `--isolated` ruff，再在 N.E.K.O 源码树内跑 `sync --clean` 与 `check -r`。

### 仍未实测
- 真实宿主中加载插件、打开面板保存、Reload，以及官方 main 的 `check` / `lint` / `precheck` / `publish` 门禁；`publish → GitHub Release → Market 上架` 全链路、Market 人工审核标准、`NEKO_PLUGIN_MARKET_SECURITY_CHECKS=1` 扫描行为。**本机没有官方 main 的完整源码树与 N.E.K.O 宿主**，4.1.1 在旧快照 CLI 上的 `check --strict`（0 error / 1 warning）不能当作官方 main 验证。`examples/minimal_plugin/README.md` 给出可复现清单，但本仓库不声称已跑通。

---

# 更新日志

本文件记录 N.E.K.O 插件开发 Skill 的所有版本变更。

---

## 4.2.0 · 2026-11-15（官方工作流对齐版）

> **只读查询**官方 `Project-N-E-K-O/N.E.K.O` main `acfbdbc`（2026-11-15），**未克隆、未下载仓库文件**。本版补齐构建方法、官方发布工作流、验证分层与 Market 审核，并纠正 4.1.1 的基线错误。

### 新增：官方构建 / 发布 / 审核
- 🆕 `neko-plugin-dev/references/51-build-publish-and-market-review.md`：`.neko-plugin` / `.neko-bundle` ZIP 包结构与 `build` 参数；`init → setup-repo / create-repo → check / lint / precheck → push → Verify CI → Market 首次审核 → Revision → publish → GitHub Release 三资产 → Market stable`；验证分层与 `check` 盲点；`market-evidence.json` 与 build provenance attestation；两版 CLI 对照表与检查清单。
- 🆕 `OTHER.md` 重写为投稿与上架全流程（首次审核 / Revision / publish 三模式 / beta / 撤回 / 常见失败）。
- `SKILL.md` §7 整段重写为双口径：两版 CLI 对照、构建方法、发布工作流、验证分层、审核与证据链、版本代差勘误；§0/§1/§2/§3/§5/§9/§10/§11 同步；454 行（<500），description 补齐发布/审核关键词。
- `references/README.md` 加 51 号索引与「官方构建/发布/审核篇」分组、铁律 #11/#18/#20 与快速排查项改为双口径；`12-master-checklist.md` 追加构建/验证/投稿审核清单；`05-testing.md`、`06-deployment.md` 头部指向 51 篇。

### 基线纠偏（重要）
- 4.1.1 的事实基准是工作区**本地旧快照**；官方 main 已演进到另一套 CLI 与 SDK。用旧快照否定新版事实导致 `REVIEW_FIXES.md §6`「未采纳清单」中多条结论**只对旧版成立**。
- 经官方 main 只读复核，下列条目**确实存在**：`push_message -> PushMessageResult`（`submitted` / `reason=payload_too_large`）、载荷上限 **512 KiB**（`plugin/settings.py:588`）、`await ctx.images.upload()`、`docs/plugins/push-message.md`、`ChatCard` / `create_card` / HTML chat cards、`bus.frames` 第 6 条总线、`[plugin.install]` / `[plugin.models]`（`schema.py:227-228`）、`publish` 顶层命令、`create-repo` 与 `setup-repo --upgrade-github-actions`。
- 逐篇纠偏：`30-push-message-internals.md` 新增 §0 版本代差；`31-bus-system-internals.md` 说明新版第六总线；`01-plugin-toml.md` 补 `[plugin.install]` / `[plugin.models]` 并说明新版已拒绝 `[plugin.host]`；`07-gotchas.md` #37 改为双口径。
- 官方新版**没有** `add` 命令（依赖写 `pyproject.toml` 后 `sync --clean`）、也没有 `init --no-interactive`；相关命令已从 `SKILL.md` / `OTHER.md` / `01` / `12` / `references/README.md` 更正。
- 仍然成立、不要写进文档的：`bus.emit()` / `get_recent()` / `union()`、`on_init` / `on_start` / `on_stop` 等虚构钩子、`[plugin.dependencies]` 内联表、`deps` / `release` 顶层子命令、ZMQ 是 PAIR/JSON。
- 完整勘误表见 `REVIEW_FIXES.md §9`。

### 仓库介绍同步（同日收尾）
- `README.md` 全面对齐 4.2.0：简介补构建 / 发布 / 验证 / 审核；事实依据改 A/B 双口径；能力清单补 4 条官方链路；结构图补 51 号专篇（现 52 篇）；快速开始补 `init → check / lint / precheck → build` 与两版 CLI 差异；安装说明删除已过时的 `(4.1.0)` 后缀提示；场景 G/H 改双口径与发布前门禁；部署表修 `build --out` → `-o` 并补 `publish` 段；发布前检查拆为「通用 / 4.2.0 追加 / 版本与日期」三组。
- `n.e.k.o_plugin_example/README.md`：`init-repo` 改为 A 版 `init` + `create-repo`（保留 B 版对照），补 lint / precheck / build 命令、Market 自动门禁与首次审核语义。
- GitHub 仓库 About 描述与 topics 同步到 4.2.0；按仓库既有命名补打 `v4.2.0` tag。

### 仍待验证
- 官方 `publish → GitHub Release → Market 上架` 全链路、`NEKO_PLUGIN_MARKET_SECURITY_CHECKS=1` 扫描行为、Market 人工审核标准**均未真机验证**（人工审核标准未在公开仓库披露）。
- 示例 `examples/minimal_plugin/` 的 `check --strict` 实测依据是**旧快照 CLI**；官方 main 新增的 `lint` / `precheck` / `publish` 门禁未跑。真实宿主加载与 Reload 仍未跑。

---

## 4.1.1 · 2026-11-15（深审修复版）

> 依据 N.E.K.O 主程序源码（`plugin/`、`docs/plugins/`、官方 `.agent/skills/neko-plugin/`）逐条核对后重写事实层。**未采纳**外部审查报告中若干与源码不符的说法（详见 `REVIEW_FIXES.md`）。

### 致命事实错误（A1–A6）
- **A1 依赖**：`[plugin].dependencies` 改为插件 ID 字符串列表（CLI 校验口径），Python 包走 `pyproject.toml [project].dependencies` + `neko-plugin add/sync` + `vendor/`；删除「自动安装」与内联表写法。涉及 `SKILL.md`、`01`、`07`、`12`、`13`、`16`、`28`、示例。
- **A2 定时器**：全文改 `async def`，删除 `new_event_loop()` 三步模板，07 的 #19 / #35 反向陷阱重写；涉及 `SKILL.md`、`02`、`07`、`10`、`12`、`24`、`32`、`39`、`46` 等。
- **A3 生命周期**：`29` 整篇按 6 个合法 id 重写，删除 `on_init` / `on_start` / `on_stop` / `on_unload`、`trigger_event`、`query_memory` 与 `self,,`。
- **A4 ZMQ**：`37` 整篇按源码改为 PUSH/PULL + `tcp://127.0.0.1:*` + pickle + channel tag，删除 PAIR / inproc / JSON / 12 种命令。
- **A5 push_message**：`30` 整篇重写为同步方法 + v2 `parts`；全仓去掉 `await` 与 `content=`；明确返回 `None`、无 `submitted` / `payload_too_large` 回执、载荷上限默认 256 KiB、`ctx.images.upload()` 不存在。
- **A6 UI action**：`SKILL.md` 完整模板、`03`、示例补 `@plugin_entry` 叠加，前端删除静默兜底按钮。

### 示例插件（B）
- `examples/web_assistant/` → `examples/minimal_plugin/`：零第三方依赖，Router 继承 `PluginRouter`，`@llm_tool` 回主类，设置面板可保存且错误不静默，补 `pyproject.toml` / `tests/` / `README.md`，修掉阻塞 I/O、非法配置崩溃、未用变量与提示注入风险。

### 一致性与覆盖（C / D / E / F）
- 统一 `config_change` kwargs、铁律 #3 `_ctx`、`store.get` 用 `unwrap_or`、禁止 `plugin.sdk.shared` 导入、`keywords` 正则语义。
- 补官方 CLI：`init / init-repo / setup-repo / add / sync / check --strict|--release|--market-release / build / install / inspect / verify`；无 `release` / `deps` 顶层子命令。
- 明确 `ChatCard`、`bus.frames`、manifest 的 `[plugin.install]` / `[plugin.models]` 均不存在；Bus 只有 5 个命名空间；`agent_hidden` / `needs_confirmation` / `clarify` / `deferred` 是宿主内部调度语义。
- 目录改名 `neko-plugin-dev(4.1.0)` → `neko-plugin-dev`；版本统一 4.1.1；修徽章链接、占位链接、死链、陷阱编号引用、`Slider` 宣传、杂文件白名单。
- `SKILL.md` 920 → 约 360 行，description 去掉「所有结论已核实」的夸大表述，新增按需加载分级与未验证声明。
- 安全：补明文 TOML 配置提示、外部 API 地址风险、抓取内容回灌 LLM 的提示注入缓解说明。

### 终验与收尾
- 清除反向扫描残留的**错误正面示例**：`16` 的旧 `[plugin.dependencies]` 迁移代码块、`24` §2.6 自相矛盾的定时器段落、`32` §11「完整插件模板」（`from nekog.sdk`、`self,,`、`@lifecycle("on_init")`、`store.get` 裸值、自建事件循环）、`31` / `33` 的 `@lifecycle("on_start")` 位置参数、`11` / `32` / `33` 的 `self,,` 与 `handler(, idx=i)` 语法错误。
- `references/README.md` 的 29 号索引、铁律 #11 / #17 / #18 与快速排查项按源码更正；`SKILL.md` §5 去掉 `push_message`「返回回执」的残留表述。
- 契约测试 `test_router_inherits_plugin_router` 改为只禁止真正的装饰器用法，注释里提及 `@llm_tool` 不再误报。
- 静态终验：相对链接 0 失效、SKILL.md 360 行 / description 352 字符、4 个 py 与 3 个 toml 全通过、契约测试 7/7。逐条结果见 `REVIEW_FIXES.md` §7。
- 补「代码块是摘录片段」的全局说明（`references/README.md`、`SKILL.md` §11），避免把方法片段当成可独立运行的模块。
- 已推送上游：单 commit `11b2bde` 更新 `main`，一次完成目录改名与旧示例删除；远端 71 个文件与本地逐条校验一致。本地已初始化 git 工作副本并跟踪 `origin/main`，`http.version=HTTP/1.1` 修复代理下的 git 握手失败。
- 官方 CLI 实测：`uv run --no-project` 隔离环境调用 `neko-plugin check --strict`，首轮 4 error / 4 warning；按官方 `setup-repo --github-actions` 补齐 `test_smoke.py` / `.vscode/*` / `.github/workflows/*`，并加 `[plugin.sdk]` 区间表与 `.gitignore` 规则后复验为 **0 error / 1 warning（exit 0）**。唯一 warning 是「示例不是独立插件仓库」，属设计使然。

### 仍待验证
- `check --strict` 已通过，但**真实宿主加载与 Reload 未跑**（原表述 `init → check → Reload` 全链路未验证）；`42` 的 firecrawl API、`41` 的 `Input type="range"`、`50` 的 file:line 出处仍未核实，已在文档标注。

---

## neko-plugin-dev (V4.1.0) · 2026-09-12

> 文档准确性修复版：对照官方开发者文档（Quick Start / Plugin Config / SDK 迁移清单）逐条核对，修正与当前 SDK 不符的接口、部署流程与安全表述，并同步 README / SKILL / references 一致性。

### 修复（准确性与一致性）

- 🔄 **Bus 定性纠正** — `31-bus-system-internals.md` 由"事件总线/pub-sub"重写为"只读/订阅门面"；移除 `get_recent()` / `reload()` / `union()/intersect()/difference()`，改为官方可重放链 `get().filter(field=value).sort(by=).limit()`；`memory` 更正为只读、有界、短 TTL 快照。
- 🔄 **部署流程重写** — `06-deployment.md` / `17-pyc-cache-trap.md` 区分「源码树开发 / Load unpacked / 已安装包」三场景，默认走官方 **Reload**；删除无预览的 `robocopy /MIR` 常规用法；清 `__pycache__` 降级为"行为不更新"的诊断分支。
- 🔄 **安全表述修正** — `43-security-hardening.md` 将 SSRF 代码重命名为"URL 输入预筛选"并标注边界；区分源码 manifest 与用户运行时配置的密钥来源。
- 🔄 **脱敏声明修正** — `48-prompt-compression-pii-redaction.md` 补 API Key 正则、撤销"绝不外泄"绝对化承诺、新增覆盖面声明。
- 🔄 **铁律对齐** — README / SKILL.md / references/README.md 20 条铁律逐条一致（#1 三处命名、#5 timeout 可配、#7 优先 Reload、#12 标注未本机验证、#20 可重放链）。
- 🔄 **协调器收缩** — `00-development-coordinator.md` 由"最高优先级强制工作流"改为"大型新插件可选工作流"，新增状态文件脱敏/`.gitignore`/删除规则。
- 🔄 **示例与结构** — `examples/minimal_plugin/` 补 `config.example.toml` 与 `.gitignore`；README 结构补 `examples/`；安装提示 `4.0.0` → `4.1.0`；首页新增「已验证目标版本」与「发布前检查」。
- 🔄 **CHANGELOG 路径** — 历史条目链接由 `neko-plugin-dev(4.0.0)/` 更新为 `neko-plugin-dev/`。

---

## neko-plugin-dev (V4.0.0) · 2026-08-19

> 二次融合：把 13 个外部开源 skill + 本地 `plugins/` 真实代码的方法论沉淀为 10 篇「融合篇」（40–49）+ **插件市场 31 个已上架插件源码逆向**（50），并附 1 个示例插件骨架（examples/minimal_plugin，当时尚未跑通端到端验证）。主题 38 → 51。

### 新增（市场插件逆向 · 50）⭐ 最新增补

- 📄 [50-market-plugin-reverse-engineering.md](neko-plugin-dev/references/50-market-plugin-reverse-engineering.md) — 从 `https://market.project-neko.cn/api/v1/plugins` 爬取全部 31 个已上架插件的 GitHub 源码（仓库已克隆至 `_crawled_repos/`），逆向提炼**六类成功插件范式**：系统自动化 / 邮件 / 搜索 / 教育 OCR / 游戏控制 / 外部程序桥接
- 🔄 **SKILL.md 新增 F9 融合核心规则** — "写复杂插件先抄真实市场骨架"（系统自动化用三合一装饰器+窗口锁定+轮询；游戏用独立 data 进程+状态机；外部程序用 HTTP 桥+退避；教育用按功能域拆分 entry）
- 🔄 **SKILL.md 新增「实战篇·七」** — 参考文档 51 篇、主题 01–50、F1–F9
- 🔄 **references/README.md / README.md** — 导航表、结构树、版本表新增 50 行 + 实战篇·七 + 交叉引用

### 新增（统领工作流 · 00 · 最高优先级）⭐ 增补

- 📄 [00-development-coordinator.md](neko-plugin-dev/references/00-development-coordinator.md) — 融合用户「AI 开发协作协调器」skill（v1.0.0, MIT）：五阶段工作流（需求澄清→方案规划→约束生成→任务拆解→编码实现）+ 状态持久化（`.skill对话构建缓存/`）+ 错误回滚 + 7 条元规则；适配本技能——每阶段挂接 01–50、RULES.md 默认注入 20 铁律 + F1–F9。
- 🔄 **SKILL.md 新增 P0 最高优先级规则** — 用户说"开发插件/启动开发协作"时先跑 00 五阶段工作流，再查 01–50；description / intro / 参考表同步声明 00 为统领层并置顶。
- 🔄 **主题 49 → 51**（+1 统领篇 00 +1 市场逆向 50，优先级 00 最高）
- 🔄 **references/README.md / README.md** — 导航表、结构树、版本表新增 00 行（最高优先级）

### 新增（10 篇融合 references · 40–49）

#### 融合外部最佳实践（第一批 · 6 篇）
- 📄 [40-engineering-discipline.md](neko-plugin-dev/references/40-engineering-discipline.md) — 工程纪律：TDD、深模块、两轴审查、诊断循环 + ponytail 的 YAGNI 阶梯反过度工程
- 📄 [41-ui-design-quality.md](neko-plugin-dev/references/41-ui-design-quality.md) — 反"AI 味"UI：impeccable + hallmark 确定性规则映射到 `@neko/plugin-ui` 受限组件
- 📄 [42-web-data-integration.md](neko-plugin-dev/references/42-web-data-integration.md) — firecrawl 网页数据集成封装为 `@llm_tool`/`@plugin_entry` 深模块
- 📄 [43-security-hardening.md](neko-plugin-dev/references/43-security-hardening.md) — strix 攻击者视角：最小权限/密钥/SSRF/注入/路径穿越/提示注入
- 📄 [44-local-plugin-architecture.md](neko-plugin-dev/references/44-local-plugin-architecture.md) — 逆向本地 `plugins/`：三种拆分范式 + 真实生命周期/配置/工具注册写法
- 📄 [45-fusion-quick-reference.md](neko-plugin-dev/references/45-fusion-quick-reference.md) — 40–44 压缩版：精髓五条 + 决策树 + 可抄片段

#### 融合外部最佳实践（第二批 · 4 篇）⭐
- 📄 [46-memory-persistence-subconscious.md](neko-plugin-dev/references/46-memory-persistence-subconscious.md) — subconscious-skill：5 阶段记忆管道、3 类记忆、衰减/归档、whisper；映射到 store + `@timer_interval`
- 📄 [47-llm-routing-cost-optimization.md](neko-plugin-dev/references/47-llm-routing-cost-optimization.md) — NadirClaw + llm-router：复杂度路由、验证器级联、Jaccard 缓存、飞行中去重
- 📄 [48-prompt-compression-pii-redaction.md](neko-plugin-dev/references/48-prompt-compression-pii-redaction.md) — token-saviour + prompthakcer：4 层 token 模型、正则压缩、本地 PII 红挡
- 📄 [49-neko-companion-state-machine.md](neko-plugin-dev/references/49-neko-companion-state-machine.md) — neko-skill：好感度状态机/指令系统（已剔除越狱内容）

### 新增（可运行示例插件）
- 📁 [examples/minimal_plugin/](neko-plugin-dev/examples/minimal_plugin/) — 可抄示例骨架，整合 40–45 精髓（深函数/Router 拆分/URL 输入预筛选/@llm_tool/to_thread/反 AI 味 UI）

### 重大更新
- 🔄 **主题 38 → 51**（+13；含 1 篇官方指南 39 + 10 篇融合 40–49 + 1 篇市场逆向 50）
- 🔄 **SKILL.md 融合核心规则 F1–F9** — 写任何插件前先默念（YAGNI/深函数/UI 克制/外部调用防 SSRF/抄真实骨架/持久状态放 store/外部 LLM 先路由再缓存再去重/外发提示词先压缩再脱敏/**写复杂插件先抄真实市场骨架**）
- 🔄 **description 扩容** — 加入 13 个外部 skill + 本地逆向 + 市场 31 插件逆向说明
- 🔄 **references/README.md** — 融合表扩到 51 行 + 交叉引用新增 46–50
- 🔄 **技能包更名为 `neko-plugin-dev(4.0.0)`**（原 `neko-plugin-dev(V2.0)`）

### 影响统计
- 主题数：38 → **51**（+13）
- 铁律：20（不变）
- 融合核心规则：0 → **F1–F9**
- 陷阱数：45（不变）
- 融合外部 skill：0 → **13**
- 逆向插件源码：0 → **31**（市场已上架插件）
- 示例插件：0 → **1**
- references 专题文档：38 → **51**（+1 官方指南 +10 融合 +1 市场逆向）

---

## V2.0 · 2026-07-12

> 大版本升级：双插件 → 四插件 + 主程序逆向 主题 15 → 38 铁律 10 → 20 陷阱 21 → 45

### 新增（23 篇 references）

#### 实战篇·二（4 篇 · `ai_singer` V0.6 重构经验）

- 📄 [16-backend-simplification.md](neko-plugin-dev/references/16-backend-simplification.md) — 后端精简与迁移（双后端→单后端迁移策略、代码清理清单、配置漂移防范、向后兼容处理）
- 📄 [17-pyc-cache-trap.md](neko-plugin-dev/references/17-pyc-cache-trap.md) — `__pycache__` 缓存陷阱（代码改了但不生效的根本原因、日志诊断法、预防方案）
- 📄 [18-streaming-output.md](neko-plugin-dev/references/18-streaming-output.md) — 流式输出与进度推送（逐句处理循环、push_message/report_status、音频合并、viseme 口型同步）
- 📄 [19-llm-workflow-design.md](neko-plugin-dev/references/19-llm-workflow-design.md) — LLM 对话工作流设计（check_setup 前置检查、多入口编排、next_action 指导、description 三要素）

#### 实战篇·三（4 篇 · 原指南 + 第三方插件分析）

- 📄 [20-plugin-router.md](neko-plugin-dev/references/20-plugin-router.md) — PluginRouter 拆分大型插件（多入口点模块化、共享逻辑、Router 能力访问、前缀命名、完整示例）
- 📄 [21-llm-tool-registration.md](neko-plugin-dev/references/21-llm-tool-registration.md) — @llm_tool LLM 工具注册（装饰器详解、架构分层、错误返回、命令式 API、生命周期与时序、main_server 重启应对）
- 📄 [22-static-ui-plugin.md](neko-plugin-dev/references/22-static-ui-plugin.md) — 纯前端/Static UI 插件（RPC 通信机制、状态管理、后台轮询、文件上传、Three.js 3D 集成、音频可视化、Toast 系统）
- 📄 [23-external-protocol-integration.md](neko-plugin-dev/references/23-external-protocol-integration.md) — 外部协议集成与消息积压管理（OneBot/NapCat 连接、积压数据结构、回复概率控制、引导式安装、信任体系、WebSocket 重连）

#### 实战篇·四（5 篇 · 三插件深度逆向）

- 📄 [24-error-handling-patterns.md](neko-plugin-dev/references/24-error-handling-patterns.md) — 错误处理与诊断模式大全（惰性导入+错误缓存、多级关键字诊断、轮询重试、分层 UI 渲染、Ok/Err 分层返回、按钮防重复、Toast 通知、RPC 超时、错误码设计规范）
- 📄 [25-concurrency-race-conditions.md](neko-plugin-dev/references/25-concurrency-race-conditions.md) — 并发与竞态条件（锁外 I/O、冻结取消、防重入刷新、消息积压上限、请求去重、WebSocket 指数退避重连、回复概率控制）
- 📄 [26-backend-design-pattern.md](neko-plugin-dev/references/26-backend-design-pattern.md) — Backend 对象设计模式（惰性导入+错误缓存、配置传播与_log注入、健康检查多时机、同步/异步桥接、多后端共存、完整模板）
- 📄 [27-audio-processing-pipeline.md](neko-plugin-dev/references/27-audio-processing-pipeline.md) — 音频处理管线（纯 Python WAV 合并无 ffmpeg 依赖、Viseme 口型同步数据生成、时长估算三级回退、双轨播放架构、句间换气停顿算法）
- 📄 [28-inter-plugin-communication.md](neko-plugin-dev/references/28-inter-plugin-communication.md) — 插件间通信（call_entry 跨插件调用、依赖声明与检查、事件总线 pub/sub、共享数据模式、版本兼容回退、防御性调用）

#### 实战篇·五（5 篇 · 主程序逆向 · 框架层）

- 📄 [29-plugin-lifecycle-internals.md](neko-plugin-dev/references/29-plugin-lifecycle-internals.md) — 插件生命周期内部机制（7 阶段状态机、ZMQ 进程通信架构、load/init/start/run/stop/unload 全流程、子进程管理、常见生命周期陷阱）
- 📄 [30-push-message-internals.md](neko-plugin-dev/references/30-push-message-internals.md) — Push Message 深度解析（visibility/ai_behavior 两轴正交模型、Parts 结构详解、coalesce_key 消息合并、旧版→v2 迁移映射、UI Action 媒体播放、内部 base64 编码机制）
- 📄 [31-bus-system-internals.md](neko-plugin-dev/references/31-bus-system-internals.md) — Bus 总线系统深度解析（惰性查询容器 BusList、计划节点树 GetNode/FilterNode/SortNode、五条总线 messages/events/lifecycle/conversations/memory、Revision 追踪、Watch 变更订阅、集合操作 union/intersect/difference）
- 📄 [32-nekopluginbase-internals.md](neko-plugin-dev/references/32-nekopluginbase-internals.md) — NekoPluginBase 内部机制（双层继承 shared/sdk、构造函数全流程、Entry 收集、Router 绑定、SDK 上下文封装、LLM Tool 注册流程、Static UI、PluginStore/PluginDatabase/PluginStatePersistence）
- 📄 [33-pluginrouter-entry-internals.md](neko-plugin-dev/references/33-pluginrouter-entry-internals.md) — PluginRouter 与 Entry 系统（懒解析策略、动态 Entry 注册、before/after/around_entry 钩子、hook 系统、quick_action 快捷操作、Entry 分发全流程、装饰器叠加规则、闭包陷阱）

#### 实战篇·六（5 篇 · 主程序逆向 · 基础设施层）⭐

- 📄 [34-logger-system-internals.md](neko-plugin-dev/references/34-logger-system-internals.md) — Logger 日志系统内部机制（PluginLoggerAdapter 双风格兼容、loguru braces/stdlib % 格式、RobustLoggerConfig 落地、Root Bridge 第三方日志捕获、敏感信息脱敏、懒解析机制）
- 📄 [35-store-database-internals.md](neko-plugin-dev/references/35-store-database-internals.md) — PluginStore 与 PluginDatabase 内部机制（JSON 键值存储 vs SQLite 关系存储、全量加载/每次写入持久化、CRUD 完整模式、批量插入分批提交、PluginStatePersistence、data_path 私有目录、持久化策略选择决策树）
- 📄 [36-i18n-internals.md](neko-plugin-dev/references/36-i18n-internals.md) — i18n 国际化引擎内部机制（回退链：用户语言→默认语言→default→key、参数插值 str.format()、懒加载翻译文件、tr 函数在装饰器中的使用、命名规范与最佳实践）
- 📄 [37-zmq-transport-internals.md](neko-plugin-dev/references/37-zmq-transport-internals.md) — ZMQ 进程通信协议内部机制（4.1.1 已按源码重写：PUSH/PULL + tcp + pickle + channel tag；旧版 PAIR / JSON / 12 种命令描述已废弃）
- 📄 [38-config-system-internals.md](neko-plugin-dev/references/38-config-system-internals.md) — 插件配置系统内部机制（plugin.toml [settings] / self.config / self.store 三层关系、合并优先级、update_own_config 点号路径、配置漂移防范与迁移策略、DEFAULT_CONFIG 完整模板、config_change 钩子注意事项）

### 重大更新

- 🔄 **铁律 10 → 20** — 新增 11–20 涵盖：双装饰器顺序、`@llm_tool` keyword-only、Router prefix、惰性导入错误缓存、跨插件 `call_entry`、`on_init` 不调其他插件、大文件用 URL、Bus 惰性链式
- 🔄 **陷阱库 21 → 45** — 新增 24 个 V2.0 陷阱（pyc 缓存、双装饰器、@llm_tool 签名、Router ID 冲突、Bus 多次 reload、base64 超限、惰性导入无缓存…）
- 🔄 **实战案例 2 → 4 + 主程序逆向** — `music_pusher`（@llm_tool + Router）、`qq_auto_reply`（外部协议 + 并发）+ N.E.K.O-main 10 篇逆向
- 🔄 **SKILL.md description** — 加入 `@llm_tool` / `PluginRouter` 关键词
- 🔄 **快速排查清单 10 → 20 项** — 与铁律对应
- 🔄 **致命陷阱速查表 10 → 20 行** — 与铁律对应
- 🔄 **references/README.md 交叉引用表扩展** — 新增 20+ 行交叉引用（Router / @llm_tool / Static UI / 错误 / 并发 / Backend / 音频 / 跨插件 / 日志 / Store / i18n / ZMQ / Config / 生命周期 / Push / Bus / NekoPluginBase）

### 影响统计

- 主题数：15 → **38**（+23）
- 铁律：10 → **20**（+10）
- 陷阱数：21 → **45**（+24）
- 实战插件数：2 → **4 + 主程序逆向**
- 文档总数：16 → **40 文件**

---

## V1.01 · 2026-07-12

> 基于 `ai_singer` 插件实战，扩展技能深度

### 新增

- 📄 [13-cloud-api-integration.md](neko-plugin-dev/references/13-cloud-api-integration.md) — 云端 API 集成模式（阿里云百炼 SDK、端点配置、健康检查、轮询等待）
- 📄 [14-multi-panel-architecture.md](neko-plugin-dev/references/14-multi-panel-architecture.md) — 多面板架构设计（双面板 + 双 Context、配置共享、标签页）
- 📄 [15-rich-ui-components.md](neko-plugin-dev/references/15-rich-ui-components.md) — 富交互 UI 组件（自定义 LyricPlayer、ActionForm 高级用法、内联样式）

### 更新

- 🔄 SKILL.md description 扩展：`report_status` / `data_path` / 双装饰器、`Slider` / `Select` / `StatusBadge` / `ActionForm` / `api.call`
- 🔄 SKILL.md 来源说明：`file_manager` 单插件 → `file_manager` + `ai_singer` 双插件
- 🔄 陷阱库：17 → **21 个**（新增 4 个 V1.01 陷阱）
- 🔄 [references/README.md](neko-plugin-dev/references/README.md) 加入「实战篇」分类
- 🔄 references 交叉引用表新增 3 行（云 API / 多面板 / 自定义 UI）

### 影响

- 主题数：12 → **15**
- 实战插件数：1 → **2**
- 文档总数：13 → **16 文件**

---

## V1.00 · 2026-07-11

> 初版：基于 `file_manager` 实战

### 内容

- 📄 SKILL.md — 技能入口（10 条铁律 + 完整模板 + 17 陷阱）
- 📄 references/01–12 — 12 篇专题参考（基础 4 + 进阶 4 + 工程 4）
- 📄 references/README.md — 文档导航 + 交叉引用
- 📄 README.md — 仓库介绍

### 覆盖能力

- plugin.toml 完整配置
- Python 后端：装饰器、生命周期、数据库、模式速查
- TSX 设置面板 + i18n
- AI 友好设计 + 权限体系 + 性能优化
- 撤销 + 日志
- 单元测试 + 部署同步

### 主题数

12 · 陷阱 17 个 · 实战插件 1 个
