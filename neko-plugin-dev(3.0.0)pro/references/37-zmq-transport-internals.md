# 37 — ZMQ 进程通信协议内部机制

> **来源**：N.E.K.O-main `plugin/core/zmq_transport.py` + `plugin/core/communication.py` 深度逆向分析  
> **适用**：理解宿主↔插件子进程的通信协议，排查跨进程调用问题

---

## 1. 架构概览

N.E.K.O 使用 **ZeroMQ PAIR socket** 在宿主进程和插件子进程之间建立双向通信：

```
宿主进程 (main_server)              子进程 (plugin process)
┌─────────────────────┐              ┌─────────────────────┐
│  PluginProcessHost  │              │  PluginChildRuntime │
│                     │   ZMQ PAIR   │                     │
│  HostTransport      │◄────────────►│  ChildTransport     │
│                     │  tcp://      │                     │
│  GlobalState        │  or inproc://│  PluginInstance     │
└─────────────────────┘              └─────────────────────┘
```

**关键设计决策**：
- **每个插件独立子进程**：通过 `multiprocessing.Process` 隔离
- **ZMQ PAIR 模式**：一对一双向通信，无路由开销
- **JSON 序列化**：所有消息使用 JSON 编码
- **请求-响应模式**：每个请求携带 `request_id`，响应匹配

---

## 2. 通信协议

### 消息格式

```json
// 请求（Host → Child）
{
  "type": "command",
  "cmd": "CALL_ENTRY",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "payload": {
    "entry_id": "do_something",
    "args": {"param": "value"}
  }
}

// 响应（Child → Host）
{
  "type": "response",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ok",
  "payload": {"result": "done"}
}

// 错误响应
{
  "type": "response",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "error",
  "error": "Entry not found: do_something",
  "error_type": "EntryNotFound"
}
```

### 命令类型

| 命令 | 方向 | 说明 | 超时 |
|------|------|------|------|
| `LOAD` | Host→Child | 加载插件代码 | 30s |
| `INIT` | Host→Child | 初始化插件 | 30s |
| `START` | Host→Child | 启动插件 | 10s |
| `STOP` | Host→Child | 停止插件 | 10s |
| `UNLOAD` | Host→Child | 卸载插件 | 10s |
| `CALL_ENTRY` | Host→Child | 调用入口方法 | 60s |
| `CALL_LIFECYCLE` | Host→Child | 调用生命周期钩子 | 30s |
| `GET_STATUS` | Host→Child | 获取状态 | 5s |
| `SET_CONFIG` | Host→Child | 设置配置 | 5s |
| `PUSH_MESSAGE` | Child→Host | 推送消息到 UI | — |
| `UPDATE_STATUS` | Child→Host | 更新插件状态 | — |
| `TRIGGER_EVENT` | Child→Host | 触发事件 | — |
| `QUERY_MEMORY` | Child→Host | 查询记忆 | 10s |
| `STORE_MEMORY` | Child→Host | 存储记忆 | 5s |

---

## 3. Transport 层实现

### HostTransport（宿主端）

```python
# 伪代码
class HostTransport:
    def __init__(self, plugin_id):
        self._ctx = zmq.Context()
        self._socket = self._ctx.socket(zmq.PAIR)
        self._socket.bind(f"tcp://127.0.0.1:{port}")

    async def send_command(self, cmd, payload):
        request_id = str(uuid.uuid4())
        msg = {"type": "command", "cmd": cmd, "request_id": request_id, "payload": payload}
        await self._socket.send_json(msg)
        return request_id  # 返回 request_id 用于匹配响应

    async def receive_response(self, request_id, timeout=30):
        poller = zmq.Poller()
        poller.register(self._socket, zmq.POLLIN)
        if poller.poll(timeout * 1000):
            msg = await self._socket.recv_json()
            if msg["request_id"] == request_id:
                return msg
        raise TimeoutError(f"Response timeout for {request_id}")
```

### ChildTransport（子进程端）

```python
# 伪代码
class ChildTransport:
    def __init__(self, port):
        self._ctx = zmq.Context()
        self._socket = self._ctx.socket(zmq.PAIR)
        self._socket.connect(f"tcp://127.0.0.1:{port}")

    async def receive_command(self):
        msg = await self._socket.recv_json()
        return msg

    async def send_response(self, request_id, status, payload):
        msg = {"type": "response", "request_id": request_id, "status": status, "payload": payload}
        await self._socket.send_json(msg)
```

---

## 4. 通信链路（以 CALL_ENTRY 为例）

```
用户/AI 调用插件
       │
       ▼
┌──────────────────────────────────────────┐
│ 1. main_server 接收请求                    │
│ 2. 查找 GlobalState 中的插件路由表          │
│ 3. 确定目标插件进程                        │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ 4. HostTransport.send_command(            │
│      "CALL_ENTRY",                        │
│      {"entry_id": "scan", "args": {...}}  │
│    )                                      │
│ 5. 通过 ZMQ PAIR 发送 JSON 消息            │
└──────────────┬───────────────────────────┘
               │  tcp://127.0.0.1:xxxxx
               ▼
┌──────────────────────────────────────────┐
│ 6. ChildTransport.receive_command()       │
│ 7. PluginChildRuntime 解析命令            │
│ 8. 查找并调用 plugin_instance.scan(...)   │
│ 9. 获取返回值 Ok({...})                   │
│ 10. ChildTransport.send_response(...)     │
└──────────────┬───────────────────────────┘
               │  tcp://127.0.0.1:xxxxx
               ▼
┌──────────────────────────────────────────┐
│ 11. HostTransport.receive_response(...)   │
│ 12. 解析响应，返回给调用者                  │
└──────────────────────────────────────────┘
```

---

## 5. 超时与重试

### 超时配置

```python
# 不同操作类型有不同超时
TIMEOUTS = {
    "LOAD": 30,
    "INIT": 30,
    "START": 10,
    "CALL_ENTRY": 60,      # 入口调用允许较长时间
    "CALL_LIFECYCLE": 30,
    "GET_STATUS": 5,       # 状态查询快速超时
    "QUERY_MEMORY": 10,
}
```

### 超时处理

```python
try:
    response = await transport.receive_response(request_id, timeout=60)
except TimeoutError:
    logger.error(f"Plugin {plugin_id} call timed out")
    # 标记插件为不健康
    GlobalState.mark_plugin_unhealthy(plugin_id)
    raise PluginTimeoutError(f"Plugin {plugin_id} did not respond in time")
```

---

## 6. 错误处理

### 子进程崩溃

```python
# 宿主端监控子进程
if not child_process.is_alive():
    logger.error(f"Plugin {plugin_id} process crashed")
    GlobalState.mark_plugin_crashed(plugin_id)
    # 触发自动重启（如果配置允许）
    if plugin_config.auto_restart:
        await restart_plugin(plugin_id)
```

### ZMQ 连接断开

```python
try:
    msg = await socket.recv_json()
except zmq.ZMQError as e:
    if e.errno == zmq.ETERM:
        logger.error(f"ZMQ context terminated for {plugin_id}")
    else:
        logger.error(f"ZMQ error for {plugin_id}: {e}")
```

---

## 7. 性能影响

### 序列化开销

所有 ZMQ 消息经过 JSON 序列化/反序列化。对于大数据：
- **文本消息**：开销可接受
- **二进制数据**：不应通过 ZMQ 传递（用 `file://` URL 代替）
- **大型列表**：考虑分页或使用 `file://` URL

### 往返延迟

每次 `CALL_ENTRY` 涉及 2 次 ZMQ 消息（请求 + 响应）+ JSON 序列化/反序列化：

```
典型延迟：1-5ms（本地 TCP）
大数据延迟：10-50ms（取决于 JSON 大小）
```

### 优化建议

```python
# ❌ 避免：循环中多次调用
for item in items:
    await self.plugins.call_entry("other:process", args={"item": item})

# ✅ 优化：批量调用
result = await self.plugins.call_entry("other:batch_process", args={"items": items})
```

---

## 8. 关键陷阱

### 陷阱 37-1：ZMQ 消息大小限制

```python
# ❌ 错误：发送超大数据
await self.push_message(parts=[{"type": "audio", "data": large_base64_string}])

# ✅ 正确：使用 file:// URL
audio_path = self.data_path("output") / "song.wav"
await self.push_message(parts=[{
    "type": "audio",
    "url": f"file:///{str(audio_path).replace(os.sep, '/')}",
    "mime": "audio/wav"
}])
```

### 陷阱 37-2：阻塞事件循环

ZMQ 的同步 `recv()` 会阻塞整个 asyncio 事件循环。框架内部使用 `zmq.asyncio` 来处理。

**插件开发者不需要直接操作 ZMQ**——所有通信通过 SDK 封装的 API 进行。

### 陷阱 37-3：子进程残留

```python
# 插件停止时确保子进程终止
@lifecycle("on_stop")
async def on_stop(self, **_):
    # 框架会自动清理 ZMQ 连接和子进程
    # 但如果有自定义的后台线程/进程，需要手动清理
    for task in self._bg_tasks:
        task.cancel()
```

---

## 9. 调试通信问题

### 症状诊断

| 症状 | 可能原因 | 检查项 |
|------|---------|--------|
| 插件调用超时 | ZMQ 消息丢失 | 检查子进程是否存活 |
| 响应为空 | JSON 序列化失败 | 检查返回值是否可序列化 |
| 连接被拒绝 | 端口冲突 | 检查端口是否被占用 |
| 插件崩溃 | 未捕获异常 | 检查子进程 stderr 日志 |

### 日志关键字

在日志中搜索以下关键字来定位通信问题：
- `ZMQError`
- `TimeoutError`
- `Connection refused`
- `Plugin process crashed`
- `response timeout`

---

## 相关文档

- [29-plugin-lifecycle-internals](29-plugin-lifecycle-internals.md) — 生命周期中的 ZMQ 通信
- [30-push-message-internals](30-push-message-internals.md) — push_message 的传输路径
- [31-bus-system-internals](31-bus-system-internals.md) — Bus 系统的 ZMQ 通信
- [28-inter-plugin-communication](28-inter-plugin-communication.md) — call_entry 跨进程调用
