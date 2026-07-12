# UI 设置面板开发指南

## 可用的 SDK 组件

从 `@neko/plugin-ui` 导入：

| 组件 | 用途 | 已验证 |
|------|------|--------|
| `Page` | 页面容器 | ✅ |
| `Card` | 卡片容器（带标题） | ✅ |
| `Section` | 通用区块 | ✅ |
| `Stack` | 垂直堆叠布局 | ✅ |
| `Grid` | 网格布局 | ✅ |
| `Text` | 文本显示（color: primary/secondary/muted） | ✅ |
| `Heading` | 标题文本（level={1-6}） | ✅ |
| `Divider` | 分割线 | ✅ |
| `Switch` | 开关（checked/onChange） | ✅ |
| `Input` | 输入框（type/value/onChange） | ✅ |
| `Select` | 下拉选择（value/onChange/options） | ✅ |
| `Slider` | 滑块（value/onChange/min/max/step） | ✅ |
| `Textarea` | 多行文本（value/onChange） | ✅ |
| `StatCard` | 统计卡片（title/value） | ✅ |
| `ActionButton` | 动作按钮（action/values/children） | ✅ |
| `ActionForm` | 表单组件（action/schema/fields/onResult） | ✅ |
| `Field` | 表单字段（label/children） | ✅ |
| `Alert` | 提示框（variant/title/children） | ✅ |
| `StatusBadge` | 状态标签（variant/label） | ✅ |
| `EmptyState` | 空状态占位（icon/title/description） | ✅ |
| `Tip` | 提示文本块 | ✅ |
| `DataTable` | 数据表格（columns/data/rowKey） | ✅ |
| `useLocalState` | 本地状态 Hook | ✅ |

**不存在/不可用的组件**：`Table`、`Button`（用 `ActionButton` 代替）、`useState`

## 标准模板

```tsx
import {
  Page, Card, Section, Stack, Grid, Text, Divider,
  Switch, Input, Textarea, StatCard, ActionButton, Field, Alert, DataTable,
} from "@neko/plugin-ui"
import type { HostedAction, PluginSurfaceProps } from "@neko/plugin-ui"
import { useLocalState } from "@neko/plugin-ui"

// 1. 定义 State 类型 — 与 Python 端 settings_context 返回的数据结构一致
type State = {
  config: {
    my_setting: boolean
    my_text: string
    my_list: string[]
  }
  status: { running: boolean }
}

// 2. 导出默认函数组件
export default function SettingsPanel(props: PluginSurfaceProps<State>) {
  const { state, actions } = props

  // 3. 缓存 actions — 避免首次渲染时按钮消失
  const [cachedActions, setCachedActions] = useLocalState(
    "ca",
    () => [] as HostedAction[]
  )
  if (actions.length > 0 && actions.length !== cachedActions.length) {
    setCachedActions(actions)
  }
  const effectiveActions = cachedActions.length > 0 ? cachedActions : actions

  // 4. 本地状态 — 每个配置项一个
  const [mySetting, setMySetting] = useLocalState(
    "ms",
    () => state.config?.my_setting ?? false
  )
  const [myText, setMyText] = useLocalState(
    "mt",
    () => state.config?.my_text ?? ""
  )
  const [myList, setMyList] = useLocalState(
    "ml",
    () => (state.config?.my_list || []).join("\n")
  )

  // 5. 查找 action
  const saveAction = effectiveActions.find(
    (a: HostedAction) => a.id === "update_settings"
  )
  const otherAction = effectiveActions.find(
    (a: HostedAction) => a.id === "other_action"
  )

  // 6. 构建配置对象
  function buildConfig(): Record<string, unknown> {
    return {
      my_setting: mySetting,
      my_text: myText,
      my_list: myList.split("\n").map((s: string) => s.trim()).filter(Boolean),
    }
  }

  // 7. 保存操作
  async function handleSave() {
    if (!saveAction) return
    try {
      await saveAction.call({ config: buildConfig() })
      // 显示保存成功提示
      setShowSaved(true)
      setTimeout(() => setShowSaved(false), 3000)
    } catch (e) { /* ignore */ }
  }

  const [showSaved, setShowSaved] = useLocalState("sv", () => false)

  // 8. 渲染
  return (
    <Page title="我的插件">
      {showSaved && <Alert title="保存成功"><Text>设置已生效</Text></Alert>}

      <Grid>
        <StatCard title="状态" value={state.status?.running ? "运行中" : "空闲"} />
      </Grid>

      <Card title="配置">
        <Stack>
          <Field label="开关设置">
            <Switch checked={mySetting} onChange={(v: boolean) => setMySetting(v)} />
          </Field>
          <Field label="文本输入">
            <Input value={myText} onChange={(v: string) => setMyText(v)} />
          </Field>
          <Field label="多行列表">
            <Textarea value={myList} onChange={(v: string) => setMyList(v)} />
          </Field>
        </Stack>
      </Card>

      <Section>
        <Stack>
          {saveAction ? (
            <ActionButton
              action={saveAction}
              values={{ config: buildConfig() }}
            >
              保存设置
            </ActionButton>
          ) : (
            <ActionButton
              action={{ id: "update_settings", call: async () => {} } as HostedAction}
              values={{ config: buildConfig() }}
            >
              保存设置 (加载中…)
            </ActionButton>
          )}
          {otherAction && <ActionButton action={otherAction}>其他操作</ActionButton>}
        </Stack>
      </Section>
    </Page>
  )
}
```

## 新增组件用法

### Select 下拉选择

```tsx
<Field label="地域">
  <Select
    value={region}
    onChange={(v: string) => setRegion(v)}
    options={[
      { value: "cn-beijing", label: "华北2（北京）" },
      { value: "cn-shanghai", label: "华东2（上海）" },
    ]}
  />
</Field>
```

### Slider 滑块

```tsx
<Field label={`语速：${speechRate.toFixed(1)}x`}>
  <Slider
    value={speechRate}
    onChange={(v: number) => setSpeechRate(v)}
    min={0.5}
    max={2.0}
    step={0.1}
  />
</Field>
```

### StatusBadge 状态标签

```tsx
<StatusBadge variant="success" label="当前使用" />
// variant 支持: "success" / "warning" / "error" / "info"
```

### EmptyState 空状态

```tsx
<EmptyState icon="music" title="暂无数据" description="去创建页面开始吧！" />
// icon 可选: "music" / "folder" / "mic" / "settings" / "file" 等
```

### Tip 提示文本

```tsx
<Tip>
  💡 提示内容，支持 <a href="https://..." target="_blank" style={{ color: "#3b82f6" }}>链接</a> 和换行。
</Tip>
```

### Heading 标题

```tsx
<Heading level={4}>🎵 歌词同步</Heading>
// level 1-6，对应 h1-h6 级别
```

---

## 关键模式

### 1. Action 缓存

```typescript
// 首次渲染时 actions 数组可能为空，导致按钮不显示
// 必须缓存首次获取到的有效 actions
const [cachedActions, setCachedActions] = useLocalState("ca", () => [] as HostedAction[])
if (actions.length > 0 && actions.length !== cachedActions.length) {
  setCachedActions(actions)
}
const effectiveActions = cachedActions.length > 0 ? cachedActions : actions
```

### 2. ActionButton 后备方案

```tsx
// 当 saveAction 还没加载时，显示一个占位按钮
{saveAction
  ? <ActionButton action={saveAction} values={{ config: buildConfig() }}>保存</ActionButton>
  : <ActionButton action={{ id: "update_settings", call: async () => {} } as HostedAction} values={{ config: buildConfig() }}>保存 (加载中…)</ActionButton>
}
```

### 3. useLocalState 的 key 必须唯一

```typescript
// 每个 useLocalState 的 key 在组件内必须唯一
// 建议用简短缩写，如 "ar" "am" "sp" "pf" 等
const [val1, setVal1] = useLocalState("k1", () => default1)
const [val2, setVal2] = useLocalState("k2", () => default2)
```

### 4. 数组字段用 Textarea 展示

```typescript
// 配置项是 string[]，UI 中用换行分隔的 Textarea
const [text, setText] = useLocalState(
  "id",
  () => (state.config?.my_list || []).join("\n")
)

// 保存时拆回数组
config: {
  my_list: text.split("\n").map(s => s.trim()).filter(Boolean)
}
```

### 5. Text 组件 color 属性

```tsx
<Text color="primary">主色文字</Text>
<Text color="secondary">次要文字</Text>
<Text color="muted">弱化文字</Text>
{/* ❌ 不支持: danger, warning, default */}
```

### 6. 条件渲染

```tsx
{mySetting && (
  <Stack>
    <Divider />
    <Field label="子选项">
      <Switch checked={sub} onChange={setSub} />
    </Field>
  </Stack>
)}
```

### 7. 时间格式化

```typescript
function formatTime(ts: number): string {
  if (!ts || ts <= 0) return "—"
  return new Date(ts * 1000).toLocaleString()
}
```

### 8. 文件大小格式化

```typescript
function fmtSize(bytes: number): string {
  if (!bytes || bytes <= 0) return "0 B"
  if (bytes >= 1_073_741_824) return (bytes / 1_073_741_824).toFixed(2) + " GB"
  if (bytes >= 1_048_576) return (bytes / 1_048_576).toFixed(2) + " MB"
  if (bytes >= 1_024) return (bytes / 1_024).toFixed(2) + " KB"
  return bytes + " B"
}
```

### 9. api.call() — 直接调用后端方法

除了 `ActionButton` 和 `ActionForm`，还可以通过 `api.call()` 直接调用 `@ui.action` 方法：

```tsx
// 在事件处理函数中直接调用后端方法
const handleDeleteSong = (recordId: string) => {
  api.call("delete_song", { record_id: recordId }).then(() => api.refresh())
}

const handleDeleteVoice = (voiceId: string) => {
  if (confirm("确定要删除吗？")) {
    api.call("delete_custom_voice", { voice_id: voiceId }).then(() => api.refresh())
  }
}

// 在按钮点击事件中使用
<button onClick={() => handleDeleteSong(song.id)} style={btnSmStyle}>
  🗑️ 删除
</button>
```

**`api.call()` 的特点**：
- 参数格式：`api.call("action_id", { param1: value1, ... })`
- 返回 Promise，需要 `.then()` 或 `await`
- 调用后通常需要 `.then(() => api.refresh())` 刷新面板数据
- 适用于不需要表单的简单操作（删除、刷新列表等）
- 不需要在 Python 端额外配置，只要方法有 `@ui.action` 装饰器即可

**三种 UI→后端调用方式对比**：

| 方式 | 适用场景 | 参数传递 | 刷新方式 |
|------|---------|---------|---------|
| `ActionButton` | 无表单输入的操作 | `values={{ config: {...} }}` | `onResult` 中手动 `api.refresh()` |
| `ActionForm` | 需要用户输入的表单 | schema + fields 定义 | `onResult` 中手动 `api.refresh()` |
| `api.call()` | 事件处理函数中调用 | 直接传参 `{param: value}` | `.then(() => api.refresh())` |

## Python 端对应的 UI 方法

```python
# settings_context — 提供面板数据
@ui.context("settings")
async def settings_context(self):
    return {
        "config": {
            "my_setting": self.my_setting,
            "my_text": self.my_text,
            "my_list": self.my_list,
        },
        "status": {"running": self._running},
    }

# update_settings — 响应保存按钮
@ui.action(id="update_settings")
async def update_settings(self, config: dict = None, _ctx=None, **_):
    if not isinstance(config, dict):
        return Err(SdkError("config 必须是对象"))
    self.my_setting = config.get("my_setting", False)
    self.my_text = config.get("my_text", "")
    self.my_list = config.get("my_list", [])
    return Ok({"status": "saved"})
```

## 相关文档

- [01-plugin-toml.md](01-plugin-toml.md) — 配置项定义（`[settings]` 节）
- [09-permission-system.md](09-permission-system.md) — 权限 UI 的完整实现
- [11-undo-and-logging.md](11-undo-and-logging.md) — 撤销按钮 + 操作日志表格
- [04-i18n.md](04-i18n.md) — 翻译文本在 UI 中的使用