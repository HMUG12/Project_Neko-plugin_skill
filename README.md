# N.E.K.O 插件开发 Skill · neko-plugin-dev 4.3.0
<img width="1024" height="1024" alt="20260912123440-c080be1e-2be8996c" src="https://github.com/user-attachments/assets/399b3757-1632-4c1c-b20d-1aac1c84430b" />



> 一套面向 [N.E.K.O](https://project-neko.online) 插件开发的 Skill 辅助：从骨架搭建、SDK 契约、避坑排查，到**构建打包（`.neko-plugin` / `.neko-bundle`）、官方 `publish` 工作流、分层验证与 Market 首次审核**全流程覆盖。当前 4.3.0 已收拢为**官方 main 单一口径**，并按官方 `init` 模板重建示例支撑文件。

[![Version](https://img.shields.io/badge/version-4.3.0-blueviolet.svg)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![N.E.K.O SDK](https://img.shields.io/badge/N.E.K.O_SDK-0.1.x-blue.svg)]()
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)]()
[![TSX](https://img.shields.io/badge/TSX-React_18-61dafb.svg)]()

## 版本基线（先看这里 · 单一口径）

| 项目 | 值 |
|------|----|
| **唯一基线** | 官方 `Project-N-E-K-O/N.E.K.O` main `acfbdbc`，2026-11-15 **只读查询**（未克隆、未下载仓库）。`SKILL.md` 与 `00`–`51` 篇全部事实层以此为准；构建 / 发布 / 验证 / 审核见 [`51-build-publish-and-market-review.md`](neko-plugin-dev/references/51-build-publish-and-market-review.md) 与 [OTHER.md](OTHER.md) |
| 历史存档 | 4.1.1 / 4.2.0 的旧快照对照与勘误只保留在 [REVIEW_FIXES.md](REVIEW_FIXES.md) 与 [CHANGELOG.md](CHANGELOG.md)，**不参与当前规则判定，也不要据此写插件代码** |
| 运行验证状态 | **未在干净环境跑通端到端示例**：示例支撑文件已按官方 `init` 模板重建、静态契约测试 10/10 通过；真宿主加载 / 面板保存 / Reload 与 `lint` / `precheck` / `publish` 均未实测 |
| 目标 SDK 约束 | `recommended = ">=0.1.0,<0.2.0"`，`supported = ">=0.1.0,<0.3.0"`（`plugin.toml` 的 `[plugin.sdk]` 区间） |

> ⚠️ 官方文档仍可能继续变化；每次主 SDK 变更后请重跑 `uv run neko-plugin check <id> --strict` 与示例验证，并更新本表与核对日期。凡是文中未标注「已验证」的代码片段，一律视为**示意**，上手前先在目标 SDK 上验证。

***

**注意：skill仅为辅助开发，调试，快速检测您Neko插件作用，并非为大规模生产低质，无效插件而使用，需要一定的编程基础和耐心。**

## 这是什么

本仓库是一个 **Agent Skill 技能包**（`SKILL.md` 格式，适用于 TRAE、WorkBuddy 等支持该格式的 AI 编程工具）。当你在对话中提到「N.E.K.O 插件」「plugin.toml」「@plugin\_entry」等关键词，AI 会自动加载本技能，按既定规范给你写代码、查 bug、做重构。

**事实依据分两层**：

- **官方基线层**：`Project-N-E-K-O/N.E.K.O` main `acfbdbc`（2026-11-15 只读查询，**未克隆、未下载仓库**）的 CLI 源码、官方文档、CI workflow 与 Market 审核流程。构建 / 发布 / 验证 / 审核以 [51 篇](neko-plugin-dev/references/51-build-publish-and-market-review.md) 与 [OTHER.md](OTHER.md) 为准。
- **实战复盘层**（方法论，非 API 契约）：4 个实战插件 + 主程序逆向 + 插件市场 31 个已上架插件源码逆向：

- `file_manager` — 文件管理插件（基础架构、权限、撤销、日志、数据库）
- `ai_singer` — 智能演唱插件（云端 API、多面板、富 UI、流式输出、音频管线）
- `music_pusher` — 音乐推送插件（@llm_tool、PluginRouter、跨插件通信）
- `qq_auto_reply` — QQ 自动回复插件（外部协议、消息积压、并发竞态）
- **N.E.K.O-main 主程序深度逆向** — 10 篇基础设施层内部机制（29–38）
- **插件市场 31 个已上架插件源码逆向** — 六类成功插件范式（50）

所有规则、模板、陷阱都来自官方源码核对与实战复盘。凡官方源码与本仓库冲突，**一律以官方为准并回填**；核对时锁定具体 commit（本版 `acfbdbc`）。旧版修订记录见 `REVIEW_FIXES.md`，属历史存档。

## 能帮你做什么

- 搭建一个可运行的 N.E.K.O 插件示例（5 分钟快速起步）
- 写出符合 SDK 规范的 Python 后端（双装饰器、`@llm_tool`、`PluginRouter`、`report_status`、`data_path`）、TSX 前端（`Input`/`Select`/`StatCard`/`ActionButton`/`api.call`；官方组件库无 `Slider`）、i18n 翻译
- 给 `@plugin_entry` / `@llm_tool` 设计「AI 友好」的 description 和错误消息
- 排查 **45 个**已知致命陷阱（BOM、目录大小写、`executemany`、启动超时、`__pycache__` 缓存、…）
- 对接云端 API（阿里云百炼、OpenAI 等）— 第三方 SDK 惰性导入 + 错误缓存、健康检查
- 设计多面板架构、PluginRouter 模块化拆分大型插件、@llm_tool LLM 工具注册
- 处理音频/多媒体管线（纯 Python WAV 合并、Viseme 口型同步、双轨播放）
- 排查 `N.E.K.O` 主程序层面的疑难问题（ZMQ 通信、Bus 总线、生命周期、配置漂移）
- 错误处理、并发竞态、跨插件通信、消息积压管理、WebSocket 重连
- **按官方 CLI 生成骨架并走完发布链路**：`init → check / lint / precheck → create-repo → publish`（见 [OTHER.md](OTHER.md) 与 [51 篇](neko-plugin-dev/references/51-build-publish-and-market-review.md)）
- **构建可校验的发布包**：`.neko-plugin` / `.neko-bundle` 的 ZIP 结构、`payload/dependencies.toml`、`metadata.payload.hash`（载荷哈希）与 `check --release` 包检查
- **对齐分层验证与 CI 门禁**：`check` / `-s` / `-r` / `-r --market-release`、`lint` 的固定 ruff 规则、`precheck` 三门禁、Verify / Release workflow 与 `check` 的盲点
- **准备 Market 投稿与审核**：首次审核提交固定提交快照、Revision 修订、自动门禁（id / version / tag / origin / release.yml）、`market-evidence.json`（构建来源证据文件）三资产与证据签名链

> 前 9 条来自 SDK 契约与实战复盘，后 4 条来自官方 CLI / CI / Market 流程，均按同一份官方 main 基线。执行任何 CLI 命令前先 `uv run neko-plugin --help` 确认命令集。



## 仓库结构

```
Project_Neko-plugin_skill/
├── README.md                              ← 你正在看的文件
├── CHANGELOG.md                           ← 版本变更日志
├── LICENSE                                ← MIT 协议
├── OTHER.md                               ← 投稿与上架（官方 publish 工作流 + 审核）
├── n.e.k.o_plugin_example/README.md       ← 市场仓库命名示例说明
├── REVIEW_FIXES.md                        ← 深审问题修复对照表（历史存档）
├── scripts/verify_skill.py                ← 仓库自检：链接/语法/frontmatter/官方 init 哈希/契约测试
├── .github/workflows/verify-skill.yml     ← CI：自检 + pinned ruff 0.12.4 + 示例静态测试
└── neko-plugin-dev/                        ← 技能包本体（目录名与 SKILL.md 的 name 一致）
    ├── SKILL.md                           ← 技能入口（Agent 工具加载这个文件）
    ├── examples/                          ← 示例插件（尚未跑通端到端验证，见 examples/README.md）⭐
    │   └── minimal_plugin/                 ← 零第三方依赖的最小示例：plugin.toml + pyproject.toml + __init__.py + routers/ + ui/ + tests/
    └── references/                        ← 52 篇专题参考文档（00 可选工作流 + 01–39 基础/进阶/工程/实战/逆向 + 40–50 融合与市场逆向 + 51 官方构建/发布/审核）
        │
        │ ── 可选篇（1 篇 · 大型新插件按需启用）── ⭐
        ├── 00-development-coordinator.md   ← 五阶段工作流 + 最小状态持久化（可选，非强制前置）
        │
        │ ── 基础篇（4 篇）──
        ├── 01-plugin-toml.md
        ├── 02-python-plugin.md
        ├── 03-ui-settings.md
        ├── 04-i18n.md
        │
        │ ── 进阶篇（5 篇）──
        ├── 08-ai-friendly-design.md
        ├── 09-permission-system.md
        ├── 10-performance.md
        ├── 11-undo-and-logging.md
        ├── 12-master-checklist.md
        │
        │ ── 工程篇（3 篇）──
        ├── 05-testing.md
        ├── 06-deployment.md
        ├── 07-gotchas.md                  ← 45 个陷阱
        │
        │ ── 实战篇·一（3 篇）──
        ├── 13-cloud-api-integration.md
        ├── 14-multi-panel-architecture.md
        ├── 15-rich-ui-components.md
        │
        │ ── 实战篇·二（4 篇）──
        ├── 16-backend-simplification.md
        ├── 17-pyc-cache-trap.md
        ├── 18-streaming-output.md
        ├── 19-llm-workflow-design.md
        │
        │ ── 实战篇·三（4 篇）──
        ├── 20-plugin-router.md
        ├── 21-llm-tool-registration.md
        ├── 22-static-ui-plugin.md
        ├── 23-external-protocol-integration.md
        │
        │ ── 实战篇·四（5 篇）──
        ├── 24-error-handling-patterns.md
        ├── 25-concurrency-race-conditions.md
        ├── 26-backend-design-pattern.md
        ├── 27-audio-processing-pipeline.md
        ├── 28-inter-plugin-communication.md
        │
        │ ── 实战篇·五（5 篇）── 框架层逆向
        ├── 29-plugin-lifecycle-internals.md
        ├── 30-push-message-internals.md
        ├── 31-bus-system-internals.md
        ├── 32-nekopluginbase-internals.md
        ├── 33-pluginrouter-entry-internals.md
        │
        │ ── 实战篇·六（5 篇）── 基础设施层逆向 ⭐
        ├── 34-logger-system-internals.md
        ├── 35-store-database-internals.md
        ├── 36-i18n-internals.md
        ├── 37-zmq-transport-internals.md
        ├── 38-config-system-internals.md
        │
        │ ── 官方指南篇（1 篇）──
        ├── 39-official-plugin-dev-guide.md
        │
        │ ── 融合外部最佳实践（10 篇）── ⭐ neko-plugin-dev 新增
        ├── 40-engineering-discipline.md        ← 工程纪律 + YAGNI
        ├── 41-ui-design-quality.md             ← 反 AI 味 UI
        ├── 42-web-data-integration.md          ← firecrawl 网页集成
        ├── 43-security-hardening.md            ← strix 安全加固
        ├── 44-local-plugin-architecture.md     ← 本地 plugins/ 逆向
        ├── 45-fusion-quick-reference.md        ← 融合速查
        ├── 46-memory-persistence-subconscious.md   ← 持久记忆
        ├── 47-llm-routing-cost-optimization.md     ← LLM 路由/成本
        ├── 48-prompt-compression-pii-redaction.md  ← 压缩/脱敏
        ├── 49-neko-companion-state-machine.md      ← 陪伴状态机
        │
        │ ── 实战篇·七（1 篇）── 市场 31 插件逆向 ⭐
        ├── 50-market-plugin-reverse-engineering.md ← 31 已上架插件六类范式
        │
        │ ── 官方构建 / 发布 / 审核篇（1 篇 · 4.2.0 新增）── ⭐
        └── 51-build-publish-and-market-review.md  ← 包格式 + build；init→check/lint/precheck→publish；验证分层与 CI；Market 首次审核 / Revision / 证据链；官方命令集
```

***

## 快速开始

### 1. 在 Agent 工具中安装本技能

把整个 `neko-plugin-dev/` 文件夹复制到工具的技能目录（以 TRAE 为例）：

```powershell
# Windows: 复制到 TRAE 全局技能目录
Copy-Item -Path ".\neko-plugin-dev" -Destination "$env:USERPROFILE\.trae\skills\neko-plugin-dev" -Recurse -Force
```

> 💡 目录名已在 4.1.1 统一为 `neko-plugin-dev`（与 `SKILL.md` 的 `name` 一致），**无需再去掉 `(4.1.0)` 后缀**，路径中也不含括号与英文句点。

或直接在工具的「技能管理」里点「从本地文件夹导入」，选择 `neko-plugin-dev` 文件夹即可。

### 2. 让 AI 加载技能

新建会话后，对 AI 说一句：

> 「我要开发一个 N.E.K.O 插件，请帮我构建框架」

AI 会自动识别并加载 `neko-plugin-dev` 技能，后续对话都会按规范回答。

### 3. 按文档顺序开发

```
plugin.toml  →  __init__.py  →  ui/  →  i18n/  →  docs/  →  测试  →  部署
```

**若使用官方最新 CLI，开发期直接走脚手架与门禁**（A 版口径，命令集以 `uv run neko-plugin --help` 为准）：

```bash
uv run neko-plugin init <id> --type plugin --name "My Plugin"   # 生成含 .git/ / ruff.toml / tests/ / verify.yml / release.yml 的骨架
uv run neko-plugin check <id> --strict                          # 静态严格检查
uv run neko-plugin lint <id>                                    # 与 Market CI 相同的固定 ruff 规则
uv run neko-plugin precheck <id>                                # lint → sync --clean → check -r
uv run neko-plugin build <id> -o out/<id>.neko-plugin            # 构建可校验的发布包
```

完整发布链路、官方命令集与 Market 审核见 [51 篇](neko-plugin-dev/references/51-build-publish-and-market-review.md) 与 [OTHER.md](OTHER.md)。CLI 没有 `add` 顶层命令，Python 依赖写进 `pyproject.toml` 后 `sync <id> --clean`。

## 典型使用场景

### 场景 A：新建插件

```
你：我想要做一个 N.E.K.O 插件，功能是把指定文件夹里的图片按日期归档。
AI：（加载 neko-plugin-dev 技能）我先帮你建目录结构，再按 plugin.toml → __init__.py → UI → i18n 的顺序生成…
```

### 场景 B：调试 bug

```
你：我的插件启动报 PluginEntryDirectoryMismatch。
AI：这说明加载器/打包器没找到 entry 对应的包。先核对 plugin.toml 的 entry 包名、目录名、plugin.id 是否对齐
   （官方强烈建议三者一致；开发期旧发现机制可能容忍不一致，但打包与生产安装不允许）。
   再确认插件放在正确位置（源码树 plugin/plugins/ 或开发者模式注册的目录）…
```

### 场景 C：AI 调不通

```
你：AI 调用我的 search_files 入口老是路径错误。
AI：这是 AI 友好设计问题。entry 的 description 必须三要素齐全，且方法内要拒绝非绝对路径…
```

### 场景 D：代码改了不生效（V2.0）

```
你：我改了 __init__.py，但插件行为没变。
AI：先确认你是哪种开发方式（06 分三场景）：
   1) 源码树/开发者模式：点插件详情页 Reload（改动依赖后还需重启插件）；
   2) 手工复制到安装目录：确认源文件已覆盖，再删目标 __pycache__/ 作为诊断分支；
   3) 已安装包：重新构建并导入 .neko-plugin。
   清缓存是"行为不更新"的兜底诊断，不是常规必做项，详见 17-pyc-cache-trap.md…
```

### 场景 E：拆分大型插件（V2.0）

```
你：我的插件有 8 个入口，500 多行代码，乱得没法维护。
AI：参考 20-plugin-router.md 用 PluginRouter 拆分多模块，并设 prefix 避免 ID 冲突（铁律 #19）…
```

### 场景 F：让 LLM 自动调插件（V2.0）

```
你：我想让 LLM 能自己调用我的插件做 TTS。
AI：用 @llm_tool 装饰器，签名用 keyword-only（铁律 #13），详见 21-llm-tool-registration.md…
```

### 场景 G：排查主程序级问题

```
你：我的 push_message 推送大图片失败了。
AI：载荷上限是 MESSAGE_PLANE_PAYLOAD_MAX_BYTES = 512 KiB，超限时本地整条拒绝并返回
    PushMessageResult（submitted=False / reason=payload_too_large）；
    大图改走 await ctx.images.upload()（源 32 MiB / 归一化 8 MiB，失败抛 ValueError），
    不要把 base64 直接塞进 parts 硬推。submitted=True 只表示 SDK 本地提交路径已接管，
    不代表宿主消费或送达。详见 30 篇、07 #37、51 篇 §3…
```

### 场景 H：上线前检查

```
你：我要发版了，帮我过一遍清单。
AI：（加载 12-master-checklist + 51 篇 §6）先过构建 / 验证 / 投稿审核三块：
   check -r（含 payload hash）→ lint → precheck → 审核已通过（不只是已申请）
   → tag v<version> 与 plugin.toml.version 一致 → publish 完整跑到「Market 发布成功」…
```

***

## 运行与部署（三种场景，默认走官方开发模式）

官方推荐**不要**把源码手工复制进用户插件目录。按你的情况选：

| 场景 | 代码从哪加载 | 改完怎么生效 |
|------|-------------|-------------|
| **A. 源码树开发（推荐）** | `N.E.K.O/plugin/plugins/<id>/`，N.E.K.O 直接扫描该目录 | `uv run neko-plugin check <id> --strict` → 插件详情页 **Reload**；改依赖后重启该插件 |
| **B. 开发者模式 Load unpacked** | 就地注册的源码绝对路径目录（文件夹名须与 entry 包名和 plugin.id 一致） | 编辑源码 → **Reload**；改依赖 → 重启插件 |
| **C. 已安装包 / 手工同步** | 安装目录代码只读；配置/数据/缓存始终在用户数据目录 | 交付：`uv run neko-plugin build <id> -o out/<id>.neko-plugin` 后在插件中心「导入」（`install` 只是兼容命令，不直接写运行时目录）；仅在手工覆盖已安装目录时才需要删目标 `__pycache__/` |

```bash
# 标准循环（源码树场景）
uv run neko-plugin init my_plugin --type plugin --name "My Plugin"
uv run neko-plugin check my_plugin --strict        # 先过静态检查
uv run python launcher.py                           # 启动源码版 N.E.K.O → Plugins 页启动/Reload/触发入口
```

```bash
# 审核通过后发布可安装版本（在 N.E.K.O 源码根目录）
uv run neko-plugin precheck <id>
uv run neko-plugin publish <id>                     # 打 v<version> tag → GitHub Release 三资产 → 通知 Market
```

> 另有 `publish github <id>`（只建 Release）与 `publish market <github-release-url>`（补通知 Market）两种拆开执行的模式；完整链路见 [OTHER.md](OTHER.md) 与 [51 篇 §2](neko-plugin-dev/references/51-build-publish-and-market-review.md)。

> ⚠️ `neko-plugin check` 通过 **不等于** 运行通过；打包成功也 ≠ 功能测试通过。示例插件本身也需在目标 SDK 上实际加载、调用、打开 UI 后才能称“可运行”。
>
> 用户运行时配置位于用户数据目录（Windows 为 `%LOCALAPPDATA%\N.E.K.O\plugins\<id>\config\plugin.toml`），**不要**把密钥写进源码 manifest 并提交。

详见 [06-deployment.md](neko-plugin-dev/references/06-deployment.md) 和 [17-pyc-cache-trap.md](neko-plugin-dev/references/17-pyc-cache-trap.md)。

***

## 4.3.0 修订说明（单一口径 + 官方 init 生成物）

> 依据 GitHub [Issue #2](https://github.com/HMUG12/Project_Neko-plugin_skill/issues/2) 的增量复核与「只留官方 main 一个口径」的复核意见。通过 GitHub Contents API **只读查询**官方源码逐条验证，未克隆、未下载仓库。
>
> - **单一口径**：删除 `SKILL.md` / `references/` / 介绍文件里的 A/B 双口径与旧快照并列，全部只按官方 main `acfbdbc` 判定；旧快照信息压缩到 `REVIEW_FIXES.md` / `CHANGELOG.md` 存档，不参与规则判定。
> - **删除 Extension**：官方 `plugin/_types/plugin_types.py:8` 只有 `plugin | adapter`，`[plugin.host]` 被 `schema.py:233` 拒绝；全仓移除 `extension` 类型与 `plugin.sdk.extension` 的正面描述。
> - **重写内部机制篇**：`30` 按 `PushMessageResult` / 512 KiB / `images.upload()` 重写；`37` 按 4 条 PUSH/PULL 通道、7 个 tag、上行 ormsgpack + per-host token 重写；`31` 改为 6 个命名空间。
> - **统一契约**：全仓 `neko-plugin add` → `sync --clean`；裸 `@ui.action` 补 `@plugin_entry`；`config_change` 签名统一为 `async def on_config_change(self, **_)`；`store.get/set` 的 `Result` 与 `await` 修正；删除 priority 自拟分档；修正 `dependencies` 在 `plugin.toml` 模板中的位置。
> - **示例按官方 init 生成物重建**：实际执行官方 main `generator.py` 的 `generate_plugin()` / `generate_repo_support_files()`（即 `neko-plugin init` 的底层实现），`ruff.toml` / 两个 workflow / `.gitignore` / `.vscode/*` / `test_smoke.py` 共 7 份支撑文件与产出**字节一致**；面板保存改为 `config.update()` 落盘并在 `startup` / `config_change` 读回；静态契约测试扩到 10 项。
> - **本机真跑（新增证据）**：pinned `ruff==0.12.4` 两种入口（本地 `--config ruff.toml` 与官方 CI `--isolated` 原命令）均 `All checks passed!`，真跑修掉 `routers/notes.py` 的 `I001`；补 `tests/pytest.ini` 后 `uvx pytest -q -c tests/pytest.ini tests` **11 passed**；5 个 `.py` 编译通过；全仓链接 0 失效、语法 0 失败。
> - **真宿主验证清单**：`examples/minimal_plugin/README.md` 给出可复现的 `init → check/lint/precheck → 加载 → 保存 → Reload` 步骤；官方 main 的 `check` / `lint` / `precheck` / `publish` 与真实宿主加载仍**未跑**，本仓库**不声称**已跑通。4.1.1 在旧快照 CLI 上的 `check --strict` 结果不作为官方 main 验证。

## 4.2.0 修订说明（历史 · 官方工作流对齐版）

> 本版本**只读查询**官方 `Project-N-E-K-O/N.E.K.O` main（commit `acfbdbc`，2026-11-15），未克隆、未下载仓库文件。重点补齐四块：
>
> - **构建方法**：`.neko-plugin` / `.neko-bundle` ZIP 包格式、`build` 参数、`payload/dependencies.toml`、`metadata.payload.hash`、`install` 只是兼容命令。
> - **官方工作流**：`init → setup-repo / create-repo → check / lint / precheck → push → Verify CI → Market 首次审核 → Revision → publish → GitHub Release 三资产 → Market stable`。
> - **验证方式**：`check` / `-s` / `-r` / `-r --market-release` 分层、pinned ruff `0.12.4`、`precheck` 三门禁、CI `verify.yml` / `release.yml`、Hosted TSX 检查、`check` 的盲点。
> - **审核**：首次审核与 Revision 语义、自动门禁（id / version / tag / origin / release.yml / 工作区）、`market-evidence.json` 与 build provenance attestation 隔离链、Market 安全扫描限额。
>
> 同时**纠正 4.1.1 的基线错误**：上一轮以本地旧快照把 `submitted` 回执、512 KiB、`ctx.images.upload()`、`ChatCard`、`bus.frames`、`[plugin.install]` / `[plugin.models]`、`publish` 判成「报告误判」，这些在官方 main 中**真实存在**。当时按 A/B 双口径标注；4.3.0 已收拢为单一口径，见 `REVIEW_FIXES.md §9` 存档。

## 4.1.1 修订说明（历史）

> 本版本依据工作区本地 N.E.K.O 快照与 `docs/plugins/` 重写事实层：修正依赖声明、定时器、生命周期、ZMQ、push_message、UI action 六类致命错误，重建示例插件，统一版本与编号。其「未采纳清单」（`REVIEW_FIXES.md §6`）**只适用于旧快照**，已在 4.2.0 纠偏。详见 `REVIEW_FIXES.md` 与 `CHANGELOG.md`。

## 历史更新日志

> 以下为历史版本的当时记录，**不是当前状态**；当前为 4.3.0、52 篇专题（含 51 号官方构建 / 发布 / 审核篇）。在 V2.0 基础上的「融合增强版」当时把主题从 38 扩到 51。

### 主题扩展 38 → 51（当时）

- 🆕 可选工作流 00：融合用户「AI 开发协作协调器」skill，五阶段工作流 + 最小状态持久化（大型新插件按需启用，**非强制前置**）
- 🆕 融合外部最佳实践 10 篇（40–49）：工程纪律、反 AI 味 UI、网页集成、安全加固、本地逆向、融合速查、持久记忆、LLM 路由、压缩脱敏、陪伴状态机
- 🆕 实战篇·七 1 篇（50）：**插件市场 31 个已上架插件源码逆向**，六类成功插件范式（系统自动化 / 邮件 / 搜索 / 教育 OCR / 游戏控制 / 外部程序桥接）⭐

### 融合核心规则 20 → 20 + F1–F9

在 20 条铁律之上新增 **9 条融合核心规则（F1–F9）**：
- F1–F8：多轮对齐、YAGNI、UI 简洁、上下文审计、配置最小化、错误信息友好、推送克制、外发压缩脱敏
- **F9（新增）**：写复杂插件先抄真实市场骨架（系统自动化用三合一装饰器+窗口锁定+轮询；游戏用独立 data 进程+状态机；外部程序用 HTTP 桥+退避；教育用按功能域拆分 entry）

### 新增 examples/ 示例插件（尚未跑通端到端验证）

- 零第三方依赖的最小插件骨架 `examples/minimal_plugin/`；上手前先 `uv run neko-plugin check minimal_plugin --strict` 并在目标 SDK 上加载验证（42 号 firecrawl 抓取仅作方法论参考）

### 文档导航 & 结构

- references/README.md 新增交叉引用表 + 50 号导航
- SKILL.md 参考文档当时扩展为 51 篇，新增「实战篇·七」；4.2.0 再新增 51 号官方构建 / 发布 / 审核篇，现为 52 篇

***

## V2.0 更新日志

### 主题扩展 15 → 38

- 🆕 实战篇·二 4 篇（16–19）：`ai_singer` V0.6 重构经验（精简、pyc 陷阱、流式、LLM 工作流）
- 🆕 实战篇·三 4 篇（20–23）：原指南 + 第三方插件分析（Router、@llm_tool、Static UI、外部协议）
- 🆕 实战篇·四 5 篇（24–28）：三插件深度逆向（错误、并发、Backend、音频、跨插件）
- 🆕 实战篇·五 5 篇（29–33）：主程序逆向·框架层（生命周期、Push Message、Bus、NekoPluginBase、PluginRouter）
- 🆕 实战篇·六 5 篇（34–38）：主程序逆向·基础设施层（Logger、Store/DB、i18n、ZMQ、Config）⭐

### 铁律 10 → 20

新增 10 条（详见上方「核心铁律」V2.0 段）：
- 11–14：装饰器/Router 顺序
- 15–17：惰性导入、跨插件、启动期约束
- 18–20：消息大文件、Router prefix、Bus 链式

### 陷阱库 21 → 45

新增 24 个 V2.0 陷阱，覆盖 pyc 缓存、双装饰器顺序、@llm_tool 签名、Router ID 冲突、Bus 多次 reload、base64 超限、惰性导入无缓存等。

### 实战案例 2 → 4 + 主程序逆向

- `file_manager` — 文件管理（基础）
- `ai_singer` — 智能演唱（V0.6 重构）
- `music_pusher` — 音乐推送（PluginRouter + @llm_tool）
- `qq_auto_reply` — QQ 自动回复（外部协议 + 并发）
- **N.E.K.O-main 源码深度逆向** — 10 篇基础设施层内部机制（29–38）

### SKILL.md 描述扩展

`@llm_tool` / `PluginRouter` 关键词加入；description 更新反映 20 条铁律 + 45 个陷阱。

***

## V1.01 更新日志

- 🆕 新增 3 篇实战篇（13/14/15），覆盖云端 API、多面板、富 UI 组件
- 🆕 实战案例从单插件（`file_manager`）扩展到双插件（`file_manager` + `ai_singer`）
- 🆕 SKILL.md description 更新：`report_status` / `data_path` / 双装饰器、Hosted UI 组件表（当时误列 `Slider`，官方组件库无此组件，4.1.1 已修正）
- 🆕 陷阱库从 17 扩到 21
- 🆕 references 目录加入「实战篇」分类
- 🆕 references/README.md 加入云 API / 多面板 / 自定义 UI 的交叉引用


## 发布前检查（维护者）

改完文档或示例准备发版时，逐项过：

**通用**
- [ ] **Markdown 本地链接**可解析（相对路径存在、锚点存在），无指向已删除文件。
- [ ] **README 与 SKILL.md 的「铁律」逐条一致**（编号、措辞、方向不得相反）；`references/README.md` 同步。
- [ ] **示例可加载性**：`examples/minimal_plugin/` 的面板 id / context 与 `@ui.context` 一致，保存动作叠加了 `@plugin_entry`，Router 继承了 `PluginRouter`，依赖通道正确。
- [ ] **敏感字段检查**：全仓无真实 API Key/Token；示例配置只留空值或 `config.example.toml` 占位。
- [ ] **仓库自检与 CI**：`python scripts/verify_skill.py` 7 项硬门禁全通过；示例的 `uvx ruff==0.12.4 ...`（官方 CI 原命令）与 `uvx pytest -q -c tests/pytest.ini tests` 通过；`.github/workflows/verify-skill.yml` 在 push / PR 上是绿的。
- [ ] **运行记录**：至少记录一次在目标 SDK 上的 `neko-plugin check <id> --strict` 输出，以及加载/调用入口/打开 UI/Reload 的结果（通过 or 失败原因）。

**4.3.0 起追加（官方口径，见 [51 篇 §6](neko-plugin-dev/references/51-build-publish-and-market-review.md)）**
- [ ] 先用 `uv run neko-plugin --help` 确认命令集；全仓只按官方 main **单一口径**，旧快照内容只在 `REVIEW_FIXES.md` / `CHANGELOG.md` 存档中出现。
- [ ] `check -r <id>` 通过（含插件测试、包检查、`payload_hash_verified=True`）；`lint <id>` 与 `precheck <id>` 通过。
- [ ] 构建产物 `manifest.toml` / `metadata.toml` / `payload/` 齐全，`payload/dependencies.toml` 为自动生成未手改。
- [ ] Market 自动门禁：id 正则、`version` 长度、仓库名 `n.e.k.o_plugin_<id>`、`origin` 指向 GitHub、`.github/workflows/release.yml` 存在、工作区无未提交文件。
- [ ] 审核**已通过**（不只是已申请）；`publish` 完整跑到「Market 发布成功」，Release 三资产齐备。
- [ ] tag `v<version>` 与 `plugin.toml.version` 一致；版本说明已写入 `CHANGELOG.md`，首页「版本基线（单一口径）」表的核对日期与 commit 号已更新。

**版本与日期**
- [ ] 更新首页「版本基线（单一口径）」表的核对日期；`CHANGELOG.md` 路径与当前版本目录名一致，tag 与徽章版本号一致。

***

本技能基于实战持续迭代，欢迎提 Issue / PR：

- 发现新陷阱 → 补到 [07-gotchas.md](neko-plugin-dev/references/07-gotchas.md)
- 新增设计模式 → 补到对应 references 文档
- 文档勘误 → 直接提 PR


## 贡献
感谢星辰大佬对错误的指正
## 协议

[MIT License](LICENSE) © 2026  未知之致

***

<p align="center">
  <sub>由未知之致 用心打磨 ✨</sub>
</p>
