# 更新日志

本文件记录 N.E.K.O 插件开发 Skill 的所有版本变更。

---

## V2.0 · 2026-07-12

> 大版本升级：双插件 → 四插件 + 主程序逆向 主题 15 → 38 铁律 10 → 20 陷阱 21 → 45

### 新增（23 篇 references）

#### 实战篇·二（4 篇 · `ai_singer` V0.6 重构经验）

- 📄 [16-backend-simplification.md](neko-plugin-dev(V2.0)/references/16-backend-simplification.md) — 后端精简与迁移（双后端→单后端迁移策略、代码清理清单、配置漂移防范、向后兼容处理）
- 📄 [17-pyc-cache-trap.md](neko-plugin-dev(V2.0)/references/17-pyc-cache-trap.md) — `__pycache__` 缓存陷阱（代码改了但不生效的根本原因、日志诊断法、预防方案）
- 📄 [18-streaming-output.md](neko-plugin-dev(V2.0)/references/18-streaming-output.md) — 流式输出与进度推送（逐句处理循环、push_message/report_status、音频合并、viseme 口型同步）
- 📄 [19-llm-workflow-design.md](neko-plugin-dev(V2.0)/references/19-llm-workflow-design.md) — LLM 对话工作流设计（check_setup 前置检查、多入口编排、next_action 指导、description 三要素）

#### 实战篇·三（4 篇 · 原指南 + 第三方插件分析）

- 📄 [20-plugin-router.md](neko-plugin-dev(V2.0)/references/20-plugin-router.md) — PluginRouter 拆分大型插件（多入口点模块化、共享逻辑、Router 能力访问、前缀命名、完整示例）
- 📄 [21-llm-tool-registration.md](neko-plugin-dev(V2.0)/references/21-llm-tool-registration.md) — @llm_tool LLM 工具注册（装饰器详解、架构分层、错误返回、命令式 API、生命周期与时序、main_server 重启应对）
- 📄 [22-static-ui-plugin.md](neko-plugin-dev(V2.0)/references/22-static-ui-plugin.md) — 纯前端/Static UI 插件（RPC 通信机制、状态管理、后台轮询、文件上传、Three.js 3D 集成、音频可视化、Toast 系统）
- 📄 [23-external-protocol-integration.md](neko-plugin-dev(V2.0)/references/23-external-protocol-integration.md) — 外部协议集成与消息积压管理（OneBot/NapCat 连接、积压数据结构、回复概率控制、引导式安装、信任体系、WebSocket 重连）

#### 实战篇·四（5 篇 · 三插件深度逆向）

- 📄 [24-error-handling-patterns.md](neko-plugin-dev(V2.0)/references/24-error-handling-patterns.md) — 错误处理与诊断模式大全（惰性导入+错误缓存、多级关键字诊断、轮询重试、分层 UI 渲染、Ok/Err 分层返回、按钮防重复、Toast 通知、RPC 超时、错误码设计规范）
- 📄 [25-concurrency-race-conditions.md](neko-plugin-dev(V2.0)/references/25-concurrency-race-conditions.md) — 并发与竞态条件（锁外 I/O、冻结取消、防重入刷新、消息积压上限、请求去重、WebSocket 指数退避重连、回复概率控制）
- 📄 [26-backend-design-pattern.md](neko-plugin-dev(V2.0)/references/26-backend-design-pattern.md) — Backend 对象设计模式（惰性导入+错误缓存、配置传播与_log注入、健康检查多时机、同步/异步桥接、多后端共存、完整模板）
- 📄 [27-audio-processing-pipeline.md](neko-plugin-dev(V2.0)/references/27-audio-processing-pipeline.md) — 音频处理管线（纯 Python WAV 合并无 ffmpeg 依赖、Viseme 口型同步数据生成、时长估算三级回退、双轨播放架构、句间换气停顿算法）
- 📄 [28-inter-plugin-communication.md](neko-plugin-dev(V2.0)/references/28-inter-plugin-communication.md) — 插件间通信（call_entry 跨插件调用、依赖声明与检查、事件总线 pub/sub、共享数据模式、版本兼容回退、防御性调用）

#### 实战篇·五（5 篇 · 主程序逆向 · 框架层）

- 📄 [29-plugin-lifecycle-internals.md](neko-plugin-dev(V2.0)/references/29-plugin-lifecycle-internals.md) — 插件生命周期内部机制（7 阶段状态机、ZMQ 进程通信架构、load/init/start/run/stop/unload 全流程、子进程管理、常见生命周期陷阱）
- 📄 [30-push-message-internals.md](neko-plugin-dev(V2.0)/references/30-push-message-internals.md) — Push Message 深度解析（visibility/ai_behavior 两轴正交模型、Parts 结构详解、coalesce_key 消息合并、旧版→v2 迁移映射、UI Action 媒体播放、内部 base64 编码机制）
- 📄 [31-bus-system-internals.md](neko-plugin-dev(V2.0)/references/31-bus-system-internals.md) — Bus 总线系统深度解析（惰性查询容器 BusList、计划节点树 GetNode/FilterNode/SortNode、五条总线 messages/events/lifecycle/conversations/memory、Revision 追踪、Watch 变更订阅、集合操作 union/intersect/difference）
- 📄 [32-nekopluginbase-internals.md](neko-plugin-dev(V2.0)/references/32-nekopluginbase-internals.md) — NekoPluginBase 内部机制（双层继承 shared/sdk、构造函数全流程、Entry 收集、Router 绑定、SDK 上下文封装、LLM Tool 注册流程、Static UI、PluginStore/PluginDatabase/PluginStatePersistence）
- 📄 [33-pluginrouter-entry-internals.md](neko-plugin-dev(V2.0)/references/33-pluginrouter-entry-internals.md) — PluginRouter 与 Entry 系统（懒解析策略、动态 Entry 注册、before/after/around_entry 钩子、hook 系统、quick_action 快捷操作、Entry 分发全流程、装饰器叠加规则、闭包陷阱）

#### 实战篇·六（5 篇 · 主程序逆向 · 基础设施层）⭐

- 📄 [34-logger-system-internals.md](neko-plugin-dev(V2.0)/references/34-logger-system-internals.md) — Logger 日志系统内部机制（PluginLoggerAdapter 双风格兼容、loguru braces/stdlib % 格式、RobustLoggerConfig 落地、Root Bridge 第三方日志捕获、敏感信息脱敏、懒解析机制）
- 📄 [35-store-database-internals.md](neko-plugin-dev(V2.0)/references/35-store-database-internals.md) — PluginStore 与 PluginDatabase 内部机制（JSON 键值存储 vs SQLite 关系存储、全量加载/每次写入持久化、CRUD 完整模式、批量插入分批提交、PluginStatePersistence、data_path 私有目录、持久化策略选择决策树）
- 📄 [36-i18n-internals.md](neko-plugin-dev(V2.0)/references/36-i18n-internals.md) — i18n 国际化引擎内部机制（回退链：用户语言→默认语言→default→key、参数插值 str.format()、懒加载翻译文件、tr 函数在装饰器中的使用、命名规范与最佳实践）
- 📄 [37-zmq-transport-internals.md](neko-plugin-dev(V2.0)/references/37-zmq-transport-internals.md) — ZMQ 进程通信协议内部机制（PAIR socket 双向通信、JSON 序列化协议、12 种命令类型及超时配置、HostTransport/ChildTransport 实现、CALL_ENTRY 完整调用链路、子进程崩溃与自动重启、大数据传输优化）
- 📄 [38-config-system-internals.md](neko-plugin-dev(V2.0)/references/38-config-system-internals.md) — 插件配置系统内部机制（plugin.toml [settings] / self.config / self.store 三层关系、合并优先级、update_own_config 点号路径、配置漂移防范与迁移策略、DEFAULT_CONFIG 完整模板、config_change 钩子注意事项）

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

- 📄 [13-cloud-api-integration.md](neko-plugin-dev(V2.0)/references/13-cloud-api-integration.md) — 云端 API 集成模式（阿里云百炼 SDK、端点配置、健康检查、轮询等待）
- 📄 [14-multi-panel-architecture.md](neko-plugin-dev(V2.0)/references/14-multi-panel-architecture.md) — 多面板架构设计（双面板 + 双 Context、配置共享、标签页）
- 📄 [15-rich-ui-components.md](neko-plugin-dev(V2.0)/references/15-rich-ui-components.md) — 富交互 UI 组件（自定义 LyricPlayer、ActionForm 高级用法、内联样式）

### 更新

- 🔄 SKILL.md description 扩展：`report_status` / `data_path` / 双装饰器、`Slider` / `Select` / `StatusBadge` / `ActionForm` / `api.call`
- 🔄 SKILL.md 来源说明：`file_manager` 单插件 → `file_manager` + `ai_singer` 双插件
- 🔄 陷阱库：17 → **21 个**（新增 4 个 V1.01 陷阱）
- 🔄 [references/README.md](neko-plugin-dev(V2.0)/references/README.md) 加入「实战篇」分类
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
