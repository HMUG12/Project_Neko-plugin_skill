# examples

包含一个可复制的最小插件：`minimal_plugin/`（零第三方依赖）。

## 什么时候看哪一篇

| 需求 | 参考 |
|---|---|
| 想看插件整体骨架 | `minimal_plugin/__init__.py` + `SKILL.md` §4 |
| 想看 Router 拆分 | `minimal_plugin/routers/notes.py` + `20-plugin-router.md` |
| 想看设置面板能保存 | `minimal_plugin/ui/settings.tsx` + `03-ui-settings.md` |
| 想看依赖与打包 | `minimal_plugin/pyproject.toml` + `01-plugin-toml.md` §6 |
| 想加持久记忆 / 后台整理 | `46-memory-persistence-subconscious.md`（store + `@timer_interval`，定时器必须 `async def`） |

## 验证

```bash
uv run pytest examples/minimal_plugin/tests
uv run neko-plugin check minimal_plugin --strict
```

> 官方 `check --strict` 已实测通过（0 error / 1 预期 warning，详见 `minimal_plugin/README.md`）；**真实宿主加载与 Reload 仍未跑**。旧版 `web_assistant` 因依赖未核实的 firecrawl API 与多处契约错误已移除；联网抓取相关内容见 `42-web-data-integration.md`，仅作方法论参考。
