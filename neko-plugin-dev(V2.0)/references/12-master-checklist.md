# 汇总检查清单

> 合并全部 38 篇文档中的检查清单，用于代码审查和上线前验证。

---

## 项目初始化

- [ ] `plugin.toml` 的 `id` 与目录名一致
- [ ] `entry` 的包名与目录名完全一致（全小写 + 下划线）
- [ ] `short_description` 和 `keywords` 中英文都写
- [ ] `[plugin.database] enabled = true`（如果需要数据库）
- [ ] `[plugin.store] enabled = true`（如果需要持久化配置）
- [ ] `[settings]` 节包含所有配置项，且有合理的默认值
- [ ] `__init__.py` 无 UTF-8 BOM（`python -c "py_compile.compile('__init__.py', doraise=True)"`）
- [ ] `[plugin.dependencies]` 声明 Python 依赖（如有第三方 SDK）
- [ ] `[settings]` 节配置项与 `DEFAULT_CONFIG` 字典 key 完全一致

## Python 后端

- [ ] 所有 `@lifecycle` 方法包含 `**_`
- [ ] 所有 `@plugin_entry` 方法包含 `_ctx=None`
- [ ] 所有 `@ui.action` 方法包含 `_ctx=None`
- [ ] `@plugin_entry` + `@ui.action` 双装饰器叠加时，`@plugin_entry` 在上
- [ ] 没有 `keywords=` 参数在 `@plugin_entry` 中
- [ ] 没有 `executemany()` 调用
- [ ] `on_startup` 总耗时 < 10 秒
- [ ] 耗时操作在 `asyncio.create_task()` 中
- [ ] 数据库操作使用 `await session.execute()` + 同步 `cursor.fetchall()`
- [ ] 定时器中使用 `def`（非 `async def`）且包含 `asyncio.new_event_loop()`
- [ ] 共享状态使用 `threading.Lock` 保护
- [ ] 磁盘 I/O 使用 `asyncio.to_thread` 分离同步逻辑
- [ ] 启动时 `_ensure_tables` 是同步等待的（不是 `create_task`）
- [ ] 所有入口方法返回 `Ok(value)` 或 `Err(SdkError(msg))`
- [ ] `i18n.t()` 调用包含 `default` 参数
- [ ] 耗时任务使用 `self.report_status()` 报告进度
- [ ] 私有文件使用 `self.data_path()` 获取存储路径
- [ ] 本地文件 URL 使用 `file:///` + `os.sep` 替换
- [ ] save 操作的数值参数默认值能区分"未传入"和"有效值"

## 云端 API 集成 ⭐ 新增

- [ ] 第三方 SDK 用 try/except 导入，设置 `HAS_SDK` 标志
- [ ] 每个 API 调用前检查 SDK 可用、API Key 存在
- [ ] Backend 封装为独立类，与插件主类解耦
- [ ] `_init_sdk()` 在每次 API 调用前调用（配置可能已变）
- [ ] 错误处理用模式匹配给出针对性指引
- [ ] 错误消息包含当前配置上下文
- [ ] 健康检查方法返回 `(bool, str)` 元组
- [ ] `save_api_config` 保存后立即做健康检查
- [ ] 健康检查结果在返回值中明确传递
- [ ] UI 端根据健康检查结果区分成功/失败提示
- [ ] 轮询操作设上限 + 日志 + 区分终态
- [ ] 异步任务用 `asyncio.sleep` 不阻塞事件循环

## 多面板架构 ⭐ 新增

- [ ] 功能复杂的插件考虑多面板架构
- [ ] 每个面板有独立的 Context ID
- [ ] 每个 Context 只返回其面板需要的数据
- [ ] Context 中包含健康检查结果（实时连接状态）
- [ ] 提供布尔判断字段供 UI 条件渲染
- [ ] 配置保存后同时更新：内存 → settings 系统 → Backend
- [ ] 所有修改状态的 action 加 `refresh_context=True`
- [ ] `save_api_config` 保存后立即做健康检查并返回结果
- [ ] 主面板标签页不超过 5 个
- [ ] 独立设置面板和主面板设置标签页共享同一个 save action
- [ ] save action 同时支持平铺参数和 config 对象两种格式
- [ ] 区分 config（配置项）和 store（运行时数据）的使用场景
- [ ] startup/reload/config_change 都恢复配置

## 权限体系

- [ ] 所有权限默认 `false`
- [ ] 有总开关（如 `enable_ops`）
- [ ] 有逐操作授权（如 `allow_read`, `allow_move`, `allow_delete`）
- [ ] 每个入口方法调用 `_check_op_allowed` 检查权限
- [ ] 权限检查包含路径范围验证
- [ ] 权限检查包含保护列表验证
- [ ] `on_reload` 和 `on_config_change` 正确读取权限
- [ ] 权限拒绝时返回引导性错误消息

## AI 友好设计

- [ ] `@plugin_entry` 的 `description` 包含：何时调用 + 前置条件 + 注意事项
- [ ] `description` 中用 ⚠️ 标记关键警告
- [ ] `input_schema` 的 `required` 只包含真正必填的参数
- [ ] 所有路径参数在代码中检查 `os.path.isabs()`
- [ ] 非绝对路径时返回引导性错误消息（告诉 AI 先用 search_files）
- [ ] 路径不存在时建议用 `search_files` 或 `scan_folder_context`
- [ ] 权限/范围错误时给出具体操作指引
- [ ] 返回值中包含验证信息（如 `result_exists`）
- [ ] 设置了 `llm_result_fields` 指定返回字段
- [ ] 错误消息包含三要素：发生了什么 + 为什么 + 怎么做

## 路径处理

- [ ] 拒绝非绝对路径（`os.path.isabs()` 检查）
- [ ] 路径范围检查使用 `rstrip(os.sep)` 避免根目录 Bug
- [ ] 路径大小写不敏感（`.lower()` 后比较）
- [ ] 目录删除时用 `LIKE` 匹配子路径

## UI 设置面板

- [ ] 使用 `useLocalState` 而非 `useState`
- [ ] 使用 `ActionButton` 而非 `Button`
- [ ] 使用 `DataTable` 而非 `Table`
- [ ] `Text` 的 `color` 只用 `primary/secondary/muted`
- [ ] 缓存 `actions` 数组避免按钮消失
- [ ] 提供 ActionButton 后备方案（加载中…）
- [ ] 每个 `useLocalState` 的 key 唯一
- [ ] 数组字段用 `Textarea` 展示（换行分隔）
- [ ] 子权限开关在总开关开启后才显示（条件渲染）

## 富交互 UI 组件 ⭐ 新增

- [ ] `useLocalState` key 全局唯一，使用有意义的前缀
- [ ] 惰性初始化用函数形式：`useLocalState("key", () => defaultValue)`
- [ ] 列表项状态 key 包含唯一 id
- [ ] DOM 元素引用用 `document.getElementById()`（非 `useRef`）
- [ ] 音频/视频事件在 `onCanPlay` 中绑定，使用标志位防重复
- [ ] 内联样式常量定义在组件外部
- [ ] 颜色用 hex 值，透明度用 `opacity` 属性
- [ ] `Grid` 用 `style={{ gridColumn: "span X" }}` 控制列宽
- [ ] 原生 HTML 元素的事件回调做类型断言
- [ ] `ActionForm` 的 `schema.properties` 与 Python `input_schema` 一致
- [ ] `onResult` 中调用 `api.refresh()` 刷新数据
- [ ] `onSubmit` 中设置 loading 状态，`onResult` 中重置
- [ ] 条件渲染覆盖 loading、空状态、错误、成功四种状态
- [ ] Action 不可用时提供降级 UI
- [ ] 列表超 3 条时提供搜索过滤
- [ ] 删除操作用红色样式 + `confirm()` 确认

## 撤销与日志

- [ ] 每种操作类型都有对应的撤销逻辑
- [ ] 操作失败时不入撤销栈
- [ ] 撤销失败时推回栈项
- [ ] 撤销栈有最大容量限制
- [ ] 操作日志记录：action、source_path、dest_path、timestamp、success、error_msg
- [ ] 危险操作有特殊标记（`is_dangerous`）
- [ ] 操作后同步更新索引数据库
- [ ] 关键事件通过 `push_message` 通知

## 性能

- [ ] 大表有关键索引（搜索字段、排序字段）
- [ ] 批量操作使用 `BATCH_SIZE` 分批提交
- [ ] 增量更新比全量更新更高效
- [ ] 编码检测有多层回退（utf-8 → gbk → shift_jis → big5 → latin-1）
- [ ] 冻结状态检查在定时器和耗时操作中

## 测试

- [ ] Mock 了 SDK 模块（`plugin.sdk.plugin`）
- [ ] 覆盖了所有权限的拒绝和允许
- [ ] 覆盖了所有操作类型
- [ ] 覆盖了错误路径（空参数、相对路径、不存在路径）
- [ ] 覆盖了边界条件（空数据库、空列表）
- [ ] 覆盖了生命周期方法
- [ ] 有集成测试（多步骤操作链）
- [ ] 测试完成后删除测试文件

## 部署

- [ ] 所有修改的文件同步到运行目录
- [ ] `__init__.py` 在运行目录中无 BOM
- [ ] `plugin.toml` 配置项与代码一致
- [ ] 运行目录中无多余旧文件
- [ ] 目录名与 `entry` 包名一致
- [ ] 已重启 N.E.K.O
- [ ] 日志无错误
- [ ] 设置面板正常显示 + 按钮可点击
- [ ] AI 入口功能正常（通过 N.E.K.O 对话测试）

## 文档

- [ ] `plugin.toml` 的 `keywords` 覆盖用户可能说法
- [ ] `docs/guide.md` 包含所有配置项说明
- [ ] `README.md` 包含使用说明
- [ ] `i18n/zh-CN.json` 和 `i18n/en.json` key 完全一致
- [ ] 每个 `@plugin_entry` 的 `description` 清晰完整

## Logger 日志系统 ⭐ 新增

- [ ] 使用 `self.logger` 而非 `loguru`
- [ ] 异常记录使用 `self.logger.exception()`（自动附加 traceback）
- [ ] 不使用 `print()` 做日志输出
- [ ] 敏感信息（api_key/token/password）不出现在日志中
- [ ] DEBUG 级别日志有惰性求值保护

## 数据持久化 ⭐ 新增

- [ ] 少量配置/状态（< 1KB）用 `self.store`
- [ ] 大量结构化数据用 `self.db`（SQLite）
- [ ] 二进制文件用 `self.data_path()` + 直接文件 I/O
- [ ] 运行时状态用 `self.state`（PluginStatePersistence）
- [ ] `self.store` 无并发写入问题
- [ ] 数据库操作使用 `unwrap(await self.db.session())` 模式
- [ ] 批量插入分批（BATCH_SIZE=500）+ 逐行 execute + 分批 commit

## i18n 国际化 ⭐ 新增

- [ ] 所有用户可见文本通过 `self.i18n.t()` 获取
- [ ] 所有 `self.i18n.t()` 调用包含 `default` 参数
- [ ] i18n 调用有 try/except 安全包装
- [ ] UI 装饰器中使用 `tr()` 函数
- [ ] 所有语言文件的 key 完全一致
- [ ] 翻译键命名遵循分层规范（actions./errors./ui./status./notifications.）

## ZMQ 进程通信 ⭐ 新增

- [ ] 大文件不通过 ZMQ 传输（用 `file://` URL）
- [ ] 循环中不频繁调用 `call_entry`（考虑批量接口）
- [ ] 返回值中无不可序列化的对象
- [ ] `on_stop` 中清理了自定义的后台线程/进程
- [ ] 子进程崩溃时不会导致宿主进程崩溃

## 配置系统 ⭐ 新增

- [ ] `[settings]` 节、`DEFAULT_CONFIG`、UI `State` 类型三处 key 一致
- [ ] `update_own_config` 使用点号路径（`"settings.xxx"`）而非整个对象
- [ ] `on_config_change` 中 `.get(key, current_value)` 有默认值
- [ ] 启动时检查并补充缺失的配置项（配置漂移防范）
- [ ] 所有配置项在 `[settings]` 中有默认值
- [ ] `config_change` 钩子正确恢复所有配置到实例变量