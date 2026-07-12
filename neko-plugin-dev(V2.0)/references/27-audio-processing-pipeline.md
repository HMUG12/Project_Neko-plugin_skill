# 音频处理管线

> 基于 `ai_singer` 和 `music_pusher` 插件。覆盖纯 Python WAV 处理、Viseme 口型同步、时长估算、双轨播放架构。

---

## 一、设计决策：为什么不用 ffmpeg

**原则**：尽量减少插件的外部依赖。每增加一个系统依赖，就多一个安装失败的可能。

`ai_singer` 刻意避免依赖 ffmpeg，所有音频处理用纯 Python 实现：
- WAV 合并 → `struct` 模块手动解析/构造
- 格式转换 → 不转换（统一使用 WAV）
- 时长获取 → 从 WAV 头中读取或估算

---

## 二、纯 Python WAV 文件合并

> 来源：`ai_singer/__init__.py` L606-692

### 2.1 RIFF/WAVE 格式回顾

```
WAV 文件结构：
┌─────────────────┐
│ RIFF Header      │  12 bytes
│  "RIFF"          │
│  file_size       │  (总文件大小 - 8)
│  "WAVE"          │
├─────────────────┤
│ fmt  chunk       │  24+ bytes
│  "fmt "          │
│  chunk_size      │  (通常是 16)
│  audio_format    │  (1 = PCM)
│  num_channels    │
│  sample_rate     │
│  byte_rate       │
│  block_align     │
│  bits_per_sample │
├─────────────────┤
│ data chunk       │
│  "data"          │
│  data_size       │
│  [音频数据...]   │
└─────────────────┘
```

### 2.2 完整合并实现

```python
import struct

def _merge_wav_files(self, wav_paths: list[str], output_path: str):
    """纯 Python 合并多个 WAV 文件，不依赖 ffmpeg。"""
    if not wav_paths:
        raise ValueError("没有可合并的 WAV 文件")

    all_audio_data = []
    sample_rate = None
    num_channels = None
    bits_per_sample = None

    for path in wav_paths:
        with open(path, "rb") as f:
            # 1. 验证 RIFF 头
            riff = f.read(4)
            if riff != b"RIFF":
                raise ValueError(f"不是有效的 WAV 文件：{path}")
            f.read(4)  # 跳过文件大小
            wave = f.read(4)
            if wave != b"WAVE":
                raise ValueError(f"不是有效的 WAV 文件：{path}")

            # 2. 扫描 chunk 找 fmt 和 data
            fmt_data = None
            audio_data = None

            while True:
                chunk_id = f.read(4)
                if len(chunk_id) < 4:
                    break

                chunk_size = struct.unpack("<I", f.read(4))[0]

                if chunk_id == b"fmt ":
                    fmt_data = f.read(chunk_size)
                    # 解析 fmt chunk
                    audio_fmt, nch, sr, _, _, bps = struct.unpack(
                        "<HHIIHH", fmt_data[:16]
                    )
                    if audio_fmt != 1:
                        raise ValueError(f"只支持 PCM 格式：{path}")
                    if sample_rate is None:
                        sample_rate = sr
                        num_channels = nch
                        bits_per_sample = bps
                    elif sr != sample_rate:
                        raise ValueError(f"采样率不一致：{sr} vs {sample_rate}")

                elif chunk_id == b"data":
                    audio_data = f.read(chunk_size)
                    all_audio_data.append(audio_data)
                    break
                else:
                    f.seek(chunk_size, 1)  # 跳过未知 chunk

    # 3. 合并音频数据
    merged = b"".join(all_audio_data)
    data_size = len(merged)

    # 4. 构造输出 WAV 文件
    with open(output_path, "wb") as out:
        # RIFF header
        out.write(b"RIFF")
        out.write(struct.pack("<I", 36 + data_size))
        out.write(b"WAVE")

        # fmt chunk
        out.write(b"fmt ")
        out.write(struct.pack("<I", 16))  # PCM 格式 chunk_size = 16
        out.write(struct.pack("<HHIIHH",
            1,                # audio_format = PCM
            num_channels,
            sample_rate,
            sample_rate * num_channels * bits_per_sample // 8,  # byte_rate
            num_channels * bits_per_sample // 8,                # block_align
            bits_per_sample,
        ))

        # data chunk
        out.write(b"data")
        out.write(struct.pack("<I", data_size))
        out.write(merged)

    return output_path
```

**关键细节**：
- 逐 chunk 扫描而非假设 fmt 在固定位置（兼容不同编码器生成的 WAV）
- 跳过未知 chunk（LIST、fact 等非标准 chunk）
- 验证所有文件采样率一致
- 只支持 PCM 格式（`audio_format == 1`）

---

## 三、Viseme 口型同步数据生成

> 来源：`ai_singer/__init__.py` L1076-1146

### 3.1 Viseme 定义

```python
# 口型映射表（0 = 闭嘴，数值越大嘴张越大）
_VISEME_MAP = {
    # 元音 → 张嘴程度
    "a": 3, "ā": 3, "á": 3, "ǎ": 3, "à": 3,
    "o": 2, "ō": 2, "ó": 2, "ǒ": 2, "ò": 2,
    "e": 2, "ē": 2, "é": 2, "ě": 2, "è": 2,
    "i": 1, "ī": 1, "í": 1, "ǐ": 1, "ì": 1,
    "u": 2, "ū": 2, "ú": 2, "ǔ": 2, "ù": 2,
    "ü": 1, "ǖ": 1, "ǘ": 1, "ǚ": 1, "ǜ": 1,
    # 英文元音
    "A": 3, "E": 2, "I": 1, "O": 2, "U": 2,
}

# 辅音聚类 → 嘴型
_CONSONANT_VISEME = {
    "b": 0, "p": 0, "m": 0,   # 双唇音 → 闭嘴
    "f": 1, "v": 1,            # 唇齿音 → 微张
    "d": 1, "t": 1, "n": 1, "l": 1,  # 舌尖音 → 微张
    "g": 1, "k": 1, "h": 1,    # 舌根音 → 微张
    "j": 1, "q": 1, "x": 1,    # 舌面音 → 微张
    "z": 1, "c": 1, "s": 1,    # 平舌音 → 微张
    "r": 1,                     # 卷舌音 → 微张
}
```

### 3.2 Viseme 时间线生成

```python
def _text_to_visemes(self, text: str, total_duration_ms: int) -> list[dict]:
    """将文本转换为口型时间线。"""
    # 1. 清理文本
    text = re.sub(r'\([^)]*\)', '', text)  # 移除括号标签如 (唱歌)
    text = re.sub(r'\[[^\]]*\]', '', text) # 移除方括号标签
    text = text.strip()

    chars = list(text)
    if not chars:
        return [{"time_ms": 0, "viseme": 0}]

    # 2. 计算每个字符的时长
    char_duration = max(50, total_duration_ms // len(chars))

    # 3. 生成时间线
    timeline = []
    current_time = 0

    for char in chars:
        viseme = self._char_to_viseme(char)
        timeline.append({
            "time_ms": current_time,
            "viseme": viseme,
        })
        current_time += char_duration

    # 4. 添加闭嘴结束
    timeline.append({
        "time_ms": current_time,
        "viseme": 0,
    })

    return timeline

def _char_to_viseme(self, char: str) -> int:
    """单个字符 → 口型值。"""
    # 1. 元音（含声调）
    if char in _VISEME_MAP:
        return _VISEME_MAP[char]

    # 2. 英文元音
    if char.isalpha() and char.upper() in "AEIOU":
        return _VISEME_MAP.get(char.upper(), 1)

    # 3. 辅音
    if char.lower() in _CONSONANT_VISEME:
        return _CONSONANT_VISEME[char.lower()]

    # 4. 标点/空格 → 闭嘴
    if char in "，。！？、；：""''（）…—\n\r\t ":
        return 0

    # 5. 未知字符 → Unicode 码点判断
    cp = ord(char)
    if 0x4E00 <= cp <= 0x9FFF:  # 中文字符范围
        return 1  # 默认微张
    return 0
```

**输出格式**：
```json
{
    "time_ms": 0,
    "viseme": 0
}
```

---

## 四、音频时长估算

### 4.1 文件大小估算法

```python
def _estimate_duration_from_size(self, file_path: str) -> float:
    """通过文件大小估算 WAV 时长。"""
    size = os.path.getsize(file_path)

    # WAV 头约 44 bytes
    # PCM 16bit 单声道 22050Hz
    audio_bytes = max(0, size - 44)
    bytes_per_second = 22050 * 2 * 1  # sample_rate * bytes_per_sample * channels

    return audio_bytes / bytes_per_second
```

### 4.2 文本长度估算法

```python
def _estimate_duration_from_text(self, text: str) -> float:
    """通过文本长度估算 TTS 时长。"""
    # 中文约 4 字/秒，英文约 2.5 字/秒
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    other_chars = len(text) - chinese_chars

    return chinese_chars / 4.0 + other_chars / 2.5
```

### 4.3 精确读取法

```python
def _get_wav_duration(self, file_path: str) -> float:
    """从 WAV 头精确读取时长。"""
    with open(file_path, "rb") as f:
        # 找 data chunk
        f.seek(12)
        while True:
            chunk_id = f.read(4)
            chunk_size = struct.unpack("<I", f.read(4))[0]
            if chunk_id == b"data":
                # data_size / byte_rate
                f.seek(-20, 1)  # 回到 fmt chunk
                fmt = f.read(16)
                _, nch, sr, br, _, bps = struct.unpack("<HHIIHH", fmt)
                return chunk_size / br
            f.seek(chunk_size, 1)
```

---

## 五、双轨播放架构

> 来源：`music_pusher/data/static_ui/index.html`

### 5.1 架构图

```
┌──────────────────────────────────────┐
│            音乐推送页面               │
│                                      │
│  ┌────────────┐   ┌──────────────┐   │
│  │ syncPlayer │   │ card <audio> │   │
│  │ (隐藏)     │   │ (可见)       │   │
│  │ muted=true │   │ controls     │   │
│  │ volume=0   │   │              │   │
│  └─────┬──────┘   └──────┬───────┘   │
│        │                 │           │
│        ▼                 ▼           │
│  ┌─────────────┐   用户可直接交互    │
│  │ 音频可视化器│   播放/暂停/进度    │
│  │ Canvas 2D   │                    │
│  └─────────────┘                    │
└──────────────────────────────────────┘
```

### 5.2 实现

```javascript
// 轨道 1：静音同步播放器（驱动可视化）
const syncPlayer = document.getElementById("syncPlayer");
syncPlayer.muted = true;
syncPlayer.volume = 0;

function syncRuntimePlayer(url) {
    if (state.lastRuntimeTrackUrl === url) return;  // 去重
    state.lastRuntimeTrackUrl = url;

    syncPlayer.src = url;
    syncPlayer.play().catch(() => {});  // 静音播放，忽略 autoplay 错误
}

// 轨道 2：用户交互播放器（卡片内）
function createAudioCard(item) {
    const audio = document.createElement("audio");
    audio.controls = true;
    audio.src = item.audio_url;
    return audio;
}
```

**为什么需要双轨**：
- 可视化需要连续的音频流，但用户可能不播放任何卡片
- 用户交互播放器让用户自行控制播放/暂停
- 静音轨道不输出声音，避免双重播放

---

## 六、句间换气停顿算法

> 来源：`ai_singer/__init__.py` L924-925

```python
# 每句歌词之间添加停顿
estimated_duration_ms = self._estimate_duration_from_text(line)
breath_ms = max(200, min(800, estimated_duration_ms // 4))

await asyncio.sleep(breath_ms / 1000)
```

**公式**：
```
breath_ms = clamp(estimated_duration_ms / 4, 200, 800)
```

| 句子时长 | 停顿 |
|----------|------|
| 1 秒 | 250ms |
| 2 秒 | 500ms |
| 3 秒 | 750ms |
| 4+ 秒 | 800ms (上限) |
| 0.5 秒 | 200ms (下限) |

---

## 七、MIME 类型检测

> 来源：`music_pusher/data/static_ui/index.html`

```javascript
function guessAudioMime(url) {
    const ext = url.split(".").pop().toLowerCase().split("?")[0];
    const mimeMap = {
        "mp3":  "audio/mpeg",
        "wav":  "audio/wav",
        "ogg":  "audio/ogg",
        "m4a":  "audio/mp4",
        "aac":  "audio/aac",
        "flac": "audio/flac",
        "opus": "audio/ogg",
    };
    return mimeMap[ext] || "audio/mpeg";
}

function applyAudioSource(audioEl, url) {
    const mime = guessAudioMime(url);
    audioEl.innerHTML = `<source src="${url}" type="${mime}">`;
    audioEl.load();
}
```

---

## 八、音频处理检查清单

- [ ] 音频合并是否避免外部依赖（ffmpeg/sox）
- [ ] WAV 处理是否正确扫描 chunk 而非假设固定偏移
- [ ] 采样率/声道数不一致时是否有明确错误提示
- [ ] 文件 I/O 是否通过 `asyncio.to_thread` 执行
- [ ] 时长估算是否有回退策略（精确读取 → 大小估算 → 文本估算）
- [ ] 可视化播放器是否使用静音轨道避免双重声音
- [ ] 播放 URL 是否有去重逻辑防止中断
