# 18. 流式输出与进度推送模式

> 基于 `ai_singer` 插件流式演唱 + 逐句口型同步的实战经验。
> 涵盖逐项流式处理、实时消息推送、进度报告、音频拼接、viseme 口型同步等模式。

---

## 18.1 适用场景

- 插件需要逐项处理数据，每处理一项就推送结果给用户
- 需要实时报告处理进度（如"正在唱第 3/20 句..."）
- 需要在处理过程中推送媒体内容（音频、图片等）到聊天窗口
- 需要合并多项输出为最终结果

---

## 18.2 整体架构

```
用户请求 "唱一首歌"
    │
    ▼
┌──────────────────────────────────────┐
│  sing entry (主入口)                  │
│  ├── 1. 参数验证                      │
│  ├── 2. 后端健康检查                   │
│  ├── 3. 发送开场消息 (push_message)     │
│  ├── 4. 循环处理每一句:                 │
│  │   ├── report_status (进度)          │
│  │   ├── 合成单句音频                   │
│  │   ├── 生成口型数据                   │
│  │   ├── push_message (歌词+状态)       │
│  │   └── asyncio.sleep (句间停顿)       │
│  ├── 5. 合并所有音频                    │
│  ├── 6. 保存记录                        │
│  ├── 7. 发送结束消息                    │
│  └── 8. 返回结果                       │
└──────────────────────────────────────┘
```

---

## 18.3 流式处理核心循环

### 基本模式

```python
async def stream_process(self, items: list, output_dir: str):
    """逐项处理 + 实时推送的通用模式"""
    success_count = 0
    total_elapsed_ms = 0
    all_results = []

    for idx, item in enumerate(items):
        line_num = idx + 1

        # 1. 报告进度
        self.report_status({
            "status": "processing",
            "progress": 5 + int(90 * line_num / len(items)),
            "message": f"正在处理第 {line_num}/{len(items)} 项..."
        })

        # 2. 执行单步处理
        try:
            result = await self._process_one(item, output_dir, line_num)
        except Exception as e:
            self.logger.warning("第 {} 项处理失败: {}", line_num, e)
            continue

        if not result:
            self.logger.warning("第 {} 项处理结果为空", line_num)
            continue

        # 3. 推送处理结果到聊天窗口
        self.push_message(
            source="plugin_id",
            visibility=["chat"],
            ai_behavior="blind",
            parts=[{
                "type": "text",
                "text": f"📦 **第 {line_num} 项已完成**\n{result['summary']}",
            }],
            priority=3,
        )

        all_results.append(result)
        success_count += 1

        # 4. 项间停顿（可选：模拟自然节奏或避免 API 限流）
        await asyncio.sleep(0.3)

    # 5. 汇总
    return success_count, all_results
```

### 进度计算技巧

```python
# ✅ 正确：5% 留给准备阶段，90% 用于处理阶段，5% 留给收尾阶段
progress = 5 + int(90 * line_num / len(lines))

# ✅ 更好：给不同阶段分配不同的权重区间
if phase == "prepare":
    progress = int(5 * line_num / len(lines))       # 0-5%
elif phase == "process":
    progress = 5 + int(85 * line_num / len(lines))  # 5-90%
elif phase == "finish":
    progress = 90 + int(10 * line_num / len(lines)) # 90-100%
```

---

## 18.4 push_message 详细用法

### 签名

```python
self.push_message(
    source: str,          # 消息来源标识（通常用 plugin_id）
    visibility: list,     # 可见范围：["chat"] 聊天窗口可见
    ai_behavior: str,     # AI 行为："blind" = AI 不处理此消息
    parts: list[dict],    # 消息内容（支持 text、image、audio 等类型）
    priority: int,        # 优先级：1-3=普通, 4-6=警告, 7-9=错误, 10=紧急
)
```

### 消息类型示例

```python
# 纯文本消息
self.push_message(
    source="ai_singer",
    visibility=["chat"],
    ai_behavior="blind",
    parts=[{"type": "text", "text": "🎵 消息内容"}],
    priority=3,
)

# 富文本消息（Markdown 格式）
self.push_message(
    source="ai_singer",
    visibility=["chat"],
    ai_behavior="blind",
    parts=[{
        "type": "text",
        "text": (
            f"🎭 **N.E.K.O 正在演唱：《{song_name}》**\n"
            f"音色：{voice} | 共 {total} 句\n"
            f"---"
        )
    }],
    priority=3,
)
```

### 消息推送频率控制

```python
# ⚠️ 不要逐字符推送
# ❌ 错误：太快太多，刷屏
for char in text:
    self.push_message(..., text=char)
    await asyncio.sleep(0.01)

# ✅ 正确：逐句推送，句间有自然停顿
for line in lines:
    # ... 处理当前句 ...
    self.push_message(..., text=f"🎵 **{line}**")
    breath_ms = max(200, min(800, estimated_duration_ms // 4))
    await asyncio.sleep(breath_ms / 1000)
```

---

## 18.5 report_status 用法

### 签名

```python
self.report_status(data: dict)
# data 中常用字段：
# - status: "processing" | "completed" | "error"
# - progress: int (0-100)
# - message: str (用户可见的状态描述)
```

### 完整流程示例

```python
# 开始
self.report_status({
    "status": "processing",
    "progress": 0,
    "message": "准备中..."
})

# 处理中（循环内）
for idx, item in enumerate(items):
    self.report_status({
        "status": "processing",
        "progress": 5 + int(90 * (idx + 1) / len(items)),
        "message": f"正在处理第 {idx + 1}/{len(items)} 项..."
    })

# 完成
self.report_status({
    "status": "completed",
    "progress": 100,
    "message": "处理完成！",
    # 可以附带额外数据
    "result_count": success_count,
    "output_path": merged_path,
})
```

### 日志中的 STATUS_UPDATE 格式

```
Plugin ai_singer status updated: {
  'type': 'STATUS_UPDATE',
  'plugin_id': 'ai_singer',
  'data': {
    'status': 'processing',
    'progress': 95,
    'message': '🎤 正在唱第 1/1 句...'
  },
  'time': '2026-07-12T04:30:53.416417Z'
}
```

---

## 18.6 音频处理模式

### 单句音频合成（asyncio.to_thread）

```python
async def synthesize(self, text: str, voice: str, output_path: str) -> Optional[str]:
    """异步合成单句语音

    关键：使用 asyncio.to_thread 避免阻塞事件循环。
    synthesize_sync 是纯同步函数，包含网络 I/O。
    """
    audio_bytes = await asyncio.to_thread(
        self.synthesize_sync, text, voice
    )
    if not audio_bytes:
        return None

    # 磁盘 I/O 用普通 open（在 asyncio 中是安全的，因为 bytes 已经拿到了）
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(audio_bytes)
    return output_path
```

### 音频时长估算

当 API 不返回精确时长时，需要估算：

```python
# 方法一：基于文件大小的粗略估算
estimated_duration_ms = 1000  # 默认 1 秒
try:
    file_size = os.path.getsize(result_path)
    data_size = file_size - 44  # 减去 WAV 头
    if data_size > 0:
        # 假设 22050 Hz 采样率，16-bit 单声道
        estimated_duration_ms = int(data_size / 22050 * 1000)
except Exception:
    pass

# 方法二：基于文本长度的经验估算
estimated_duration_ms = max(1000, int(len(text) / 2.5 * 1000))
# 中文约 2.5 字/秒（唱歌时更慢）
```

### 多段音频合并（纯 Python，无需 ffmpeg）

```python
@staticmethod
def _merge_wav_files(output_dir: str, count: int, merged_path: str) -> str:
    """用纯 Python 拼接多个 WAV 文件为单个文件

    避免依赖 ffmpeg，使用标准库 struct 解析和拼接 WAV。
    返回 file:// URL，失败返回空字符串。
    """
    import struct

    wav_data_list: list[bytes] = []
    sample_rate = 0
    num_channels = 1
    bits_per_sample = 16

    for i in range(1, count + 1):
        line_path = os.path.join(output_dir, f"line_{i:03d}.wav")
        if not os.path.exists(line_path):
            continue
        with open(line_path, "rb") as f:
            data = f.read()

        if len(data) < 44:
            continue

        # 验证 RIFF/WAVE 头
        riff, _, wave = struct.unpack_from("<4sI4s", data, 0)
        if riff != b"RIFF" or wave != b"WAVE":
            continue

        # 解析 fmt chunk
        fmt_size = struct.unpack_from("<I", data, 16)[0]
        if fmt_size < 16:
            continue
        fmt_data = struct.unpack_from("<HHIIHH", data, 20)
        audio_format, nc, sr, _, _, bps = fmt_data
        if audio_format != 1:  # 只处理 PCM
            continue
        if not sample_rate:
            sample_rate = sr
        if nc > 0:
            num_channels = nc
        if bps > 0:
            bits_per_sample = bps

        # 定位 data chunk
        pos = 20 + fmt_size
        while pos < len(data) - 8:
            chunk_id, chunk_size = struct.unpack_from("<4sI", data, pos)
            if chunk_id == b"data":
                audio_data = data[pos + 8 : pos + 8 + chunk_size]
                wav_data_list.append(audio_data)
                break
            pos += 8 + chunk_size

    if not wav_data_list:
        return ""

    if not sample_rate:
        sample_rate = 22050

    merged_audio = b"".join(wav_data_list)
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8

    # 构造 WAV 头
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(merged_audio),
        b"WAVE", b"fmt ", 16,
        1, num_channels, sample_rate,
        byte_rate, block_align, bits_per_sample,
        b"data", len(merged_audio),
    )

    with open(merged_path, "wb") as f:
        f.write(header)
        f.write(merged_audio)

    return f"file:///{merged_path.replace(os.sep, '/')}"
```

**合并音频的关键点**：
- 解析每个 WAV 的 RIFF 头 + fmt chunk + data chunk
- 只拼接 data chunk 的原始音频数据
- 重新构造一个统一的 WAV 头
- 使用 `file:///` 协议返回 URL，供前端 `<audio>` 标签使用

---

## 18.7 口型同步 (Viseme) 数据生成

### 数据结构

```python
@dataclass
class LyricLine:
    text: str
    start_ms: int = 0
    end_ms: int = 0
```

### Viseme 序列

```python
@staticmethod
def _text_to_visemes(text: str, total_ms: int) -> list:
    """将文本转换为口型序列

    简单映射规则（中文拼音口型）:
    - 开口音 (a/ang/an/ai/ao 等) → 3 (全开)
    - 半开音 (e/en/eng/ei/er/o/ou 等) → 2 (半开)
    - 微开音 (i/in/ing/ü) → 1 (微张)
    - 闭口音 (b/p/m/f, 标点/空格) → 0 (闭嘴)
    - 默认 → 1 (微张)

    返回: [{"time_ms": 0, "viseme": 0}, {"time_ms": 100, "viseme": 2}, ...]
    """
    # 清理括号内的标签文本
    clean_text = re.sub(r'[\(\（][^\)\）]*[\)\）]', '', text)
    clean_text = re.sub(r'\[[^\]]*\]', '', clean_text)
    chars = list(clean_text) if clean_text else list(text)

    char_duration = max(50, total_ms // max(1, len(chars)))
    visemes = []
    current_time = 0

    for ch in chars:
        viseme_level = 1  # 默认微张

        # 标点和空白 → 闭嘴
        if ch in "，。！？；：、…— \t\n\r":
            viseme_level = 0
        # 开口元音 → 全开
        elif ch in "aāáǎàōóǒòēéěè":
            viseme_level = 3
        # 半开元音 → 半开
        elif ch in "oōóǒòeēéěè":
            viseme_level = 2
        # 闭口元音 → 微张
        elif ch in "iīíǐìuūúǔùüǖǘǚǜ":
            viseme_level = 1
        # 中文字符 → 基于 Unicode 的启发式分类
        elif '\u4e00' <= ch <= '\u9fff':
            code = ord(ch)
            if code % 5 == 0:
                viseme_level = 3
            elif code % 5 in (1, 3):
                viseme_level = 2
            elif code % 5 == 2:
                viseme_level = 1
            else:
                viseme_level = 0
        # 英文字母
        elif ch.isalpha():
            viseme_level = 2 if ch.lower() in "ae" else 1

        visemes.append({"time_ms": current_time, "viseme": viseme_level})
        current_time += char_duration

    # 确保有结束点
    if visemes and visemes[-1]["time_ms"] < total_ms:
        visemes.append({"time_ms": total_ms, "viseme": 0})

    return visemes
```

**口型同步的设计要点**：
- 先清理文本中的标签（如 `(唱歌)` `(开心)` 等，它们不需要口型）
- 基于字符数均匀分配时间（简化方案，精确方案需要音素级时间戳）
- 确保序列以 `viseme=0`（闭嘴）结束

---

## 18.8 句间停顿（模拟自然呼吸）

```python
# 句间换气停顿
# 经验公式：200ms ~ 800ms，约为当前句时长的 1/4
breath_ms = max(200, min(800, estimated_duration_ms // 4))
await asyncio.sleep(breath_ms / 1000)
```

**停顿的目的**：
- 模拟真人唱歌的自然呼吸节奏
- 避免连续推送消息刷屏
- 给前端播放器时间缓冲当前句的音频

---

## 18.9 完整演唱入口示例

```python
@plugin_entry(
    id="sing",
    name="流式演唱",
    description="⚠️ 流式逐句演唱。AI 应先调用 check_setup 确认配置就绪。",
    input_schema={
        "type": "object",
        "properties": {
            "song_name": {"type": "string", "description": "歌曲名称"},
            "lyrics": {"type": "string", "description": "歌词内容（每行一句）"},
            "style": {"type": "string", "description": "演唱风格描述"},
            "mimo_voice": {"type": "string", "description": "音色"},
        },
        "required": ["song_name", "lyrics"],
    },
    llm_result_fields=["success", "song_name", "total_lines", "lines_sung", "merged_audio_url"],
)
async def sing(self, song_name="", lyrics="", style="", mimo_voice="", _ctx=None, **__):
    if self._frozen:
        return Err(SdkError("插件已被冻结"))

    # 1. 参数验证
    if not song_name.strip():
        return Err(SdkError("请提供歌曲名称"))
    if not lyrics.strip():
        return Err(SdkError("请提供歌词内容"))

    lines = [l.strip() for l in lyrics.split("\n") if l.strip()]

    # 2. 后端检查
    if not self._mimo:
        return Err(SdkError("后端未初始化"))
    mimo_ok, mimo_msg = await self._mimo.health_check()
    if not mimo_ok:
        return Err(SdkError(f"后端不可用: {mimo_msg}"))

    use_voice = mimo_voice or self._config.get("mimo_voice", "冰糖")

    # 3. 开场消息
    self.push_message(
        source="ai_singer",
        visibility=["chat"],
        ai_behavior="blind",
        parts=[{
            "type": "text",
            "text": f"🎭 **正在演唱：《{song_name}》**\n音色：{use_voice} | 共 {len(lines)} 句\n---"
        }],
        priority=3,
    )

    # 4. 输出目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = str(self.data_path("live_songs") / f"{self._sanitize(song_name)}_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    # 5. 逐句流式合成
    success_count = 0
    total_elapsed_ms = 0
    all_lyric_lines = []

    for idx, line in enumerate(lines):
        if self._frozen:
            break

        line_num = idx + 1
        self.report_status({
            "status": "processing",
            "progress": 5 + int(90 * line_num / len(lines)),
            "message": f"🎤 正在唱第 {line_num}/{len(lines)} 句..."
        })

        try:
            output_path = os.path.join(output_dir, f"line_{line_num:03d}.wav")
            sing_text = f"(唱歌){line}"  # 添加唱歌标签
            result_path = await self._mimo.synthesize(
                text=sing_text, voice=use_voice,
                context=style, output_path=output_path,
            )
        except Exception as e:
            self.logger.warning("第 {} 句合成失败: {}", line_num, e)
            continue

        if not result_path or not os.path.exists(result_path):
            continue

        # 估算时长 + 生成口型
        estimated_duration_ms = max(1000, int(len(line) / 2.5 * 1000))
        line_start_ms = total_elapsed_ms
        line_end_ms = line_start_ms + estimated_duration_ms
        total_elapsed_ms = line_end_ms

        viseme_data = self._text_to_visemes(line, estimated_duration_ms)

        lyric_entry = {
            "text": line, "line_num": line_num,
            "start_ms": line_start_ms, "end_ms": line_end_ms,
            "duration_ms": estimated_duration_ms,
            "visemes": viseme_data,
        }
        all_lyric_lines.append(lyric_entry)

        # 推送歌词
        self.push_message(
            source="ai_singer", visibility=["chat"], ai_behavior="blind",
            parts=[{
                "type": "text",
                "text": f"🎵 **{line}**\n_{line_num}/{len(lines)} · ⏱ {estimated_duration_ms/1000:.1f}s_"
            }],
            priority=3,
        )

        success_count += 1
        breath_ms = max(200, min(800, estimated_duration_ms // 4))
        await asyncio.sleep(breath_ms / 1000)

    # 6. 合并音频
    merged_path = os.path.join(output_dir, "merged.wav")
    merged_url = await asyncio.to_thread(
        self._merge_wav_files, output_dir, success_count, merged_path
    )

    # 7. 结束消息
    self.push_message(
        source="ai_singer", visibility=["chat"], ai_behavior="blind",
        parts=[{
            "type": "text",
            "text": f"🎭 **《{song_name}》演唱完毕！**\n"
                    f"共演唱 {success_count}/{len(lines)} 句 · 总时长约 {total_elapsed_ms/1000:.0f} 秒\n"
                    f"音色：{use_voice}"
        }],
        priority=3,
    )

    self.report_status({
        "status": "completed", "progress": 100, "message": "演唱完成！",
        "merged_audio_url": merged_url, "lyric_lines": all_lyric_lines,
    })

    return Ok({
        "success": True,
        "song_name": song_name,
        "total_lines": len(lines),
        "lines_sung": success_count,
        "total_duration_ms": total_elapsed_ms,
        "merged_audio_url": merged_url,
        "lyric_lines": all_lyric_lines,
    })
```

---

## 18.10 流式输出检查清单

- [ ] 逐项处理的循环中使用 `try/except` 包裹单项，单次失败不影响后续
- [ ] 循环中使用 `report_status` 报告实时进度
- [ ] 每完成一项调用 `push_message` 推送结果
- [ ] 项间用 `asyncio.sleep` 控制节奏（避免刷屏或 API 限流）
- [ ] 开始和结束都有 `push_message` 通知
- [ ] `push_message` 设置 `ai_behavior="blind"`（消息不需要 AI 回复）
- [ ] 进度计算给不同阶段分配权重（准备 5% + 处理 90% + 收尾 5%）
- [ ] 处理前检查 `self._frozen`（支持冻结）
- [ ] 磁盘 I/O 使用 `asyncio.to_thread`（如文件读取、音频合并）
- [ ] 合并结果时处理空数据（所有项都失败的情况）
- [ ] `report_status` 最终状态设为 `"completed"` 且 `progress=100`
- [ ] 返回值中包含汇总信息（成功数、总时长、输出路径）
- [ ] 音频合并使用纯 Python 实现（不依赖 ffmpeg）
- [ ] WAV 文件 URL 使用 `file:///` 协议（前端 `<audio>` 可用）
- [ ] 口型数据在推送时附带，前端可实现实时对口型
