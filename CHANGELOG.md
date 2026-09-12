# 更新日志

本文件记录 N.E.K.O 插件开发 Skill 的所有版本变更。

---

## neko-plugin-dev(4.1.0) (V4.1.0) · 2026-09-12

> 文档准确性修复版：对照官方开发者文档（Quick Start / Plugin Config / SDK 迁移清单）逐条核对，修正与当前 SDK 不符的接口、部署流程与安全表述，并同步 README / SKILL / references 一致性。

### 修复（准确性与一致性）

- 🔄 **Bus 定性纠正** — `31-bus-system-internals.md` 由"事件总线/pub-sub"重写为"只读/订阅门面"；移除 `get_recent()` / `reload()` / `union()/intersect()/difference()`，改为官方可重放链 `get().filter(field=value).sort(by=).limit()`；`memory` 更正为只读、有界、短 TTL 快照。
- 🔄 **部署流程重写** — `06-deployment.md` / `17-pyc-cache-trap.md` 区分「源码树开发 / Load unpacked / 已安装包」三场景，默认走官方 **Reload**；删除无预览的 `robocopy /MIR` 常规用法；清 `__pycache__` 降级为"行为不更新"的诊断分支。
- 🔄 **安全表述修正** — `43-security-hardening.md` 将 SSRF 代码重命名为"URL 输入预筛选"并标注边界；区分源码 manifest 与用户运行时配置的密钥来源。
- 🔄 **脱敏声明修正** — `48-prompt-compression-pii-redaction.md` 补 API Key 正则、撤销"绝不外泄"绝对化承诺、新增覆盖面声明。
- 🔄 **铁律对齐** — README / SKILL.md / references/README.md 20 条铁律逐条一致（#1 三处命名、#5 timeout 可配、#7 优先 Reload、#12 标注未本机验证、#20 可重放链）。
- 🔄 **协调器收缩** — `00-development-coordinator.md` 由"最高优先级强制工作流"改为"大型新插件可选工作流"，新增状态文件脱敏/`.gitignore`/删除规则。
- 🔄 **示例与结构** — `examples/web_assistant/` 补 `config.example.toml` 与 `.gitignore`；README 结构补 `examples/`；安装提示 `4.0.0` → `4.1.0`；首页新增「已验证目标版本」与「发布前检查」。
- 🔄 **CHANGELOG 路径** — 历史条目链接由 `neko-plugin-dev(4.0.0)/` 更新为 `neko-plugin-dev(4.1.0)/`。

---

## neko-plugin-dev(4.1.0) 基础版 (V4.0.0) · 2026-08-19

> 二次融合：把 13 个外部开源 skill + 本地 `plugins/` 真实代码的方法论沉淀为 10 篇「融合篇」（40–49）+ **插件市场 31 个已上架插件源码逆向**（50），并附 1 个示例插件骨架（examples/web_assistant，当时尚未跑通端到端验证）。主题 38 → 51。

### 新增（市场插件逆向 · 50）⭐ 最新增补

- 📄 [50-market-plugin-reverse-engineering.md](neko-plugin-dev(4.1.0)/references/50-market-plugin-reverse-engineering.md) — 从 `https://market.project-neko.cn/api/v1/plugins` 爬取全部 31 个已上架插件的 GitHub 源码（仓库已克隆至 `_crawled_repos/`），逆向提炼**六类成功插件范式**：系统自动化 / 邮件 / 搜索 / 教育 OCR / 游戏控制 / 外部程序桥接
- 🔄 **SKILL.md 新增 F9 融合核心规则** — "写复杂插件先抄真实市场骨架"（系统自动化用三合一装饰器+窗口锁定+轮询；游戏用独立 data 进程+状态机；外部程序用 HTTP 桥+退避；教育用按功能域拆分 entry）
- 🔄 **SKILL.md 新增「实战篇·七」** — 参考文档 51 篇、主题 01–50、F1–F9
- 🔄 **references/README.md / README.md** — 导航表、结构树、版本表新增 50 行 + 实战篇·七 + 交叉引用

### 新增（统领工作流 · 00 · 最高优先级）⭐ 增补

- 📄 [00-development-coordinator.md](neko-plugin-dev(4.1.0)/references/00-development-coordinator.md) — 融合用户「AI 开发协作协调器」skill（v1.0.0, MIT）：五阶段工作流（需求澄清→方案规划→约束生成→任务拆解→编码实现）+ 状态持久化（`.skill对话构建缓存/`）+ 错误回滚 + 7 条元规则；适配本技能——每阶段挂接 01–50、RULES.md 默认注入 20 铁律 + F1–F9。
- 🔄 **SKILL.md 新增 P0 最高优先级规则** — 用户说"开发插件/启动开发协作"时先跑 00 五阶段工作流，再查 01–50；description / intro / 参考表同步声明 00 为统领层并置顶。
- 🔄 **主题 49 → 51**（+1 统领篇 00 +1 市场逆向 50，优先级 00 最高）
- 🔄 **references/README.md / README.md** — 导航表、结构树、版本表新增 00 行（最高优先级）

### 新增（10 篇融合 references · 40–49）

#### 融合外部最佳实践（第一批 · 6 篇）
- 📄 [40-engineering-discipline.md](neko-plugin-dev(4.1.0)/references/40-engineering-discipline.md) — 工程纪律：TDD、深模块、两轴审查、诊断循环 + ponytail 的 YAGNI 阶梯反过度工程
- 📄 [41-ui-design-quality.md](neko-plugin-dev(4.1.0)/references/41-ui-design-quality.md) — 反"AI 味"UI：impeccable + hallmark 确定性规则映射到 `@neko/plugin-ui` 受限组件
- 📄 [42-web-data-integration.md](neko-plugin-dev(4.1.0)/references/42-web-data-integration.md) — firecrawl 网页数据集成封装为 `@llm_tool`/`@plugin_entry` 深模块
- 📄 [43-security-hardening.md](neko-plugin-dev(4.1.0)/references/43-security-hardening.md) — strix 攻击者视角：最小权限/密钥/SSRF/注入/路径穿越/提示注入
- 📄 [44-local-plugin-architecture.md](neko-plugin-dev(4.1.0)/references/44-local-plugin-architecture.md) — 逆向本地 `plugins/`：三种拆分范式 + 真实生命周期/配置/工具注册写法
- 📄 [45-fusion-quick-reference.md](neko-plugin-dev(4.1.0)/references/45-fusion-quick-reference.md) — 40–44 压缩版：精髓五条 + 决策树 + 可抄片段

#### 融合外部最佳实践（第二批 · 4 篇）⭐
- 📄 [46-memory-persistence-subconscious.md](neko-plugin-dev(4.1.0)/references/46-memory-persistence-subconscious.md) — subconscious-skill：5 阶段记忆管道、3 类记忆、衰减/归档、whisper；映射到 store + `@timer_interval`
- 📄 [47-llm-routing-cost-optimization.md](neko-plugin-dev(4.1.0)/references/47-llm-routing-cost-optimization.md) — NadirClaw + llm-router：复杂度路由、验证器级联、Jaccard 缓存、飞行中去重
- 📄 [48-prompt-compression-pii-redaction.md](neko-plugin-dev(4.1.0)/references/48-prompt-compression-pii-redaction.md) — token-saviour + prompthakcer：4 层 token 模型、正则压缩、本地 PII 红挡
- 📄 [49-neko-companion-state-machine.md](neko-plugin-dev(4.1.0)/references/49-neko-companion-state-machine.md) — neko-skill：好感度状态机/指令系统（已剔除越狱内容）

### 新增（可运行示例插件）
- 📁 [examples/web_assistant/](neko-plugin-dev(4.1.0)/examples/web_assistant/) — 可抄示例骨架，整合 40–45 精髓（深函数/Router 拆分/URL 输入预筛选/@llm_tool/to_thread/反 AI 味 UI）

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

- 📄 [16-backend-simplification.md](neko-plugin-dev(4.1.0)/references/16-backend-simplification.md) — 后端精简与迁移（双后端→单后端迁移策略、代码清理清单、配置漂移防范、向后兼容处理）
- 📄 [17-pyc-cache-trap.md](neko-plugin-dev(4.1.0)/references/17-pyc-cache-trap.md) — `__pycache__` 缓存陷阱（代码改了但不生效的根本原因、日志诊断法、预防方案）
- 📄 [18-streaming-output.md](neko-plugin-dev(4.1.0)/references/18-streaming-output.md) — 流式输出与进度推送（逐句处理循环、push_message/report_status、音频合并、viseme 口型同步）
- 📄 [19-llm-workflow-design.md](neko-plugin-dev(4.1.0)/references/19-llm-workflow-design.md) — LLM 对话工作流设计（check_setup 前置检查、多入口编排、next_action 指导、description 三要素）

#### 实战篇·三（4 篇 · 原指南 + 第三方插件分析）

- 📄 [20-plugin-router.md](neko-plugin-dev(4.1.0)/references/20-plugin-router.md) — PluginRouter 拆分大型插件（多入口点模块化、共享逻辑、Router 能力访问、前缀命名、完整示例）
- 📄 [21-llm-tool-registration.md](neko-plugin-dev(4.1.0)/references/21-llm-tool-registration.md) — @llm_tool LLM 工具注册（装饰器详解、架构分层、错误返回、命令式 API、生命周期与时序、main_server 重启应对）
- 📄 [22-static-ui-plugin.md](neko-plugin-dev(4.1.0)/references/22-static-ui-plugin.md) — 纯前端/Static UI 插件（RPC 通信机制、状态管理、后台轮询、文件上传、Three.js 3D 集成、音频可视化、Toast 系统）
- 📄 [23-external-protocol-integration.md](neko-plugin-dev(4.1.0)/references/23-external-protocol-integration.md) — 外部协议集成与消息积压管理（OneBot/NapCat 连接、积压数据结构、回复概率控制、引导式安装、信任体系、WebSocket 重连）

#### 实战篇·四（5 篇 · 三插件深度逆向）

- 📄 [24-error-handling-patterns.md](neko-plugin-dev(4.1.0)/references/24-error-handling-patterns.md) — 错误处理与诊断模式大全（惰性导入+错误缓存、多级关键字诊断、轮询重试、分层 UI 渲染、Ok/Err 分层返回、按钮防重复、Toast 通知、RPC 超时、错误码设计规范）
- 📄 [25-concurrency-race-conditions.md](neko-plugin-dev(4.1.0)/references/25-concurrency-race-conditions.md) — 并发与竞态条件（锁外 I/O、冻结取消、防重入刷新、消息积压上限、请求去重、WebSocket 指数退避重连、回复概率控制）
- 📄 [26-backend-design-pattern.md](neko-plugin-dev(4.1.0)/references/26-backend-design-pattern.md) — Backend 对象设计模式（惰性导入+错误缓存、配置传播与_log注入、健康检查多时机、同步/异步桥接、多后端共存、完整模板）
- 📄 [27-audio-processing-pipeline.md](neko-plugin-dev(4.1.0)/references/27-audio-processing-pipeline.md) — 音频处理管线（纯 Python WAV 合并无 ffmpeg 依赖、Viseme 口型同步数据生成、时长估算三级回退、双轨播放架构、句间换气停顿算法）
- 📄 [28-inter-plugin-communication.md](neko-plugin-dev(4.1.0)/references/28-inter-plugin-communication.md) — 插件间通信（call_entry 跨插件调用、依赖声明与检查、事件总线 pub/sub、共享数据模式、版本兼容回退、防御性调用）

#### 实战篇·五（5 篇 · 主程序逆向 · 框架层）

- 📄 [29-plugin-lifecycle-internals.md](neko-plugin-dev(4.1.0)/references/29-plugin-lifecycle-internals.md) — 插件生命周期内部机制（7 阶段状态机、ZMQ 进程通信架构、load/init/start/run/stop/unload 全流程、子进程管理、常见生命周期陷阱）
- 📄 [30-push-message-internals.md](neko-plugin-dev(4.1.0)/references/30-push-message-internals.md) — Push Message 深度解析（visibility/ai_behavior 两轴正交模型、Parts 结构详解、coalesce_key 消息合并、旧版→v2 迁移映射、UI Action 媒体播放、内部 base64 编码机制）
- 📄 [31-bus-system-internals.md](neko-plugin-dev(4.1.0)/references/31-bus-system-internals.md) — Bus 总线系统深度解析（惰性查询容器 BusList、计划节点树 GetNode/FilterNode/SortNode、五条总线 messages/events/lifecycle/conversations/memory、Revision 追踪、Watch 变更订阅、集合操作 union/intersect/difference）
- 📄 [32-nekopluginbase-internals.md](neko-plugin-dev(4.1.0)/references/32-nekopluginbase-internals.md) — NekoPluginBase 内部机制（双层继承 shared/sdk、构造函数全流程、Entry 收集、Router 绑定、SDK 上下文封装、LLM Tool 注册流程、Static UI、PluginStore/PluginDatabase/PluginStatePersistence）
- 📄 [33-pluginrouter-entry-internals.md](neko-plugin-dev(4.1.0)/references/33-pluginrouter-entry-internals.md) — PluginRouter 与 Entry 系统（懒解析策略、动态 Entry 注册、before/after/around_entry 钩子、hook 系统、quick_action 快捷操作、Entry 分发全流程、装饰器叠加规则、闭包陷阱）

#### 实战篇·六（5 篇 · 主程序逆向 · 基础设施层）⭐

- 📄 [34-logger-system-internals.md](neko-plugin-dev(4.1.0)/references/34-logger-system-internals.md) — Logger 日志系统内部机制（PluginLoggerAdapter 双风格兼容、loguru braces/stdlib % 格式、RobustLoggerConfig 落地、Root Bridge 第三方日志捕获、敏感信息脱敏、懒解析机制）
- 📄 [35-store-database-internals.md](neko-plugin-dev(4.1.0)/references/35-store-database-internals.md) — PluginStore 与 PluginDatabase 内部机制（JSON 键值存储 vs SQLite 关系存储、全量加载/每次写入持久化、CRUD 完整模式、批量插入分批提交、PluginStatePersistence、data_path 私有目录、持久化策略选择决策树）
- 📄 [36-i18n-internals.md](neko-plugin-dev(4.1.0)/references/36-i18n-internals.md) — i18n 国际化引擎内部机制（回退链：用户语言→默认语言→default→key、参数插值 str.format()、懒加载翻译文件、tr 函数在装饰器中的使用、命名规范与最佳实践）
- 📄 [37-zmq-transport-internals.md](neko-plugin-dev(4.1.0)/references/37-zmq-transport-internals.md) — ZMQ 进程通信协议内部机制（PAIR socket 双向通信、JSON 序列化协议、12 种命令类型及超时配置、HostTransport/ChildTransport 实现、CALL_ENTRY 完整调用链路、子进程崩溃与自动重启、大数据传输优化）
- 📄 [38-config-system-internals.md](neko-plugin-dev(4.1.0)/references/38-config-system-internals.md) — 插件配置系统内部机制（plugin.toml [settings] / self.config / self.store 三层关系、合并优先级、update_own_config 点号路径、配置漂移防范与迁移策略、DEFAULT_CONFIG 完整模板、config_change 钩子注意事项）

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

- 📄 [13-cloud-api-integration.md](neko-plugin-dev(4.1.0)/references/13-cloud-api-integration.md) — 云端 API 集成模式（阿里云百炼 SDK、端点配置、健康检查、轮询等待）
- 📄 [14-multi-panel-architecture.md](neko-plugin-dev(4.1.0)/references/14-multi-panel-architecture.md) — 多面板架构设计（双面板 + 双 Context、配置共享、标签页）
- 📄 [15-rich-ui-components.md](neko-plugin-dev(4.1.0)/references/15-rich-ui-components.md) — 富交互 UI 组件（自定义 LyricPlayer、ActionForm 高级用法、内联样式）

### 更新

- 🔄 SKILL.md description 扩展：`report_status` / `data_path` / 双装饰器、`Slider` / `Select` / `StatusBadge` / `ActionForm` / `api.call`
- 🔄 SKILL.md 来源说明：`file_manager` 单插件 → `file_manager` + `ai_singer` 双插件
- 🔄 陷阱库：17 → **21 个**（新增 4 个 V1.01 陷阱）
- 🔄 [references/README.md](neko-plugin-dev(4.1.0)/references/README.md) 加入「实战篇」分类
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
