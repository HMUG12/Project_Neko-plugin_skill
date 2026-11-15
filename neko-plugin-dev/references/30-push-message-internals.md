# 30 — Push Message（旧快照基线；新版差异见 §0）

> ## 0. 版本代差（先读）
> 本篇依据**工作区本地旧快照** `N.E.K.O-main (1)`：`plugin/sdk/shared/core/context.py:390`、`plugin/core/context.py:846`（`-> None`）、`plugin/core/context.py:1272`（`push_message_async`）、`plugin/settings.py:447`（**256 KiB**）、`docs/changelog/plugin-push-message-v2.md`。
>
> **官方 `Project-N-E-K-O/N.E.K.O` main `acfbdbc`（2026-11-15）已演进**，与本篇冲突之处一律以官方新版为准：
> - `push_message(...) -> PushMessageResult`，返回**本地提交回执** `{"submitted": bool, "reason": ..., "ok": ...}`；`reason` 稳定取值为 `backpressure` / `transport_error` / `transport_unavailable` / `payload_too_large`。`submitted=True` 只表示 SDK 已把载荷交给本地权威提交路径并接管责任，**不代表宿主已消费、已显示或已送达**。
> - `MESSAGE_PLANE_PAYLOAD_MAX_BYTES` 默认 **512 KiB**（`plugin/settings.py:588` = `512 * 1024`，`NEKO_MESSAGE_PLANE_PAYLOAD_MAX_BYTES` 可调）；超限时**本地拒绝整条 push**，`submitted=False` + `reason=payload_too_large`，同一消息里的 text / `ui_action` 一起被拒。
> - 新增 `await ctx.images.upload(image_bytes, mime="image/png")`：线程池归一化（最长边 ≤2048 的 JPEG）后走独立媒体通道上传，返回 `image` part。源图 >32 MiB 抛 `ValueError`，归一化后 >8 MiB 也抛 `ValueError`；chat 侧另有每推 8 图 / 内联 8 MiB 上限。它**只准备临时资源**，不显示、不入模型上下文、不触发回复。
> - 新增 `docs/plugins/push-message.md`（官方完整规范）与 `docs/plugins/chat-cards.md`（HTML 卡片，见 `51` 篇 / `SKILL.md §5`）。
> - `visibility` 可组合（如 `["chat","hud"]`）、`ai_behavior` 为 `respond / read / blind`；HUD 目前只渲染 text part。
>
> **修订说明**：旧版本曾把 `push_message` 写成 `async` 并 `await`（约 18 处），把 `content=` 当「快捷用法」，臆造 priority 语义分档——这些仍是错的。但早期外部审查报告提到的 `submitted` / `payload_too_large` / 512KiB / `ctx.images.upload()` **在官方新版确实存在**；上一轮以旧快照判其「不存在」是基线选择错误，见 `REVIEW_FIXES.md §9`。

## 1. 它是同步方法（旧快照返回 `None`）

SDK 侧（`plugin/sdk/shared/core/context.py:390`）是普通 `def`，宿主侧（`plugin/core/context.py:846`）签名标注 `-> None`。

```python
def push_message(self, *, visibility=None, ai_behavior=None, parts=None,
                 source="", target_lanlan=None, metadata=None, priority=0,
                 coalesce_key=None,
                 # v1 legacy：以下参数均会触发 DeprecationWarning
                 message_type=None, description=None, content=None,
                 binary_data=None, binary_url=None, mime=None, unsafe=False,
                 fast_mode=False, delivery=None, reply=None) -> None:
```

- **不要 `await`**：它是同步方法，`await ctx.push_message(...)` 会抛 `TypeError`（两版一致）。
- **回执有代差**：旧快照返回 `None`，插件侧拿不到回执；**官方新版返回 `PushMessageResult`**，可 `result["submitted"]` / `result.get("reason")`，但只能当「本地已提交」用。写兼容代码时先确认目标版本，不要在新版里断言「一定没有回执」，也不要在旧版里检查 `submitted`。
- 需要非阻塞时用 `await self.ctx.push_message_async(...)`，它用 `asyncio.to_thread` 包装同步调用（`plugin/core/context.py:1272`）。
- **v2 优先**：用 `parts`；`message_type` / `description` / `content` / `binary_data` / `binary_url` / `mime` / `delivery` / `reply` / `unsafe` 等 v1 参数都会告警，官方计划移除。
- `priority` 是整数，默认 `0`；**官方没有定义 info / warning / 紧急分档**，不要自行编造语义。

## 2. 两轴正交模型

| 轴 | 取值 | 含义 |
|---|---|---|
| `visibility` | `["chat"]` / `["hud"]` / `[]` | 用户在哪里**原样看到**插件 parts；空列表表示不直接展示 |
| `ai_behavior` | `respond` / `read` / `blind` | LLM 立即生成一轮 / 纳入上下文稍后提及 / 完全忽略（默认 `respond`） |

`coalesce_key` 是**可选、显式开启**的合并键：同一个 key 的主动提示会折叠为最新一条；不设置就永不合并。不同类别的提示用不同 key。

## 3. parts 形状（`push_message_schema.py`）

```text
{"type": "text",  "text": str}
{"type": "image", "data": bytes, "mime": str}   # 内联
{"type": "image", "url":  str,   "mime": str}   # 远端
{"type": "audio", "data": bytes, "mime": str} / {"type": "audio", "url": str, "mime": str}
{"type": "video", "url":  str,   "mime": str}
{"type": "ui_action", "action": "media_play_url", "url": str, "media_type": "audio", ...}
```

`data: bytes` 由 SDK 转成 `binary_base64`（`push_message_schema.py:96-108`），以便消息平面用 JSON 承载；下游应以 `binary_base64` 为准。

## 4. 正确写法

```python
self.ctx.push_message(
    visibility=["chat"],
    ai_behavior="blind",
    parts=[{"type": "text", "text": "任务已完成"}],
    source="my_plugin",
    priority=0,
)
```

角色占位符：进入对话通道的文本可以用 `{MASTER_NAME}` / `{LANLAN_NAME}`，由宿主在注入边界按会话展开（SDK 侧 docstring 说明）；**不要**硬编码「用户 / 主人 / master」。

## 5. 载荷上限与媒体 URL

- 消息平面有载荷上限：`plugin/settings.py:447` 的 `MESSAGE_PLANE_PAYLOAD_MAX_BYTES`，**默认 256 KiB**，可由环境变量 `NEKO_MESSAGE_PLANE_PAYLOAD_MAX_BYTES` 调整。不是审查报告说的 512 KiB。
- 超限由消息平面侧处理（`plugin/message_plane/ingest_server.py`），但插件调用 `push_message` 拿不到结构化错误返回。
- `data` 转 base64 会膨胀约 33%，大文件不要内联；优先减小体积或用宿主支持的媒体通道。
- `ui_action` 的 `media_play_url` 明确支持 url（`push_message_schema.py:253-267`）；其余 url 型媒体 part 能否被渲染取决于目标版本的宿主路径，**以实测为准**。不要假设任意外部 URL 都可用，也不要断言宿主一定有 SSRF 拒绝策略——审查报告里那条「AI 路径会拒绝任意外部 URL」在源码中查无依据。

## 6. 旧写法 → 新写法

| 旧（错误 / 弃用） | 新 |
|---|---|
| `await ctx.push_message(...)` | `ctx.push_message(...)` 或 `await ctx.push_message_async(...)` |
| `if receipt.submitted:` | 删掉，返回 `None` |
| `content="hello"` | `parts=[{"type": "text", "text": "hello"}]` |
| `delivery="silent"` / `reply=True` | `ai_behavior="read"` / `visibility=["hud"]` |
| `binary_data=...` + `mime=...` | `parts=[{"type": "image", "data": raw, "mime": "image/png"}]` |
| `ctx.images.upload(...)` | 不存在，改用上面的 image part |
| 硬编码「主人」 | `{MASTER_NAME}` |

## 7. 与其他文档的关系

`18-streaming-output.md`、`29-plugin-lifecycle-internals.md`、`31-bus-system-internals.md`、`37-zmq-transport-internals.md`、`50-market-plugin-reverse-engineering.md` 中曾出现 `await ...push_message`，本次修订已统一去掉 `await`。`SKILL.md` §5 与 `07-gotchas.md` #37 是速查版。

> **仍未核实**：`audio` / `video` part 在 AI 对话路径中的最终渲染行为、url 型媒体在下游的具体处理，均需在你的目标 SDK 上实测；本文只写源码能证实的签名与形状。
