# N.E.K.O 插件开发 Skill

> 一套面向 [N.E.K.O](https://github.com) 插件开发的skil辅助，Agent编辅助，从程搭建到避坑上线，全流程覆盖。

[![Version](https://img.shields.io/badge/version-V2.0-blueviolet.svg)](CHANGELOG)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![N.E.K.O SDK](https://img.shields.io/badge/N.E.K.O_SDK-0.1.x-blue.svg)]()
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)]()
[![TSX](https://img.shields.io/badge/TSX-React_18-61dafb.svg)]()

***

**注意：skill仅为辅助开发，调试，快速检测您Neko插件作用，并非为大规模生产低质，无效插件而使用，需要一定的编程基础和耐心。**

## 这是什么

本仓库是一个 **TRAE Skill**（技能包），用于在 TRAE 等 AI IDE 中协助开发 N.E.K.O 桌面助手插件。当你在对话中提到「N.E.K.O 插件」「plugin.toml」「@plugin\_entry」等关键词，AI 会自动加载本技能，按既定规范给你写代码、查 bug、做重构。

**底层是 4 个实战插件 + 主程序逆向**：

- `file_manager` — 文件管理插件（基础架构、权限、撤销、日志、数据库）
- `ai_singer` — 智能演唱插件（云端 API、多面板、富 UI、流式输出、音频管线）
- `music_pusher` — 音乐推送插件（@llm_tool、PluginRouter、跨插件通信）
- `qq_auto_reply` — QQ 自动回复插件（外部协议、消息积压、并发竞态）
- **N.E.K.O-main 主程序深度逆向** — 10 篇基础设施层内部机制（29–38）

所有规则、模板、陷阱都来自这些项目和主程序源码的实战复盘，不是纸上谈兵。

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

## 版本

| 版本 | 插件案例 | 主题数 | 铁律 | 陷阱数 | 主要更新 |
|------|---------|--------|------|--------|---------|
| V1.00 | file\_manager | 12 | 10 | 17 | 初版：基础架构 + 权限 + 撤销 + 日志 |
| V1.01 | file\_manager + ai\_singer | 15 | 10 | 21 | +云端 API +多面板 +富 UI 组件 |
| **V2.0**（当前）| + music\_pusher + qq\_auto\_reply + **N.E.K.O-main 逆向** | **38** | **20** | **45** | +Router +@llm\_tool +Static UI +外部协议 +错误/并发模式 +主程序 10 篇内部机制 |

## 仓库结构

```
Project_Neko-plugin_skill/
├── README.md                              ← 你正在看的文件
├── CHANGELOG.md                           ← 版本变更日志
├── LICENSE                                ← MIT 协议
├── assets/                                ← 图片资源
│   └── banner.png                         ← README 顶部 banner
└── neko-plugin-dev(V2.0)/                 ← V2.0 技能包本体
    ├── SKILL.md                           ← 技能入口（TRAE 加载这个文件）
    └── references/                        ← 38 篇专题参考文档
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
        │ ── 实战篇·六（5 篇）── 基础设施层逆向 ⭐ V2.0 新增
        ├── 34-logger-system-internals.md
        ├── 35-store-database-internals.md
        ├── 36-i18n-internals.md
        ├── 37-zmq-transport-internals.md
        └── 38-config-system-internals.md
```

***

## 快速开始

### 1. 在 TRAE 中安装本技能

把整个 `neko-plugin-dev(V2.0)/` 文件夹复制到你的 TRAE 技能目录：

```powershell
# Windows: 复制到 TRAE 全局技能目录
Copy-Item -Path ".\neko-plugin-dev(V2.0)" -Destination "$env:USERPROFILE\.trae\skills\neko-plugin-dev" -Recurse -Force
```

> 💡 复制到 TRAE 时建议去掉 `(V2.0)` 后缀，避免路径中的特殊字符。

或直接在 TRAE 的「技能管理」里点「从本地文件夹导入」，选择 `neko-plugin-dev(V2.0)` 文件夹即可。

### 2. 让 AI 加载技能

新建会话后，对 AI 说一句：

> 「我要开发一个 N.E.K.O 插件，请帮我构建框架」

AI 会自动识别并加载 `neko-plugin-dev` 技能，后续对话都会按规范回答。

### 3. 按文档顺序开发

```
plugin.toml  →  __init__.py  →  ui/  →  i18n/  →  docs/  →  测试  →  部署
```

详细步骤见 [`neko-plugin-dev(V2.0)/references/README.md`](neko-plugin-dev(V2.0)/references/README.md) 的「从零搭建」章节。

***

## 核心铁律（务必先看）

> 完整版在 [`SKILL.md`](neko-plugin-dev(V2.0)/SKILL.md)，这里只列最致命的 20 条。

### 基础 10 条（V1.00 起）

1. **文件名全小写 + 下划线** — 目录名与 `plugin.toml` 的 `entry` 包名严格一致
2. **Python 文件无 BOM** — `UTF-8 without BOM`，否则 `SyntaxError`
3. **`_ctx=None`** — 所有 `@plugin_entry` 和 `@ui.action` 方法必须包含
4. **`**_`** — 所有 `@lifecycle` 方法必须包含
5. **启动 < 10 秒** — 耗时操作丢 `asyncio.create_task()` 后台执行
6. **无** **`executemany`** — 数据库批量操作必须逐行 `await session.execute()`
7. **手动同步 + 删 `__pycache__`** — 改完同步后**必须**删部署目录的 `__pycache__/`
8. **权限默认** **`false`** — 安全优先：总开关 + 逐操作授权
9. **AI 需要绝对路径** — 拒绝非绝对路径，错误消息引导 AI 先搜索
10. **磁盘 I/O 用** **`asyncio.to_thread`** — 不阻塞事件循环

### V2.0 新增 10 条

11. **`plugin.toml` dependencies 用内联表** — `openai = ">=1.0.0"` 而非列表格式
12. **`@plugin_entry` 在上，`@ui.action` 在下** — 双装饰器叠加时顺序不能反
13. **`@llm_tool` 用 `*,`** — 强制 keyword-only，避免位置参数错误
14. **Router 在 `__init__` 中注册** — `include_router` 必须在 `super().__init__` 之后
15. **第三方库惰性导入 + 错误缓存** — `ImportError` 后缓存失败，不重复重试
16. **跨插件用** **`call_entry`** — 不直接 import 其他插件类
17. **`on_init` 不调其他插件** — 跨插件调用放在 `on_start` 中
18. **`push_message` 大文件用 URL** — 大文件 base64 体积膨胀 33%
19. **Router entry 设 prefix** — 多 Router 用 prefix 避免 ID 冲突
20. **Bus 查询用惰性链式** — `filter().limit()` 而非多次 `reload()`

***

## 文档导航

### 基础篇（必读）

| #  | 文档                                                                       | 何时打开      |
| -- | ------------------------------------------------------------------------ | --------- |
| 01 | [plugin.toml 配置](neko-plugin-dev(V2.0)/references/01-plugin-toml.md)     | 新建插件、加配置项 |
| 02 | [Python 后端](neko-plugin-dev(V2.0)/references/02-python-plugin.md)        | 写核心逻辑     |
| 03 | [UI 设置面板](neko-plugin-dev(V2.0)/references/03-ui-settings.md)          | 做设置界面     |
| 04 | [i18n 国际化](neko-plugin-dev(V2.0)/references/04-i18n.md)                | 支持多语言     |

### 进阶篇（推荐）

| #  | 文档                                                                       | 何时打开                              |
| -- | ------------------------------------------------------------------------ | --------------------------------- |
| 08 | [AI 友好设计](neko-plugin-dev(V2.0)/references/08-ai-friendly-design.md)   | **每次写** **`@plugin_entry`** **前** |
| 09 | [权限体系](neko-plugin-dev(V2.0)/references/09-permission-system.md)       | 涉及读/写/删等危险操作                      |
| 10 | [性能优化](neko-plugin-dev(V2.0)/references/10-performance.md)             | 处理大量数据                            |
| 11 | [撤销与日志](neko-plugin-dev(V2.0)/references/11-undo-and-logging.md)       | 需要可撤销操作                           |
| 12 | [上线前总清单](neko-plugin-dev(V2.0)/references/12-master-checklist.md)     | **每次发版前必看**                       |

### 工程篇（流程）

| #  | 文档                                                                  | 何时打开        |
| -- | ------------------------------------------------------------------- | ----------- |
| 05 | [单元测试](neko-plugin-dev(V2.0)/references/05-testing.md)            | 开发完成时       |
| 06 | [部署同步](neko-plugin-dev(V2.0)/references/06-deployment.md)         | 每次修改后       |
| 07 | [踩坑大全](neko-plugin-dev(V2.0)/references/07-gotchas.md)            | 遇到 bug 时    |

### 实战篇·一（V1.01 · 基于 `ai_singer`）

| #  | 文档                                                                          | 何时打开                |
| -- | --------------------------------------------------------------------------- | ------------------- |
| 13 | [云端 API 集成](neko-plugin-dev(V2.0)/references/13-cloud-api-integration.md) | 对接云服务/第三方 API      |
| 14 | [多面板架构](neko-plugin-dev(V2.0)/references/14-multi-panel-architecture.md) | 功能复杂需要多面板/标签页      |
| 15 | [富交互 UI](neko-plugin-dev(V2.0)/references/15-rich-ui-components.md)       | 自定义组件、歌词同步、ActionForm |

### 实战篇·二（V2.0 · `ai_singer` V0.6 重构经验）

| #  | 文档                                                                          | 何时打开           |
| -- | --------------------------------------------------------------------------- | -------------- |
| 16 | [后端精简与迁移](neko-plugin-dev(V2.0)/references/16-backend-simplification.md) | 重构/移除旧后端      |
| 17 | [pyc 缓存陷阱](neko-plugin-dev(V2.0)/references/17-pyc-cache-trap.md)          | 部署后行为不变时      |
| 18 | [流式输出](neko-plugin-dev(V2.0)/references/18-streaming-output.md)           | 需要逐条输出进度      |
| 19 | [LLM 工作流设计](neko-plugin-dev(V2.0)/references/19-llm-workflow-design.md)   | 设计 AI 调用流程    |

### 实战篇·三（V2.0 · 原指南 + 第三方插件分析）

| #  | 文档                                                                                  | 何时打开                  |
| -- | ----------------------------------------------------------------------------------- | --------------------- |
| 20 | [PluginRouter 拆分](neko-plugin-dev(V2.0)/references/20-plugin-router.md)               | 插件超 300 行/5+ 入口       |
| 21 | [@llm_tool 注册](neko-plugin-dev(V2.0)/references/21-llm-tool-registration.md)        | 让 LLM 自动调用插件          |
| 22 | [纯前端插件](neko-plugin-dev(V2.0)/references/22-static-ui-plugin.md)                  | 3D/可视化/富媒体插件         |
| 23 | [外部协议集成](neko-plugin-dev(V2.0)/references/23-external-protocol-integration.md)   | OneBot/NapCat/QQ 等外部协议 |

### 实战篇·四（V2.0 · 三插件深度逆向）

| #  | 文档                                                                                | 何时打开                  |
| -- | --------------------------------------------------------------------------------- | --------------------- |
| 24 | [错误处理模式](neko-plugin-dev(V2.0)/references/24-error-handling-patterns.md)     | 写任何涉及错误的代码            |
| 25 | [并发与竞态](neko-plugin-dev(V2.0)/references/25-concurrency-race-conditions.md)    | 多入口/定时器/外部协议          |
| 26 | [Backend 设计](neko-plugin-dev(V2.0)/references/26-backend-design-pattern.md)      | 对接外部 API/服务           |
| 27 | [音频处理管线](neko-plugin-dev(V2.0)/references/27-audio-processing-pipeline.md)    | 处理音频/多媒体              |
| 28 | [插件间通信](neko-plugin-dev(V2.0)/references/28-inter-plugin-communication.md)     | 多插件协作联动               |

### 实战篇·五（V2.0 · 主程序逆向 — 框架层）

| #  | 文档                                                                                      | 何时打开              |
| -- | --------------------------------------------------------------------------------------- | ----------------- |
| 29 | [生命周期内部机制](neko-plugin-dev(V2.0)/references/29-plugin-lifecycle-internals.md)       | 排查启动/停止 bug       |
| 30 | [Push Message 深度解析](neko-plugin-dev(V2.0)/references/30-push-message-internals.md)     | 推送任何消息           |
| 31 | [Bus 总线系统](neko-plugin-dev(V2.0)/references/31-bus-system-internals.md)                | 查询消息/事件/记忆        |
| 32 | [NekoPluginBase 内部](neko-plugin-dev(V2.0)/references/32-nekopluginbase-internals.md)      | 深入理解插件基类          |
| 33 | [PluginRouter Entry 系统](neko-plugin-dev(V2.0)/references/33-pluginrouter-entry-internals.md) | 设计多模块插件          |

### 实战篇·六（V2.0 · 主程序逆向 — 基础设施层）⭐ 新增

| #  | 文档                                                                                  | 何时打开              |
| -- | ----------------------------------------------------------------------------------- | ----------------- |
| 34 | [Logger 日志系统](neko-plugin-dev(V2.0)/references/34-logger-system-internals.md)     | 排查日志不落地/格式问题    |
| 35 | [Store 与 Database](neko-plugin-dev(V2.0)/references/35-store-database-internals.md)  | 选择数据存储方案        |
| 36 | [i18n 引擎](neko-plugin-dev(V2.0)/references/36-i18n-internals.md)                    | 实现多语言支持          |
| 37 | [ZMQ 传输协议](neko-plugin-dev(V2.0)/references/37-zmq-transport-internals.md)         | 理解跨进程通信          |
| 38 | [配置系统](neko-plugin-dev(V2.0)/references/38-config-system-internals.md)             | 管理插件配置项         |

***

## 典型使用场景

### 场景 A：新建插件

```
你：我想要做一个 N.E.K.O 插件，功能是把指定文件夹里的图片按日期归档。
AI：（加载 neko-plugin-dev 技能）我先帮你建目录结构，再按 plugin.toml → __init__.py → UI → i18n 的顺序生成…
```

### 场景 B：调试 bug

```
你：我的插件启动报 PluginEntryDirectoryMismatch。
AI：这是铁律 #1 触发。检查 plugin.toml 的 entry 字段包名是否与目录名大小写完全一致…
```

### 场景 C：AI 调不通

```
你：AI 调用我的 search_files 入口老是路径错误。
AI：这是 AI 友好设计问题。entry 的 description 必须三要素齐全，且方法内要拒绝非绝对路径…
```

### 场景 D：代码改了不生效（V2.0）

```
你：我改了 __init__.py，但插件行为没变。
AI：铁律 #7 触发！除了同步文件，还要删除部署目录的 __pycache__/，详见 17-pyc-cache-trap.md…
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

## 部署到 N.E.K.O 的标准动作

工作区改完后，**必须**手动同步到 N.E.K.O 的运行目录并删除 `__pycache__/`：

```powershell
# 1. 把工作区文件覆盖到部署目录
$src = "e:\你的工作区\你的插件\*"
$dst = "$env:LOCALAPPDATA\N.E.K.O\plugins\你的插件\"
Copy-Item -Path $src -Destination $dst -Recurse -Force

# 2. ⚠️ 删除部署目录的 __pycache__/（铁律 #7）
Get-ChildItem -Path $dst -Recurse -Filter "__pycache__" -Directory | Remove-Item -Recurse -Force

# 3. 重启 N.E.K.O 让变更生效
```

详见 [06-deployment.md](neko-plugin-dev(V2.0)/references/06-deployment.md) 和 [17-pyc-cache-trap.md](neko-plugin-dev(V2.0)/references/17-pyc-cache-trap.md)。

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

***

## 贡献与反馈

本技能基于实战持续迭代，欢迎提 Issue / PR：

- 发现新陷阱 → 补到 [07-gotchas.md](neko-plugin-dev(V2.0)/references/07-gotchas.md)
- 新增设计模式 → 补到对应 references 文档
- 文档勘误 → 直接提 PR

## 协议

[MIT License](LICENSE) © 2026 Noda-Core 工作室 × 未知之致

***

<p align="center">
  <sub>由 Noda-Core 工作室 × 未知之致 用心打磨 ✨</sub>
</p>
