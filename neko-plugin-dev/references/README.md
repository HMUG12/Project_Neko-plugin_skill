# N.E.K.O 插件开发 Skill 指南

> 基于 `file_manager` 插件实战踩坑总结，从零到一，从入门到避坑，涵盖 12 个主题。

---

## 从零搭建（5 分钟快速入门）

```bash
# 1. 创建目录
mkdir my_plugin && cd my_plugin

# 2. 创建 plugin.toml（复制 01 模板，改 id/name/entry）
# 3. 创建 __init__.py（复制 02 模板，改类名）
# 4. 创建 ui/settings.tsx（复制 03 模板）
# 5. 创建 i18n/zh-CN.json + i18n/en.json（复制 04 格式）
# 6. 语法验证
python -c "import py_compile; py_compile.compile('__init__.py', doraise=True)"

# 7. 同步到部署目录
Copy-Item '.\*' 'C:\Users\Admin\AppData\Local\N.E.K.O\plugins\my_plugin\' -Recurse -Force

# 8. 重启 N.E.K.O
```

**最简骨架**：只需要 `plugin.toml` + `__init__.py`（含 `on_startup`）就能跑起来。

---

## 文档导航

### 基础篇（必读）

| 编号 | 文档 | 内容 | 何时需要 |
|------|------|------|---------|
| 01 | [plugin.toml](01-plugin-toml.md) | 完整模板、配置项、AI 关键词 | 新建插件、添加配置项 |
| 02 | [Python 后端](02-python-plugin.md) | 装饰器、生命周期、数据库、模式速查 | 写核心逻辑 |
| 03 | [UI 设置面板](03-ui-settings.md) | 可用组件、标准模板、ActionButton | 做设置界面 |
| 04 | [i18n 国际化](04-i18n.md) | 翻译格式、命名规范 | 支持多语言 |

### 进阶篇（推荐）

| 编号 | 文档 | 内容 | 何时需要 |
|------|------|------|---------|
| 08 | [AI 友好设计](08-ai-friendly-design.md) | 让 AI 正确调用插件、工作流设计 | **每次添加 @plugin_entry** |
| 09 | [权限体系](09-permission-system.md) | 两层权限、操作映射、安全原则 | 涉及危险操作 |
| 10 | [性能优化](10-performance.md) | asyncio.to_thread、批量、索引、编码 | 处理大量数据 |
| 11 | [撤销与日志](11-undo-and-logging.md) | 撤销栈、操作日志、数据库同步 | 需要可撤销操作 |

### 工程篇（开发流程）

| 编号 | 文档 | 内容 | 何时需要 |
|------|------|------|---------|
| 05 | [单元测试](05-testing.md) | Mock SDK、Fake 对象、测试模板 | 开发完成时 |
| 06 | [部署同步](06-deployment.md) | 工作区 vs 运行目录、同步命令 | 每次修改后 |
| 07 | [踩坑大全](07-gotchas.md) | 17 个已知陷阱、排查清单 | 遇到 bug 时 |
| 12 | [汇总清单](12-master-checklist.md) | 所有文档的检查清单合并 | 代码审查/上线前 |

---

## 交叉引用速查

| 当你在... | 需要同时参考... |
|-----------|---------------|
| 写 `@plugin_entry` 时 | 08 (AI 设计) + 09 (权限检查) + 02 (方法签名) |
| 写设置面板 UI 时 | 03 (UI 组件) + 09 (权限 UI) + 01 (配置项) |
| 做文件操作时 | 09 (权限) + 08 (路径验证) + 11 (撤销/日志) |
| 做数据库操作时 | 02 (数据库模式) + 10 (批量/索引) + 07 (#4 #7 陷阱) |
| 写定时器时 | 02 (定时器签名) + 10 (性能 #8) + 09 (冻结保护) |
| 做启动初始化时 | 02 (启动分离) + 10 (启动优化) + 07 (#5 超时) |
| 部署时 | 06 (同步指南) + 07 (#1 BOM, #2 目录名) |
| 写测试时 | 05 (Mock 模板) + 02 (返回值模式) |

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

## 10 条铁律

1. **文件名全小写 + 下划线** — 目录名与 `entry` 的包名严格一致
2. **Python 文件无 BOM** — `UTF-8 without BOM`
3. **`_ctx=None`** — 所有 `@plugin_entry` 和 `@ui.action` 必须包含
4. **`**_`** — 所有 `@lifecycle` 必须包含
5. **启动 < 10 秒** — 耗时操作丢 `asyncio.create_task()`
6. **无 `executemany`** — 逐行 `await session.execute()`
7. **手动同步** — 工作区改完必须同步到部署目录
8. **权限默认 `false`** — 安全优先，总开关 + 逐操作授权
9. **AI 需要绝对路径** — 拒绝非绝对路径，错误消息中引导搜索
10. **磁盘 I/O 用 `asyncio.to_thread`** — 不阻塞事件循环

## 开发顺序

```
plugin.toml  →  __init__.py  →  ui/  →  i18n/  →  docs/  →  测试  →  部署
```

## 快速排查

1. ☐ BOM？ 2. ☐ 目录名一致？ 3. ☐ `_ctx=None`？ 4. ☐ `**_`？ 5. ☐ `executemany`？ 6. ☐ `keywords`？ 7. ☐ `database.enabled`？ 8. ☐ 同步了？ 9. ☐ 重启了？ 10. ☐ `rstrip(os.sep)`？