# 29 — 插件生命周期内部机制

> **来源**：N.E.K.O-main `plugin/core/` + `plugin/server/lifecycle.py` 深度逆向分析  
> **适用**：理解插件在宿主中的完整生命周期，排查启动/停止相关 bug

---

## 1. 生命周期总览

插件在 N.E.K.O 中的完整生命周期分为 7 个阶段：

```
[扫描] → [加载] → [初始化] → [启动] → [运行] → [停止] → [卸载]
 scan     load      init      start     run      stop     unload
```

每个阶段由 `PluginHost` / `PluginProcessHost` 驱动，通过 ZMQ 传输层与子进程通信。

---

## 2. 阶段一：扫描 (Scan)

### 触发方式
- N.E.K.O 启动时自动扫描 `plugins/` 目录
- 管理员通过 API 手动触发 `scan_plugins`

### 执行流程（`registry.py`）

```
1. 遍历 plugins/ 下所有子目录
2. 查找每个目录下的 plugin.toml
3. 解析 TOML → PluginMeta 对象
4. 验证必需字段（name, version, entry 等）
5. 与已注册插件对比（新增/更新/删除）
6. 将元数据写入 GlobalState.plugin_registry
```

### 关键验证项
- `entry` 字段指向的 Python 包必须存在
- `plugin.toml` 格式正确（TOML 语法）
- 插件名不与其他插件冲突
- 版本号格式合法

### 常见错误
| 错误 | 原因 |
|------|------|
| `PluginEntryDirectoryMismatch` | 目录名 ≠ entry 包名 |
| `InvalidPluginToml` | TOML 语法错误 |
| `DuplicatePluginName` | 插件名重复 |

---

## 3. 阶段二：加载 (Load)

### 执行流程（`host.py:PluginProcessHost.load_plugin()`）

```
1. 创建子进程（multiprocessing.Process）
2. 建立 ZMQ PAIR 通信通道
3. 发送 LOAD 命令 + 插件元数据
4. 子进程接收后：
   a. 动态 import entry 包（importlib.import_module）
   b. 查找被 @neko_plugin 装饰的类
   c. 实例化插件对象（传入 PluginContext）
   d. 收集所有 entry / event / lifecycle 处理器
   e. 注册到子进程内的 PluginChildRegistry
5. 子进程回复 LOAD_OK + 处理器清单
6. 宿主进程将处理器清单注册到 GlobalState
```

### 子进程加载关键点

```python
# 子进程端的简化逻辑
spec = importlib.util.spec_from_file_location(entry, plugin_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# 查找被 @neko_plugin 装饰的类
for name, obj in inspect.getmembers(module):
    if hasattr(obj, NEKO_PLUGIN_TAG):
        plugin_cls = obj
        break

# 实例化
plugin_instance = plugin_cls(ctx)
```

### 关键点
- **每个插件运行在独立子进程中**（进程隔离）
- **ZMQ PAIR socket** 用于双向通信
- **加载超时**：默认 30 秒，超时视为失败
- **import 错误**：子进程捕获后通过 ZMQ 传回宿主

---

## 4. 阶段三：初始化 (Init)

### 执行流程

```
1. 宿主发送 INIT 命令
2. 子进程调用 plugin_instance.on_init(**init_kwargs)
3. 子进程回复 INIT_OK 或 INIT_FAILED
```

### `on_init` 生命周期钩子

```python
@lifecycle("on_init")
async def on_init(self, **_):
    """插件初始化。此时：
    - self.ctx 已可用
    - self.config 已加载默认配置
    - self.db 已连接（如果启用）
    - self.store 已初始化
    - 但其他插件可能尚未加载
    """
    pass
```

### 典型用途
- 数据库迁移（建表）
- 从配置文件恢复状态
- 注册事件监听器
- 预热连接/缓存

### 注意事项
- **不要在此阶段调用其他插件**（其他插件可能尚未加载）
- **不要做耗时操作**（会阻塞整个初始化流程）
- **可以启动后台任务**：`asyncio.create_task(self._background_work())`

---

## 5. 阶段四：启动 (Start)

### 执行流程

```
1. 宿主发送 START 命令
2. 子进程调用 plugin_instance.on_start(**start_kwargs)
3. 子进程回复 START_OK 或 START_FAILED
```

### `on_start` 生命周期钩子

```python
@lifecycle("on_start")
async def on_start(self, **_):
    """插件启动。此时：
    - 所有插件已加载完毕
    - 可以调用其他插件（self.plugins.call_entry）
    - 可以注册动态 entry
    - 定时器开始生效
    """
    pass
```

### 典型用途
- 启动定时器/后台任务
- 注册动态 entry（如基于配置动态创建）
- 连接外部服务（WebSocket、API 等）
- 与其他插件建立协作关系

### 注意事项
- **启动超时 10 秒**：耗时操作丢 `asyncio.create_task()`
- **启动失败不会阻止其他插件**：单个插件启动失败不影响系统
- **定时器在 on_start 之后才开始触发**

---

## 6. 阶段五：运行 (Run)

运行阶段是插件的主要工作阶段，持续到插件被停止。

### 运行期间可用的操作

#### 接收调用
```python
@plugin_entry(id="do_something")
async def do_something(self, _ctx=None, *, param: str):
    """AI 或用户通过此入口调用插件"""
    return Ok({"result": param})
```

#### 推送消息
```python
await self.ctx.push_message(
    content="处理完成",
    visibility=["chat"],
    ai_behavior="respond"
)
```

#### 更新状态
```python
await self.ctx.update_status("处理中...", progress=0.5)
```

#### 触发事件
```python
await self.ctx.trigger_event("custom_event", data={"key": "value"})
```

#### 查询记忆
```python
memories = await self.ctx.query_memory(
    query="用户喜欢什么",
    limit=5
)
```

#### 调用其他插件
```python
result = await self.plugins.call_entry(
    "other_plugin:some_entry",
    args={"param": "value"}
)
```

### 运行期间的生命周期钩子

```python
@lifecycle("on_config_change")
async def on_config_change(self, config: dict, **_):
    """用户修改插件配置时触发"""
    self._api_key = config.get("api_key")

@lifecycle("on_freeze")
async def on_freeze(self, **_):
    """插件被冻结时触发（暂停所有活动）"""
    self._frozen = True

@lifecycle("on_unfreeze")
async def on_unfreeze(self, **_):
    """插件被解冻时触发"""
    self._frozen = False
```

---

## 7. 阶段六：停止 (Stop)

### 执行流程

```
1. 宿主发送 STOP 命令
2. 子进程调用 plugin_instance.on_stop(**stop_kwargs)
3. 子进程清理资源
4. 子进程回复 STOP_OK
5. 宿主标记插件为已停止
```

### `on_stop` 生命周期钩子

```python
@lifecycle("on_stop")
async def on_stop(self, **_):
    """插件停止。清理资源。"""
    await self._ws_client.close()
    self._running_tasks.clear()
```

### 典型用途
- 关闭 WebSocket 连接
- 取消后台任务
- 保存未持久化的数据
- 通知外部服务下线

---

## 8. 阶段七：卸载 (Unload)

### 执行流程

```
1. 宿主发送 UNLOAD 命令
2. 子进程调用 plugin_instance.on_unload(**unload_kwargs)
3. 子进程回复 UNLOAD_OK
4. 宿主终止子进程
5. 宿主从 GlobalState 中移除插件
```

### `on_unload` 生命周期钩子

```python
@lifecycle("on_unload")
async def on_unload(self, **_):
    """插件卸载。最终清理。"""
    pass
```

---

## 9. 进程通信架构

### ZMQ 传输层

```
宿主进程 (main_server)              子进程 (plugin process)
┌─────────────────────┐              ┌─────────────────────┐
│  PluginProcessHost  │              │  PluginChildRuntime │
│                     │   ZMQ PAIR   │                     │
│  HostTransport      │◄────────────►│  ChildTransport     │
│                     │   inproc://  │                     │
│  GlobalState        │              │  PluginInstance     │
└─────────────────────┘              └─────────────────────┘
```

### 通信协议

所有宿主↔子进程通信通过 JSON 消息：

```json
{
  "type": "command",
  "cmd": "CALL_ENTRY",
  "request_id": "uuid",
  "payload": {
    "entry_id": "do_something",
    "args": {"param": "value"}
  }
}
```

```json
{
  "type": "response",
  "request_id": "uuid",
  "status": "ok",
  "payload": {"result": "done"}
}
```

### 支持的命令类型
| 命令 | 方向 | 说明 |
|------|------|------|
| `LOAD` | Host→Child | 加载插件 |
| `INIT` | Host→Child | 初始化 |
| `START` | Host→Child | 启动 |
| `STOP` | Host→Child | 停止 |
| `UNLOAD` | Host→Child | 卸载 |
| `CALL_ENTRY` | Host→Child | 调用插件入口 |
| `CALL_LIFECYCLE` | Host→Child | 调用生命周期钩子 |
| `GET_STATUS` | Host→Child | 获取状态 |
| `SET_CONFIG` | Host→Child | 设置配置 |
| `PUSH_MESSAGE` | Child→Host | 推送消息 |
| `UPDATE_STATUS` | Child→Host | 更新状态 |
| `TRIGGER_EVENT` | Child→Host | 触发事件 |

---

## 10. 插件状态机

```
                    ┌─────────┐
                    │ UNKNOWN │
                    └────┬────┘
                         │ scan
                    ┌────▼────┐
                    │ SCANNED │
                    └────┬────┘
                         │ load
                    ┌────▼────┐
               ┌────│ LOADED  │────┐
               │    └────┬────┘    │
               │         │ init    │ unload
               │    ┌────▼────┐    │
               │    │ INITED  │    │
               │    └────┬────┘    │
               │         │ start   │
               │    ┌────▼────┐    │
               │    │ RUNNING ├────┤
               │    └────┬────┘    │
               │         │ stop    │
               │    ┌────▼────┐    │
               │    │ STOPPED ├────┘
               │    └─────────┘
               │
               └──── 错误状态：
                    ┌──────────┐
                    │  ERROR   │
                    │ CRASHED  │
                    └──────────┘
```

---

## 11. 常见生命周期陷阱

### 陷阱 29-1：on_init 中调用其他插件
```python
# ❌ 错误：其他插件可能尚未加载
@lifecycle("on_init")
async def on_init(self, **_):
    await self.plugins.call_entry("other_plugin:entry")

# ✅ 正确：在 on_start 中调用
@lifecycle("on_start")
async def on_start(self, **_):
    await self.plugins.call_entry("other_plugin:entry")
```

### 陷阱 29-2：on_start 中做耗时操作
```python
# ❌ 错误：阻塞启动
@lifecycle("on_start")
async def on_start(self, **_):
    await self._download_large_model()  # 10+ 秒

# ✅ 正确：丢到后台
@lifecycle("on_start")
async def on_start(self, **_):
    asyncio.create_task(self._download_large_model())
```

### 陷阱 29-3：忽略 on_stop 清理
```python
# ❌ 错误：不清理资源
@lifecycle("on_stop")
async def on_stop(self, **_):
    pass  # WebSocket 泄漏

# ✅ 正确：清理所有资源
@lifecycle("on_stop")
async def on_stop(self, **_):
    for task in self._bg_tasks:
        task.cancel()
    await self._ws.close()
```

### 陷阱 29-4：重复注册事件监听器
```python
# ❌ 错误：每次 on_start 都注册，重启后重复
@lifecycle("on_start")
async def on_start(self, **_):
    self.ctx.on_event("message", self._handler)

# ✅ 正确：在 on_init 中注册一次
@lifecycle("on_init")
async def on_init(self, **_):
    self.ctx.on_event("message", self._handler)
```

---

## 12. 调试生命周期

### 查看插件状态
```python
# 在插件内部
status = await self.ctx.get_status()
print(status.state)  # RUNNING / STOPPED / ERROR

# 通过 API
GET /api/plugins/{plugin_id}/status
```

### 日志级别
```python
self.logger.info("初始化完成")
self.logger.warning("配置缺失，使用默认值")
self.logger.error("连接外部服务失败")
self.logger.debug(f"内部状态: {self._internal_state}")
```

### 排查清单
1. ☐ 插件在哪个阶段失败？（看日志中的 LOAD/INIT/START 标记）
2. ☐ 子进程是否正常启动？（检查是否有 crash 日志）
3. ☐ ZMQ 连接是否正常？（检查是否有 timeout）
4. ☐ 是否有未捕获的异常？（检查子进程 stderr）
5. ☐ `on_init` 中是否调用了其他插件？
6. ☐ `on_start` 是否超时（>10秒）？
