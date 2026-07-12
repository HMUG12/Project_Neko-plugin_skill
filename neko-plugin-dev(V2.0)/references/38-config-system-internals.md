# 38 — 插件配置系统内部机制

> **来源**：N.E.K.O-main `plugin/sdk/shared/core/config.py` + `plugin/core/` 深度逆向分析  
> **适用**：理解 `self.config`、`self.store`、`plugin.toml [settings]` 三者的关系和内部流转

---

## 1. 三种配置存储的定位

```
┌─────────────────────────────────────────────────────┐
│                   plugin.toml [settings]              │
│  静态默认值，插件开发者定义，随插件分发                  │
│  scan_paths = []                                     │
│  enable_ops = false                                  │
├─────────────────────────────────────────────────────┤
│                   self.config (运行时配置)             │
│  合并了 toml 默认值 + store 持久化值 + 用户修改         │
│  cfg = await self.config.dump()                      │
├─────────────────────────────────────────────────────┤
│                   self.store (键值持久化)              │
│  用户通过 UI 修改后的值持久化到 JSON 文件              │
│  await self.store.set("enable_ops", True)            │
└─────────────────────────────────────────────────────┘
```

**合并优先级**：用户修改 (store) > toml 默认值

---

## 2. 配置读取

### 基本模式

```python
@lifecycle(id="startup")
async def on_startup(self, **_):
    cfg = await self.config.dump()          # 获取完整配置
    settings = cfg.get("settings", {})      # 提取 settings 节

    self.enable_ops = settings.get("enable_ops", False)
    self.scan_paths = settings.get("scan_paths", [])
    self.api_key = settings.get("api_key", "")
```

### 在入口方法中读取

```python
@plugin_entry(id="do_something")
async def do_something(self, _ctx=None, **_):
    # 不需要每次读取配置，使用实例变量（在 on_startup 中已加载）
    if not self.enable_ops:
        return Err(SdkError("操作未启用"))
    ...
```

---

## 3. 配置更新

### 用户通过 UI 修改配置

```python
# 在 UI action 中更新配置
@ui.action(id="update_settings")
async def update_settings(self, config: dict = None, _ctx=None, **_):
    if not isinstance(config, dict):
        return Err(SdkError("config 必须是对象"))

    # 1. 更新内存中的实例变量
    self.enable_ops = config.get("enable_ops", self.enable_ops)
    self.scan_paths = config.get("scan_paths", self.scan_paths)

    # 2. 持久化到 store（通过 config 系统）
    await self.config.update({"settings": config})

    return Ok({"status": "saved"})
```

### 通过 config_change 钩子响应

```python
@lifecycle(id="config_change")
async def on_config_change(self, old_config=None, new_config=None, **_):
    """配置变更时自动触发。"""
    if new_config:
        settings = new_config.get("settings", {})
        # ⚠️ 使用 .get() + 默认值，避免覆盖已有值
        self.enable_ops = settings.get("enable_ops", self.enable_ops)
        self.scan_paths = settings.get("scan_paths", self.scan_paths)
    return Ok({"status": "config_updated"})
```

---

## 4. update_own_config 模式

```python
# 只传变更项，不传整个配置对象
await self.update_own_config({
    "settings.enable_ops": True,
    "settings.scan_paths": ["/data", "/docs"]
})

# ⚠️ 使用点号路径访问嵌套配置
# settings.enable_ops → settings 节的 enable_ops 字段
```

### 注意事项

```python
# ❌ 错误：覆盖整个 settings
await self.update_own_config({
    "settings": {"enable_ops": True}  # 丢失了其他配置项！
})

# ✅ 正确：只传变更的字段
await self.update_own_config({
    "settings.enable_ops": True
})
```

---

## 5. 配置生命周期

```
插件安装
   │
   ▼
[plugin.toml] 默认值 ──────┐
   │                      │
   ▼                      ▼
[self.config.dump()] ← [store JSON 文件]
   │                      │
   ▼                      │
[on_startup 读取]         │
   │                      │
   ▼                      │
[用户修改 UI] ─────────────┘
   │
   ▼
[config_change 钩子]
   │
   ▼
[on_reload 钩子]
```

---

## 6. 配置漂移防范

### 什么是配置漂移

当 `plugin.toml` 修改了默认值或新增了配置项，但用户的 store 中保存的是旧配置，导致行为不一致。

### 防范方案

```python
@lifecycle(id="startup")
async def on_startup(self, **_):
    cfg = await self.config.dump()
    settings = cfg.get("settings", {})

    # 1. 读取配置
    self.enable_ops = settings.get("enable_ops", False)

    # 2. 检查缺失的配置项
    defaults = {"enable_ops": False, "scan_paths": [], "api_key": ""}
    missing = {k: v for k, v in defaults.items() if k not in settings}

    # 3. 补充缺失项
    if missing:
        self.logger.warning(f"配置项缺失，补充默认值: {list(missing.keys())}")
        await self.update_own_config(
            {f"settings.{k}": v for k, v in missing.items()}
        )
```

### 迁移策略

```python
@lifecycle(id="startup")
async def on_startup(self, **_):
    cfg = await self.config.dump()
    settings = cfg.get("settings", {})

    # V0.2 迁移：将旧的 api_endpoint 重命名为 base_url
    if "api_endpoint" in settings and "base_url" not in settings:
        settings["base_url"] = settings.pop("api_endpoint")
        await self.config.update({"settings": settings})
        self.logger.info("配置迁移: api_endpoint → base_url")

    self.base_url = settings.get("base_url", "https://api.example.com")
```

---

## 7. 完整配置模板

### plugin.toml

```toml
[plugin.store]
enabled = true

[settings]
# 布尔配置
enable_ops = false
enable_cache = true

# 字符串配置
api_key = ""
base_url = "https://api.example.com"

# 数组配置
scan_paths = []
allowed_extensions = [".txt", ".md", ".py"]

# 数值配置
max_file_size = 10485760  # 10MB
cache_ttl = 3600
```

### Python 端

```python
DEFAULT_CONFIG = {
    "enable_ops": False,
    "enable_cache": True,
    "api_key": "",
    "base_url": "https://api.example.com",
    "scan_paths": [],
    "allowed_extensions": [".txt", ".md", ".py"],
    "max_file_size": 10 * 1024 * 1024,
    "cache_ttl": 3600,
}

@neko_plugin
class MyPlugin(NekoPluginBase):
    def __init__(self, ctx):
        super().__init__(ctx)
        # 从 DEFAULT_CONFIG 初始化所有实例变量
        for key, default in DEFAULT_CONFIG.items():
            setattr(self, key, default)

    @lifecycle(id="startup")
    async def on_startup(self, **_):
        cfg = await self.config.dump()
        settings = cfg.get("settings", {})

        for key, default in DEFAULT_CONFIG.items():
            setattr(self, key, settings.get(key, default))

        # 补充缺失的配置项
        missing = {k: v for k, v in DEFAULT_CONFIG.items() if k not in settings}
        if missing:
            await self.update_own_config(
                {f"settings.{k}": v for k, v in missing.items()}
            )
```

### UI 端

```tsx
type State = {
    config: {
        enable_ops: boolean
        enable_cache: boolean
        api_key: string
        base_url: string
        scan_paths: string[]
        allowed_extensions: string[]
        max_file_size: number
        cache_ttl: number
    }
}
```

---

## 8. 关键陷阱

### 陷阱 38-1：on_config_change 覆盖已有值

```python
# ❌ 错误：new_config 不包含的字段被覆盖为 None
@lifecycle(id="config_change")
async def on_config_change(self, new_config=None, **_):
    settings = new_config.get("settings", {})
    self.enable_ops = settings.get("enable_ops")        # 可能变成 None！
    self.scan_paths = settings.get("scan_paths")        # 可能变成 None！

# ✅ 正确：使用 get() 的第二个参数做默认值
@lifecycle(id="config_change")
async def on_config_change(self, new_config=None, **_):
    settings = new_config.get("settings", {})
    self.enable_ops = settings.get("enable_ops", self.enable_ops)
    self.scan_paths = settings.get("scan_paths", self.scan_paths)
```

### 陷阱 38-2：settings 节与 DEFAULT_CONFIG key 不一致

```python
# plugin.toml
[settings]
enable_file_ops = false       # ← toml 中的 key

# Python
DEFAULT_CONFIG = {
    "enable_ops": False,      # ← 代码中的 key，不匹配！
}
```

**修复**：确保 `[settings]` 节中的 key 与 `DEFAULT_CONFIG` 中的 key 完全一致。

### 陷阱 38-3：update_own_config 传整个对象

```python
# ❌ 错误：覆盖了整个 settings
await self.update_own_config({
    "settings": {"enable_ops": True}  # 丢失了其他所有配置项！
})

# ✅ 正确：只传变更项
await self.update_own_config({
    "settings.enable_ops": True
})
```

---

## 9. 配置设计原则

1. **所有配置项有默认值** — 在 `[settings]` 和 `DEFAULT_CONFIG` 中
2. **只传变更项** — `update_own_config` 不传整个对象
3. **get() 有默认值** — `settings.get(key, default_value)`
4. **三处一致** — toml `[settings]`、Python `DEFAULT_CONFIG`、UI `State` 类型
5. **配置漂移防护** — 启动时检查并补充缺失项

---

## 相关文档

- [01-plugin-toml](01-plugin-toml.md) — plugin.toml 配置
- [02-python-plugin](02-python-plugin.md) — 配置读取模式
- [16-backend-simplification](16-backend-simplification.md) — 配置漂移防范
- [35-store-database-internals](35-store-database-internals.md) — Store 内部机制
