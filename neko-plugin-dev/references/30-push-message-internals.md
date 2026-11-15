# 30 — Push Message（按官方源码重写）

> **依据**：`plugin/sdk/shared/core/context.py:390`（SDK 侧签名）、`plugin/core/context.py:846`（宿主侧签名，返回 `None`）、`plugin/core/context.py:1272`（`push_message_async`）、`plugin/sdk/shared/core/push_message_schema.py`（parts 形状与 v1→v2 翻译）、`plugin/settings.py:447`（载荷上限常量）、`docs/changelog/plugin-push-message-v2.md`。
>
> **修订说明**：旧版本把 `push_message` 写成 `async` 并对它 `await`（约 18 处），把带 `DeprecationWarning` 的 `content=` 当成「快捷用法」，还臆造了 priority 语义分档。另有外部审查报告声称存在 `submitted` 回执、`payload_too_large`、512KiB 上限与 `ctx.images.upload()`——**源码里都不存在**，本文不采纳这些说法。

## 1. 它是同步方法，返回 `None`

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

- **不要 `await`**：`await ctx.push_message(...)` 会抛 `TypeError`。
- **插件侧拿不到回执**：返回 `None`，没有 `submitted` / `payload_too_large` 之类的字段可检查。发送是否成功要看宿主日志与消息平面，不要写 `if receipt.submitted`。
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
