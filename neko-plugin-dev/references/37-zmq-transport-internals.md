# 37 — ZMQ 进程间传输（官方 main 基线）

> **依据（本技能包唯一基线）**：官方 `Project-N-E-K-O/N.E.K.O` main `acfbdbc` 的 `plugin/core/zmq_transport.py` 文件头 `:1-32`、通道常量 `:55-76`、`_encode_uplink` `:113-122`。
>
> **这是宿主内部实现，插件作者不需要、也不应该直接依赖它。** 历史修订与勘误见 `REVIEW_FIXES.md`，那是存档，不参与当前规则判定。

## 1. 拓扑：四条 PUSH/PULL 通道

```text
Host (plugin host)                              Child (plugin process)
  PUSH ── downlink        (tcp://127.0.0.1:*) ──▶ PULL   # 命令 / 跨插件响应
  PULL ◀─ control uplink  (tcp://127.0.0.1:*) ── PUSH   # 结果 / 状态 / 跨插件请求（拒绝消息通道）
  PULL ◀─ message uplink  (tcp://127.0.0.1:*) ── PUSH   # 单条与批量插件消息
  PULL ◀─ image uplink    (tcp://127.0.0.1:*) ── PUSH   # 有上限的原始图片上传
```

- 四条**独立单向** PUSH/PULL 通道，替代早期的 `multiprocessing.Queue`；地址绑定后由 `LAST_ENDPOINT` 取实际端口。按 Queue 语义推导的行为不可靠。
- 不是 PAIR、不是 `inproc://`、不是纯 JSON。
- **下行用 `pickle`**（兼容既有宿主命令）；**上行用 `ormsgpack`（MessagePack）**——上行从不可信插件代码进入宿主，用不可执行宿主对象的编码，且每帧携带 **per-host token** 供宿主校验。两个方向都带 channel tag 供接收端分发。
- 图片上行是独立帧格式：JSON metadata + 单独 raw bytes 帧（避免把几 MB 重新打包进 MessagePack），token 放在 metadata 帧里，因此每条 child→host 通道都由同一个凭据把关。
- 每个 host socket 只解码自己允许的 channel 集合：control uplink 只收 `res` / `sts` / `comm`，message uplink 只收 `msg` / `msg_batch`。插件即便拿到 control endpoint，也无法借它绕过消息平面的大小上限。

## 2. Channel tag（7 个）

| tag | 方向 | 通道 | 用途 |
|---|---|---|---|
| `cmd` | host → child | downlink | 命令 |
| `res` | child → host | control uplink | 请求 / 响应结果 |
| `sts` | child → host | control uplink | 状态更新 |
| `comm` | child → host | control uplink | 插件间请求 |
| `msg` | child → host | message uplink | 单条插件消息 |
| `msg_batch` | child → host | message uplink | 批量插件消息 |
| `resp` | host → child | downlink | 插件间响应 |

常量定义在 `zmq_transport.py:56-62`；`_CONTROL_UPLINK_CHANNELS` / `_MESSAGE_UPLINK_CHANNELS` 在 `:68-70`。旧文档写的「2 条通道 / 6 个 tag / 只用 pickle / PAIR / JSON」均已废弃。

## 3. 实现要点（仅供排障）

- `HostTransport` 用 `zmq.asyncio.Context`，公开 send/recv 是协程；`ChildTransport` 用同步 `zmq.Context` 的 PUSH socket 上报、PULL 接收下行。
- 上行打包选项 `OPT_NON_STR_KEYS | OPT_PASSTHROUGH_TUPLE | OPT_SERIALIZE_NUMPY | OPT_SERIALIZE_PYDANTIC`；**解包必须带 `OPT_NON_STR_KEYS`**，否则非字符串 map key 会触发 `ValueError: invalid type U16`，导致 `CH_RES` 到不了 `_dispatch_result`、调用方只看到超时。
- 上行有 `_refuse_oversized_uplink_frame` 尺寸闸门；`CH_RES` 超限时会被替换成 `RESULT_TOO_LARGE` 错误帧，而不是让 future 悬空。
- 设置了 `LINGER` / `SNDHWM` / `RCVHWM` 与接收超时；这些参数随版本调整，不要照抄数值。

## 4. 对插件作者的结论

1. 插件代码只通过 `self.ctx` / 公开 SDK facade 与宿主交互，**不要 import `plugin.core.zmq_transport`**。
2. 消息推送用同步的 `ctx.push_message(...)`（见 `30-push-message-internals.md`），不是自己发 ZMQ 帧；大图用 `await ctx.images.upload(...)` 走图片上行。
3. 跨插件调用用 `self.plugins.call_entry(...)`（见 `28-inter-plugin-communication.md`），不是自己构造 `comm` 帧。
4. 遇到 IPC 故障，先看宿主日志与 `neko-plugin check`，不要按「PAIR / JSON / 12 种命令」的旧模型排查。

> 本篇不复述未经证实的「12 种命令类型与超时表」「子进程崩溃自动重启策略」。序列化方式、通道数与具体参数随版本变化，以目标版本 `plugin/core/zmq_transport.py` 为准；本技能包事实一律锁定官方 main `acfbdbc`。
