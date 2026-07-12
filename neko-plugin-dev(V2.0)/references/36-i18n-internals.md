# 36 — i18n 国际化引擎内部机制

> **来源**：N.E.K.O-main `plugin/sdk/` 深度逆向分析  
> **适用**：理解 `self.i18n.t()` 的内部工作原理，正确编写多语言插件

---

## 1. 架构概览

```
用户设置语言 (N.E.K.O 全局)
        │
        ▼
┌───────────────────┐
│   I18nManager     │  ← 插件 SDK 层
│   self.i18n.t()   │
├───────────────────┤
│   LocaleLoader    │  ← 加载 JSON 翻译文件
│   FallbackChain   │  ← 回退链：用户语言 → 默认语言 → key 本身
└───────────────────┘
        │
        ▼
  i18n/zh-CN.json
  i18n/en.json
```

---

## 2. 翻译文件格式

### 文件结构

```
my_plugin/
├── i18n/
│   ├── zh-CN.json    # 中文翻译
│   └── en.json        # 英文翻译
```

### 内容格式

```json
// i18n/zh-CN.json
{
    "actions": {
        "scan": {
            "label": "扫描文件",
            "description": "扫描指定目录中的文件"
        }
    },
    "errors": {
        "path_not_found": "路径不存在: {path}",
        "permission_denied": "权限不足，需要 {permission} 权限"
    },
    "ui": {
        "title": "文件管理器",
        "settings": "设置",
        "save": "保存"
    }
}
```

```json
// i18n/en.json
{
    "actions": {
        "scan": {
            "label": "Scan Files",
            "description": "Scan files in the specified directory"
        }
    },
    "errors": {
        "path_not_found": "Path not found: {path}",
        "permission_denied": "Permission denied, need {permission} permission"
    },
    "ui": {
        "title": "File Manager",
        "settings": "Settings",
        "save": "Save"
    }
}
```

---

## 3. 基本用法

### Python 后端

```python
# 直接调用（推荐包装安全函数）
text = self.i18n.t("ui.title", default="文件管理器")

# 带参数
text = self.i18n.t("errors.path_not_found", default="路径不存在: {path}", path="/tmp/test")

# 带复数
text = self.i18n.t("results.found", default="找到 {count} 个文件", count=5)
```

### UI 前端（装饰器中使用 tr）

```python
@ui.action(
    id="scan",
    label=tr("actions.scan.label", default="扫描文件"),
    tone="primary"
)
async def scan(self, ...):
    ...
```

### i18n 安全包装（推荐）

```python
def _t(self, key: str, default: str, **kwargs) -> str:
    """安全调用 self.i18n.t()，异常时自动回退到 default。"""
    try:
        return self.i18n.t(key, default=default, **kwargs)
    except Exception:
        return kwargs.get("default", default) if kwargs else default

# 使用
msg = self._t("errors.not_found", "文件未找到", file=filename)
```

---

## 4. 回退链机制

当翻译键不存在时，按以下优先级回退：

```
1. 用户当前语言 (如 zh-CN) → 查找翻译
2. 默认语言 (default_locale) → 查找翻译
3. default 参数 → 使用默认值
4. key 本身 → 最终回退
```

**示例**：

```python
# 用户语言 = "ja"（日语），默认语言 = "zh-CN"
# ja.json 不存在 → 回退到 zh-CN.json → 如果也没找到 → 使用 default
text = self.i18n.t("ui.title", default="文件管理器")
# 结果: "文件管理器"（从 zh-CN.json 读取）
```

---

## 5. 配置声明

```toml
# plugin.toml
[plugin.i18n]
default_locale = "zh-CN"     # 默认语言
locales_dir = "i18n"         # 翻译文件目录（相对于插件根目录）
```

### 支持的语言代码

| 代码 | 语言 | 文件名 |
|------|------|--------|
| `zh-CN` | 简体中文 | `zh-CN.json` |
| `en` | 英语 | `en.json` |
| `zh-TW` | 繁体中文 | `zh-TW.json` |
| `ja` | 日语 | `ja.json` |
| `ko` | 韩语 | `ko.json` |

---

## 6. 内部机制

### 懒加载

翻译文件在**首次访问**时才加载到内存，而非插件启动时：

```python
# 伪代码
class I18nManager:
    def __init__(self, plugin_id, locales_dir, default_locale):
        self._cache = {}  # {locale: {key: value}}

    def t(self, key, default="", **kwargs):
        locale = self._get_current_locale()
        if locale not in self._cache:
            self._cache[locale] = self._load_locale(locale)

        text = self._cache[locale].get(key)
        if text is None:
            text = self._load_fallback(key, default)

        return text.format(**kwargs) if kwargs else text
```

### 参数插值

使用 Python 的 `str.format()` 进行参数插值：

```python
# JSON 中
"not_found": "文件 {name} 不存在于 {path}"

# 调用
self.i18n.t("not_found", default="...", name="test.txt", path="/data")
# 输出: "文件 test.txt 不存在于 /data"
```

---

## 7. 关键陷阱

### 陷阱 36-1：翻译文件 key 不一致

```json
// zh-CN.json
{ "save": "保存" }

// en.json
{ "save_button": "Save" }  // ❌ key 不一致！
```

**修复**：确保所有语言文件的 key 完全一致，可用脚本校验。

### 陷阱 36-2：直接使用 self.i18n.t() 无异常保护

```python
# ❌ 错误：i18n 加载失败会导致整个方法崩溃
async def my_action(self, **_):
    msg = self.i18n.t("errors.fail", default="操作失败")
    return Err(SdkError(msg))

# ✅ 正确：使用安全包装
async def my_action(self, **_):
    msg = self._t("errors.fail", "操作失败")
    return Err(SdkError(msg))
```

### 陷阱 36-3：忘记 default 参数

```python
# ❌ 错误：key 不存在时可能返回空或异常
label = self.i18n.t("actions.scan")

# ✅ 正确：始终提供 default
label = self.i18n.t("actions.scan", default="扫描")
```

### 陷阱 36-4：UI 端不使用 tr 函数

```python
# ❌ 错误：硬编码中文
@ui.action(id="scan", label="扫描文件")
async def scan(self, ...):
    ...

# ✅ 正确：使用 tr 函数
@ui.action(id="scan", label=tr("actions.scan.label", default="扫描文件"))
async def scan(self, ...):
    ...
```

---

## 8. 最佳实践

### 命名规范

```
# 推荐的分层命名
actions.<action_id>.label        # 操作按钮标签
actions.<action_id>.description  # 操作描述
errors.<error_code>              # 错误消息
ui.<component>.<field>           # UI 组件文本
status.<status_code>             # 状态消息
notifications.<event>            # 通知消息
```

### 完整示例

```python
# Python 端
@plugin_entry(
    id="file_search",
    name="文件搜索",
    description="搜索指定目录中的文件...",
    input_schema={...},
)
async def file_search(self, path: str, keyword: str, **_):
    if not os.path.isabs(path):
        msg = self._t("errors.not_absolute", "路径必须是绝对路径")
        return Err(SdkError(msg))

    results = await self._search(path, keyword)
    if not results:
        msg = self._t("results.empty", "未找到匹配的文件", keyword=keyword)
        return Ok({"message": msg, "files": []})

    msg = self._t("results.found", "找到 {count} 个文件", count=len(results))
    return Ok({"message": msg, "files": results})
```

```json
// i18n/zh-CN.json
{
    "errors": {
        "not_absolute": "路径必须是绝对路径，请使用 search_files 获取完整路径"
    },
    "results": {
        "empty": "未找到匹配 '{keyword}' 的文件",
        "found": "找到 {count} 个匹配文件"
    }
}
```

---

## 9. 配置声明清单

```toml
# ✅ 完整的 i18n 配置
[plugin.i18n]
default_locale = "zh-CN"
locales_dir = "i18n"
```

- `default_locale` — 必须与一个翻译文件名匹配（不含 .json 后缀）
- `locales_dir` — 相对于插件根目录的路径

---

## 相关文档

- [02-python-plugin](02-python-plugin.md) — i18n 安全调用模式
- [04-i18n](04-i18n.md) — 国际化基础指南
- [03-ui-settings](03-ui-settings.md) — UI 中的 i18n
