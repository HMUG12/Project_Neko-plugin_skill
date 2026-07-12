# 30 — Push Message 深度解析

> **来源**：N.E.K.O-main `plugin/sdk/shared/core/push_message_schema.py` 深度逆向分析  
> **适用**：理解插件消息推送的完整机制，掌握 visibility/ai_behavior 两轴模型

---

## 1. 核心概念：两轴正交模型

N.E.K.O v2 的消息推送使用两个正交轴来控制消息行为：

```
          visibility (用户看到什么)
          ─────────────────────────
          │ chat │ hud  │ []    │
──────────┼──────┼──────┼───────┤
respond   │ ✓    │ ✓    │ ✓     │  ← AI 立即回复
read      │ ✓    │ ✓    │ ✓     │  ← AI 读取但不回复
blind     │ ✗    │ ✗    │ ✗     │  ← AI 完全忽略
          ─────────────────────────
          ai_behavior (AI 如何处理)
```

- **visibility**：控制前端渲染位置
- **ai_behavior**：控制 LLM 是否/如何处理消息内容

---

## 2. push_message 完整签名

```python
async def push_message(
    self,
    # ─── v2 API（推荐） ───
    *,
    parts: list[dict] | None = None,       # 内容片段列表
    visibility: list[str] | None = None,   # ["chat", "hud"]
    ai_behavior: str = "respond",          # "respond" | "read" | "blind"
    coalesce_key: str | None = None,       # 合并键（相同 key 的消息会折叠）

    # ─── 简化文本消息 ───
    content: str | None = None,            # 快捷：纯文本内容
    description: str | None = None,        # 简短描述（HUD 显示用）

    # ─── 旧版 API（已废弃） ───
    message_type: str | None = None,       # 旧版消息类型
    delivery: str | None = None,           # 旧版投递方式
    reply: bool | None = None,             # 旧版回复标志
    binary_data: bytes | None = None,      # 旧版二进制数据
    binary_url: str | None = None,         # 旧版二进制 URL
    unsafe: bool | None = None,            # 旧版安全标志
) -> None:
```

---

## 3. Parts 结构详解

### 文本片段
```python
{"type": "text", "text": "你好，世界！"}
```

### 图片片段
```python
# 方式一：base64 编码（自动处理）
{"type": "image", "data": image_bytes, "mime": "image/png"}

# 方式二：URL
{"type": "image", "url": "https://example.com/image.png", "mime": "image/png"}
```

### 音频片段
```python
# 方式一：base64
{"type": "audio", "data": audio_bytes, "mime": "audio/wav"}

# 方式二：URL
{"type": "audio", "url": "https://example.com/audio.wav", "mime": "audio/wav"}
```

### 视频片段
```python
{"type": "video", "url": "https://example.com/video.mp4", "mime": "video/mp4"}
```

### UI Action 片段（前端副作用）
```python
# 播放媒体
{"type": "ui_action", "action": "media_play_url", "url": "file:///..."}

# 添加媒体白名单
{"type": "ui_action", "action": "media_allowlist_add", "url": "file:///..."}
```

---

## 4. visibility 详解

| 值 | 含义 | 使用场景 |
|----|------|---------|
| `["chat"]` | 在聊天区渲染 | 文本回复、对话内容 |
| `["hud"]` | 在 HUD（抬头显示）渲染 | 状态更新、通知 |
| `["chat", "hud"]` | 两处都渲染 | 重要消息需双重展示 |
| `[]`（空列表） | 用户不直接看到 parts | 纯后台数据，只给 AI 看 |

### 配合 ai_behavior 的空 visibility

```python
# 静默喂数据给 AI，用户看不到
await ctx.push_message(
    parts=[{"type": "text", "text": "[系统] 后台任务完成"}],
    visibility=[],           # 不显示
    ai_behavior="respond"    # 但触发 AI 回复
)
```

---

## 5. ai_behavior 详解

| 值 | 含义 | LLM 行为 | 使用场景 |
|----|------|---------|---------|
| `"respond"` | 响应 | 喂入 LLM + **触发 AI 回合** | 用户消息、需要 AI 回复的事件 |
| `"read"` | 已读 | 喂入 LLM + **不触发回合** | 系统通知、后台数据 |
| `"blind"` | 盲 | **不喂入 LLM** | 纯 UI 更新、HUD 通知 |

### 行为组合示例

```python
# 场景1：插件完成任务，通知用户并让 AI 总结
await ctx.push_message(
    parts=[{"type": "text", "text": "[插件] 歌曲生成完成，文件: song.wav"}],
    visibility=["chat"],
    ai_behavior="respond"  # 用户看到 + AI 回复
)

# 场景2：后台状态更新，只记录不给用户看
await ctx.push_message(
    parts=[{"type": "text", "text": "[插件] 缓存刷新完成"}],
    visibility=[],         # 不显示
    ai_behavior="read"     # AI 知道但不回复
)

# 场景3：纯 UI 通知
await ctx.push_message(
    parts=[{"type": "text", "text": "下载进度: 50%"}],
    visibility=["hud"],    # 只在 HUD 显示
    ai_behavior="blind"    # AI 不需要知道
)
```

---

## 6. coalesce_key — 消息合并

相同 `coalesce_key` 的排队消息会被折叠为最新的：

```python
# 进度更新：只保留最新的一条
for i in range(100):
    await ctx.push_message(
        content=f"进度: {i}%",
        coalesce_key="task_progress",  # 相同 key
        visibility=["hud"],
        ai_behavior="blind"
    )
    await asyncio.sleep(0.1)
# 最终只有 "进度: 99%" 被显示
```

---

## 7. 内部转换机制

### 从旧版 API 到 v2 的映射

`translate_push_message()` 函数处理所有旧版→v2 的转换：

```python
# 旧版 delivery → 新版 (visibility, ai_behavior)
"reply"      → (["chat"], "respond")
"silent"     → (["chat"], "read")
"append"     → (["chat"], "respond")
"context"    → ([], "read")
"hud"        → (["hud"], "blind")
"notify"     → (["hud"], "respond")
"hud_silent" → (["hud"], "read")
```

### 二进制数据编码

```python
# parts 中的 bytes 数据会被自动编码为 base64
# 内部：{"type": "image", "data": b"..."}
# 线格式：{"type": "image", "binary_base64": "base64string", "mime": "image/png"}
```

---

## 8. 旧版 API 迁移指南

### 旧版 → 新版对照

| 旧版 | 新版 |
|------|------|
| `push_message("hello", reply=True)` | `push_message(content="hello", visibility=["chat"], ai_behavior="respond")` |
| `push_message("note", delivery="silent")` | `push_message(content="note", visibility=["chat"], ai_behavior="read")` |
| `push_message("status", delivery="hud")` | `push_message(content="status", visibility=["hud"], ai_behavior="blind")` |
| `push_message(binary_data=img)` | `push_message(parts=[{"type": "image", "data": img, "mime": "image/png"}])` |
| `push_message(content="x", description="摘要")` | `push_message(content="x", description="摘要")` ✅ 仍支持 |

### 废弃警告

使用旧版参数会在日志中产生 `DeprecationWarning`：
- `delivery` — 将在 v0.9 移除
- `reply` — 将在 v0.9 移除
- `message_type` — 将在 v0.9 移除
- `binary_data` / `binary_url` — 将在 v0.9 移除

---

## 9. 完整示例

### 示例1：多 part 消息
```python
@plugin_entry(id="show_result")
async def show_result(self, _ctx=None, *, text: str, image_path: str):
    with open(image_path, "rb") as f:
        img_data = f.read()

    await self.ctx.push_message(
        parts=[
            {"type": "text", "text": text},
            {"type": "image", "data": img_data, "mime": "image/png"}
        ],
        visibility=["chat"],
        ai_behavior="respond"
    )
    return Ok({"status": "sent"})
```

### 示例2：进度报告
```python
@plugin_entry(id="long_task")
async def long_task(self, _ctx=None):
    for i in range(10):
        # 模拟耗时操作
        await asyncio.sleep(1)

        await self.ctx.push_message(
            content=f"已完成 {i+1}/10 步",
            coalesce_key="task_progress",
            visibility=["hud"],
            ai_behavior="blind"
        )

    await self.ctx.push_message(
        content="任务完成！",
        visibility=["chat"],
        ai_behavior="respond"
    )
    return Ok({"done": True})
```

### 示例3：媒体播放
```python
@plugin_entry(id="play_music")
async def play_music(self, _ctx=None, *, file_path: str):
    # 1. 添加媒体白名单
    await self.ctx.push_message(
        parts=[{
            "type": "ui_action",
            "action": "media_allowlist_add",
            "url": f"file:///{file_path}"
        }],
        visibility=[],
        ai_behavior="blind"
    )

    # 2. 触发播放
    await self.ctx.push_message(
        parts=[{
            "type": "ui_action",
            "action": "media_play_url",
            "url": f"file:///{file_path}"
        }],
        visibility=["chat"],
        ai_behavior="blind"
    )

    # 3. 发送文本
    await self.ctx.push_message(
        content="正在播放音乐...",
        visibility=["chat"],
        ai_behavior="respond"
    )
    return Ok({"playing": file_path})
```

---

## 10. 常见陷阱

### 陷阱 30-1：visibility 和 ai_behavior 冲突
```python
# ❌ 问题：用户看不到内容，但 AI 要回复，用户会觉得莫名其妙
await ctx.push_message(
    parts=[{"type": "text", "text": "秘密数据"}],
    visibility=[],         # 用户看不到
    ai_behavior="respond"  # AI 会回复（但用户不知道上下文）
)

# ✅ 正确：如果用户看不到内容，用 "read" 而非 "respond"
await ctx.push_message(
    parts=[{"type": "text", "text": "秘密数据"}],
    visibility=[],
    ai_behavior="read"     # AI 知道但不回复
)
```

### 陷阱 30-2：忘记添加媒体白名单
```python
# ❌ 错误：直接播放文件，前端可能拒绝
await ctx.push_message(
    parts=[{"type": "ui_action", "action": "media_play_url", "url": f"file:///{path}"}],
    ...
)

# ✅ 正确：先添加白名单
await ctx.push_message(
    parts=[{"type": "ui_action", "action": "media_allowlist_add", "url": f"file:///{path}"}],
    visibility=[], ai_behavior="blind"
)
await ctx.push_message(
    parts=[{"type": "ui_action", "action": "media_play_url", "url": f"file:///{path}"}],
    ...
)
```

### 陷阱 30-3：大数据量 base64 编码
```python
# ❌ 问题：大文件 base64 编码后体积膨胀 33%
large_audio = open("song.wav", "rb").read()  # 10MB
await ctx.push_message(
    parts=[{"type": "audio", "data": large_audio, "mime": "audio/wav"}],
    ...
)  # 线格式约 13.3MB，可能超时

# ✅ 正确：大文件用 URL
await ctx.push_message(
    parts=[{"type": "audio", "url": "file:///path/to/song.wav", "mime": "audio/wav"}],
    ...
)
```
