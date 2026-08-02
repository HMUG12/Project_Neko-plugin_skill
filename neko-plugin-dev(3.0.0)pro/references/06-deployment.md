# 部署与同步指南

## 工作区 vs 运行目录

N.E.K.O 插件有两个独立的目录：

| 目录 | 用途 | 示例路径 |
|------|------|---------|
| **工作区** | 开发、编辑代码 | `e:\新创意构思\文件管理\` |
| **运行目录** | N.E.K.O 实际加载 | `C:\Users\Admin\AppData\Local\N.E.K.O\plugins\file_manager\` |

**修改工作区文件后，不会自动同步到运行目录。必须手动同步！**

## 需要同步的文件

以下文件每次修改后都需要同步：

```
需要同步的文件:
├── __init__.py          # Python 主逻辑（每次修改必同步）
├── plugin.toml          # 配置变更时同步
├── ui/
│   └── settings.tsx     # UI 变更时同步
├── i18n/
│   ├── zh-CN.json       # 翻译变更时同步
│   └── en.json          # 翻译变更时同步
├── docs/
│   └── guide.md         # 文档变更时同步
└── README.md            # 说明文档变更时同步

不需要同步的:
├── __pycache__/         # Python 缓存，自动生成
├── tsconfig.json        # TypeScript 配置，仅开发用
├── neko-plugin-skill/   # 开发文档，仅开发用
└── *.pyc                # Python 编译缓存
```

## 同步方式

### 方式一：手动复制（推荐）

```powershell
# 复制单个文件
Copy-Item 'e:\新创意构思\文件管理\__init__.py' -Destination 'C:\Users\Admin\AppData\Local\N.E.K.O\plugins\file_manager\__init__.py' -Force

# 复制整个目录
Copy-Item 'e:\新创意构思\文件管理\*' -Destination 'C:\Users\Admin\AppData\Local\N.E.K.O\plugins\file_manager\' -Recurse -Force
```

### 方式二：Robocopy（增量同步）

```powershell
robocopy 'e:\新创意构思\文件管理' 'C:\Users\Admin\AppData\Local\N.E.K.O\plugins\file_manager' /MIR /XD __pycache__ neko-plugin-skill /XF *.pyc
```

## 同步后操作

1. **重启 N.E.K.O** — 只有重启才会重新加载插件代码
2. **检查日志** — 查看 `N.E.K.O_Plugin_file_manager_*.log` 确认无错误
3. **验证功能** — 打开设置面板，确认配置项和按钮正常显示

## 常见问题

### Q: 修改了代码但插件行为没变
**A:** 检查是否同步了文件到运行目录。运行目录中可能有旧文件覆盖了新逻辑。

### Q: 重启后报 BOM 错误
**A:** 工作区文件可能带有 UTF-8 BOM。用以下命令检查并移除：

```powershell
# 检查是否有 BOM
$content = [System.IO.File]::ReadAllBytes('path\to\__init__.py')
if ($content[0] -eq 0xEF -and $content[1] -eq 0xBB -and $content[2] -eq 0xBF) {
    Write-Host "BOM detected!"
}

# 移除 BOM
$content = [System.IO.File]::ReadAllBytes('path\to\__init__.py')
$newContent = $content[3..$content.Length]
[System.IO.File]::WriteAllBytes('path\to\__init__.py', $newContent)
```

### Q: 部署目录中的文件有 BOM 但工作区没有
**A:** 说明之前同步时带了 BOM。需要同步移除 BOM 后的文件。

### Q: 目录名大小写不匹配
**A:** 运行目录名必须与 `plugin.toml` 中 `entry` 的包名完全一致。例如 `entry = "plugins.file_manager:..."` 要求目录名为 `file_manager`（全小写），不能是 `FileManager`。

## 部署检查清单

- [ ] `__init__.py` 无 BOM
- [ ] `plugin.toml` 配置项与代码一致
- [ ] 所有修改的文件已同步到运行目录
- [ ] 运行目录中无多余的旧文件
- [ ] 目录名与 `entry` 包名一致
- [ ] 已重启 N.E.K.O
- [ ] 日志无错误