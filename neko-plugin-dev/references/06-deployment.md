# 部署与同步指南

> 官方推荐的开发方式**不是**把手写源码复制进用户插件目录，而是在源码目录或用开发者模式就地开发，改完点插件详情页 **Reload**。手工复制只是"已安装包"场景的兜底手段。
>
> 本文已对照官方 Quick Start / Plugin Config 文档核对（核对日期 2026-09-12）；未在干净环境跑通端到端流程，命令与路径请以你目标 SDK 的官方示例为准。

## 三种运行场景（先确认你是哪一种）

| 场景 | 代码从哪加载 | 配置/数据从哪来 | 改完怎么生效 |
|------|-------------|----------------|-------------|
| **A. 源码树开发（推荐）** | `N.E.K.O/plugin/plugins/<id>/`，N.E.K.O 直接扫描该目录 | 用户数据目录下的运行时配置 | `uv run neko-plugin check <id> --strict` → 详情页 **Reload**；改依赖后重启该插件 |
| **B. 开发者模式 Load unpacked** | 就地注册的源码绝对路径目录（文件夹名须与 entry 包名、`plugin.id` 一致） | 同上 | 编辑源码 → **Reload**；改依赖 → 重启插件 |
| **C. 已安装包 / 手工同步** | 安装目录中的代码副本（只读）；配置/数据/缓存始终在用户数据目录 | 用户数据目录 | 重新 `build` 并导入 `.neko-plugin`；仅手工覆盖已安装目录时才需删目标 `__pycache__/` |

> ⚠️ **不要**把源码手工复制进用户插件目录（Windows `%LOCALAPPDATA%\N.E.K.O\plugins\<id>\`），也**不要**创建符号链接——两者都不被官方开发流程支持。

## 各目录职责

| 目录 | 用途 | 示例路径 |
|------|------|---------|
| **开发/工作区** | 开发、编辑源码 | `e:\新创意构思\文件管理\` |
| **插件数据目录** | 运行时配置 + 数据 + 缓存 | Windows：`%LOCALAPPDATA%\N.E.K.O\plugins\<id>\`（`config/plugin.toml` 等） |

**关键点**：运行时配置（含密钥）位于**用户数据目录**，不要写进源码 manifest 并提交仓库。参见 [01-plugin-toml](01-plugin-toml.md) 与 [43-security-hardening](43-security-hardening.md) §2。

## 场景 A：源码树 / 官方开发模式（推荐）

```bash
uv run neko-plugin init my_plugin --type plugin --name "My Plugin"
uv run neko-plugin check my_plugin --strict     # 静态检查（通过 ≠ 运行通过）
uv run python launcher.py                        # 启动源码版 N.E.K.O → Plugins 页启动/Reload/触发入口
```

改动生效：编辑源码 → `check` → 详情页 **Reload**；改了依赖或 manifest 中的依赖声明 → 重启该插件。

## 场景 B：开发者模式 Load unpacked

- 在 N.E.K.O 开发者模式里注册**源码绝对路径目录**（就地加载）。
- 该目录文件夹名必须与 `entry` 包名、`plugin.id` **一致**，否则加载/打包失败。
- 改动生效同上：编辑 → **Reload**。

## 场景 C：已安装包 / 手工同步（兜底）

仅在无法使用 A/B、或需要交付给别人安装时使用。

```bash
# 交付/测试打包
uv run neko-plugin build my_plugin --out my_plugin.neko-plugin
# 在 N.E.K.O 中导入该 .neko-plugin
```

如果确实手工覆盖了已安装目录，再按需同步文件：

```powershell
# 复制单个文件
Copy-Item 'e:\新创意构思\文件管理\__init__.py' -Destination "$env:LOCALAPPDATA\N.E.K.O\plugins\file_manager\__init__.py" -Force

# 复制整个目录（排除缓存/开发文件）
Copy-Item 'e:\新创意构思\文件管理\*' -Destination "$env:LOCALAPPDATA\N.E.K.O\plugins\file_manager\" -Recurse -Force -Exclude '__pycache__','*.pyc','tsconfig.json'
```

> ⚠️ **不要用 `robocopy /MIR` 做常规同步**：`/MIR` 会镜像并**删除目标端多余文件**，一个手误的源路径就可能清空用户数据目录。若确需镜像，先加 `/L`（仅列出、不删除）确认清单，再人工确认后执行，且必须用 `/XD __pycache__`、`/XF *.pyc` 排除缓存。

## 需要/不需要同步的文件

```
需要同步（仅场景 C）:
├── __init__.py          # Python 主逻辑
├── plugin.toml          # manifest 变更时
├── routers/             # 路由模块
├── ui/settings.tsx      # UI 变更时
├── i18n/*.json          # 翻译变更时
└── docs/guide.md        # 文档变更时

不同步:
├── __pycache__/ *.pyc   # Python 缓存（不要带过去）
├── tsconfig.json        # 仅开发用
└── 开发文档/            # 仅开发用
```

## 同步后检查

1. **确认生效方式**：A/B 场景以 **Reload** 为准，不要用"重启整个 N.E.K.O"代替 Reload 判断。
2. **看插件日志**：`N.E.K.O_Plugin_<id>_*.log` 确认无错误。
3. **验证功能**：打开设置面板，确认配置项与按钮正常显示、入口可触发。

## 常见问题

### Q: 修改了代码但插件行为没变
**A:** 按场景排查：
1. A/B 场景先点 **Reload**；改了依赖/配置再重启该插件。
2. C 场景确认源文件已真正覆盖到目标目录。
3. 前三步都正常仍不更新 → 删目标目录 `__pycache__/`（诊断分支，见 [17-pyc-cache-trap](17-pyc-cache-trap.md)）。

### Q: 重启后报 BOM 错误
**A:** 源码文件可能带 UTF-8 BOM。检查并移除：

```powershell
# 检查
$b = [System.IO.File]::ReadAllBytes('path\to\__init__.py')
if ($b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF) { Write-Host "BOM detected!" }

# 移除
$b = [System.IO.File]::ReadAllBytes('path\to\__init__.py')
[System.IO.File]::WriteAllBytes('path\to\__init__.py', $b[3..($b.Length - 1)])
```

### Q: 报 `PluginEntryDirectoryMismatch` / 找不到入口
**A:** 说明加载器/打包器没找到 `entry` 对应的包。核对三处是否对齐：**源码目录名 = `plugin.id` = `entry` 包名**（大小写敏感）。官方强烈建议三者一致；开发期旧发现机制可能容忍不一致，但打包与生产安装不允许。

### Q: `neko-plugin check` 通过，但插件加载失败或功能不对
**A:** 静态检查只覆盖 manifest/结构，不覆盖运行时。必须在目标 SDK 上实际加载、触发入口、打开 UI、Reload 后才能算"可运行"。

## 部署检查清单

- [ ] 明确所处场景（A 源码 / B Load unpacked / C 已安装包）
- [ ] A/B：改完走 **Reload**（改依赖后重启插件）
- [ ] C：源文件已覆盖 + 必要文件齐全
- [ ] 源码目录名 = `plugin.id` = `entry` 包名
- [ ] `__init__.py` 无 BOM
- [ ] 密钥只写在用户数据目录的运行时配置，未进源码
- [ ] 行为不更新时，才删目标 `__pycache__/`（诊断）
- [ ] 已在目标 SDK 上实际验证：加载成功 + 入口可触发 + UI 可打开 + Reload 生效
