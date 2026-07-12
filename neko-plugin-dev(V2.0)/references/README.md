# N.E.K.O 插件开发 Skill 指南

> 基于 `file_manager` + `ai_singer` + `music_pusher` + `qq_auto_reply` 多插件实战 + N.E.K.O-main 主程序深度逆向分析，从零到一，从入门到避坑，涵盖 38 个主题。

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

### 实战篇（基于 ai_singer 插件）

| 编号 | 文档 | 内容 | 何时需要 |
|------|------|------|---------|
| 13 | [云端 API 集成](13-cloud-api-integration.md) | 第三方 SDK 集成、端点配置、错误诊断、健康检查、保存后验证 | 对接云服务/第三方 API |
| 14 | [多面板架构](14-multi-panel-architecture.md) | 双面板 + 双 Context、配置共享、标签页组织、持久化策略 | 功能复杂需要多面板 |
| 15 | [富交互 UI](15-rich-ui-components.md) | 自定义组件、LyricPlayer、ActionForm 高级用法、内联样式、条件渲染 | 需要复杂 UI 交互 |

### 实战篇·二（基于 ai_singer V0.6 重构）

| 编号 | 文档 | 内容 | 何时需要 |
|------|------|------|---------|
| 16 | [后端精简与迁移](16-backend-simplification.md) | 双后端→单后端迁移、代码清理、配置漂移防范、向后兼容 | 重构/移除旧后端 |
| 17 | [pyc 缓存陷阱](17-pyc-cache-trap.md) | 代码改了但不生效的原因、日志诊断、预防方案 | 部署后行为不变时 |
| 18 | [流式输出](18-streaming-output.md) | 逐句处理、push_message/report_status、音频合并、viseme | 需要逐条输出进度 |
| 19 | [LLM 工作流设计](19-llm-workflow-design.md) | check_setup、多入口编排、next_action、description 三要素 | 设计 AI 调用流程 |

### 实战篇·三（基于原指南 + 第三方插件分析）

| 编号 | 文档 | 内容 | 何时需要 |
|------|------|------|---------|
| 20 | [PluginRouter 拆分](20-plugin-router.md) | 大型插件模块化、共享逻辑、Router 能力、前缀命名 | 插件超 300 行/5+ 入口 |
| 21 | [@llm_tool 注册](21-llm-tool-registration.md) | LLM 工具调用、架构分层、错误返回、生命周期、重启应对 | 让 LLM 自动调用插件 |
| 22 | [纯前端插件](22-static-ui-plugin.md) | RPC 通信、状态管理、轮询、Three.js、音频可视化 | 3D/可视化/富媒体插件 |
| 23 | [外部协议集成](23-external-protocol-integration.md) | OneBot/NapCat、积压管理、概率控制、引导安装、信任体系 | 跨平台通信插件 |

### 实战篇·四（基于三插件深度逆向分析）

| 编号 | 文档 | 内容 | 何时需要 |
|------|------|------|---------|
| 24 | [错误处理模式](24-error-handling-patterns.md) | 惰性导入+错误缓存、多级关键字诊断、轮询重试、分层UI渲染、Ok/Err分层、按钮防重复、Toast通知、RPC超时 | 写任何涉及错误的代码 |
| 25 | [并发与竞态条件](25-concurrency-race-conditions.md) | 锁外I/O、冻结取消、防重入刷新、积压上限、请求去重、WebSocket指数退避、概率控制 | 多入口/定时器/外部协议 |
| 26 | [Backend设计模式](26-backend-design-pattern.md) | 惰性导入+错误缓存、配置传播、健康检查多时机、同步异步桥接、多后端共存 | 对接外部API/服务 |
| 27 | [音频处理管线](27-audio-processing-pipeline.md) | 纯Python WAV合并、Viseme口型同步、时长估算三级回退、双轨播放、换气停顿 | 处理音频/多媒体 |
| 28 | [插件间通信](28-inter-plugin-communication.md) | call_entry调用、依赖声明检查、事件总线、共享数据、版本兼容回退 | 多插件协作联动 |

### 实战篇·五（基于 N.E.K.O 主程序深度逆向分析 — 框架层）

| 编号 | 文档 | 内容 | 何时需要 |
|------|------|------|---------|
| 29 | [生命周期内部机制](29-plugin-lifecycle-internals.md) | 7阶段状态机、ZMQ进程通信、load/init/start/run/stop/unload、子进程管理 | 排查启动/停止 bug |
| 30 | [Push Message 深度解析](30-push-message-internals.md) | visibility/ai_behavior两轴模型、Parts结构、coalesce_key、媒体播放、base64编码 | 推送任何消息 |
| 31 | [Bus 总线系统](31-bus-system-internals.md) | BusList惰性查询、计划节点树、五条总线、Revision追踪、Watch订阅、集合操作 | 查询消息/事件/记忆 |
| 32 | [NekoPluginBase 内部](32-nekopluginbase-internals.md) | 双层继承、Entry收集、Router绑定、SDK上下文封装、LLM Tool注册、Store/DB/State | 深入理解插件基类 |
| 33 | [PluginRouter Entry 系统](33-pluginrouter-entry-internals.md) | 懒解析策略、动态Entry、before/after钩子、hook系统、quick_action、分发全流程 | 设计多模块插件 |

### 实战篇·六（基于 N.E.K.O 主程序深度逆向分析 — 基础设施层）⭐ 新增

| 编号 | 文档 | 内容 | 何时需要 |
|------|------|------|---------|
| 34 | [Logger 日志系统](34-logger-system-internals.md) | 双风格兼容、日志落地路径、Root Bridge、敏感信息脱敏、懒解析机制 | 排查日志不落地/格式问题 |
| 35 | [Store 与 Database](35-store-database-internals.md) | JSON vs SQLite、全量加载、每次写入持久化、持久化策略决策树 | 选择数据存储方案 |
| 36 | [i18n 引擎](36-i18n-internals.md) | 回退链、参数插值、懒加载、tr函数、命名规范 | 实现多语言支持 |
| 37 | [ZMQ 传输协议](37-zmq-transport-internals.md) | PAIR socket、JSON协议、12种命令超时、CALL_ENTRY调用链、崩溃恢复 | 理解跨进程通信 |
| 38 | [配置系统](38-config-system-internals.md) | toml/store/config三层关系、合并优先级、配置漂移防范、迁移策略 | 管理插件配置项 |

### 工程篇（开发流程）

| 编号 | 文档 | 内容 | 何时需要 |
|------|------|------|---------|
| 05 | [单元测试](05-testing.md) | Mock SDK、Fake 对象、测试模板 | 开发完成时 |
| 06 | [部署同步](06-deployment.md) | 工作区 vs 运行目录、同步命令 | 每次修改后 |
| 07 | [踩坑大全](07-gotchas.md) | 40 个已知陷阱、排查清单 | 遇到 bug 时 |
| 12 | [汇总清单](12-master-checklist.md) | 所有文档的检查清单合并 | 代码审查/上线前 |

---

## 交叉引用速查

| 当你在... | 需要同时参考... |
|-----------|---------------|
| 写 `@plugin_entry` 时 | 08 (AI 设计) + 09 (权限检查) + 02 (方法签名) |
| 写设置面板 UI 时 | 03 (UI 组件) + 09 (权限 UI) + 01 (配置项) |
| 做文件操作时 | 09 (权限) + 08 (路径验证) + 11 (撤销/日志) |
| 做数据库操作时 | 02 (数据库模式) + 10 (批量/索引) + 07 (#4 #7 陷阱) |
| 写定时器时 | 02 (定时器签名) + 10 (性能 #8) + 09 (冻结保护) + 24 (错误处理 §2.6) |
| 做启动初始化时 | 02 (启动分离) + 10 (启动优化) + 07 (#5 超时) |
| 部署时 | 06 (同步指南) + 07 (#1 BOM, #2 目录名, #22 pyc) |
| 写测试时 | 05 (Mock 模板) + 02 (返回值模式) |
| 对接云 API 时 | 13 (云端集成) + 14 (多面板) + 08 (AI 友好错误消息) + 26 (Backend 设计) |
| 做多面板/标签页时 | 14 (架构设计) + 15 (UI 模式) + 03 (组件清单) |
| 做自定义 UI 组件时 | 15 (富交互 UI) + 03 (可用组件) + 07 (不可用组件) |
| 拆分大型插件时 | 20 (PluginRouter) + 02 (Python 后端) + 07 (#26 ID重复) |
| 让 LLM 调用插件时 | 21 (@llm_tool) + 08 (AI 设计) + 19 (LLM 工作流) + 07 (#27 签名) |
| 做纯前端/3D 插件时 | 22 (Static UI) + 15 (富交互 UI) + 07 (#28 路径, #29 超时) |
| 对接外部协议时 | 23 (外部协议) + 09 (权限) + 25 (并发) + 07 (#30 积压上限) |
| 做错误处理时 | 24 (错误处理) + 08 (AI 友好错误消息) + 07 (#31 锁内I/O) |
| 处理并发问题时 | 25 (并发) + 10 (性能) + 07 (#32 冻结检查, #35 定时器await) |
| 设计 Backend 对象时 | 26 (Backend设计) + 13 (云端集成) + 24 (错误处理 §2.1) |
| 处理音频/多媒体时 | 27 (音频管线) + 18 (流式输出) + 22 (Static UI 播放器) |
| 使用日志调试时 | 34 (Logger内部) + 24 (错误处理) + 07 (#34-1 用loguru) |
| 选择数据存储方案时 | 35 (Store/DB内部) + 02 (数据库模式) + 10 (性能优化) |
| 做多语言支持时 | 36 (i18n内部) + 04 (i18n基础) + 02 (tr函数) |
| 理解跨进程调用时 | 37 (ZMQ内部) + 29 (生命周期) + 28 (跨插件通信) |
| 管理配置项时 | 38 (Config内部) + 01 (plugin.toml) + 16 (配置漂移) |
| 多插件协作联动时 | 28 (插件间通信) + 07 (#34 直接import) + 25 (并发) |
| 排查生命周期 bug 时 | 29 (生命周期内部) + 02 (Python后端) + 07 (#29-1 on_init调其他插件) |
| 推送消息/媒体时 | 30 (Push Message) + 22 (Static UI) + 07 (#30-1 visibility冲突) |
| 查询总线数据时 | 31 (Bus系统) + 29 (生命周期) + 07 (#31-1 on_init用Bus) |
| 理解插件基类时 | 32 (NekoPluginBase内部) + 02 (Python后端) + 21 (LLM Tool) |
| 设计多模块插件时 | 33 (PluginRouter) + 20 (Router拆分) + 07 (#33-1 ID冲突) |

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

## 20 条铁律

1. **文件名全小写 + 下划线** — 目录名与 `entry` 的包名严格一致
2. **Python 文件无 BOM** — `UTF-8 without BOM`
3. **`_ctx=None`** — 所有 `@plugin_entry` 和 `@ui.action` 必须包含
4. **`**_`** — 所有 `@lifecycle` 必须包含
5. **启动 < 10 秒** — 耗时操作丢 `asyncio.create_task()`
6. **无 `executemany`** — 逐行 `await session.execute()`
7. **手动同步 + 删 `__pycache__`** — 同步后必须删除部署目录的 `__pycache__/`
8. **权限默认 `false`** — 安全优先，总开关 + 逐操作授权
9. **AI 需要绝对路径** — 拒绝非绝对路径，错误消息中引导搜索
10. **磁盘 I/O 用 `asyncio.to_thread`** — 不阻塞事件循环
11. **dependencies 用内联表** — `openai = ">=1.0.0"` 而非列表格式
12. **`@plugin_entry` 在上** — 双装饰器叠加时顺序不能反
13. **`@llm_tool` 用 `*,`** — 强制 keyword-only 避免位置参数错误
14. **Router 在 `__init__` 中注册** — `include_router` 必须在 `super().__init__` 之后
15. **第三方库惰性导入 + 错误缓存** — ImportError 后缓存失败结果，不重复重试
16. **跨插件用 call_entry** — 不直接 import 其他插件类
17. **on_init 不调其他插件** — 跨插件调用放在 on_start 中
18. **push_message 大文件用 URL** — 大文件 base64 体积膨胀 33%
19. **Router entry 设 prefix** — 多 Router 用 prefix 避免 ID 冲突
20. **Bus 查询用惰性链式** — filter().limit() 而非多次 reload()

## 开发顺序

```
plugin.toml  →  __init__.py  →  ui/  →  i18n/  →  docs/  →  测试  →  部署
```

## 快速排查

```
1.☐BOM? 2.☐目录名一致? 3.☐_ctx=None? 4.☐**_? 5.☐executemany?
6.☐keywords? 7.☐database.enabled? 8.☐同步+删__pycache__了? 9.☐重启了? 10.☐rstrip(os.sep)?
11.☐dependencies格式? 12.☐双装饰器顺序? 13.☐@llm_tool签名有*? 14.☐Router在__init__中注册?
15.☐第三方导入有错误缓存? 16.☐跨插件用call_entry而非import?
17.☐on_init不调其他插件? 18.☐大文件用URL而非base64? 19.☐Router有prefix? 20.☐Bus用惰性链式?
```