# plugin.toml 完整参考

## 完整模板

```toml
[plugin]
id = "your_plugin_id"                    # 唯一标识符，必须与目录名一致
name = "插件中文名"                       # 显示名称
description = "插件功能描述（给用户看）"     # 长描述
short_description = "简短描述（给 AI 看）"   # 短描述，AI 用来匹配用户意图
keywords = ["关键词1", "关键词2", ...]      # AI 匹配关键词，中英文都写
version = "0.1.0"
entry = "plugins.插件目录名:PluginClassName"  # 必须与目录名完全一致！

[plugin.author]
name = "作者名"

[plugin.sdk]
recommended = ">=0.1.0,<0.2.0"
supported = ">=0.1.0,<0.3.0"

[plugin_runtime]
enabled = true       # 是否启用
auto_start = true    # 是否随 N.E.K.O 自动启动

[plugin.store]
enabled = true       # 是否启用持久化存储

[plugin.database]
enabled = true       # 是否启用 SQLite 数据库（需要才能用 self.db）

[plugin.i18n]
default_locale = "zh-CN"     # 默认语言
locales_dir = "i18n"         # 翻译文件目录

[plugin.ui]
enabled = true

[[plugin.ui.panel]]
id = "settings"
title = "设置面板标题"
entry = "ui/settings.tsx"
context = "settings"
permissions = ["state:read", "action:call", "config:read"]

[[plugin.ui.guide]]
id = "guide"
title = "使用指南"
entry = "docs/guide.md"
permissions = ["state:read"]

# ── 业务配置项 ──
[settings]
# 在这里定义所有插件自定义配置项，每个配置项要：
# 1. 有明确的类型（bool/string/array）
# 2. 有合理的默认值
# 3. 在 __init__ 和 __init__.py 的 on_startup 中读取
```

## 关键注意事项

### 1. entry 路径必须与目录名一致

```toml
# 假设目录名是 my_plugin，类名是 MyPlugin
entry = "plugins.my_plugin:MyPlugin"   # ✅ 正确
entry = "plugins.MyPlugin:MyPlugin"    # ❌ 大小写不匹配 → PluginEntryDirectoryMismatch
```

### 2. short_description 和 keywords 是 AI 匹配的关键

AI 通过这两个字段决定是否调用你的插件。**必须中英文都写，覆盖用户可能的所有说法**。

```toml
# ❌ 太简单，AI 匹配不到
keywords = ["文件", "搜索"]

# ✅ 覆盖各种说法
keywords = [
    "文件", "搜索", "扫描", "索引", "查找", "找文件", "找不到", "在哪",
    "目录", "管理", "读取", "复制", "移动", "删除", "粘贴", "最近",
    "file", "search", "scan", "find", "locate", "read", "copy",
    "move", "delete", "paste", "recent"
]
```

### 3. settings 节定义配置项

```toml
[settings]
# 数组类型 — 默认空数组
scan_paths = []

# 布尔类型 — 默认 false
enable_file_ops = false

# 字符串类型 — 默认空字符串
api_key = ""
```

**注意**：依赖 `plugin.store` 时，配置项会被持久化。修改 `plugin.toml` 后必须同步到部署目录。

### 4. 权限声明

```toml
[[plugin.ui.panel]]
permissions = ["state:read", "action:call", "config:read"]
```

- `state:read` — 面板可以读取插件状态
- `action:call` — 面板可以调用 `@ui.action` 方法
- `config:read` — 面板可以读取配置

### 5. 版本兼容性

```toml
[plugin.sdk]
recommended = ">=0.1.0,<0.2.0"   # 推荐版本范围
supported = ">=0.1.0,<0.3.0"     # 支持版本范围（宽于推荐）
```

## 配置项在 Python 中的读取

```python
# __init__.py → on_startup
cfg = await self.config.dump()
settings = cfg.get("settings", {})

# 直接映射到实例变量
self.scan_paths = settings.get("scan_paths", [])
self.enable_file_ops = settings.get("enable_file_ops", False)
self.api_key = settings.get("api_key", "")
```

## 配置项在 UI 中的读取

```typescript
// settings.tsx → State 类型
type State = {
    config: {
        scan_paths: string[]
        enable_file_ops: boolean
        api_key: string
        // ...
    }
}

// 使用
const [scanPathsText, setScanPathsText] = useLocalState(
    "sp",
    () => (state.config?.scan_paths || []).join("\n")
)
```