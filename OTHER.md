# 投稿前准备（对齐官方 CLI）

向 N.E.K.O 插件市场投稿前，请在 N.E.K.O 本体目录中完成以下步骤。

1. **准备公开仓库**：插件源码与发布支撑文件（`plugin.toml`、`pyproject.toml`、`README.md`、`tests/`、`vendor/`）都在一个 public GitHub 仓库里。
2. **命名规范**：仓库名必须是 `n.e.k.o_plugin_<plugin_id>`（例如 `n.e.k.o_plugin_example`），且根目录包含 `plugin.toml`。
3. **建仓库与工作流**（在 N.E.K.O 本体目录执行）：

```bash
uv run neko-plugin init-repo <plugin_id>      # 创建市场仓库
uv run neko-plugin setup-repo <plugin>        # 准备仓库工作流
```

4. **依赖与校验**：

```bash
uv run neko-plugin add <plugin_id> "httpx>=0.27"   # 装进 vendor/ 并更新 pyproject.toml
uv run neko-plugin sync <plugin_id>                # 从 pyproject.toml 重装依赖
uv run neko-plugin check <plugin_id> --strict       # 缺支撑文件按错误处理
uv run neko-plugin check <plugin_id> --release --market-release
```

`--market-release` 必须与 `--release` 同用，会额外检查仓库名、tag 与版本对齐、release workflow 是否存在。执行前用 `--help` 复核参数。

> `neko-plugin` **没有** `release` 或 `deps` 顶层子命令；`check` 通过不等于运行通过，仍需真实加载、调用入口、打开 UI 与 Reload 验证。

本文件是仓库说明文件之一，已列入 `.gitignore` 白名单与 README 仓库结构图。
