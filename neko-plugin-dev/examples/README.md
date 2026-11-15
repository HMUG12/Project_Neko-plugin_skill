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
| 想看官方 init 生成物与真跑记录 | `minimal_plugin/README.md`「支撑文件确实来自官方 init 生成器」 |

## 验证

```bash
cd minimal_plugin
uvx ruff==0.12.4 check --ignore-noqa --config ruff.toml .
uvx pytest -q -c tests/pytest.ini tests
uv run neko-plugin check minimal_plugin --strict     # 需官方 main 的 N.E.K.O 源码树
```

> **4.3.0 真跑记录**：官方 main 的 `generator.py` 生成函数已实际执行，`ruff.toml` / `verify.yml` / `release.yml` / `.gitignore` / `.vscode/*` / `test_smoke.py` 共 7 份支撑文件与产出**字节一致**；pinned `ruff==0.12.4` 两种入口（本地 config 与官方 CI isolated 原命令）均 `All checks passed!`；`uvx pytest -q -c tests/pytest.ini tests` **11 passed**；5 个 `.py` 编译通过。真跑修掉了 `routers/notes.py` 的 `I001`，并补 `tests/pytest.ini` 让静态测试在裸环境也可收集。
>
> **仍未跑**：真实宿主加载、面板保存与 Reload，以及官方 main 的 `check` / `lint` / `precheck` / `publish`。4.1.1 的 `check --strict`（0 error / 1 预期 warning）是本地旧快照 CLI 的结果，不能当作官方 main 验证。可复现清单见 `minimal_plugin/README.md`，发布门禁见 [`../references/51-build-publish-and-market-review.md`](../references/51-build-publish-and-market-review.md)。旧版 `web_assistant` 因依赖未核实的 firecrawl API 与多处契约错误已移除；联网抓取相关内容见 `42-web-data-integration.md`，仅作方法论参考。
