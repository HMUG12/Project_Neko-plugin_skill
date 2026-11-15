# plugin.toml 完整参考

## 完整模板

```toml
[plugin]
id = "your_plugin_id"                    # 唯一标识符，建议与源码目录名一致（打包/生产安装要求对齐）
name = "插件中文名"                       # 显示名称
description = "插件功能描述（给用户看）"     # 长描述
short_description = "简短描述（给 AI 看）"   # 短描述，AI 用来匹配用户意图
keywords = ["^查.*文件$", "search"]      # 正则表达式，仅用于粗筛候选（注意转义）
version = "0.1.0"
type = "plugin"                          # 普通插件；可省略（默认值）
entry = "plugin.plugins.目录名:PluginClassName"  # module.path:ClassName，且必须是 NekoPluginBase 子类

[plugin.author]
name = "作者名"

[plugin.sdk]
recommended = ">=0.1.0,<0.2.0"
supported = ">=0.1.0,<0.3.0"

[plugin_runtime]
enabled = true       # 是否启用
auto_start = true    # 是否随 N.E.K.O 自动启动
timeout = 10         # 启动就绪秒数，须 0 < timeout <= 300

[plugin.store]
enabled = true       # 是否启用持久化存储

dependencies = ["other_plugin_id"]   # 插件 ID 字符串列表；无依赖可省略整行
# Python 第三方包不写在这里，见本文 §6（pyproject.toml + vendor/）

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

### 1. entry 包名建议与目录名一致

```toml
# 假设目录名是 my_plugin，类名是 MyPlugin
entry = "plugin.plugins.my_plugin:MyPlugin"   # ✅ 官方推荐：目录名 = plugin.id = entry 包名
entry = "plugin.plugins.MyPlugin:MyPlugin"    # ⚠️ 大小写不一致；开发期旧发现机制可能容忍，但打包/生产安装会失败
```

`[plugin].entry` 必须是 `module.path:ClassName`，且解析到的类必须是 `NekoPluginBase` 子类（`PluginRouter` 不能直接作为入口）。

### 2. short_description 与 keywords 的作用

`keywords` 在 SDK 里是**正则表达式**（`sdk/shared/core/base.py` 注释），只用于**粗筛候选**，不是给 AI 看的关键词列表。堆砌几十个纯词既不会提升召回，还可能因未转义的特殊字符匹配异常。

```toml
# ✅ 少量、精确、已转义的正则
keywords = ["^查.*文件$", "^(find|search)\s", "weather"]

# ❌ 把中文词当 AI 匹配关键词硬塞
keywords = ["文件", "搜索", "找不到", "在哪"]   # 这些是字面正则，覆盖面很窄
```

真正决定 AI 是否调用的是 `@plugin_entry` 的 `name` / `description`（写清何时调用、前置条件、注意事项）。特殊字符记得转义。

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

> 段名需与代码读取配置时的键一致：官方允许**自定义顶层节名**（如 `[settings]` 或 `[my_plugin]`），只要 `plugin.toml` 与代码（`self.config.dump()["<段名>"]`）一致即可。真实密钥不要写进源码，放用户运行时配置（见 [43-security-hardening.md](43-security-hardening.md) §2）。

**注意**：依赖 `plugin.store` 时，配置项会被持久化。修改 `plugin.toml` 后：源码树/开发者模式点 **Reload**（改了依赖/结构需重启该插件）；手工同步场景再覆盖文件（见 [06-deployment.md](06-deployment.md)）。

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

### 6. Python 第三方依赖声明（两条通道，不要混用）

`plugin.toml` 的 `[plugin].dependencies` 只接受**插件 ID 字符串列表**，表示插件间依赖：

```toml
[plugin]
dependencies = ["base_plugin"]
```

Python 包写在插件目录下的 `pyproject.toml`，再同步进 `vendor/`：

```toml
[project]
dependencies = ["httpx>=0.27"]
```

```bash
uv run neko-plugin sync <plugin_id>   # 安装进 vendor/
uv run neko-plugin check <plugin_id>       # 校验 vendor/ 是否满足声明
```

- **内联表 `openai = ">=1.0.0"` 是错误写法**：既不是字符串列表也不是依赖对象，加载/打包会失败（`neko_plugin_cli/core/dependencies.py` 会抛 `must be a list of plugin id strings`）。
- 官方**不会**在安装插件时自动 pip 安装依赖；缺依赖时代码要做惰性导入 + 错误缓存（见 13-cloud-api-integration.md）。
- 版本规范用 PEP 440；`vendor/` 必须随包一起发布。