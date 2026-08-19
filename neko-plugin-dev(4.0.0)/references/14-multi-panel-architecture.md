# 14. 多面板架构设计

> 基于 `ai_singer` 插件双面板（主面板 + 独立设置面板）+ 双 Context 的实战经验。
> 涵盖面板划分策略、Context 设计、配置共享、状态同步等通用模式。

---

## 14.1 为什么需要多面板

当一个插件功能复杂时，单个面板会变得拥挤且难以使用。多面板架构可以：

- **分离关注点**：设置 vs 功能操作，各司其职
- **降低认知负荷**：用户不需要在同一个页面中看到所有配置
- **复用 Context**：不同面板从不同 Context 获取所需数据
- **灵活权限控制**：不同面板可以有不同的权限声明

---

## 14.2 面板划分策略

以 ai_singer 为例，划分为两个面板：

| 面板 | ID | Context | 用途 |
|------|-----|---------|------|
| 主面板 | `main` | `ai_singer_dashboard` | 演唱、历史记录、声音克隆、内置设置 |
| 独立设置 | `settings` | `ai_singer_settings` | 独立设置页面，API Key 等初始配置 |

**plugin.toml 配置**：
```toml
[plugin.ui]
enabled = true

[[plugin.ui.panel]]
id = "main"
title = "AI 歌手"
entry = "ui/panel.tsx"
context = "ai_singer_dashboard"
permissions = ["state:read", "action:call", "config:read"]

[[plugin.ui.panel]]
id = "settings"
title = "AI 歌手 · 设置"
entry = "ui/settings.tsx"
context = "ai_singer_settings"
permissions = ["state:read", "action:call", "config:read"]

# 使用指南面板（Markdown，给用户看）
[[plugin.ui.guide]]
id = "quickstart"
title = "快速开始"
entry = "docs/quickstart.md"
permissions = ["state:read"]
```

**划分原则**：

1. **初始配置独立成面板**：首次使用需要配置 API Key 等 → 独立设置面板，降低主面板复杂度
2. **主面板内嵌设置标签页**：常用配置（模型选择、参数调整）放在主面板的 settings 标签页
3. **功能按标签页组织**：主面板内的"演唱""历史""克隆""设置"用标签页切换
4. **使用指南用 guide**：Markdown 文档放在 `[[plugin.ui.guide]]` 中

---

## 14.3 Context 设计模式

### 双 Context 策略

不同面板可能需要不同的数据视图：

```python
# 设置面板专用 Context — 返回所有可编辑的配置项
@ui.context(id="ai_singer_settings")
async def provide_settings(self) -> Dict[str, Any]:
    cv_ok, cv_msg = False, "后端未就绪"
    if self._backend:
        cv_ok, cv_msg = await self._backend.health_check()
    return {
        # 配置项（供 UI 绑定初始值）
        "api_key": self._config.get("api_key", ""),
        "workspace": self._config.get("workspace", ""),
        "region": self._config.get("region", "cn-beijing"),
        "model": self._config.get("model", "default"),
        # 连接状态
        "cosyvoice_ok": cv_ok,
        "cosyvoice_status": cv_msg,
    }

# 主面板 Context — 返回业务数据
@ui.context(id="ai_singer_dashboard")
async def provide_dashboard(self) -> Dict[str, Any]:
    cv_ok, cv_msg = False, "后端未就绪"
    if self._backend:
        cv_ok, cv_msg = await self._backend.health_check()
    # 刷新业务数据
    if cv_ok:
        try:
            self._items = await self._backend.list_items()
        except Exception:
            pass
    return {
        # 连接状态
        "cosyvoice_ok": cv_ok,
        "cosyvoice_status": cv_msg,
        # 布尔判断字段（UI 中做条件渲染）
        "api_key_configured": bool(self._config.get("api_key", "")),
        "workspace_configured": bool(self._config.get("workspace", "")),
        # 业务数据
        "items": self._items,
        "recent_records": self._recent_records[-20:],
        # 参数
        "speech_rate": self._config.get("speech_rate", 1.0),
    }
```

**Context 设计原则**：

| 原则 | 说明 | 反例 |
|------|------|------|
| 返回所需最小数据 | 每个 Context 只返回其面板需要的数据 | 所有 Context 返回全量配置 |
| 提供布尔判断字段 | `api_key_configured: bool` 比返回 `api_key: str` 更安全 | 在 UI 中用 `state.api_key.length > 0` 判断 |
| 实时健康检查 | 每次 Context 刷新都做健康检查，不缓存状态 | 只在 startup 检查一次 |
| 业务数据实时刷新 | 在 Context 中刷新列表等数据 | 依赖 action 回调手动刷新 |

---

## 14.4 配置共享模式

多面板需要共享同一份配置，关键是**配置变更后的同步**：

### Python 端

```python
# save_api_config 同时更新：
# 1. 内存中的 self._config（立即生效）
# 2. N.E.K.O settings 系统（持久化）
# 3. 重建 Backend（端点可能变了）

async def save_api_config(self, config: dict = None, **_):
    # 更新内存配置
    self._config["api_key"] = config.get("api_key", "")
    self._config["workspace"] = config.get("workspace", "")

    # 持久化
    await self.ctx.update_own_config({"settings": {
        "api_key": self._config["api_key"],
        "workspace": self._config["workspace"],
    }})

    # 重建后端
    self._init_backend()

    # 健康检查
    cv_ok, cv_msg = await self._backend.health_check()
    return Ok({"success": True, "cosyvoice_ok": cv_ok, "warning": cv_msg if not cv_ok else ""})
```

### 生命周期中恢复配置

```python
@lifecycle(id="startup")
async def on_startup(self, **_):
    cfg = await self.config.dump()
    settings = cfg.get("settings", {})
    for key in self.DEFAULT_CONFIG:
        if key in settings:
            self._config[key] = settings[key]
    self._init_backend()
    # ...

@lifecycle(id="reload")
async def on_reload(self, **_):
    # 同样恢复配置
    cfg = await self.config.dump()
    settings = cfg.get("settings", {})
    for key in self.DEFAULT_CONFIG:
        if key in settings:
            self._config[key] = settings[key]
    self._init_backend()

@lifecycle(id="config_change")
async def on_config_change(self, old_config=None, new_config=None, **_):
    if new_config:
        settings = new_config.get("settings", {})
        for key in self.DEFAULT_CONFIG:
            if key in settings:
                self._config[key] = settings[key]
        self._init_backend()
```

### UI 端：`refresh_context=True`

```python
# 所有修改配置的 action 都加 refresh_context=True
@ui.action(label="💾 保存配置", refresh_context=True)
async def save_api_config(self, ...): ...

@ui.action(label="🎙️ 克隆声音", refresh_context=True)
async def clone_voice(self, ...): ...

@ui.action(label="🗑️ 删除", refresh_context=True)
async def delete_item(self, ...): ...
```

`refresh_context=True` 确保 action 执行后，关联面板的 Context 自动刷新，UI 数据同步更新。

---

## 14.5 面板内标签页模式

主面板使用标签页组织多个功能区域：

```tsx
export default function MainPanel(props: PluginSurfaceProps<State>) {
  const { state, actions, api, t } = props

  // 标签页状态
  const [activeTab, setActiveTab] = useLocalState<"create" | "history" | "clone" | "settings">(
    "tab", "create"
  )

  // 定义标签页
  const tabs = [
    { id: "create" as const,  label: "演唱",   icon: "music" },
    { id: "history" as const, label: "历史",   icon: "folder" },
    { id: "clone" as const,  label: "声音克隆", icon: "mic" },
    { id: "settings" as const, label: "设置",   icon: "settings" },
  ]

  return (
    <Page
      title="AI 歌手"
      subtitle="云端声音克隆 · 歌词同步演唱"
      tabs={tabs.map((tab) => ({
        ...tab,
        active: activeTab === tab.id,
        onClick: () => setActiveTab(tab.id),
      }))}
    >
      {/* 根据 activeTab 条件渲染不同内容 */}
      {activeTab === "create" && (
        <Stack gap="lg">
          {/* 演唱表单 */}
        </Stack>
      )}

      {activeTab === "history" && (
        <Stack gap="lg">
          {/* 历史记录列表 */}
        </Stack>
      )}

      {/* ... 更多标签页 */}
    </Page>
  )
}
```

**标签页设计要点**：

1. **`useLocalState` 管理当前标签**：key 如 `"tab"`，默认值为首个标签
2. **`Page` 组件支持 `tabs` 属性**：自动渲染标签页导航栏
3. **条件渲染**：用 `{activeTab === "xxx" && (...)}` 而非路由
4. **标签不宜超过 5 个**：过多标签考虑拆分面板

---

## 14.6 两个面板的保存操作协调

独立设置面板和主面板内嵌设置标签页**都可能调用同一个 `save_api_config` action**：

```python
@plugin_entry(id="save_api_config", ...)
@ui.action(label="💾 保存配置", refresh_context=True)
async def save_api_config(
    self,
    api_key: str = "",
    workspace: str = "",
    # ... 平铺参数
    config: dict = None,   # ← 兼容 settings.tsx 传来的 config 对象
    **___,
):
    # 支持从 settings UI 传入 config 对象
    if isinstance(config, dict):
        api_key = api_key or config.get("api_key", "")
        workspace = workspace or config.get("workspace", "")
        # ...

    # 更新配置 + 持久化 + 重建 backend + 健康检查
    # ...
```

**UI 端两种调用方式**：

```tsx
// settings.tsx（独立面板）：用 ActionButton + config 对象
<ActionButton
  action={saveAction}
  values={{ config: buildConfig() }}  // 打包为 config 对象
  onResult={handleResult}
>
  保存全部配置
</ActionButton>

// panel.tsx（主面板设置标签页）：用 ActionForm + 平铺字段
<ActionForm
  action={saveAction}
  schema={{
    type: "object",
    properties: {
      api_key: { type: "string", label: "API Key" },
      workspace: { type: "string", label: "Workspace ID" },
      // ...
    },
  }}
  fields={{
    api_key: { placeholder: "sk-xxx", defaultValue: "" },
    workspace: { placeholder: "ws-xxx", defaultValue: "" },
    // ...
  }}
  onResult={handleResult}
  submitLabel="💾 保存全部配置"
  layout="vertical"
/>
```

**关键设计**：

- **同时支持两种参数格式**：平铺参数（`ActionForm` 默认）和 config 对象（`ActionButton` 手动打包）
- **`isinstance(config, dict)` 判断**：识别参数来源并正确解包
- **`refresh_context=True`**：保存后自动刷新关联 Context

### 第三种调用方式：api.call()

除了 `ActionButton` 和 `ActionForm`，UI 还可以通过 `api.call()` 直接调用后端方法：

```tsx
// 直接调用任何 @ui.action 方法
const handleDelete = (recordId: string) => {
  api.call("delete_song", { record_id: recordId }).then(() => api.refresh())
}

// 在按钮中触发
<button onClick={() => handleDelete(song.id)} style={btnSmStyle}>
  🗑️ 删除
</button>
```

**`api.call()` 在多面板中的注意事项**：
- 两个面板都可以调用同一个 action
- 调用后通常需要 `.then(() => api.refresh())` 刷新当前面板
- 不需要 `refresh_context=True`，因为刷新是手动控制的

---

## 14.7 数据持久化：Config vs Store

| 机制 | 用途 | 特点 |
|------|------|------|
| `self.config` / `settings` | 插件配置项 | 持久化、自动同步、`config_change` 生命周期触发 |
| `self.store` | 运行时状态/历史数据 | 键值存储、手动读写 |

```python
# Config：API Key、模型选择等配置
self._config["api_key"] = "sk-xxx"
await self.ctx.update_own_config({"settings": {"api_key": "sk-xxx"}})

# Store：历史歌曲记录、克隆音色 ID 等
await self.store.set("recent_songs", json.dumps(songs))
songs = await self.store.get("recent_songs")

# Store 恢复（startup 时）
async def _restore_data(self):
    try:
        raw = unwrap(await self.store.get("recent_songs"))
        if raw:
            self._recent_songs = json.loads(raw) if isinstance(raw, str) else raw
    except Exception as e:
        self.logger.debug("无历史记录可恢复: {}", e)
```

**选择指南**：

- **配置项**（API Key、模型、开关）→ `settings` / `self.config`
- **运行时数据**（历史记录、缓存、克隆音色 ID）→ `self.store`
- **大数据量**（文件索引等）→ `self.db`

---

## 14.8 检查清单

- [ ] 功能复杂的插件考虑多面板架构
- [ ] 每个面板有独立的 Context ID（`@ui.context(id="xxx")`）
- [ ] 每个 Context 只返回其面板需要的数据
- [ ] Context 中包含健康检查结果（实时连接状态）
- [ ] 提供布尔判断字段（如 `api_key_configured`）供 UI 条件渲染
- [ ] 配置保存后同时更新：内存 → settings 系统 → Backend
- [ ] 所有修改状态的 action 加 `refresh_context=True`
- [ ] `save_api_config` 保存后立即做健康检查并返回结果
- [ ] 主面板标签页不超过 5 个
- [ ] `useLocalState` key 全局唯一（不同面板/标签不冲突）
- [ ] 独立设置面板和主面板设置标签页共享同一个 save action
- [ ] save action 同时支持平铺参数和 config 对象两种格式
- [ ] 区分 config（配置项）和 store（运行时数据）的使用场景
- [ ] startup/reload/config_change 都恢复配置
