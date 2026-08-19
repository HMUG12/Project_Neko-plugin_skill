# 17. `__pycache__` 缓存陷阱 — 代码改了但不生效

> 基于 `ai_singer` 插件开发中最致命的调试经历。
> 这个问题浪费了大量时间，因为**没有任何报错**——代码逻辑正确，只是加载了旧版本。

---

## 17.1 问题现象

```
你修改了 __init__.py → 同步到部署目录 → 重启 N.E.K.O
→ 日志显示旧代码仍在运行
→ 旧 entries 仍然存在
→ 旧配置项仍然被持久化
→ 旧日志仍然在输出
```

**关键特征**：没有报错、没有异常、没有崩溃——只是行为不变。这比报错更难排查。

---

## 17.2 根本原因

Python 在首次 `import` 模块时，会将 `.py` 源文件编译为 `.pyc` 字节码文件，存放在 `__pycache__/` 目录中：

```
ai_singer/
├── __init__.py                          # ← 你修改了这个
├── __pycache__/
│   └── __init__.cpython-313.pyc         # ← 但 N.E.K.O 加载的是这个！
```

**Python 的 import 优先级**：
1. 如果 `.pyc` 文件存在且时间戳匹配 → 直接加载 `.pyc`
2. 如果 `.pyc` 不存在或过期 → 编译 `.py` → 生成新的 `.pyc` → 加载

问题出在**时间戳判断**。在某些场景下（文件复制、网络同步、Docker 挂载），`.pyc` 的时间戳可能比 `.py` 更新，Python 会认为缓存有效。

---

## 17.3 真实日志证据

以下来自 `ai_singer` 的实际运行日志，展示了从旧版到新版的整个过程：

### 阶段一：旧版代码在运行（10:57 - 12:49）

```
# 第 3 行：entries 包含已删除的 CosyVoice 入口
Plugin entries collected: ['check_setup', 'clone_neko_voice', 'delete_all_songs',
  'delete_custom_voice', 'delete_song', 'list_custom_voices', ...]

# 第 7 行：启动日志显示 CosyVoice 检查
ai_singer: 启动完成, cosyvoice_ok=False

# 第 18 行：保存的是 CosyVoice 配置项
配置已持久化: ['cosyvoice_api_key', 'cosyvoice_workspace', 'cosyvoice_region',
  'cosyvoice_model', 'cosyvoice_speech_rate', 'cosyvoice_pitch_rate']

# 第 13 行：依赖检查警告 dashscope
config schema validation warnings: [...'dashscope>=1.20.0'...]
```

尽管此时 `__init__.py` 中已经没有 CosyVoice 代码，但 N.E.K.O 加载的是 `.pyc` 缓存。

### 阶段二：新版代码生效（13:50:04）

```
# 第 203 行：entries 不再包含 CosyVoice 入口
Plugin entries collected: ['check_setup', 'delete_all_songs', 'delete_song',
  'config_change', 'freeze', 'reload', 'shutdown', 'startup', 'unfreeze',
  'rename_song', 'save_api_config', 'sing', 'sing_cover', 'sing_live', 'stop_sing_live']

# 第 205 行：依赖只剩 openai
config schema validation warnings: [...'openai>=1.0.0'...]

# 第 207 行：启动日志简化
ai_singer: 启动完成

# 第 218 行：只持久化 MiMo 配置
配置已持久化: ['mimo_api_key', 'mimo_voice']
```

**注意**：从阶段一到阶段二，中间经历了多次重启和修改，最终才生效。这意味着用户一直在与旧代码交互。

---

## 17.4 哪些操作会触发 `.pyc` 残留

| 操作 | 是否清除 `.pyc` | 说明 |
|------|:---:|------|
| 修改 `.py` 文件 | ❌ | 只改源文件，缓存不动 |
| 从工作区复制到部署目录 | ❌ | `__pycache__` 也会被复制过去 |
| 重启 N.E.K.O | ❌ | 重启不会清缓存 |
| 手动删除 `__pycache__/` | ✅ | **唯一可靠的方法** |
| `python -B` 运行 | ✅ | 禁用字节码缓存（不适用 N.E.K.O） |

---

## 17.5 解决方案

### 立即修复（一次性）

```powershell
# Windows PowerShell
Remove-Item -Path "path\to\plugin\__pycache__" -Recurse -Force

# Linux / macOS
rm -rf path/to/plugin/__pycache__/
```

### 部署脚本中加入自动清理

在同步脚本中始终清理 `.pyc`：

```powershell
# sync.ps1 — 同步 + 清缓存 + 验证
$src = "E:\workspace\my_plugin"
$dst = "$env:LOCALAPPDATA\N.E.K.O\plugins\my_plugin"

# 1. 同步文件（排除 __pycache__）
robocopy $src $dst /MIR /XD __pycache__ node_modules .git

# 2. 确保目标目录没有 pycache
if (Test-Path "$dst\__pycache__") {
    Remove-Item "$dst\__pycache__" -Recurse -Force
}

# 3. 验证：检查关键文件时间戳
Write-Host "部署完成。请重启 N.E.K.O。"
```

### 开发工作流中的最佳实践

```
# 每次修改 Python 文件后的标准流程：
1. 编辑 __init__.py
2. 运行同步脚本（自动清除 __pycache__）
3. 重启 N.E.K.O
4. 检查日志确认新代码生效
```

---

## 17.6 如何确认代码已生效

### 方法一：检查启动日志中的 entries

```
# 旧版日志（包含已删除的 entry）
Plugin entries collected: [..., 'clone_neko_voice', 'delete_custom_voice', ...]

# 新版日志（不包含）
Plugin entries collected: [..., 'sing', 'sing_cover', 'sing_live', ...]
```

### 方法二：检查配置持久化内容

```
# 旧版：保存 CosyVoice 配置
配置已持久化: ['cosyvoice_api_key', 'cosyvoice_workspace', ...]

# 新版：只保存 MiMo 配置
配置已持久化: ['mimo_api_key', 'mimo_voice']
```

### 方法三：检查依赖警告

```
# 旧版：警告 dashscope
config schema validation warnings: [...'dashscope>=1.20.0'...]

# 新版：只警告 openai（或没有警告）
config schema validation warnings: [...'openai>=1.0.0'...]
```

### 方法四：检查启动完成日志

```
# 旧版
ai_singer: 启动完成, cosyvoice_ok=False

# 新版
ai_singer: 启动完成
```

---

## 17.7 为什么 `.pyc` 缓存问题在 N.E.K.O 插件中特别严重

1. **独立进程**：N.E.K.O 插件在独立进程中运行，无法通过 IDE 的 "Restart Kernel" 等方式清除缓存
2. **部署目录分离**：工作区改了，部署目录可能没同步
3. **无显式报错**：代码语法正确，只是版本不对，没有任何异常
4. **多层缓存**：工作区 `.pyc` → 部署目录 `.pyc` → N.E.K.O 进程内存中的模块对象
5. **时间戳不可靠**：文件复制可能保留原始时间戳，导致 `.pyc` 被认为比 `.py` 更新

---

## 17.8 终极预防方案

### 在 `plugin.toml` 同级目录添加 `.gitignore`

```gitignore
# .gitignore
__pycache__/
*.pyc
*.pyo
```

### 在 SKILL.md 的铁律中加入

```
11. 改完 Python 必删 __pycache__ — 否则旧代码继续运行，无报错！
```

### 在部署检查清单中加入

```
- [ ] 目标目录的 __pycache__ 已删除
- [ ] 启动日志中的 entries 与预期一致
- [ ] 启动日志中的依赖警告与预期一致
```

---

## 17.9 速查

| 症状 | 诊断命令/方法 | 根因 |
|------|-------------|------|
| 删除的 entry 仍在日志中 | 搜索日志中的 `collect_entries` | `.pyc` 缓存 |
| 删除的配置项仍被持久化 | 搜索日志中的 `配置已持久化` | `.pyc` 缓存 |
| 删除的依赖仍报警告 | 搜索日志中的 `schema validation` | `.pyc` 缓存 |
| 新增的 entry 不出现 | 搜索日志中的 `collect_entries` | `.pyc` 缓存 或 文件未同步 |
| 新增的配置项不生效 | 搜索日志中的 `配置已持久化` | `.pyc` 缓存 或 plugin.toml 未同步 |
