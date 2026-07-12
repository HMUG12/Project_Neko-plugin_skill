# 19. LLM 对话工作流设计 — 让 AI 正确使用你的插件

> 基于 `ai_singer` 插件「用户说"我想听你唱歌"→ AI 检查配置→ 询问/选歌→ 联网搜歌词→ 调用演唱入口」的完整对话工作流。
> 涵盖多入口编排、前置检查模式、AI 行为引导、错误消息设计。

---

## 19.1 核心问题

在 N.E.K.O 中，用户通过**自然语言对话**与插件交互。LLM（大语言模型）作为中间层，需要理解用户意图，然后调用正确的插件入口。

**设计挑战**：
- LLM 不是开发者，需要通过 `description` 理解每个入口的用途
- LLM 不知道调用顺序，需要你设计"工作流骨架"
- LLM 可能跳过必要的前置步骤（如不检查配置就直接调用）
- LLM 可能传错参数格式

---

## 19.2 多入口编排模式

### 典型对话工作流

```
用户: "我想听你唱歌"
    │
    ▼
LLM 理解意图 → 匹配到 check_setup entry
    │
    ├── ready=false → LLM 告诉用户需要配置 API Key
    │
    └── ready=true → LLM 询问用户想听什么歌
            │
            ▼
        用户: "唱《月亮代表我的心》"
            │
            ▼
        LLM 联网搜索歌词 (web_search)
            │
            ▼
        LLM 调用 sing entry (song_name + lyrics)
            │
            ▼
        插件流式演唱 → 用户听到歌声
```

### 入口设计原则

| 原则 | 说明 | 示例 |
|------|------|------|
| **前置检查独立入口** | 把"能不能用"单独作为一个 entry | `check_setup` |
| **核心操作独立入口** | 实际执行业务逻辑 | `sing` |
| **变体入口委托核心** | `sing_cover`、`sing_live` 委托给 `sing` | 避免重复代码 |
| **description 描述工作流** | 告诉 LLM 何时调用、调用前要做什么 | ⚠️ 必须先调用 check_setup |

---

## 19.3 check_setup 模式 — 前置条件检查

这是**最重要的设计模式**。将"能否使用"检查封装为独立入口，让 LLM 在调用核心功能前先检查：

```python
@plugin_entry(
    id="check_setup",
    name="检查配置状态",
    description=(
        "⚠️ 当用户说「唱歌」「唱首歌」「我想听你唱歌」「来一首」等任何唱歌相关请求时，"
        "必须先调用此入口检查配置是否就绪。"
        "如果未就绪，引导用户在设置面板中配置 API Key 和音色。"
    ),
    input_schema={"type": "object", "properties": {}},
    llm_result_fields=["ready", "mimo_ok", "mimo_voice", "missing", "next_action"],
)
async def check_setup(self, _ctx=None, **_):
    mimo_ok, mimo_msg = False, ""
    if self._mimo:
        mimo_ok, mimo_msg = await self._mimo.health_check()

    missing = []
    if not mimo_ok:
        if not self._config.get("mimo_api_key"):
            missing.append("MiMo API Key")
        else:
            missing.append(f"MiMo 连接失败: {mimo_msg}")

    return Ok({
        "ready": mimo_ok,
        "mimo_ok": mimo_ok,
        "mimo_voice": self._config.get("mimo_voice", "冰糖"),
        "missing": missing,
        # ⚠️ 关键：next_action 字段指导 LLM 下一步做什么
        "next_action": (
            "配置就绪！当用户说「听你唱歌」时，询问用户想听什么歌（或根据对话上下文选择），"
            "然后联网搜索歌词，最后调用 sing 入口流式演唱。"
            if mimo_ok else
            f"需要先完成配置: {', '.join(missing)}。请引导用户去设置面板配置。"
        ),
    })
```

### check_setup 的设计要点

1. **description 中列举触发关键词**：帮助 LLM 判断何时调用
2. **返回 `ready` 布尔值**：LLM 直接判断能否继续
3. **返回 `missing` 列表**：告诉 LLM 缺什么，用于生成引导消息
4. **返回 `next_action`**：指导 LLM 下一步行为（这是最容易被忽略但最关键的设计）
5. **input_schema 为空对象**：不需要参数，纯查询

### next_action 的写法

```python
# ✅ 好：具体的、可操作的指导
"next_action": (
    "配置就绪！当用户说「听你唱歌」时，你可以询问用户想听什么歌"
    "（或根据对话上下文自动选择），然后联网搜索歌词，最后调用 sing 入口。"
)

# ❌ 差：模糊、无指导
"next_action": "可以唱歌了"
```

---

## 19.4 核心入口的 description 写法

```python
@plugin_entry(
    id="sing",
    name="N.E.K.O 唱歌（流式演唱）",
    description=(
        "⚠️ N.E.K.O 的核心演唱入口。"
        "当用户说「我想听你唱歌」「唱一首歌」「来一首」时，"
        "AI 应先调用 check_setup 确认配置就绪，"
        "然后询问用户想听什么歌（或根据对话上下文自动选择歌曲），"
        "联网搜索获取完整歌词，最后调用此入口。"
        "歌词会自动添加 (唱歌) 标签以触发唱歌模式。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "song_name": {"type": "string", "description": "歌曲名称"},
            "lyrics": {"type": "string", "description": "歌词内容（每行一句，需要完整歌词。AI 应通过联网搜索获取歌词后传入）"},
            "style": {"type": "string", "description": "演唱风格/情绪描述（如：温柔地唱、深情地唱、欢快地唱）"},
            "mimo_voice": {"type": "string", "description": "音色（冰糖/茉莉/苏打/白桦/Mia/Chloe/Milo/Dean），留空使用默认音色"},
        },
        "required": ["song_name", "lyrics"],
    },
    llm_result_fields=["success", "song_name", "total_lines", "lines_sung", "merged_audio_url"],
)
```

### description 三要素（再次强调）

| 要素 | 内容 | 在 description 中的位置 |
|------|------|----------------------|
| **何时调用** | 用户说"唱歌"等 | 开头 |
| **前置条件** | 先调用 check_setup → 询问用户 → 联网搜歌词 | 中间 |
| **注意事项** | 歌词每行一句，会自动添加 (唱歌) 标签 | 末尾 |

### input_schema description 写法

```python
# ✅ 好：告诉 LLM 如何获取数据
"lyrics": {
    "type": "string",
    "description": "歌词内容（每行一句，需要完整歌词。AI 应通过联网搜索获取歌词后传入）"
}

# ❌ 差：只描述格式
"lyrics": {
    "type": "string",
    "description": "歌词"
}
```

---

## 19.5 参数传递模式 — 委托入口

```python
# sing_cover 和 sing_live 直接委托给 sing，避免重复代码

@plugin_entry(id="sing_cover", ...)
@ui.action(label="🎤 翻唱歌曲", ...)
async def sing_cover(self, song_name="", artist="", lyrics="", mimo_voice="", _ctx=None, **__):
    if not lyrics.strip():
        return Err(SdkError("翻唱需要提供歌曲歌词。请先联网搜索该歌曲的完整歌词。"))
    full_name = f"{artist} - {song_name}" if artist else song_name
    return await self.sing(song_name=full_name, lyrics=lyrics, mimo_voice=mimo_voice)

@plugin_entry(id="sing_live", ...)
@ui.action(label="🎭 流式演唱", ...)
async def sing_live(self, song_name="", lyrics="", style="", voice="", _ctx=None, **__):
    return await self.sing(song_name=song_name, lyrics=lyrics, style=style, mimo_voice=voice)
```

**委托模式的好处**：
- 核心逻辑只写一次（`sing`）
- 变体入口提供不同的 description 和 UI label
- LLM 可以根据不同场景选择不同入口
- 保持 `llm_result_fields` 与核心入口一致

---

## 19.6 错误消息设计 — 引导而非阻塞

### 好的错误消息

```python
# 参数缺失时，告诉 LLM 如何获取
if not lyrics.strip():
    return Err(SdkError(
        "请提供歌词内容。AI 应通过联网搜索获取完整歌词后传入。"
    ))

# 后端不可用时，告诉 LLM 如何引导用户
if not mimo_ok:
    return Err(SdkError(
        f"MiMo V2.5 不可用: {mimo_msg}\n\n"
        "请在设置面板中配置 MiMo API Key（从 https://mimo.xiaomi.com/ 获取）。"
    ))

# 参数格式错误时，给出示例
if not song_name.strip():
    return Err(SdkError("请提供歌曲名称"))
```

### 坏的错误消息

```python
# ❌ 只说有问题，不说怎么做
return Err(SdkError("参数错误"))

# ❌ 只说缺什么，不说怎么获取
return Err(SdkError("缺少歌词"))

# ❌ 技术细节暴露给用户
return Err(SdkError(f"KeyError: 'lyrics' in dict.get()"))
```

---

## 19.7 llm_result_fields 设计

```python
llm_result_fields=["success", "song_name", "total_lines", "lines_sung", "merged_audio_url"]
```

**设计原则**：
- 只列出 LLM 需要知道的关键字段
- `success` 总是第一个（让 LLM 先判断成败）
- 不列出内部实现细节字段（如 `output_dir`、`sync_data_file`）
- 列出用户关心的结果（如 `song_name`、`lines_sung`）
- 如果返回列表数据，列出列表字段名

---

## 19.8 双装饰器模式（plugin_entry + ui.action）

```python
@plugin_entry(
    id="sing",
    name="N.E.K.O 唱歌",
    description="⚠️ ...",  # 给 LLM 看
    input_schema={...},
    llm_result_fields=[...],
)
@ui.action(
    label=tr("actions.sing.label", default="🎤 开始演唱"),
    tone="primary",
    refresh_context=True,
)
async def sing(self, ...):
    ...
```

**双装饰器的规则**：
1. `@plugin_entry` 在**上**，`@ui.action` 在**下**
2. `@plugin_entry` 定义 LLM 如何调用（description、input_schema）
3. `@ui.action` 定义 UI 如何展示（label、tone、按钮位置）
4. 两个装饰器共享同一个方法体
5. 方法签名必须兼容两种调用方式（LLM 传入命名参数，UI 传入 config 对象）

---

## 19.9 完整工作流模板

```python
# ═══ 工作流骨架 ═══
#
# 1. check_setup  — 前置检查（LLM 第一步必须调用）
# 2. save_api_config — 配置保存（用户手动配置时调用）
# 3. sing          — 核心操作（LLM 在确认配置就绪 + 获取歌词后调用）
# 4. sing_cover    — 变体操作（委托给 sing）
# 5. sing_live     — 变体操作（委托给 sing，向后兼容）
# 6. stop_sing_live — 中断操作
# 7. delete_song   — 管理操作
# 8. rename_song   — 管理操作
# 9. delete_all_songs — 管理操作


# check_setup 的 description 中描述完整工作流
description=(
    "⚠️ 当用户说「唱歌」「唱首歌」「我想听你唱歌」「来一首」等任何唱歌相关请求时，"
    "必须先调用此入口检查配置是否就绪。"
    "如果未就绪，引导用户在设置面板中配置 API Key 和音色。"
    "如果已就绪，询问用户想听什么歌（或根据对话上下文选择），"
    "联网搜索歌词，然后调用 sing 入口流式演唱。"
)

# sing 的 description 中重复前置条件
description=(
    "⚠️ 核心演唱入口。"
    "调用前必须先 check_setup 确认配置就绪，"
    "然后询问用户/选歌，联网搜索获取完整歌词。"
    "歌词会自动添加 (唱歌) 标签触发唱歌模式。"
)
```

**为什么要在多个入口重复描述工作流？**
- LLM 可能在任一入口处开始执行
- 每个入口的 description 是独立的上下文
- 冗余描述确保 LLM 无论从哪个入口切入都知道完整流程

---

## 19.10 常见 LLM 行为问题及对策

| 问题 | 原因 | 对策 |
|------|------|------|
| LLM 不调用 check_setup | description 不够明确 | 在 description 中用 ⚠️ 开头，写"必须先调用" |
| LLM 乱编歌词 | 没有联网搜索 | 在 lyrics 的 description 中写"应通过联网搜索获取" |
| LLM 传入相对路径 | 不理解绝对路径要求 | 在 description 中写"必须是绝对路径" |
| LLM 跳过必填参数 | input_schema required 不对 | 确保 required 包含所有必填字段 |
| LLM 调用错误的入口 | description 不够有区分度 | 每个入口的 description 明确场景 |
| LLM 忽略错误消息 | 错误消息不够有指导性 | 错误消息包含"请先..."的引导 |

---

## 19.11 检查清单

- [ ] 有独立的 `check_setup` 入口用于前置检查
- [ ] `check_setup` 返回 `ready` 布尔值 + `missing` 列表 + `next_action` 指导
- [ ] 核心入口的 `description` 包含：何时调用 + 前置条件 + 注意事项
- [ ] `description` 中用 ⚠️ 标记关键警告
- [ ] `input_schema` 的 `description` 告诉 LLM 如何获取参数值
- [ ] 参数缺失时的错误消息引导 LLM 如何获取
- [ ] 后端不可用时的错误消息引导用户如何配置
- [ ] 变体入口委托给核心入口，避免重复代码
- [ ] `llm_result_fields` 列出 LLM 需要的关键字段
- [ ] 双装饰器叠加时 `@plugin_entry` 在上
- [ ] 在多个相关入口的 description 中重复描述工作流
- [ ] 错误消息包含三要素：发生了什么 + 为什么 + 怎么做
