# 汇总检查清单

> 合并所有 11 篇文档中的检查清单，用于代码审查和上线前验证。

---

## 项目初始化

- [ ] `plugin.toml` 的 `id` 与目录名一致
- [ ] `entry` 的包名与目录名完全一致（全小写 + 下划线）
- [ ] `short_description` 和 `keywords` 中英文都写
- [ ] `[plugin.database] enabled = true`（如果需要数据库）
- [ ] `[plugin.store] enabled = true`（如果需要持久化配置）
- [ ] `[settings]` 节包含所有配置项，且有合理的默认值
- [ ] `__init__.py` 无 UTF-8 BOM（`python -c "py_compile.compile('__init__.py', doraise=True)"`）

## Python 后端

- [ ] 所有 `@lifecycle` 方法包含 `**_`
- [ ] 所有 `@plugin_entry` 方法包含 `_ctx=None`
- [ ] 所有 `@ui.action` 方法包含 `_ctx=None`
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