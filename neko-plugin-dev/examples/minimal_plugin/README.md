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
├── tests/                  # 静态契约测试
└── README.md
```

## 验证

```bash
uv run pytest examples/minimal_plugin/tests       # 不依赖 N.E.K.O 运行时
uv run neko-plugin check minimal_plugin --strict  # 需在 N.E.K.O 仓库环境执行
```

`check --strict` 会把缺仓库支撑文件按错误处理，所以这里保留了 `pyproject.toml` / `tests/` / `README.md`。面板已在 `[[plugin.ui.panel]]` 的 `permissions` 中声明 `config:write`；权限全集以目标版本 `plugin/core/ui_manifest.py` 为准。

## 与旧版示例的区别

旧版 `web_assistant` 依赖未核实的 firecrawl API，`WebRouter` 未继承 `PluginRouter`、在 Router 里写 `@llm_tool`、调用了 Router 上不存在的 `self._reload_config()`，设置面板四个输入框只存本地 state 且没有保存动作，`handleRefresh` 是死代码、`catch` 静默吞异常，前端还用空操作按钮静默兜底。这些都会导致插件加载失败或保存静默失败，已全部修正。

`42-web-data-integration.md` 里的 firecrawl 抓取模式是**方法论参考**，其依赖名与 API 未核实，不作为可运行示例；若要联网抓取，请先核实目标版本 API 并自行做 SSRF 预筛与提示注入缓解。

## 未验证声明

本示例**未在干净环境跑通端到端**（`init → check → Reload`）。`config.update` / `store.set` / `unwrap_or` 等具体方法名请以目标版本 `sdk/plugin/base.py` 与 `docs/plugins/sdk-reference.md` 复核。
