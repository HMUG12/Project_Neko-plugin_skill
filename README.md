# N.E.K.O 插件开发 Skill · neko-plugin-dev(4.1.0plus)
<img width="1024" height="1024" alt="20260912123440-c080be1e-2be8996c" src="https://github.com/user-attachments/assets/399b3757-1632-4c1c-b20d-1aac1c84430b" />



> 一套面向 [N.E.K.O](https://github.com) 插件开发的 Skill 辅助，由 Agent 辅助，从搭建到避坑上线，全流程覆盖，推荐使用最新技能哦。

[![Version](https://img.shields.io/badge/version-neko--plugin--dev(4.1.0)-blueviolet.svg)](CHANGELOG)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![N.E.K.O SDK](https://img.shields.io/badge/N.E.K.O_SDK-0.1.x-blue.svg)]()
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)]()
[![TSX](https://img.shields.io/badge/TSX-React_18-61dafb.svg)]()

## 已验证目标版本（先看这里）

| 项目 | 值 |
|------|----|
| 目标 SDK 约束 | `recommended = ">=0.1.0,<0.2.0"`，`supported = ">=0.1.0,<0.3.0"` |
| 官方文档核对日期 | 2026-09-12（[Quick Start](https://project-neko.online/plugins/quick-start) · [Plugin Config](https://project-neko.online/plugins/plugin-toml) · [SDK 迁移清单](https://project-neko.online/plugins/migration-v0.9)） |
| 运行验证状态 | **未在干净环境跑通端到端示例**。本文档的“已核实”仅指与上述官方文档逐条对照，**不等于**已在本机 SDK 上运行通过 |

> ⚠️ 只有本表对齐的 SDK 版本区间内结论才可靠。官方文档仍可能继续变化；每次主 SDK 变更后请重跑 `uv run neko-plugin check <id> --strict` 与示例验证，并更新本表与核对日期。凡是文中未标注“已验证”的代码片段，一律视为**示意**，上手前先在目标 SDK 上验证。

***

**注意：skill仅为辅助开发，调试，快速检测您Neko插件作用，并非为大规模生产低质，无效插件而使用，需要一定的编程基础和耐心。**

## 这是什么

本仓库是一个 **TRAE Skill**（技能包），用于在 TRAE 等 AI IDE 中协助开发 N.E.K.O 插件。当你在对话中提到「N.E.K.O 插件」「plugin.toml」「@plugin\_entry」等关键词，AI 会自动加载本技能，按既定规范给你写代码、查 bug、做重构。

**底层是 4 个实战插件 + 主程序逆向 + 插件市场 31 个已上架插件逆向**：

- `file_manager` — 文件管理插件（基础架构、权限、撤销、日志、数据库）
- `ai_singer` — 智能演唱插件（云端 API、多面板、富 UI、流式输出、音频管线）
- `music_pusher` — 音乐推送插件（@llm_tool、PluginRouter、跨插件通信）
- `qq_auto_reply` — QQ 自动回复插件（外部协议、消息积压、并发竞态）
- **N.E.K.O-main 主程序深度逆向** — 10 篇基础设施层内部机制（29–38）
- **插件市场 31 个已上架插件源码逆向** — 六类成功插件范式（50）

所有规则、模板、陷阱都来自这些项目、主程序源码与真实市场插件的实战复盘，不是纸上谈兵。

## 能帮你做什么

- 搭建一个可运行的 N.E.K.O 插件示例（5 分钟快速起步）
- 写出符合 SDK 规范的 Python 后端（双装饰器、`@llm_tool`、`PluginRouter`、`report_status`、`data_path`）、TSX 前端（`Slider`/`Select`/`StatusBadge`/`ActionForm`/`api.call`）、i18n 翻译
- 给 `@plugin_entry` / `@llm_tool` 设计「AI 友好」的 description 和错误消息
- 排查 **45 个**已知致命陷阱（BOM、目录大小写、`executemany`、启动超时、`__pycache__` 缓存、…）
- 对接云端 API（阿里云百炼、OpenAI 等）— 第三方 SDK 惰性导入 + 错误缓存、健康检查
- 设计多面板架构、PluginRouter 模块化拆分大型插件、@llm_tool LLM 工具注册
- 处理音频/多媒体管线（纯 Python WAV 合并、Viseme 口型同步、双轨播放）
- 排查 `N.E.K.O` 主程序层面的疑难问题（ZMQ 通信、Bus 总线、生命周期、配置漂移）
- 错误处理、并发竞态、跨插件通信、消息积压管理、WebSocket 重连



## 仓库结构

```
Project_Neko-plugin_skill/
├── README.md                              ← 你正在看的文件
├── CHANGELOG.md                           ← 版本变更日志
├── LICENSE                                ← MIT 协议
└── neko-plugin-dev(4.1.0)/                 ← neko-plugin-dev(4.1.0) 技能包本体
    ├── SKILL.md                           ← 技能入口（TRAE 加载这个文件）
    ├── examples/                          ← 示例插件（尚未跑通端到端验证，见 examples/README.md）⭐
    │   └── web_assistant/                 ← plugin.toml + __init__.py + routers/ + ui/ + config.example.toml + .gitignore
    └── references/                        ← 51 篇专题参考文档（含 00 可选工作流 + 39 官方指南 + 40–50 融合/逆向篇）
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
        │ ── 融合外部最佳实践（10 篇）── ⭐ neko-plugin-dev(4.1.0) 新增
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
        └── 50-market-plugin-reverse-engineering.md ← 31 已上架插件六类范式
```

***

## 快速开始

### 1. 在 TRAE 中安装本技能

把整个 `neko-plugin-dev(4.1.0)/` 文件夹复制到你的 TRAE 技能目录：

```powershell
# Windows: 复制到 TRAE 全局技能目录
Copy-Item -Path ".\neko-plugin-dev(4.1.0)" -Destination "$env:USERPROFILE\.trae\skills\neko-plugin-dev" -Recurse -Force
```

> 💡 复制到 TRAE 时建议去掉 `(4.1.0)` 后缀，避免路径中的特殊字符（括号与英文句点）；重命名后不影响技能加载。

或直接在 TRAE 的「技能管理」里点「从本地文件夹导入」，选择 `neko-plugin-dev(4.1.0)` 文件夹即可。

### 2. 让 AI 加载技能

新建会话后，对 AI 说一句：

> 「我要开发一个 N.E.K.O 插件，请帮我构建框架」

AI 会自动识别并加载 `neko-plugin-dev` 技能，后续对话都会按规范回答。

### 3. 按文档顺序开发

```
plugin.toml  →  __init__.py  →  ui/  →  i18n/  →  docs/  →  测试  →  部署
```

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

### 场景 G：排查主程序级问题（V2.0）

```
你：我的 push_message 推送大图片失败了。
AI：铁律 #18 触发！大文件 base64 体积膨胀 33% 超 ZMQ 上限。详见 30-push-message-internals.md + 37-zmq-transport-internals.md…
```

### 场景 H：上线前检查

```
你：我要发版了，帮我过一遍清单。
AI：（加载 12-master-checklist）按 9 大类 80+ 项逐一过…
```

***

## 运行与部署（三种场景，默认走官方开发模式）

官方推荐**不要**把源码手工复制进用户插件目录。按你的情况选：

| 场景 | 代码从哪加载 | 改完怎么生效 |
|------|-------------|-------------|
| **A. 源码树开发（推荐）** | `N.E.K.O/plugin/plugins/<id>/`，N.E.K.O 直接扫描该目录 | `uv run neko-plugin check <id> --strict` → 插件详情页 **Reload**；改依赖后重启该插件 |
| **B. 开发者模式 Load unpacked** | 就地注册的源码绝对路径目录（文件夹名须与 entry 包名和 plugin.id 一致） | 编辑源码 → **Reload**；改依赖 → 重启插件 |
| **C. 已安装包 / 手工同步** | 安装目录代码只读；配置/数据/缓存始终在用户数据目录 | 交付：`uv run neko-plugin build <id> --out <id>.neko-plugin` 再导入；仅在手工覆盖已安装目录时才需要删目标 `__pycache__/` |

```bash
# 官方标准循环（源码树场景）
uv run neko-plugin init my_plugin --type plugin --name "My Plugin"
uv run neko-plugin check my_plugin --strict        # 先过静态检查
uv run python launcher.py                           # 启动源码版 N.E.K.O → Plugins 页启动/Reload/触发入口
```

> ⚠️ `neko-plugin check` 通过 **不等于** 运行通过；打包成功也 ≠ 功能测试通过。示例插件本身也需在目标 SDK 上实际加载、调用、打开 UI 后才能称“可运行”。
>
> 用户运行时配置位于用户数据目录（Windows 为 `%LOCALAPPDATA%\N.E.K.O\plugins\<id>\config\plugin.toml`），**不要**把密钥写进源码 manifest 并提交。

详见 [06-deployment.md](neko-plugin-dev(4.1.0)/references/06-deployment.md) 和 [17-pyc-cache-trap.md](neko-plugin-dev(4.1.0)/references/17-pyc-cache-trap.md)。

***

## neko-plugin-dev(4.1.0) 更新日志

> 在 V2.0 基础上的「融合增强版」，主题 38 → 51。

### 主题扩展 38 → 51

- 🆕 可选工作流 00：融合用户「AI 开发协作协调器」skill，五阶段工作流 + 最小状态持久化（大型新插件按需启用，**非强制前置**）
- 🆕 融合外部最佳实践 10 篇（40–49）：工程纪律、反 AI 味 UI、网页集成、安全加固、本地逆向、融合速查、持久记忆、LLM 路由、压缩脱敏、陪伴状态机
- 🆕 实战篇·七 1 篇（50）：**插件市场 31 个已上架插件源码逆向**，六类成功插件范式（系统自动化 / 邮件 / 搜索 / 教育 OCR / 游戏控制 / 外部程序桥接）⭐

### 融合核心规则 20 → 20 + F1–F9

在 20 条铁律之上新增 **9 条融合核心规则（F1–F9）**：
- F1–F8：多轮对齐、YAGNI、UI 简洁、上下文审计、配置最小化、错误信息友好、推送克制、外发压缩脱敏
- **F9（新增）**：写复杂插件先抄真实市场骨架（系统自动化用三合一装饰器+窗口锁定+轮询；游戏用独立 data 进程+状态机；外部程序用 HTTP 桥+退避；教育用按功能域拆分 entry）

### 新增 examples/ 示例插件（尚未跑通端到端验证）

- 融合 40–45 的示例插件骨架，可扩展 46–50，演示最佳实践落地；上手前先 `uv run neko-plugin check web_assistant --strict` 并在目标 SDK 上加载验证

### 文档导航 & 结构

- references/README.md 新增交叉引用表 + 50 号导航
- SKILL.md 参考文档扩展为 51 篇，新增「实战篇·七」

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
- 15–17：惰性导入、跨插件、on_init
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
- 🆕 SKILL.md description 更新：`report_status` / `data_path` / 双装饰器、`Slider` / `Select` / `StatusBadge` / `ActionForm` / `api.call`
- 🆕 陷阱库从 17 扩到 21
- 🆕 references 目录加入「实战篇」分类
- 🆕 references/README.md 加入云 API / 多面板 / 自定义 UI 的交叉引用


## 发布前检查（维护者）

改完文档或示例准备发版时，逐项过：

- [ ] **Markdown 本地链接**可解析（相对路径存在、锚点存在），无指向已删除文件。
- [ ] **README 与 SKILL.md 的「铁律」逐条一致**（编号、措辞、方向不得相反）；references/README.md 同步。
- [ ] **示例可加载性**：`examples/web_assistant/` 的 `plugin.toml` 有 `[[plugin.ui.panel]].entry` 且该文件存在、`title` 字段正确；依赖已声明。
- [ ] **敏感字段检查**：全仓无真实 API Key/Token；示例配置只留空值或 `config.example.toml` 占位。
- [ ] **运行记录**：至少记录一次在目标 SDK 上的 `neko-plugin check <id> --strict` 输出，以及加载/调用入口/打开 UI/Reload 的结果（通过 or 失败原因）。
- [ ] **版本与日期**：更新首页「已验证目标版本」表的核对日期；`CHANGELOG.md` 路径与当前版本目录名一致。

***

本技能基于实战持续迭代，欢迎提 Issue / PR：

- 发现新陷阱 → 补到 [07-gotchas.md](neko-plugin-dev(4.1.0)/references/07-gotchas.md)
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
