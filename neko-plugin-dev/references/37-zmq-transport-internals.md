# 37 — ZMQ 进程间传输（按官方源码重写）

> **依据**：`plugin/core/zmq_transport.py`（本地 N.E.K.O 主仓库快照，约 1–140 行）。
>
> **修订说明**：旧版本写的是「PAIR socket + inproc:// + JSON 序列化 + 12 种命令类型」，与源码不符，已整篇重写。**这是宿主内部实现，插件作者不需要、也不应该直接依赖它。**

## 1. 实际拓扑

```text
Host (user_plugin_server)                    Child (plugin process)
  PUSH  ── downlink (tcp://127.0.0.1:*) ──▶  PULL   # 命令 / 跨插件响应
  PULL  ◀─ uplink   (tcp://127.0.0.1:*) ──  PUSH   # 结果 / 状态 / 消息 / 请求
```

- 两条独立的 **PUSH/PULL** 单向通道，地址均为 `tcp://127.0.0.1:*`（绑定后由 `LAST_ENDPOINT` 取实际端口）。
- 不是 PAIR、不是 `inproc://`、不是 JSON。
- 本快照中消息用 **`pickle`** 序列化，并带 channel tag 供接收端分发（见 `zmq_transport.py` 文件头与 `send_command` 等实现）。上游较新版本的「消息平面」模块另用 `ormsgpack` / JSON，但那属于 `plugin/message_plane/*`，不是这个传输层。

## 2. Channel tag

| tag | 方向 | 用途 |
|---|---|---|
| `cmd` | host → child | 命令 |
| `res` | child → host | 请求 / 响应结果 |
| `sts` | child → host | 状态更新 |
| `msg` | child → host | 消息 |
| `comm` | child → host | 插件间请求 |
| `resp` | host → child | 插件间响应 |

## 3. 实现要点（仅供排障）

- `HostTransport` 用 `zmq.asyncio.Context`，公开 send/recv 都是协程；`ChildTransport` 用同步 `zmq.Context` 的 PUSH socket 上报，并用 PULL 接收下行。
- 设置了 `LINGER`、`SNDHWM` / `RCVHWM` 等参数，接收有超时参数。
- 它替换的是早期的 `multiprocessing.Queue`，所以旧文档里按 Queue 语义推导的行为不可靠。

## 4. 对插件作者的结论

1. 插件代码只通过 `self.ctx` / 公开 SDK facade 与宿主交互，**不要 import `plugin.core.zmq_transport`**。
2. 消息推送用同步的 `ctx.push_message(...)`（见 `30-push-message-internals.md`），不是自己发 ZMQ 帧。
3. 跨插件调用用 `self.plugins.call_entry(...)`（见 `28-inter-plugin-communication.md`），不是自己构造 `comm` 帧。
4. 遇到 IPC 相关故障，先看宿主日志与 `neko-plugin check`，不要按「PAIR / JSON / 12 种命令」的旧模型排查。

> 本篇不再复述未经证实的「12 种命令类型与超时表」「子进程崩溃自动重启策略」等细节。序列化方式与具体参数随版本变化，以目标版本 `plugin/core/zmq_transport.py` 为准。
