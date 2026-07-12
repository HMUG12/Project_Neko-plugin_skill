# AI 友好设计 — 让 N.E.K.O AI 正确调用你的插件

> 这是 N.E.K.O 插件开发中最容易被忽视但最关键的部分。N.E.K.O 通过 AI 自动调用插件入口，如果你的 `@plugin_entry` 设计不当，AI 会反复出错。

---

## 核心问题：AI 不是用户

用户知道"桌面"、"文档"等概念，但 AI 需要的是**完整的绝对路径**。如果 AI 拿到一个相对路径，它会自己拼接到当前工作目录，导致路径错误。

### 错误示例

```
用户: "帮我把那个日志文件复制到桌面"
AI: file_operation(action="copy", source_path="目标报错日志路径", dest_path="C:\Users\Admin\Desktop")
→ 错误: "路径不存在: F:\SteamLibrary\...\目标报错日志路径"
```

AI 把 "目标报错日志路径" 当作文件名，拼接到 N.E.K.O 的 bin 目录后，产生了无效路径。

### 正确的工作流

```
用户: "帮我把那个日志文件复制到桌面"
AI: search_files(query="日志") → 获取 F:\MyApp\logs\error.log
AI: file_operation(action="copy", source_path="F:\MyApp\logs\error.log", dest_path="C:\Users\Admin\Desktop\error.log")
→ 成功
```

---

## 设计原则

### 1. 强制「搜索先行」工作流

**插件必须拒绝任何非绝对路径**，并在错误消息中明确引导 AI 先搜索：

```python
@plugin_entry(
    id="file_operation",
    name="文件操作",
    description="对文件执行操作。⚠️ 重要：source_path 和 dest_path 必须是绝对路径（如 C:\\Users\\...），你必须先用 search_files 或 scan_folder_context 获取完整路径，绝不能传相对路径（如'桌面'、'文档'）！",
    input_schema={
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "操作类型"},
            "source_path": {"type": "string", "description": "源文件/文件夹路径，create 时可为空"},
            "dest_path": {"type": "string", "description": "目标路径"},
        },
        "required": ["action", "source_path"],
    },
)
async def file_operation(self, source_path, dest_path, ...):
    # 拒绝非绝对路径，并引导 AI
    if source_path and not os.path.isabs(source_path):
        return Err(SdkError(
            f"喵～源路径 '{source_path}' 不是绝对路径的说。"
            "请先用 search_files 或 scan_folder_context 找到文件的完整路径，再操作哦～"
        ))
```

### 2. 路径不存在时引导 AI 搜索

```python
if not os.path.exists(source_path):
    return Err(SdkError(
        f"喵～路径不存在: {source_path}。"
        "请先用 search_files 搜索确认文件完整路径，"
        "或用 scan_folder_context 扫描目录获取文件列表喵～"
    ))
```

### 3. 权限/范围错误时给出具体操作指引

```python
# ❌ 错误 — 只说不行，不告诉怎么做
return Err(SdkError("权限不足"))

# ✅ 正确 — 告诉 AI 下一步该做什么
if not self._path_in_scan_range(source_path):
    return Err(SdkError(
        "咦？这个路径不在允许的扫描范围里喵～"
        "请先用 search_files 确认文件在扫描范围内"
    ))
```

---

## description 字段编写规范

`description` 是 AI 决定调用哪个入口方法的关键依据。**必须包含三个要素：**

| 要素 | 说明 | 示例 |
|------|------|------|
| **何时调用** | 什么场景下触发 | "用于'帮我看看这个文件'等场景" |
| **前置条件** | 调用前需要做什么 | "⚠️ file_path 必须是用 search_files 获取的完整绝对路径" |
| **注意事项** | 限制和边界 | "仅支持文本文件，二进制文件返回 is_binary: true" |

### 好的 description 示例

```python
@plugin_entry(
    id="read_file",
    name="读取文件",
    description=(
        "读取文本文件内容。"
        "⚠️ file_path 必须是用 search_files 获取的完整绝对路径。"
        "用于'帮我看看这个文件'、'这个文件里写了什么'等场景。"
        "如果是二进制文件，返回 is_binary: true 且 content 为空。"
    ),
)
```

### 坏的 description 示例

```python
# ❌ 太模糊，AI 不知道什么时候用
description="读取文件"

# ❌ 没有说明前置条件
description="读取文件内容"

# ❌ 没有说明限制
description="读取任意文件的内容"
```

### 使用 ⚠️ 标记关键警告

AI 对 ⚠️ 符号敏感，在 description 中用 ⚠️ 标记关键警告：

```python
description="⚠️ 重要：source_path 和 dest_path 必须是绝对路径，你必须先用 search_files 获取完整路径！"
```

---

## input_schema 设计规范

### required 字段

`required` 数组告诉 AI 哪些参数是必填的。**不要把所有参数都放进去**，只标记真正必须的：

```python
input_schema={
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "搜索关键词"},
        "max_results": {"type": "integer", "default": 50},
        "extension": {"type": "string", "default": "", "description": "扩展名过滤，如 .pdf"},
    },
    "required": ["query"],  # 只有 query 是必填，其他都有默认值
}
```

### llm_result_fields

告诉 AI 哪些字段应该返回给用户：

```python
@plugin_entry(
    id="read_file",
    llm_result_fields=["content", "file_path", "truncated", "total_lines"],
)
```

- `["content"]` — AI 会提取 content 字段展示给用户
- 不设置 — AI 可能返回整个 JSON 或只返回 summary

### 参数类型

| Python 类型 | JSON Schema 类型 | 说明 |
|------------|-----------------|------|
| `str` | `"type": "string"` | 字符串 |
| `int` | `"type": "integer"` | 整数 |
| `float` | `"type": "number"` | 浮点数 |
| `bool` | `"type": "boolean"` | 布尔值 |
| `list` | `"type": "array"` | 数组 |
| `dict` | `"type": "object"` | 对象 |

---

## 完整工作流设计

对于一个需要多步操作的插件，设计「搜索 → 扫描 → 操作 → 验证」闭环：

```python
# 步骤 1: search_files — 搜索文件获取完整路径
@plugin_entry(id="search_files", name="搜索文件",
    description="在已索引的文件中搜索完整绝对路径。⚠️ 这是文件操作的第一步！先搜索获取路径，再用 file_operation 执行操作。")

# 步骤 2: scan_folder_context — 扫描目录获取上下文
@plugin_entry(id="scan_folder_context", name="扫描目录",
    description="扫描目录结构，返回文件列表和统计信息。⚠️ 用于 AI 了解目录内容后再决策操作。")

# 步骤 3: file_operation — 执行操作
@plugin_entry(id="file_operation", name="文件操作",
    description="执行文件操作。⚠️ 路径必须是 search_files 或 scan_folder_context 返回的完整绝对路径！")

# 步骤 4: verify_context（file_operation 返回值的一部分）
# file_operation 成功后返回操作的目录快照，供 AI 验证结果
```

### 返回值中的 verify_context

```python
# 操作成功后，返回目标目录的快照供 AI 验证
result_path = dest_path
verify_dir = os.path.dirname(result_path) if not os.path.isdir(result_path) else result_path
entries = os.listdir(verify_dir)
verify_context = {
    "dir": verify_dir,
    "entries": [{"name": e, "is_dir": os.path.isdir(os.path.join(verify_dir, e))} for e in entries[:50]],
}
return Ok({
    "action": action,
    "result_exists": os.path.exists(result_path),
    "verify_context": verify_context,
})
```

---

## 错误消息设计规范

### 喵～风格（猫娘对话感）

```python
# 权限错误
"人家还没被允许读文件啦…去设置里开一下喵？"

# 路径错误
"喵～源路径不是绝对路径的说。请先用 search_files 找到文件再操作哦～"

# 操作成功
"索引完成喵～共找到 {count} 个文件 ✨"

# 操作失败
"呜…索引出错了喵: {error}"
```

### 错误消息三要素

每个错误消息应包含：
1. **发生了什么**（状态描述）
2. **为什么**（原因）
3. **怎么做**（下一步指引）

```python
# ✅ 好的错误消息
"喵～源路径不存在: {path}。请先用 search_files 搜索确认文件完整路径，或用 scan_folder_context 扫描目录获取文件列表喵～"

# ❌ 差的错误消息
"路径不存在"
```

---

## 常见陷阱

### 1. 把 AI 当用户

```python
# ❌ 错误 — 用户懂的 AI 不一定懂
description="读取桌面上的文件"

# ✅ 正确 — 说明 AI 需要知道的具体操作
description="读取文本文件。⚠️ file_path 必须是绝对路径，需先用 search_files 获取。"
```

### 2. 没有拒绝无效输入

```python
# ❌ 错误 — 直接尝试操作，可能产生奇怪错误
if not os.path.exists(path):
    os.makedirs(path)  # 可能创建到错误位置

# ✅ 正确 — 拒绝并引导
if not os.path.isabs(path):
    return Err(SdkError("请提供绝对路径，先用 search_files 获取"))
```

### 3. 返回结果没有 verify_context

```python
# ❌ 错误 — AI 不知道操作是否成功
return Ok({"status": "done"})

# ✅ 正确 — 返回验证信息
return Ok({
    "status": "done",
    "result_exists": os.path.exists(result_path),
    "verify_context": {
        "dir": parent_dir,
        "entries": os.listdir(parent_dir)[:50],
    },
})
```

---

## 检查清单

设计新 `@plugin_entry` 时确认：

- [ ] `description` 包含「何时调用 + 前置条件 + 注意事项」
- [ ] `input_schema` 的 `required` 只包含真正必填的参数
- [ ] 所有路径参数在代码中检查 `os.path.isabs()`
- [ ] 非绝对路径时返回引导性错误消息
- [ ] 路径不存在时建议用 `search_files` 或 `scan_folder_context`
- [ ] 权限/范围错误时给出具体操作指引
- [ ] 设置了 `llm_result_fields` 指定返回字段
- [ ] 返回值中包含验证信息（如 `result_exists`）
- [ ] `description` 中用 ⚠️ 标记关键警告

## 相关文档

- [02-python-plugin.md](02-python-plugin.md) — `@plugin_entry` 方法签名和 `input_schema` 定义
- [09-permission-system.md](09-permission-system.md) — 权限错误消息的引导写法
- [11-undo-and-logging.md](11-undo-and-logging.md) — `verify_context` 与操作验证