# minimal_plugin

零第三方依赖的最小插件示例，用来演示 **N.E.K.O 插件契约**，而不是演示某个业务功能。事实基线为官方 `Project-N-E-K-O/N.E.K.O` main `acfbdbc`（2026-11-15 只读核对）。

## 目录

```
minimal_plugin/
├── plugin.toml             # 清单：身份、权限、面板；无 dependencies 内联表   [教学定制]
├── pyproject.toml          # Python 依赖（本示例为空）                        [教学定制]
├── config.example.toml     # [minimal_plugin].greeting，代码会真正读取        [教学定制]
├── __init__.py             # 主类：生命周期 / 入口 / 面板 / 定时器 / 推送     [教学定制]
├── README.md               # 本文件                                          [教学定制]
├── routers/notes.py        # Router 子包（继承 PluginRouter）                 [教学定制]
├── ui/settings.tsx         # Hosted TSX 设置面板                             [教学定制]
├── tests/
│   ├── test_plugin_contract.py  # 静态契约测试（10 项）                       [教学定制]
│   ├── test_smoke.py            # 官方 init 生成物                            [官方原样]
│   └── pytest.ini               # 让静态测试在裸环境也能被 pytest 收集         [教学定制]
├── .vscode/                # settings.json / tasks.json                      [官方原样]
├── .github/workflows/      # verify.yml / release.yml                        [官方原样]
├── .gitignore                                                               [官方原样]
└── ruff.toml                                                                [官方原样]
```

### 支撑文件确实来自官方 `init` 生成器（不是手写仿制）

4.3.0 把官方 main 的 `plugin/neko_plugin_cli/templates/generator.py`、`plugin/_types/plugin_types.py`、`plugin/utils/source_paths.py` 以只读方式取出，组成本机最小可运行包，**实际执行了 `generate_plugin()` 与 `generate_repo_support_files()`**（即 `neko-plugin init` 的底层实现），再把产出与示例逐字节比对。生成时用了官方支持的 `entry_point_override="plugin.plugins.minimal_plugin:MinimalPlugin"`，以对齐本示例的类名。

| 官方原样产物 | 比对结果 | sha256 前 12 位 |
|---|---|---|
| `ruff.toml` | 字节一致 | `b4303b147c48` |
| `.github/workflows/verify.yml` | 字节一致 | `48c2a6f662ca` |
| `.github/workflows/release.yml` | 字节一致 | `147616596278` |
| `.gitignore` | 字节一致 | `8fe1127ae54e` |
| `.vscode/settings.json` | 字节一致 | `ba3aab557e84` |
| `.vscode/tasks.json` | 字节一致 | `f257d0b74ebd` |
| `tests/test_smoke.py` | 字节一致 | `34a02e266a33` |

两个 workflow 都 `uses: Project-N-E-K-O/N.E.K.O/.github/workflows/plugin-market-*.yml@main`，`release.yml` 具备 `id-token: write` / `attestations: write`。旧的「把插件挂进 N.E.K.O 树再 `check -r`」模板与旧式 `python -m plugin.neko_plugin_cli.cli ...` VS Code task 已废弃。

`.vscode/settings.json` 的 `repoRoot: ".."` 是官方「插件目录即独立仓库」布局下的取值；本示例内嵌于技能包，该路径仅作模板示意，独立仓库使用时才准确。

## 验证

### 本机真跑过的（4.3.0）

```bash
cd minimal_plugin
uvx ruff==0.12.4 check --ignore-noqa --config ruff.toml .        # All checks passed!
uvx ruff==0.12.4 check --ignore-noqa --isolated \
  --no-respect-gitignore --target-version py311 --line-length 120 \
  --select E4,E7,E9,F,I --exclude vendor .                        # All checks passed!（官方 CI 原命令）
uvx pytest -q -c tests/pytest.ini tests                      # 11 passed（从插件根目录执行）
python -m compileall -q .                                          # 5 个 .py 全部编译通过
```

真跑发现并修掉的真实问题：`routers/notes.py` 的 import 顺序触发 `I001`（已按 `Err, Ok, PluginRouter, SdkError, plugin_entry` 排序）；pytest 默认收集会因插件根有 `__init__.py` 且本机无 `plugin.sdk` 而 `ModuleNotFoundError`，加 `tests/pytest.ini`（`--import-mode=importlib`）后静态测试在裸环境也能跑通。

> 官方 CI 的 lint 用 `--isolated` 不读 `ruff.toml`，两套入口规则等价（pinned `ruff==0.12.4` / `E4,E7,E9,F,I` / `py311` / 120 / exclude vendor），上面两条都实际跑过。

### 需要 N.E.K.O 源码环境的

```bash
uv run neko-plugin check minimal_plugin --strict
uv run neko-plugin lint minimal_plugin
uv run neko-plugin precheck minimal_plugin          # lint → sync --clean → check -r
```

官方 `plugin-market-verify.yml` 会把插件 checkout 进 N.E.K.O 源码树（那里有 `plugin.sdk`），再跑 `sync --clean` 与 `check -r`；因此官方 CI 中 `test_smoke.py` 可以正常收集。**当前本机没有官方 main 的完整源码树与宿主**，这一层仍未跑。此前 4.1.1 的 `check --strict`（0 error / 1 warning）是在本地旧快照 CLI 上跑的，**不能当作官方 main 的验证结果**。

> ⚠️ **仍未在真实宿主中加载、打开面板保存并 Reload**，也未跑过官方 main 的 `check` / `lint` / `precheck` / `publish`。官方门禁需要完整 N.E.K.O 宿主、插件自己的独立 Git 仓库与 Market 平台，当前环境不具备；下文给出可复现清单，但**不冒充实测结果**。逐条阻塞事实、解除条件与审核决策见仓库根目录 [`../../../UNVERIFIED.md`](../../../UNVERIFIED.md)（待审）。

## 在真宿主上跑通一次（可复现清单）

在装有官方 main 的 N.E.K.O 环境里，把示例当作独立插件仓库运行：

```bash
# 推荐路径：直接用官方脚手架生成新目录，再逐段对照本示例的契约写法
uv run neko-plugin init minimal_plugin --type plugin --name "Minimal Plugin"
cd minimal_plugin
uv run neko-plugin check minimal_plugin --strict
uv run neko-plugin lint minimal_plugin
uv run neko-plugin precheck minimal_plugin

# 宿主侧：启动 N.E.K.O → Plugins 页启动插件 → 打开「设置」面板 →
#   改问候语并保存 → 确认配置写入 → Reload 插件 → 确认问候语仍在
#   → 触发 count 入口 → 触发 notify 并确认 submitted=True
```

若要把本示例目录本身作为插件仓库，先 `git init`、把 `origin` 指向 `n.e.k.o_plugin_minimal_plugin` 的公开仓库，再按 [`../../references/51-build-publish-and-market-review.md`](../../references/51-build-publish-and-market-review.md) 与 [`../../../OTHER.md`](../../../OTHER.md) 跑完整发布流程。

## 与旧版示例的区别

旧版 `web_assistant` 依赖未核实的 firecrawl API，`WebRouter` 未继承 `PluginRouter`、在 Router 里写 `@llm_tool`、调用了 Router 上不存在的 `self._reload_config()`，设置面板四个输入框只存本地 state 且没有保存动作，`handleRefresh` 是死代码、`catch` 静默吞异常，前端还用空操作按钮静默兜底。这些都会导致插件加载失败或保存静默失败，已全部修正。

本次复核又修了两处：面板保存原先只改 `self._greeting` 内存值（Reload 后丢失），现改为 `await self.config.update(...)` 并在 `startup` / `config_change` 用 `await self.config.dump(timeout=5.0)` 重读；`config.example.toml` 原先的顶层 `greeting` 无人读取，现改为 `[minimal_plugin]` 命名空间并与代码对齐。配置读写方法名参照官方 `plugin/plugins/lifekit/__init__.py` 的公开用法。

`42-web-data-integration.md` 里的 firecrawl 抓取模式是**方法论参考**，其依赖名与 API 未核实，不作为可运行示例；若要联网抓取，请先核实目标版本 API 并自行做 SSRF 预筛与提示注入缓解。

## 未验证声明

`check` 的盲点（运行时 entry 是否 `async def`、UI action 是否真的暴露、面板保存是否落盘生效）只能靠真宿主验证，静态检查、lint、契约测试**不能替代**。官方 `publish → GitHub Release → Market 上架` 全链路同样未实测。面板已在 `[[plugin.ui.panel]]` 的 `permissions` 中声明 `config:write`；权限全集以 `plugin/core/ui_manifest.py` 为准。
