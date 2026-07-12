# 16. 后端精简与迁移模式

> 基于 `ai_singer` 插件从 CosyVoice+MiMo 双后端简化为纯 MiMo 单后端的实战经验。
> 涵盖多后端到单后端的迁移策略、代码清理清单、向后兼容处理、配置漂移防范。

---

## 16.1 适用场景

- 插件最初设计了多个后端/服务商，但实际只有一种可靠
- 需要移除某个已废弃的 SDK 依赖（如从阿里云 CosyVoice 迁移到小米 MiMo）
- 用户配置太复杂，需要简化到"只配一个 API Key 就能用"
- 插件设置面板因后端过多导致 UX 混乱

---

## 16.2 迁移前：现状评估清单

在动手改代码前，先完整梳理影响范围：

| 评估项 | 说明 | ai_singer 实例 |
|--------|------|---------------|
| 要移除的后端类 | 类名、文件位置 | `CosyVoiceBackend`（~280 行） |
| 要保留的后端类 | 类名 | `MiMoTTSBackend`（~100 行） |
| 废弃的 plugin_entry | 不再需要的 AI 入口 | `clone_neko_voice`, `list_custom_voices`, `delete_custom_voice` |
| 废弃的 settings 项 | plugin.toml 中的配置 | 6 项 CosyVoice 配置 |
| 废弃的 UI 标签页 | panel.tsx 中的 tab | 「声音克隆」标签页 |
| 废弃的依赖 | plugin.toml dependencies | `dashscope>=1.20.0` |
| 废弃的 Context 字段 | UI Context 返回值 | `cosyvoice_ok`, `cosyvoice_status`, `custom_voices` |
| 废弃的健康检查 | 启动日志中的状态 | `cosyvoice_ok=False` 日志 |
| 受影响的 UI 文件 | settings.tsx, panel.tsx | 两个文件都需要改 |
| 受影响的文档 | docs/ 目录 | 使用指南中的 CosyVoice 描述 |

**关键教训**：不要边改边想。先做完这个清单，确保不会遗漏任何引用。

---

## 16.3 迁移步骤（有序执行）

### 第一步：更新 DEFAULT_CONFIG

```python
# 迁移前：双后端配置
DEFAULT_CONFIG: Dict[str, Any] = {
    # CosyVoice 配置（要移除）
    "cosyvoice_api_key": "",
    "cosyvoice_workspace": "",
    "cosyvoice_region": "cn-beijing",
    "cosyvoice_model": "cosyvoice-v3-flash",
    "cosyvoice_speech_rate": 1.0,
    "cosyvoice_pitch_rate": 1.0,
    # MiMo 配置
    "mimo_api_key": "",
    "mimo_base_url": "https://api.xiaomimimo.com/v1",
    "mimo_voice": "冰糖",
    "mimo_enabled": False,
}

# 迁移后：纯 MiMo 配置
DEFAULT_CONFIG: Dict[str, Any] = {
    "mimo_api_key": "",
    "mimo_base_url": "https://api.xiaomimimo.com/v1",
    "mimo_voice": "冰糖",
    "mimo_enabled": True,  # ← 注意：默认改为 True
}
```

**要点**：
- 移除所有废弃配置项
- 保留的配置项确认默认值合理（如 `mimo_enabled` 从 `False` 改为 `True`）
- `DEFAULT_CONFIG` 的 key 必须与 `plugin.toml` 的 `[settings]` 节完全一致

### 第二步：更新 __init__.py 的 __init__ 方法

```python
# 迁移前
def __init__(self, ctx):
    super().__init__(ctx)
    self._config: Dict[str, Any] = dict(self.DEFAULT_CONFIG)
    self._cosyvoice: Optional[CosyVoiceBackend] = None  # ← 删除
    self._mimo: Optional[MiMoTTSBackend] = None
    self._custom_voices: List[Dict] = []                 # ← 删除
    self._recent_songs: List[Dict[str, Any]] = []

# 迁移后
def __init__(self, ctx):
    super().__init__(ctx)
    self._config: Dict[str, Any] = dict(self.DEFAULT_CONFIG)
    self._mimo: Optional[MiMoTTSBackend] = None
    self._recent_songs: List[Dict[str, Any]] = []
```

### 第三步：清理生命周期方法

```python
# 需要检查的方法清单：
# on_startup    — 移除 CosyVoice 初始化代码
# on_shutdown   — 移除 _cosyvoice.close()
# on_reload     — 通常只是重新读取配置，可能不需要改
# on_config_change — 同 reload
# _async_startup_warmup — 移除 CosyVoice 预热
# _restore_songs — 移除 CosyVoice voice_id 恢复逻辑
```

### 第四步：精简 _init_backend

```python
# 迁移前
def _init_backend(self):
    cfg = {**self._config, "_log": lambda msg: self.logger.info(msg)}
    old_cv = self._cosyvoice
    old_mimo = self._mimo
    self._cosyvoice = CosyVoiceBackend(cfg) if self._config.get("cosyvoice_enabled") else None
    self._mimo = MiMoTTSBackend(cfg)
    if old_cv:
        asyncio.create_task(old_cv.close())
    if old_mimo:
        asyncio.create_task(old_mimo.close())

# 迁移后
def _init_backend(self):
    cfg = {**self._config, "_log": lambda msg: self.logger.info(msg)}
    old_mimo = self._mimo
    self._mimo = MiMoTTSBackend(cfg)
    if old_mimo:
        asyncio.create_task(old_mimo.close())
```

### 第五步：精简 UI Context

```python
# 迁移前：返回双后端状态
@ui.context(id="ai_singer_dashboard")
async def provide_dashboard(self):
    cv_ok, cv_msg = ...
    mimo_ok, mimo_msg = ...
    return {
        "cosyvoice_ok": cv_ok,
        "cosyvoice_status": cv_msg,
        "mimo_ok": mimo_ok,
        "mimo_status": mimo_msg,
        "custom_voices": self._custom_voices,  # ← 删除
        ...
    }

# 迁移后：只返回 MiMo 状态
@ui.context(id="ai_singer_dashboard")
async def provide_dashboard(self):
    mimo_ok, mimo_msg = False, "MiMo 未就绪"
    if self._mimo:
        mimo_ok, mimo_msg = await self._mimo.health_check()
    return {
        "mimo_ok": mimo_ok,
        "mimo_status": mimo_msg,
        "mimo_voice": self._config.get("mimo_voice", "冰糖"),
        "recent_songs": self._recent_songs[-20:],
    }
```

### 第六步：简化核心入口

以 `check_setup` 和 `sing` 为例：

```python
# check_setup — 迁移前检查两个后端
async def check_setup(self, ...):
    cv_ok, cv_msg = ...
    mimo_ok, mimo_msg = ...
    ready = cv_ok or mimo_ok
    missing = []
    if not cv_ok and not mimo_ok:
        missing.append("API Key")

# check_setup — 迁移后只检查 MiMo
async def check_setup(self, ...):
    mimo_ok, mimo_msg = ...
    missing = []
    if not mimo_ok:
        if not self._config.get("mimo_api_key"):
            missing.append("MiMo API Key")
    return Ok({
        "ready": mimo_ok,
        "mimo_ok": mimo_ok,
        "mimo_voice": ...,
        "missing": missing,
    })

# sing — 迁移后移除所有 voice_id / CosyVoice 分支
async def sing(self, song_name, lyrics, style, mimo_voice, ...):
    # 只保留 MiMo 演唱逻辑
    # 移除 CosyVoice 分支
    # 每条歌词前自动添加 (唱歌) 标签
```

### 第七步：删除废弃的 plugin_entry

```python
# 以下三个入口需要从 __init__.py 中完全删除：
# @plugin_entry(id="clone_neko_voice")     — 声音克隆（CosyVoice 专属）
# @plugin_entry(id="list_custom_voices")   — 列出克隆音色
# @plugin_entry(id="delete_custom_voice")  — 删除克隆音色
```

**注意**：删除时确保也删除对应的 `@ui.action` 装饰器（如果有双装饰器叠加）。

### 第八步：更新 plugin.toml

```toml
# 迁移前
[plugin.dependencies]
python = ["dashscope>=1.20.0", "openai>=1.0.0"]

[settings]
cosyvoice_api_key = ""
cosyvoice_workspace = ""
cosyvoice_region = "cn-beijing"
cosyvoice_model = "cosyvoice-v3-flash"
cosyvoice_speech_rate = 1.0
cosyvoice_pitch_rate = 1.0
mimo_api_key = ""
mimo_base_url = "https://api.xiaomimimo.com/v1"
mimo_voice = "冰糖"
mimo_enabled = false

# 迁移后
[plugin.dependencies]
openai = ">=1.0.0"

[settings]
mimo_api_key = ""
mimo_base_url = "https://api.xiaomimimo.com/v1"
mimo_voice = "冰糖"
mimo_enabled = true
```

**dependencies 格式注意**：
- `plugin.toml` 中 `[plugin.dependencies]` 是 TOML 内联表格式
- N.E.K.O 期望 `key = "value"` 格式，如 `openai = ">=1.0.0"`
- 不是 `python = ["xxx"]` 列表格式（虽然某些版本兼容但会报警告）

### 第九步：更新 UI 文件

#### settings.tsx
```tsx
// 迁移后：移除所有 CosyVoice 输入项
// 只保留 MiMo API Key + 音色选择
// State 接口从 ~15 个字段精简到 ~4 个
interface State {
  mimo_api_key: string
  mimo_voice: string
  mimo_ok: boolean
  mimo_status: string
}
```

#### panel.tsx
```tsx
// 迁移后：移除「声音克隆」标签页
// 移除所有 CosyVoice 相关的 State 字段
// 移除 CustomVoice / CloneResult 接口定义
// tabs 数组从 4 项减到 3 项
const tabs = [
  { id: "create",  label: "演唱" },
  { id: "history", label: "历史" },
  { id: "settings", label: "设置" },
]
```

---

## 16.4 向后兼容处理

### 保留 Backend 类定义（不实例化）

如果其他代码或插件可能 import 你的 Backend 类，保留类定义但不实例化：

```python
# ✅ 保留类定义（向后兼容），但在 _init_backend 中不再实例化
class CosyVoiceBackend:
    """阿里云百炼 CosyVoice 云端后端
    注意：此类已废弃，仅保留定义以确保向后兼容。
    插件当前仅使用 MiMo V2.5 TTS。
    """
    # ... 类定义保留

# 在 _init_backend 中
def _init_backend(self):
    cfg = {...}
    self._mimo = MiMoTTSBackend(cfg)
    # self._cosyvoice 不再创建
```

### 处理旧数据兼容

```python
# 如果 store 中可能存有旧格式数据，做兼容处理
async def _restore_songs(self):
    try:
        raw = unwrap(await self.store.get("recent_songs"))
        if raw:
            songs = json.loads(raw) if isinstance(raw, str) else raw
            # 清理旧格式字段
            for song in songs:
                song.pop("cosyvoice_voice_id", None)
                song.pop("neko_voice_file", None)
                song.pop("cv_voice", None)
            self._recent_songs = songs
    except Exception as e:
        self.logger.debug("无历史记录可恢复: {}", e)
```

---

## 16.5 配置漂移陷阱

### 问题：旧配置残留

当用户在旧版本配置了 CosyVoice，升级到新版本后，N.E.K.O settings 系统中**仍保留旧配置项**。每次 `config.dump()` 都会返回这些旧字段。

**日志证据**（来自 ai_singer 实际运行）：
```
# 新代码只写入 mimo_api_key + mimo_voice
# 但 config.dump() 返回了旧的 cosyvoice_* 配置
配置已持久化: ['cosyvoice_region', 'cosyvoice_model', 'cosyvoice_speech_rate',
               'cosyvoice_pitch_rate', 'mimo_api_key', 'mimo_voice', 'mimo_enabled']
```

### 解决方案

在 `save_api_config` 中只持久化当前需要的配置项：

```python
async def save_api_config(self, mimo_api_key="", mimo_voice="", config=None, **_):
    new_settings = {}
    if mimo_api_key:
        self._config["mimo_api_key"] = mimo_api_key
        new_settings["mimo_api_key"] = mimo_api_key
    if mimo_voice:
        self._config["mimo_voice"] = mimo_voice
        new_settings["mimo_voice"] = mimo_voice

    if new_settings:
        await self.ctx.update_own_config({"settings": new_settings})
        # ← 只传变更项，N.E.K.O 会合并到已有 settings 中
        # 注意：旧配置项（cosyvoice_*）仍然保留在系统中
```

**如果确实需要清理旧配置**，可以传入一个标记来触发全量覆盖：

```python
# 慎用！这会清除所有旧配置
await self.ctx.update_own_config({"settings": {
    "mimo_api_key": self._config["mimo_api_key"],
    "mimo_base_url": self._config["mimo_base_url"],
    "mimo_voice": self._config["mimo_voice"],
    "mimo_enabled": self._config["mimo_enabled"],
    # 显式列出所有需要的配置项，不包含旧项
}})
```

但在 `on_startup` / `on_reload` / `on_config_change` 中用 `for key in self.DEFAULT_CONFIG` 过滤即可安全忽略旧配置项：

```python
# ✅ 安全：只处理 DEFAULT_CONFIG 中声明的 key
for key in self.DEFAULT_CONFIG:
    if key in settings:
        self._config[key] = settings[key]
```

---

## 16.6 版本号管理

```toml
# plugin.toml
version = "0.6.0"  # 从 0.5.0 升级，主版本不变，次版本+1
```

**版本号策略**：
- 移除功能 → 次版本号 +1（0.5.0 → 0.6.0）
- 新增功能 → 次版本号 +1
- 纯 Bug 修复 → 修订号 +1（0.5.0 → 0.5.1）
- 破坏性 API 变更 → 主版本号 +1（1.0.0）

---

## 16.7 迁移检查清单

### 代码层面
- [ ] `DEFAULT_CONFIG` 移除所有废弃 key，确认保留项默认值合理
- [ ] `__init__` 移除废弃属性（`_cosyvoice`、`_custom_voices` 等）
- [ ] `_async_startup_warmup` 移除废弃后端预热
- [ ] `on_shutdown` 移除废弃后端的 `close()` 调用
- [ ] `_init_backend` 移除废弃后端实例化
- [ ] `_restore_songs` 移除废弃字段恢复逻辑
- [ ] 删除废弃的 `@plugin_entry` + 对应的 `@ui.action`
- [ ] 核心入口（`check_setup`、`sing`、`save_api_config`）移除废弃分支
- [ ] UI Context（`provide_settings`、`provide_dashboard`）移除废弃字段
- [ ] 定时器中的健康检查移除废弃后端

### 配置层面
- [ ] `plugin.toml` 的 `[settings]` 节移除废弃配置项
- [ ] `plugin.toml` 的 `[plugin.dependencies]` 移除废弃 SDK
- [ ] `plugin.toml` 的 `version` 更新
- [ ] `plugin.toml` 的 `description`、`keywords` 更新

### UI 层面
- [ ] `settings.tsx` 的 State 接口移除废弃字段
- [ ] `settings.tsx` 移除废弃配置输入组件
- [ ] `panel.tsx` 的 State 接口移除废弃字段
- [ ] `panel.tsx` 移除废弃标签页
- [ ] `panel.tsx` 移除废弃的接口定义（CustomVoice 等）
- [ ] `panel.tsx` 移除废弃的 action 引用

### 验证层面
- [ ] 删除 `__pycache__` 目录（关键！见 17-pyc-cache-trap）
- [ ] 同步文件到部署目录
- [ ] 重启 N.E.K.O
- [ ] 检查启动日志：不再出现废弃后端的日志
- [ ] 检查 entries：不再包含已删除的 entry
- [ ] 检查配置保存：只持久化当前需要的配置项
- [ ] UI 面板正常显示，标签页数量正确
