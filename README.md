# N.E.K.O 插件开发 Skill


> 一套面向 [N.E.K.O](https://github.com/Project-N-E-K-O/N.E.K.O) 插件开发的skil辅助，Agent编辅助，从程搭建到避坑上线，全流程覆盖。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![N.E.K.O SDK](https://img.shields.io/badge/N.E.K.O_SDK-0.1.x-blue.svg)]()
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)]()
[![TSX](https://img.shields.io/badge/TSX-React_18-61dafb.svg)]()

***

**注意：skill仅为辅助开发，调试，快速检测您Neko插件作用，并非为大规模生产低质，无效插件而使用，需要一定的编程基础和耐心。**

## 这是什么

本仓库是一个 **TRAE Skill**（技能包），用于在 TRAE 等 AI IDE 中协助开发 N.E.K.O 桌面助手插件。当你在对话中提到「N.E.K.O 插件」「plugin.toml」「@plugin\_entry」等关键词，AI 会自动加载本技能，按既定规范给你写代码、查 bug、做重构。

**底层是真实踩坑经验**：所有规则、模板、陷阱都来自 `file_manager` 插件的实战复盘，不是纸上谈兵。

## 能帮你做什么

- 搭建一个可运行的 N.E.K.O 插件示例（5 分钟快速起步）
- 写出符合 SDK 规范的 Python 后端、TSX 前端、i18n 翻译
- 给 `@plugin_entry` 设计「AI 友好」的 description 和错误消息
- 排查 17 个已知致命陷阱（BOM、目录大小写、`executemany`、启动超时…）
- 在 AI 调插件时提供上下文约束、权限校验、撤销/日志

## 仓库结构

```
Project_Neko-plugin_skill/
├── README.md                      ← 你正在看的文件
├── LICENSE                        ← MIT 协议
└── neko-plugin-dev/               ← 技能包本体
    ├── SKILL.md                   ← 技能入口（TRAE 加载这个文件）
    └── references/                ← 12 篇专题参考文档
        ├── README.md              ← 文档导航 + 交叉引用
        ├── 01-plugin-toml.md      ← 配置文件完整模板
        ├── 02-python-plugin.md    ← Python 后端模式
        ├── 03-ui-settings.md      ← TSX 设置面板
        ├── 04-i18n.md             ← 国际化翻译
        ├── 05-testing.md          ← 单元测试
        ├── 06-deployment.md       ← 部署同步
        ├── 07-gotchas.md          ← 17 个陷阱
        ├── 08-ai-friendly-design.md
        ├── 09-permission-system.md
        ├── 10-performance.md
        ├── 11-undo-and-logging.md
        └── 12-master-checklist.md ← 上线前总清单
```

***

## 快速开始

### 1. 在 TRAE 中安装本技能

把整个 `neko-plugin-dev/` 文件夹复制到你的 TRAE 技能目录：

```powershell
# Windows: 复制到 TRAE 全局技能目录
Copy-Item -Path ".\neko-plugin-dev" -Destination "$env:USERPROFILE\.trae\skills\neko-plugin-dev" -Recurse -Force
```

或直接在 TRAE 的「技能管理」里点「从本地文件夹导入」，选择 `neko-plugin-dev` 文件夹即可。

### 2. 让 AI 加载技能

新建会话后，对 AI 说一句：

> 「我要开发一个 N.E.K.O 插件，请帮我构建框架」

AI 会自动识别并加载 `neko-plugin-dev` 技能，后续对话都会按规范回答。

### 3. 按文档顺序开发

```
plugin.toml  →  __init__.py  →  ui/  →  i18n/  →  docs/  →  测试  →  部署
```

详细步骤见 [`neko-plugin-dev/references/README.md`](neko-plugin-dev/references/README.md) 的「从零搭建」章节。

***

## 核心铁律（务必先看）

> 完整版在 [`SKILL.md`](neko-plugin-dev/SKILL.md)，这里只列最致命的 10 条。

1. **文件名全小写 + 下划线** — 目录名与 `plugin.toml` 的 `entry` 包名严格一致
2. **Python 文件无 BOM** — `UTF-8 without BOM`，否则 `SyntaxError`
3. **`_ctx=None`** — 所有 `@plugin_entry` 和 `@ui.action` 方法必须包含
4. **`**_`** — 所有 `@lifecycle` 方法必须包含
5. **启动 < 10 秒** — 耗时操作丢 `asyncio.create_task()` 后台执行
6. **无** **`executemany`** — 数据库批量操作必须逐行 `await session.execute()`
7. **手动同步** — 工作区改完必须同步到 `C:\Users\...\AppData\Local\N.E.K.O\plugins\`
8. **权限默认** **`false`** — 安全优先：总开关 + 逐操作授权
9. **AI 需要绝对路径** — 拒绝非绝对路径，错误消息引导 AI 先搜索
10. **磁盘 I/O 用** **`asyncio.to_thread`** — 不阻塞事件循环

***

## 文档导航

### 基础篇（必读）

| #  | 文档                                                             | 何时打开      |
| -- | -------------------------------------------------------------- | --------- |
| 01 | [plugin.toml 配置](neko-plugin-dev/references/01-plugin-toml.md) | 新建插件、加配置项 |
| 02 | [Python 后端](neko-plugin-dev/references/02-python-plugin.md)    | 写核心逻辑     |
| 03 | [UI 设置面板](neko-plugin-dev/references/03-ui-settings.md)        | 做设置界面     |
| 04 | [i18n 国际化](neko-plugin-dev/references/04-i18n.md)              | 支持多语言     |

### 进阶篇（推荐）

| #  | 文档                                                             | 何时打开                              |
| -- | -------------------------------------------------------------- | --------------------------------- |
| 08 | [AI 友好设计](neko-plugin-dev/references/08-ai-friendly-design.md) | **每次写** **`@plugin_entry`** **前** |
| 09 | [权限体系](neko-plugin-dev/references/09-permission-system.md)     | 涉及读/写/删等危险操作                      |
| 10 | [性能优化](neko-plugin-dev/references/10-performance.md)           | 处理大量数据                            |
| 11 | [撤销与日志](neko-plugin-dev/references/11-undo-and-logging.md)     | 需要可撤销操作                           |

### 工程篇（流程）

| #  | 文档                                                          | 何时打开        |
| -- | ----------------------------------------------------------- | ----------- |
| 05 | [单元测试](neko-plugin-dev/references/05-testing.md)            | 开发完成时       |
| 06 | [部署同步](neko-plugin-dev/references/06-deployment.md)         | **每次修改后**   |
| 07 | [踩坑大全](neko-plugin-dev/references/07-gotchas.md)            | 遇到 bug 时    |
| 12 | [上线前总清单](neko-plugin-dev/references/12-master-checklist.md) | **每次发版前必看** |

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
AI：这是铁律 #2 触发。检查 plugin.toml 的 entry 字段包名是否与目录名大小写完全一致…
```

### 场景 C：AI 调不通

```
你：AI 调用我的 search_files 入口老是路径错误。
AI：这是 AI 友好设计问题。entry 的 description 必须三要素齐全，且方法内要拒绝非绝对路径…
```

### 场景 D：上线前检查

```
你：我要发版了，帮我过一遍清单。
AI：（加载 12-master-checklist）按 9 大类 80+ 项逐一过…
```

***

## 部署到 N.E.K.O 的标准动作

工作区改完后，**必须**手动同步到 N.E.K.O 的运行目录（AI 不会自动同步）：

```powershell
# 把工作区文件覆盖到部署目录
$src = "e:\你的工作区\你的插件\*"
$dst = "$env:LOCALAPPDATA\N.E.K.O\plugins\你的插件\"
Copy-Item -Path $src -Destination $dst -Recurse -Force

# 重启 N.E.K.O 让变更生效
```

详见 [06-deployment.md](neko-plugin-dev/references/06-deployment.md)。

***

## 贡献与反馈

本技能基于实战持续迭代，欢迎提 Issue / PR：

- 发现新陷阱 → 补到 [07-gotchas.md](neko-plugin-dev/references/07-gotchas.md)
- 新增设计模式 → 补到对应 references 文档
- 文档勘误 → 直接提 PR

## 协议

[MIT License](LICENSE) © 2026 Noda-Core 工作室 × 未知之致

***

<p align="center">
  <sub>由 Noda-Core 工作室 × 未知之致 用心打磨 ✨</sub>
</p>
