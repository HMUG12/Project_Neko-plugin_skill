# n.e.k.o_plugin_example

本目录是 **市场仓库命名示例**，只放说明文件，不是一个可加载的插件。

> **基线（单一口径）**：本技能包只按官方 `Project-N-E-K-O/N.E.K.O` main `acfbdbc`（2026-11-15 只读核对）编写，不再并列旧快照。执行前一律 `uv run neko-plugin --help` 确认命令集；官方命令集见 [51 篇 §5](../neko-plugin-dev/references/51-build-publish-and-market-review.md)。

## 仓库命名与目录

官方要求市场仓库名为 `n.e.k.o_plugin_<plugin_id>`，且**仓库根目录**包含 `plugin.toml`、`pyproject.toml`、`README.md`、`tests/`、`ruff.toml`、`.github/workflows/verify.yml` 与 `release.yml` 等发布支撑文件。真实插件应放在 `n.e.k.o_plugin_<plugin_id>/` 自己的仓库里：

```bash
# init 直接生成带 .git/ / ruff.toml / verify.yml / release.yml 的完整骨架
uv run neko-plugin init <plugin_id> --type plugin --name "My Plugin"
uv run neko-plugin create-repo <plugin_id>          # 用 gh 建公开仓库并设为 origin
uv run neko-plugin lint <plugin_id>
uv run neko-plugin precheck <plugin_id>
```

创建仓库时不要让 GitHub 自动添加 README / `.gitignore` / License，避免首次 push 冲突。

> 旧版本说明里提到的 `main.py` 与 `scripts/verify_plugin.py` 在本仓库中并不存在，已删除相应描述。

## 本地校验与构建

在 N.E.K.O 源码根目录执行：

```bash
uv run neko-plugin check <plugin_id> --strict
uv run neko-plugin sync <plugin_id> --clean       # 仅当有第三方 Python 依赖
uv run neko-plugin lint <plugin_id>               # 与 Market CI 相同的固定 ruff 规则
uv run neko-plugin precheck <plugin_id>           # lint → sync --clean → check -r
uv run neko-plugin check <plugin_id> --release --market-release
uv run neko-plugin build <plugin_id> -o out/<plugin_id>.neko-plugin
```

`check --release` 会构建并校验 `metadata.toml` 的 payload hash；`install` 只是兼容命令，真实安装走插件中心「导入」。

## Market 自动门禁（发布前）

- id 匹配 `^[a-z][a-z0-9_]*$` 且不超过 100 字符；`version` 不超过 50 字符。
- `origin` 指向 GitHub；仓库名推荐 `n.e.k.o_plugin_<plugin_id>`。
- tag `v<version>` 与 `plugin.toml.version` 一致；`.github/workflows/release.yml` 存在；工作区无未提交文件。
- 首次审核提交的是**固定 commit 快照**，不是 `.neko-plugin` 包；审核通过 ≠ 可安装，发布第一个可安装版本用 `publish <id>`。

完整流程见 [OTHER.md](../OTHER.md) 与 [51 篇](../neko-plugin-dev/references/51-build-publish-and-market-review.md)。

可复制的最小插件示例见技能包内的 `neko-plugin-dev/examples/minimal_plugin/`：其 7 份支撑文件由官方 `generator.py` 生成函数**实际执行产出并逐字节一致**，本机真跑 pinned `ruff==0.12.4`（两种入口）与 `uvx pytest -q -c tests/pytest.ini tests`（11 passed）均通过；但真宿主加载、面板保存与 Reload，以及官方 main 的 `check` / `lint` / `precheck` / `publish` 门禁尚未实测。

本目录已列入 `.gitignore` 白名单与 README 仓库结构图。
