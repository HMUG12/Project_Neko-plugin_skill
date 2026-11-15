# minimal_plugin

零第三方依赖的最小插件示例，用来演示 **N.E.K.O 插件契约**，而不是演示某个业务功能。

## 目录

```
minimal_plugin/
├── plugin.toml             # 清单：身份、权限、面板；无 dependencies 内联表
├── pyproject.toml          # Python 依赖（本示例为空）
├── config.example.toml     # 运行时配置示例
├── __init__.py             # 主类：生命周期 / 入口 / 面板 / 定时器 / 推送
├── routers/notes.py        # Router 子包（继承 PluginRouter）
├── ui/settings.tsx         # Hosted TSX 设置面板（能真正保存）
├── tests/                  # test_plugin_contract.py（静态契约）+ test_smoke.py（官方模板）
├── .vscode/                # 官方 setup-repo 生成的 settings/tasks
├── .github/workflows/      # 官方 verify.yml / release.yml 模板
├── .gitignore              # 含 .pytest_cache/ 与 store.db
└── README.md
```

## 验证

```bash
uv run pytest examples/minimal_plugin/tests       # 不依赖 N.E.K.O 运行时
uv run neko-plugin check <本目录绝对路径> --strict   # 在 N.E.K.O 仓库环境执行
```

**2026-11-15 实测**：用工作区内的 N.E.K.O 主程序源码、经 `uv run --no-project` 隔离环境调用官方 CLI，`check --strict` 返回 **`[OK] 0 error(s), 1 warning(s)`（exit 0）**。唯一警告是 `plugin directory is not a standalone git repository`——示例按设计放在技能包仓库内，用 `neko-plugin init-repo` / `setup-repo` 拆成独立插件仓库后即消失，不建议在示例目录里再 `git init`。

`check --strict` 把缺仓库支撑文件按错误处理，所以这里补齐了 `tests/test_smoke.py`、`.vscode/settings.json`、`.vscode/tasks.json`、`.github/workflows/verify.yml`（均由官方 `setup-repo --github-actions` 生成）、`[plugin.sdk]` 区间表，以及 `.gitignore` 里的 `.pytest_cache/` 与 `store.db`。面板已在 `[[plugin.ui.panel]]` 的 `permissions` 中声明 `config:write`；权限全集以目标版本 `plugin/core/ui_manifest.py` 为准。

## 与旧版示例的区别

旧版 `web_assistant` 依赖未核实的 firecrawl API，`WebRouter` 未继承 `PluginRouter`、在 Router 里写 `@llm_tool`、调用了 Router 上不存在的 `self._reload_config()`，设置面板四个输入框只存本地 state 且没有保存动作，`handleRefresh` 是死代码、`catch` 静默吞异常，前端还用空操作按钮静默兜底。这些都会导致插件加载失败或保存静默失败，已全部修正。

`42-web-data-integration.md` 里的 firecrawl 抓取模式是**方法论参考**，其依赖名与 API 未核实，不作为可运行示例；若要联网抓取，请先核实目标版本 API 并自行做 SSRF 预筛与提示注入缓解。

## 未验证声明

官方静态校验 `check --strict` **已跑通**（见上）；本示例仍**未在真实宿主中加载、打开面板并 Reload**。`init → check → Reload` 全链路的运行时部分未验证。`config.update` / `store.set` / `unwrap_or` 等具体方法名请以目标版本 `sdk/plugin/base.py` 与 `docs/plugins/sdk-reference.md` 复核。
