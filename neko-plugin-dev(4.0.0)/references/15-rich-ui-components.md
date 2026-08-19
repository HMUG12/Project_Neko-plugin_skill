# 15. 富交互 UI 组件模式

> 基于 `ai_singer` 插件面板的实战经验。
> 涵盖歌词同步播放器、ActionForm 高级用法、标签页切换、自定义内联样式、音频播放集成等模式。

---

## 15.1 自定义组件 vs SDK 组件

N.E.K.O SDK 提供了基础 UI 组件，但复杂交互需要自定义组件。ai_singer 中实现了一个完整的**歌词同步播放器**，展示了如何在 N.E.K.O 插件中构建自定义交互组件。

### 组件层次

```
Page
├── tabs (标签页导航)
├── Alert (连接状态提示)
├── Card (模式选择)
├── Section
│   ├── Heading + Text (声音选择说明)
│   └── select (自定义下拉)
├── Section
│   ├── Heading + textarea (歌词输入)
│   └── Text (字数统计)
├── ActionForm (演唱表单)
├── LyricPlayer (自定义歌词同步播放器)
├── SongCard (自定义歌曲卡片)
└── Tip (提示信息)
```

---

## 15.2 歌词同步播放器 (LyricPlayer)

完整实现一个带音频播放 + 实时歌词高亮 + 点击跳转的播放器组件：

```tsx
interface LyricLine {
  text: string
  start_ms: number
  end_ms: number
}

function LyricPlayer({
  audioUrl,
  lyricLines,
  songName,
}: {
  audioUrl: string
  lyricLines: LyricLine[]
  songName: string
}) {
  const [currentIndex, setCurrentIndex] = useLocalState<number>("lyric_idx", -1)
  const [audioMounted, setAudioMounted] = useLocalState<boolean>("audio_mounted", false)

  // ⚠️ 关键：使用 DOM id 替代 useRef
  // N.E.K.O 环境中 useRef 不可用，必须通过 document.getElementById 获取 DOM 元素
  const audioId = `lyric-audio-${songName.replace(/[^a-zA-Z0-9]/g, "_")}`
  const lyricsContainerId = `lyric-container-${songName.replace(/[^a-zA-Z0-9]/g, "_")}`

  // 音频事件绑定（通过 onCanPlay 回调）
  const handleAudioReady = () => {
    if (audioMounted) return  // 防止重复绑定
    setAudioMounted(true)

    const audio = document.getElementById(audioId) as HTMLAudioElement | null
    if (!audio || !lyricLines.length) return

    const onTimeUpdate = () => {
      const currentTimeMs = audio.currentTime * 1000
      let idx = -1
      for (let i = 0; i < lyricLines.length; i++) {
        if (currentTimeMs >= lyricLines[i].start_ms &&
            currentTimeMs < lyricLines[i].end_ms) {
          idx = i
          break
        }
        if (currentTimeMs >= lyricLines[i].end_ms) {
          idx = i
        }
      }
      setCurrentIndex(idx)

      // 自动滚动到当前歌词
      const container = document.getElementById(lyricsContainerId)
      if (container) {
        const activeEl = container.querySelector(`[data-lyric-idx="${idx}"]`)
        if (activeEl) {
          activeEl.scrollIntoView({ behavior: "smooth", block: "center" })
        }
      }
    }

    const onEnded = () => {
      setCurrentIndex(-1)
    }

    audio.addEventListener("timeupdate", onTimeUpdate)
    audio.addEventListener("ended", onEnded)
  }

  // 点击歌词跳转
  const handleLyricClick = (line: LyricLine) => {
    const audio = document.getElementById(audioId) as HTMLAudioElement | null
    if (audio) {
      audio.currentTime = line.start_ms / 1000
    }
  }

  return (
    <Card>
      <Stack gap="md">
        <Heading level={4}>🎵 {songName} - 歌词同步</Heading>

        {/* 音频播放器 */}
        <audio
          id={audioId}
          src={audioUrl}
          controls
          onCanPlay={() => handleAudioReady()}
          style={{ width: "100%", borderRadius: 8 }}
        />

        {/* 歌词列表 */}
        {lyricLines.length > 0 && (
          <div
            id={lyricsContainerId}
            style={{
              maxHeight: 360,
              overflowY: "auto",
              padding: "16px 0",
              borderRadius: 8,
              background: "linear-gradient(135deg, #f0f4ff 0%, #faf5ff 100%)",
            }}
          >
            {lyricLines.map((line, idx) => {
              const isActive = idx === currentIndex
              const isPassed = idx < currentIndex
              return (
                <div
                  key={idx}
                  data-lyric-idx={idx}
                  style={{
                    padding: "8px 24px",
                    textAlign: "center",
                    fontSize: isActive ? 20 : 15,
                    fontWeight: isActive ? 700 : 400,
                    color: isActive ? "#3b82f6" : isPassed ? "#9ca3af" : "#374151",
                    opacity: isPassed ? 0.5 : 1,
                    transition: "all 0.3s ease",
                    cursor: "pointer",
                    lineHeight: 1.8,
                  }}
                  onClick={() => handleLyricClick(line)}
                >
                  {line.text || "── ♪ ──"}
                </div>
              )
            })}
          </div>
        )}
      </Stack>
    </Card>
  )
}
```

### 核心模式

| 模式 | 实现方式 | 原因 |
|------|---------|------|
| DOM 元素引用 | `document.getElementById(id)` | N.E.K.O 不支持 `useRef` |
| 音频事件绑定 | `onCanPlay` 回调中 `addEventListener` | 确保 audio 元素已挂载 |
| 防重复绑定 | `audioMounted` 标志位 | `onCanPlay` 可能多次触发 |
| 状态管理 | `useLocalState` | 组件状态不丢失 |
| 自动滚动 | `scrollIntoView({ behavior: "smooth", block: "center" })` | 平滑跟随当前歌词 |
| data 属性 | `data-lyric-idx={idx}` | 便于 DOM 查询 |
| 点击跳转 | `audio.currentTime = line.start_ms / 1000` | 直接操作 audio 元素 |
| ID 生成 | `lyric-audio-${songName.replace(...)}` | 确保多个播放器不冲突 |

---

## 15.3 歌曲卡片组件 (SongCard)

将历史记录中的每首歌曲封装为独立卡片，包含播放、下载、复制链接、重命名、删除等操作：

```tsx
function SongCard({
  song,
  t,
  onDelete,
  onRename,
  onResing,
}: {
  song: SongRecord
  t: TFunc
  onDelete: (id: string) => void
  onRename: (id: string, name: string) => void
  onResing: (song: SongRecord) => void
}) {
  const [showLyrics, setShowLyrics] = useLocalState<boolean>(
    `lyrics_${song.id || song.created_at}`, false
  )

  // 格式化工具函数
  const formatDuration = (sec: number) => {
    const m = Math.floor(sec / 60)
    const s = sec % 60
    return `${m}:${s.toString().padStart(2, "0")}`
  }
  const formatSize = (bytes?: number) => {
    if (!bytes) return ""
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  return (
    <Card>
      <Stack gap="md">
        <Grid columns={12} gap="sm">
          {/* 左侧：歌曲信息 */}
          <div style={{ gridColumn: "span 8" }}>
            <Heading level={4}>{song.song_name}</Heading>
            <Stack gap="xs">
              <Text size="sm">
                <span style={{ opacity: 0.6 }}>后端:</span> {song.provider}
              </Text>
              <Text size="sm">
                <span style={{ opacity: 0.6 }}>时长:</span> {formatDuration(song.duration_sec)}
                {song.file_size_bytes && ` · ${formatSize(song.file_size_bytes)}`}
              </Text>
              <Text size="sm">
                <span style={{ opacity: 0.6 }}>创建:</span> {song.created_at}
              </Text>
            </Stack>
          </div>
          {/* 右侧：操作按钮 */}
          <div style={{ gridColumn: "span 4", textAlign: "right" }}>
            <Stack gap="xs">
              {song.audio_url && (
                <audio controls src={song.audio_url} style={{ width: "100%", borderRadius: 8 }} />
              )}
              <Grid columns={6} gap="xs">
                <button onClick={() => onResing(song)} style={btnSmStyle} title="重新合成">🔄</button>
                <button onClick={() => {
                  const newName = prompt("请输入新名称", song.song_name)
                  if (newName) onRename(song.id || song.created_at, newName)
                }} style={btnSmStyle} title="重命名">✏️</button>
                <button onClick={() => setShowLyrics(!showLyrics)} style={btnSmStyle} title="歌词">📜</button>
                <button onClick={() => {
                  if (song.audio_url) {
                    navigator.clipboard.writeText(song.audio_url)
                    alert("已复制到剪贴板")
                  }
                }} style={btnSmStyle} title="复制链接">🔗</button>
                <button onClick={() => {
                  if (song.audio_url) {
                    const link = document.createElement("a")
                    link.href = song.audio_url
                    link.download = `${song.song_name}.mp3`
                    link.click()
                  }
                }} style={btnSmStyle} title="下载">📥</button>
                <button onClick={() => {
                  if (confirm("确定要删除吗？")) onDelete(song.id || song.created_at)
                }} style={{ ...btnSmStyle, background: "#fee2e2", color: "#dc2626", border: "1px solid #fca5a5" }} title="删除">🗑️</button>
              </Grid>
            </Stack>
          </div>
        </Grid>

        {/* 歌词同步（展开时） */}
        {showLyrics && song.lyric_lines && song.lyric_lines.length > 0 && song.audio_url && (
          <LyricPlayer
            audioUrl={song.audio_url}
            lyricLines={song.lyric_lines}
            songName={song.song_name}
          />
        )}
      </Stack>
    </Card>
  )
}
```

### 关键模式

| 模式 | 说明 |
|------|------|
| **子组件 `useLocalState` key** | 使用 `lyrics_${id}` 确保不同卡片的状态隔离 |
| **`Grid columns={12}`** | 灵活的两栏布局（8+4），不依赖预设列数 |
| **`style={{ gridColumn: "span X" }}`** | 精确控制 Grid 内子元素的列跨度 |
| **原生 `<audio>` 元素** | N.E.K.O 没有音频组件，直接用 HTML5 audio |
| **下载文件** | 创建临时 `<a>` 元素 + `click()` 触发下载 |
| **复制到剪贴板** | `navigator.clipboard.writeText()` |
| **删除按钮红色样式** | 通过 style 覆盖背景色和边框色 |
| **回调函数传递** | 通过 props 将操作委托给父组件，保持数据流单向 |

---

## 15.4 ActionForm 高级用法

`ActionForm` 是最常用的表单组件，支持 schema 定义、字段配置、布局等：

```tsx
<ActionForm
  action={singAction}                    // HostedAction 对象
  onResult={handleSingResult}            // 结果回调
  onSubmit={() => setIsProcessing(true)} // 提交前回调
  submitLabel={isProcessing ? "演唱中..." : "🎤 开始演唱"}  // 提交按钮文字
  loadingLabel="云端合成中..."           // 加载中文字
  schema={{                              // JSON Schema 定义
    type: "object",
    properties: {
      song_name: { type: "string", label: "歌曲名称" },
      lyrics: { type: "string", label: "歌词" },
      style: { type: "string", label: "风格" },
      voice_id: { type: "string", label: "声音 ID" },
    },
    required: ["song_name"],
  }}
  fields={{                              // 字段配置
    song_name: {
      placeholder: "给这首歌起个名字...",
      defaultValue: songNameInput,
    },
    lyrics: {
      defaultValue: lyricsInput,         // 从 useLocalState 取默认值
    },
    style: { defaultValue: "流行" },
    voice_id: { defaultValue: selectedVoiceId },
  }}
  layout="vertical"                      // 垂直布局
/>
```

### ActionForm 字段映射

| schema property | fields 配置 | 说明 |
|----------------|------------|------|
| `type: "string"` | `placeholder`, `defaultValue` | 文本输入 |
| `type: "number"` | `defaultValue`, `min`, `max` | 数字输入 |
| `required: [...]` | — | 必填验证 |

### onResult 回调模式

```tsx
const handleResult = (result: unknown) => {
  setIsProcessing(false)
  const r = result as SingResult
  setLastResult(r)
  if (r.success) {
    api.refresh()       // 刷新 Context 数据
    setActiveTab("history")  // 切换到历史标签页查看结果
  }
}
```

---

## 15.5 自定义内联样式模式

N.E.K.O 插件中不能用 CSS 文件或 CSS-in-JS，只能用内联 `style` 对象。定义样式常量的最佳实践：

```tsx
// 定义可复用的样式常量
const btnStyle: Record<string, string | number> = {
  padding: "8px 16px",
  borderRadius: 8,
  border: "1px solid #d1d5db",
  background: "#f9fafb",
  color: "#374151",
  cursor: "pointer",
  fontSize: 14,
  fontWeight: 500,
  display: "inline-flex",
  alignItems: "center",
  gap: 4,
}

const btnSmStyle: Record<string, string | number> = {
  padding: "4px 8px",
  borderRadius: 8,
  border: "1px solid #d1d5db",
  background: "#f9fafb",
  color: "#374151",
  cursor: "pointer",
  fontSize: 12,
  fontWeight: 500,
  display: "inline-flex",
  alignItems: "center",
  gap: 4,
}

// 使用
<button style={btnStyle}>普通按钮</button>
<button style={btnSmStyle}>小按钮</button>
<button style={{ ...btnSmStyle, background: "#fee2e2", color: "#dc2626", border: "1px solid #fca5a5" }}>
  危险按钮
</button>
```

**内联样式最佳实践**：

1. **定义在组件外部**：避免每次渲染重新创建对象
2. **使用 `Record<string, string | number>`**：正确的类型标注
3. **展开运算符覆盖**：`{ ...baseStyle, background: "red" }` 覆盖特定属性
4. **颜色用 hex**：`#3b82f6`（蓝色）、`#10b981`（绿色）、`#ef4444`（红色）、`#f59e0b`（黄色）
5. **透明度用 `opacity`**：`style={{ opacity: 0.6 }}` 而非 `color: "rgba(...)"`

---

## 15.6 条件渲染模式

```tsx
// 1. 连接状态提示
{!cvOk && (
  <Alert variant="warning" title="云端未连接">
    <Text>云端不可用：{cvStatus || "未配置"}</Text>
    <Text size="sm" style={{ marginTop: 4 }}>
      请先在「设置」中配置 API Key
    </Text>
  </Alert>
)}

// 2. 操作结果反馈
{lastResult && lastResult.success && (
  <Alert variant="success" title="操作成功！">
    <LyricPlayer audioUrl={lastResult.audio_url} lyricLines={lastResult.lyric_lines} songName={lastResult.song_name} />
  </Alert>
)}

{lastResult && !lastResult.success && (
  <Alert variant="error" title="操作失败">
    <Text style={{ whiteSpace: "pre-wrap" }}>{lastResult.error}</Text>
  </Alert>
)}

// 3. 空状态
{items.length === 0 ? (
  <EmptyState icon="music" title="暂无数据" description="去创建页面开始吧！" />
) : (
  <Stack gap="md">
    {items.map(item => <ItemCard key={item.id} item={item} />)}
  </Stack>
)}

// 4. Action 不可用时降级
{action ? (
  <ActionForm action={action} ... />
) : (
  <EmptyState icon="music" title="操作不可用" description="请检查配置" />
)}

// 5. 布尔标志的条件样式
<button style={{
  ...btnStyle,
  background: isActive ? "#3b82f6" : "#f9fafb",
  color: isActive ? "#fff" : "#374151",
  border: isActive ? "2px solid #3b82f6" : "1px solid #d1d5db",
}}>
  {isActive ? "✅ 已激活" : "点击激活"}
</button>
```

---

## 15.7 列表搜索过滤

```tsx
const [searchText, setSearchText] = useLocalState<string>("search", "")

// 搜索输入框
{items.length > 3 && (
  <Card>
    <Stack gap="sm">
      <Text size="sm">搜索：</Text>
      <input
        type="text"
        placeholder="搜索名称、描述..."
        value={searchText}
        onChange={(e) => setSearchText((e.target as HTMLInputElement).value)}
        style={{
          width: "100%",
          padding: 8,
          borderRadius: 4,
          border: "1px solid #e5e7eb",
        }}
      />
    </Stack>
  </Card>
)}

{/* 过滤后的列表 */}
{items
  .filter((item) => {
    if (!searchText) return true
    const s = searchText.toLowerCase()
    return (
      item.name?.toLowerCase().includes(s) ||
      item.desc?.toLowerCase().includes(s) ||
      item.provider?.toLowerCase().includes(s)
    )
  })
  .map((item) => (
    <ItemCard key={item.id} item={item} />
  ))}
```

---

## 15.8 `useLocalState` 最佳实践

### Key 命名规范

```tsx
// ✅ 正确：使用有意义且唯一的前缀
const [activeTab, setActiveTab] = useLocalState<string>("tab", "create")
const [lyricsInput, setLyricsInput] = useLocalState<string>("lyricsInput", "")
const [selectedVoiceId, setSelectedVoiceId] = useLocalState<string>("selectedVoice", nekoVoiceId)

// ✅ 正确：列表项状态用 id 组合 key
const [showLyrics, setShowLyrics] = useLocalState<boolean>(`lyrics_${song.id}`, false)

// ❌ 错误：过于通用的 key 会冲突
const [value, setValue] = useLocalState("val", "")
const [data, setData] = useLocalState("data", [])
```

### 惰性初始化

```tsx
// ✅ 正确：使用函数初始化避免每次渲染都计算
const [items, setItems] = useLocalState<CustomVoice[]>("voices", () => state?.custom_voices ?? [])
const [apiKey, setApiKey] = useLocalState<string>("apiKey", () => state?.api_key ?? "")

// ❌ 错误：直接传值，每次渲染都计算（对于大对象浪费性能）
const [items, setItems] = useLocalState<CustomVoice[]>("voices", state?.custom_voices ?? [])
```

### TypeScript 类型标注

```tsx
// ✅ 正确：明确类型参数
const [activeTab, setActiveTab] = useLocalState<"create" | "history" | "settings">("tab", "create")
const [isProcessing, setIsProcessing] = useLocalState<boolean>("processing", false)
const [lastResult, setLastResult] = useLocalState<SingResult | null>("result", null)

// ✅ 正确：actions 缓存
const [cachedActions, setCachedActions] = useLocalState<HostedAction[]>("ca", () => [])
```

---

## 15.9 原生 HTML 元素使用

N.E.K.O 没有提供所有 HTML 元素的封装，可以直接使用原生元素：

```tsx
{/* 下拉选择 */}
<select
  value={selectedVoiceId}
  onChange={(e) => setSelectedVoiceId((e.target as HTMLSelectElement).value)}
  style={{ padding: 8, borderRadius: 6, border: "1px solid #d1d5db", width: "100%" }}
>
  {voices.map((v) => (
    <option key={v.id} value={v.id}>
      {v.name} ({v.id})
    </option>
  ))}
</select>

{/* 多行文本 */}
<textarea
  value={lyricsInput}
  onChange={(e) => setLyricsInput((e.target as HTMLTextAreaElement).value)}
  placeholder="输入歌词，每行一句..."
  rows={10}
  style={{
    width: "100%",
    padding: 12,
    borderRadius: 8,
    border: "1px solid #d1d5db",
    fontSize: 14,
    fontFamily: "serif",
    lineHeight: 1.8,
    resize: "vertical",
  }}
/>

{/* 搜索输入 */}
<input
  type="text"
  placeholder="搜索..."
  value={searchText}
  onChange={(e) => setSearchText((e.target as HTMLInputElement).value)}
  style={{ width: "100%", padding: 8, borderRadius: 4, border: "1px solid #e5e7eb" }}
/>

{/* 音频播放器 */}
<audio
  id={audioId}
  src={audioUrl}
  controls
  onCanPlay={() => handleAudioReady()}
  style={{ width: "100%", borderRadius: 8 }}
/>
```

**注意**：原生元素的事件回调中，`e.target` 需要类型断言，如 `(e.target as HTMLInputElement).value`。

---

## 15.10 检查清单

- [ ] `useLocalState` key 全局唯一，使用有意义的前缀
- [ ] 惰性初始化用函数形式：`useLocalState("key", () => defaultValue)`
- [ ] 列表项状态 key 包含唯一 id：`useLocalState(`item_${id}`, ...)`
- [ ] DOM 元素引用用 `document.getElementById()`（非 `useRef`）
- [ ] 音频/视频事件在 `onCanPlay` 中绑定，使用标志位防重复
- [ ] 内联样式常量定义在组件外部
- [ ] 颜色用 hex 值，透明度用 `opacity` 属性
- [ ] `Grid` 用 `style={{ gridColumn: "span X" }}` 控制列宽
- [ ] 原生 HTML 元素的事件回调做类型断言
- [ ] `ActionForm` 的 `schema.properties` 与 Python `input_schema` 一致
- [ ] `onResult` 中调用 `api.refresh()` 刷新数据
- [ ] `onSubmit` 中设置 loading 状态，`onResult` 中重置
- [ ] 条件渲染覆盖 loading、空状态、错误、成功四种状态
- [ ] Action 不可用时提供降级 UI（`EmptyState` 或提示文本）
- [ ] 列表超 3 条时提供搜索过滤
- [ ] 删除操作用红色样式 + `confirm()` 确认
