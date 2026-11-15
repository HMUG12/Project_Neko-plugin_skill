# 30 — Push Message（官方 main 基线）

> **依据（本技能包唯一基线）**：官方 `Project-N-E-K-O/N.E.K.O` main `acfbdbc`（2026-11-15 只读核对）：`plugin/sdk/shared/core/context.py:463-541`（`PushMessageResult`）、`plugin/settings.py:588`（512 KiB）、`plugin/sdk/shared/core/push_message_schema.py`、`docs/plugins/push-message.md`、`docs/plugins/migration-v0.9.md`。
>
> 本篇描述宿主内部机制；插件作者只用公开 SDK facade，**不要 import `plugin/core/*`**。写插件代码以 `docs/plugins/` 与 `plugin/sdk/plugin/` 的公开签名为准。历史修订与勘误见 `REVIEW_FIXES.md`，那是存档，不参与当前规则判定。

## 1. 同步方法，返回 `PushMessageResult`

```python
# plugin/sdk/shared/core/context.py:463
def push_message(self, *, visibility=None, ai_behavior=None, parts=None,
                 source="", priority=0, coalesce_key=None, ...) -> PushMessageResult:
```

- **不要 `await`**：它是普通 `def`，`await ctx.push_message(...)` 会抛 `TypeError`。需要非阻塞时用 `await self.ctx.push_message_async(...)`（`asyncio.to_thread` 包装）。
- **有本地提交回执**：返回 `PushMessageResult`，可直接判 `result["submitted"]` / `result.get("reason")`；`ok=False` 只是给旧调用方的兼容字段，新代码一律看 `submitted`。
- `submitted=False` 的 `reason` 是稳定枚举：`backpressure` / `transport_error` / `transport_unavailable` / `payload_too_large`。前三者描述传输状态，最后一个是**本地**在打包后测量并整条拒绝。
- **`submitted=True` 不是送达保证**：只表示 SDK 已把载荷交给本地权威提交路径并接管责任，**不代表宿主已消费、已显示或已送达**；宿主背压或进程重启仍可能静默丢弃。返回值不回显消息正文、异常文本或内部传输名。
- **v1 字段是 compatibility-only**：`message_type` / `description` / `content` / `binary_data` / `binary_url` / `mime` / `delivery` / `reply` / `unsafe` / `fast_mode` 会触发静态检查与运行时警告，**必须迁移，不要用 `# noqa` 压制**（`migration-v0.9.md` §Verification）。
- `priority` 是整数、默认 `0`；`docs/plugins/decorators.md:186` 说明它只影响展示顺序，**官方未定义 info/warning/紧急语义分档**，不要自拟。

## 2. 两轴正交模型

| 轴 | 取值 | 含义 |
|---|---|---|
| `visibility` | `["chat"]` / `["hud"]` / `["chat","hud"]` / `[]` | 用户在哪里**原样看到**插件 parts；空列表表示不直接展示。HUD 目前只渲染 text part |
| `ai_behavior` | `respond` / `read` / `blind` | LLM 立即生成一轮 / 纳入上下文稍后提及 / 完全忽略 |

`coalesce_key` 是**可选、显式开启**的合并键：同一 key 的主动提示折叠为最新一条；不设置就永不合并。不同类别的提示用不同 key。

## 3. parts 形状（`push_message_schema.py`）

```text
{"type": "text",  "text": str}
{"type": "image", "data": bytes, "mime": str}   # 内联，SDK 转成 binary_base64
{"type": "image", "url":  str,   "mime": str}   # 远端 / images.upload() 返回的临时 URL
{"type": "audio", "data": bytes, "mime": str} / {"type": "audio", "url": str, "mime": str}
{"type": "video", "url":  str,   "mime": str}
{"type": "ui_action", "action": "media_play_url", "url": str, "media_type": "audio", ...}
```

`data: bytes` 由 SDK 转成 `binary_base64: str`（`push_message_schema.py:158-170`），以便消息平面序列化承载；下游以 `binary_base64` 为准。`ui_action` 的 `media_play_url` 明确支持 url。其余 url 型媒体能否渲染取决于宿主路径，**以目标版本实测为准**，不要假设任意外部 URL 都可用，也不要断言宿主一定有 SSRF 拒绝策略。

## 4. 正确写法

```python
result = self.ctx.push_message(
    visibility=["chat"],
    ai_behavior="blind",
    parts=[{"type": "text", "text": "任务已完成"}],
    source="my_plugin",
    priority=0,
)
if not result["submitted"]:
    self.logger.warning("message submission failed: %s", result.get("reason"))
```

角色占位符：进入对话通道的文本可以用 `{MASTER_NAME}` / `{LANLAN_NAME}`，由宿主在注入边界按会话展开；**不要**硬编码「用户 / 主人 / master」。

大图走独立媒体通道：

```python
image_part = await self.ctx.images.upload(image_bytes, mime="image/png")
# 再把 image_part 放进 parts；upload() 只准备当前运行时的临时资源，
# 不显示图片、不写入模型上下文、不触发回复，送达仍由 push_message 控制。
```

`images.upload()` 在线程池里把图片归一化为最长边 ≤2048 的 JPEG，源图 >32 MiB 或归一化后 >8 MiB 抛 `ValueError`（后者容易被忽略：噪点大图压缩后仍可能超 8 MiB）。Chat 显示另有**每推** 8 图 / 内联 8 MiB 上限，与 `ai_behavior="read"` 的暂存行为叠加时按官方 `push-message.md` 的预算表计算。

## 5. 载荷上限

- `MESSAGE_PLANE_PAYLOAD_MAX_BYTES` 默认 **512 KiB**（`plugin/settings.py:588` = `512 * 1024` = 524288，不是十进制 512 KB），可用 `NEKO_MESSAGE_PLANE_PAYLOAD_MAX_BYTES` 调整。
- 超限**本地拒绝整条 push**：`push_message()` 先打包测量再交给消息平面，返回 `submitted=False` + `reason="payload_too_large"`，同一条里的 text / `ui_action` 一起被拒。
- `data` 转 base64 会膨胀约 33%，大文件不要内联；优先用 `await ctx.images.upload()`。

## 6. 旧写法 → 新写法

| 旧（错误 / 弃用） | 新 |
|---|---|
| `await ctx.push_message(...)` | `ctx.push_message(...)` 或 `await ctx.push_message_async(...)` |
| 忽略返回值、假定一定送达 | 判 `result["submitted"]`，失败读 `result.get("reason")` |
| 把 `submitted=True` 当送达保证 | 只当「本地已提交」，另做业务层确认 |
| `content="hello"` | `parts=[{"type": "text", "text": "hello"}]` |
| `delivery="silent"` / `reply=True` | `ai_behavior="read"` / `visibility=["hud"]` |
| `binary_data=...` + `mime=...` | `parts=[{"type": "image", "data": raw, "mime": "image/png"}]` |
| 大图塞进 base64 `image` part | `await ctx.images.upload(bytes, mime=...)` 后用返回的 part |
| 硬编码「主人」 | `{MASTER_NAME}` |

## 7. 与其他文档的关系

`SKILL.md §5` 与 `07-gotchas.md` #37 是速查版；`37-zmq-transport-internals.md` 讲承载这些帧的传输层；`51-build-publish-and-market-review.md` 讲发布与验证门禁。HTML 卡片另见 `docs/plugins/chat-cards.md`（`await ctx.create_card()`）。

> **仍未核实**：`audio` / `video` part 在 AI 对话路径中的最终渲染行为、url 型媒体在下游的具体处理，需在你的目标 SDK 上实测；本文只写官方 main 源码与文档能证实的签名、回执与上限。
