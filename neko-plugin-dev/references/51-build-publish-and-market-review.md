# 51 — 构建、官方发布工作流、验证与审核

> **基线（务必先读）**：本技能包全部事实只按官方 `Project-N-E-K-O/N.E.K.O` 的 `main`（commit `acfbdbc`，2026-11-15 **只读查询**，未克隆、未下载仓库）判定。依据 `docs/zh-CN/plugins/cli.md`、`docs/plugins/cli.md`、`docs/zh-CN/plugins/quick-start.md`、`plugin/neko_plugin_cli/docs/package-format.md`、`plugin/neko_plugin_cli/cli.py` 与各 `commands/*_cmd.py`、`.github/workflows/plugin-market-verify.yml` / `plugin-market-release.yml`、`.agent/skills/neko-plugin/references/plugin-checks-and-tests.md`。
>
> **执行前一律用 `uv run neko-plugin --help` 确认命令集**。历史修订与旧版差异只记录在 `REVIEW_FIXES.md` / `CHANGELOG.md`，属存档，不作为当前规则。
>
> 本篇**未在真实环境中跑过** `publish` → Release → Market 上架全链路；示例支撑文件已按官方 `generator.py` 的 `init` 模板重建，静态契约测试通过，但真宿主加载、面板保存与 Reload 仍未验证。

---

## 1. 构建方法

### 1.1 两种包，都是 ZIP

| 包类型 | 扩展名 | `manifest.toml` 的 `package_type` | `payload/plugins/` 要求 |
|---|---|---|---|
| 单插件包 | `.neko-plugin` | `"plugin"` | **恰好 1 个**插件目录 |
| 整合包 | `.neko-bundle` | `"bundle"` | 1 个或多个，且在 manifest 声明 `[[plugins]]` |

两者内部目录布局相同，标准 ZIP，普通解压工具可读。

```
package.neko-plugin
├── manifest.toml          # 必需：包身份 / 类型 / 版本 / 展示信息
├── metadata.toml          # 建议：payload hash、来源信息
├── sign.toml              # 可选：签名；缺省视为未签名，不是非法包
└── payload/
    ├── dependencies.toml  # 构建时自动生成，开发者不要手写/修改
    ├── plugins/<plugin_id>/
    │   ├── plugin.toml    # 必需
    │   ├── pyproject.toml # 建议
    │   ├── vendor/        # 有第三方 Python 依赖时必需
    │   └── ...源码与静态资源
    └── profiles/          # 包级 profile（替代旧的 configs/ 目录）
```

`payload/dependencies.toml` 由 `build` 从每个插件的 `plugin.toml` + `pyproject.toml` 汇总生成，并计入 payload hash；安装时用它校验 `vendor/` 是否满足声明，无需重新解析包内源码。

### 1.2 依赖的两条通道（不变，但新版 CLI 命令不同）

- `[plugin].dependencies`（`plugin.toml`）：**只声明对其他 N.E.K.O 插件的依赖**，与 Python 包无关。
- Python 运行时依赖：写在**插件自己的** `pyproject.toml` 的 `[project].dependencies`，再用 `uv run neko-plugin sync <plugin_id> --clean` 装进该插件的 `vendor/`。
- **不支持 `requirements.txt`**；**禁止**把第三方包装进共享的 N.E.K.O 解释器。
- CLI **没有 `add` 顶层命令**：Python 依赖写进 `pyproject.toml` 后直接 `sync <id> --clean`。

包内**禁止**出现：`__pycache__/`、`.pytest_cache/`、`.mypy_cache/`、`.venv/`、`dist/`、`build/` 及其他开发期临时产物。

### 1.3 `build` 命令

```bash
uv run neko-plugin build <plugin_id>                  # 单个
uv run neko-plugin build <id1> <id2>                  # 多个
uv run neko-plugin build --all                        # 全部
uv run neko-plugin build <id> -o out/my.neko-plugin   # 指定输出文件
uv run neko-plugin build <id> -t <target-dir>         # 指定输出目录
uv run neko-plugin build <id1> <id2> --bundle \
    --bundle-id suite --package-name "My Suite" --version 1.0.0
```

- `build` 接受 `plugin/plugins/` 下的名字或显式路径；**没有** `--plugins-root` 参数。
- 单插件 `build` 只支持 `[plugin].type = "plugin"`（新版实现亦支持 `adapter` 打成 `package_type = "plugin"`）。
- 构建会同时校验**源码侧**与 **payload 侧**的依赖布局。
- 先做包级 profile 迁移：`[plugin_runtime]` 提供 `auto_start` 等运行标志，与插件 id 同名的顶层表迁移进 default profile 作为插件配置，其余元数据表留在 `plugin.toml`。

### 1.4 校验与安装

- `metadata.toml` 的 `[payload].hash` 是对**规范化后的 `payload/` 内容**计算的 sha256，**不是**对整个 zip 计算。
- `check --release` 会 `build` → `inspect_package` → **校验 payload hash**，失败即 `[FAIL]`。
- **`install` 只是兼容命令**：官方明确它拒绝直接写入插件运行时目录，避免绕过 Plugin Center 的确认 / 回滚 / 锁 / 来源追踪流程。真实安装请在 N.E.K.O **插件中心用「导入」**，或在插件制作工作台里打包。
- 后端另有 `POST /plugin-cli/install-plan`，把请求分类为 `install / upgrade / reinstall / downgrade / override_builtin / blocked`，升级类需要 plan token + 显式确认；写操作走 CSRF 契约。

---

## 2. 官方工作流（从 init 到 Market 上架）

### 2.1 前提条件

- 装好 **Git** 与 **uv**（`git --version` / `uv --version` 都要有输出）。
- 在 **N.E.K.O 源码仓库根目录**执行 `uv sync`，然后 `uv run neko-plugin --help` 应至少看到 `init / check / sync / build / publish`。
- 插件源码放在 `N.E.K.O/plugin/plugins/<plugin_id>/`；**该目录本身就是插件自己的 Git 仓库**。不要复制源码、不要建符号链接、不要把安装包导回开发环境。
- 插件 ID 规则：`^[a-z][a-z0-9_]*$`，且 Market 限制最长 **100 字符**；目录名 = `[plugin].id` = `entry` 包名。

### 2.2 `init` 一次生成完整骨架

```bash
uv run neko-plugin init hello_world --type plugin --name "Hello World"
```

生成物（`plugin/plugins/hello_world/`）：

```
├── .git/                      # 插件独立仓库
├── .gitignore
├── .vscode/
├── plugin.toml
├── config.example.toml        # 运行配置模板，不写密钥
├── __init__.py
├── pyproject.toml
├── README.md
├── tests/test_smoke.py
├── ruff.toml                  # 与 Market CI 相同的固定 lint 规则
└── .github/workflows/
    ├── verify.yml             # push / PR 触发的 Verify 门禁
    └── release.yml            # v* tag 触发的 Release + 证据签名
```

`init` 在目标目录已存在时会**直接停止且不覆盖**。官方 `neko-plugin` skill 要求：先出一份 `DESIGN.md`（Identity Lock / 目的 / 包类型 / 首版范围 / out-of-scope / 风险追问），再只在生成的工作区内改动。

> `config.example.toml` 与用户数据目录的 `config/plugin.toml` 是两回事：前者是首次运行模板，后者是真实运行配置（含密钥），**不要提交进仓库**。Windows 用户数据根目录默认是 `%LOCALAPPDATA%\N.E.K.O`。

### 2.3 完整链路（首次发布）

```bash
# ① 开发期
uv run neko-plugin check hello_world                 # 日常检查
uv run neko-plugin sync hello_world --clean          # 仅当有第三方依赖
uv run neko-plugin check hello_world --strict        # 缺支撑文件按 error 处理
uv run neko-plugin lint hello_world                  # 与 Market CI 相同的 ruff
uv run neko-plugin precheck hello_world              # 本地跑完整的三道 CI 门禁

# ② 建 GitHub 公开仓库（二选一）
uv run neko-plugin create-repo hello_world           # 用 gh 自动建并设为 origin
# 或手动建空仓库 n.e.k.o_plugin_hello_world，再在插件目录内：
#   git remote add origin https://github.com/<you>/n.e.k.o_plugin_hello_world.git

# ③ 推送（注意：在插件自己的目录里操作）
cd plugin/plugins/hello_world
git add . && git commit -m "feat: first release"
git push -u origin main
cd ../../..

# ④ 等 GitHub Actions「Verify N.E.K.O Plugin」通过

# ⑤ 到 https://market.project-neko.cn/#/upload 提交首次审核（见 §4）

# ⑥ 审核通过后发布第一个可安装版本
uv run neko-plugin publish hello_world
```

`setup-repo` 用于给**已有**插件目录补支撑文件；升级标准工作流用：

```bash
uv run neko-plugin setup-repo hello_world --upgrade-github-actions --dry-run   # 先预览
uv run neko-plugin setup-repo hello_world --upgrade-github-actions             # 再执行
```

它只管理 `ruff.toml`、`.github/workflows/verify.yml`、`release.yml`；发现无法识别的自定义内容会**停止而不覆盖**。`--dry-run` 必须与 `--upgrade-github-actions` 同用，且不能与 `--overwrite` 同用。

### 2.4 `publish` 内部做了什么

`uv run neko-plugin publish <plugin>` 顺序执行：

1. 检查插件目录有自己的 `.git/`、工作区**无未提交修改**（`git status --short` 应为空）。
2. 检查标准 `release.yml` 是**当前版本**（不是旧模板）。
3. 跑发布检查、插件测试、构建、安装包与 payload hash 校验。
4. 确认当前 commit 已推送到 `origin`。
5. 按 `plugin.toml` 的 `version` 创建并推送 `v<version>` 标签（用你的 GitHub 凭据，**不推代码**）。
6. 等 GitHub Actions 生成 Release，并确认三个资产都可下载：`<id>.neko-plugin`、`<id>.market-release-check.txt`、`market-evidence.json`。
7. 通知 Market 读取该 Release 并发布到 **stable** 渠道（不需要 Market 密码/令牌）。

三种模式：

| 命令 | 作用 |
|---|---|
| `publish <plugin>` | GitHub Release + 通知 Market（默认 stable，无 Changelog） |
| `publish github <plugin>` | 只生成 GitHub Release（用于发 beta / 手填 Changelog） |
| `publish market <github-release-url>` | 只重试 Market 通知，**不做本地扫描** |

超时参数：`--timeout`（等 Release，默认 900s）、`--market-wait`（Market 核验重试，默认 1800s）。

> ⚠️ **只推 tag 不等于发布完成**：`release.yml` 只负责创建 GitHub Release，不会自己在 Market 建版本。必须让 `publish` 完整跑到「Market 发布成功」。

### 2.5 后续版本、beta 与撤回

- **首次审核通过后**，普通更新**不需要**重新提交审核：改源码 → 换一个**从未发布过**的新版本号 →（依赖变化时）`sync --clean` → `check` → commit/push → `publish`。
- Market 按「在 Market 中的发布时间」切换 latest，**不比较版本号大小**；不要在发新版后补发更旧的版本。
- beta / Changelog：`publish github <plugin>` 生成 Release 后，到 Market 版本页「发布新版本」选该 Release、选 `stable|beta`、填 Changelog。**同一插件的版本号全局唯一，不分 stable/beta**；已作 beta 发布的版本号不能再用于 stable。
- 撤回是**单向**的：版本不能恢复，也不能用相同版本号或同一 Release 重发。修复后用新版本号走新 Release。
- 发布中断：Release 已成就直接重跑完整 `publish`（远程 tag 仍指向当前 commit 时不会建第二个版本）；Actions 失败且需要改代码/配置时，必须**换版本号**重发，不要让同一版本号指向另一份代码。

---

## 3. 验证方式（分层）

### 3.1 CLI 分层

| 层级 | 命令 | 检查内容 |
|---|---|---|
| 日常 | `check <id>` | manifest/身份/入口/装饰器 AST/依赖/支撑文件，输出 error+warning |
| 严格 | `check <id> --strict` / `-s` | 把**缺失仓库支撑文件**从 warning 升为 error |
| 发布 | `check <id> --release` / `-r` | 严格校验 + 插件本地 `tests/` + 构建包 + 包检查 + **payload hash 验证** |
| 市场发布 | `check <id> --release --market-release` | 在上面基础上追加 Market 仓库/tag/版本约定检查（`--market-release` **必须**与 `--release` 同用） |
| 固定 lint | `lint <id>` | 与 Market CI 相同的 pinned ruff |
| 本地 CI 门禁 | `precheck <id>` | 依次跑 `lint` → `sync --clean` → `check -r`，可加 `--json` 出机器可读报告、`--skip-tests` |
| 包分析 | `analyze <id1> <id2>` | bundle 候选的插件数、SDK 版本重叠、共享依赖 |

`check --release` 常用附属参数：`-t/--target-dir`（包输出目录）、`--skip-tests`。

`check` 覆盖：`plugin.toml` 可解析、`[plugin]` 必需字段、未知字段告警、`id/name/version/entry/type/sdk/store/i18n/safety/config_profiles/dependencies/plugin_runtime/plugin_state/adapter mode`、目录与 id 不匹配、entry 模块/文件/类、`@neko_plugin`、基类与类型匹配（warning）、startup/shutdown 钩子（warning）、`vendor/` 外 `.py` 的 AST 语法、`@plugin_entry` 的 id 字面量/重复/`input_schema` 浅校验/互斥关键字组、UI surface 文件存在、UI 权限串可识别、拒绝 `requirements.txt`、`pyproject.toml` 有外部依赖时要求 `vendor/`、支撑文件可选检查。

**已知盲点**（`plugin-checks-and-tests.md` 明确列出，`check` 通过 ≠ 运行通过）：

- 运行时触发的 `@plugin_entry` 必须是 `async def`，`check` 不能完全保证；改 entry 要补触发测试。
- 不覆盖 lifecycle / timer / message / custom event / hook / UI / adapter 装饰器的完整语义。
- `input_schema` 只在字面 dict 时做浅检查；互斥检查是静态关键字判断。
- `auto_start=false` **不能**阻止父进程导入与静态扫描，顶层副作用仍需 import smoke test。
- UI action 权限与实际暴露需要 Hosted UI / 运行时检查。
- `passive=true` 只是发现/派发元数据，不是运行时禁用开关。

### 3.2 固定 lint 规则

Market CI 与 `lint` / `precheck` 共用 pinned `ruff==0.12.4`：

```
--ignore-noqa --isolated --no-respect-gitignore
--target-version py311 --line-length 120
--select E4,E7,E9,F,I --exclude vendor
```

生成的 `ruff.toml` 与之对应：`target-version = "py311"`、`line-length = 120`、`extend-exclude = ["vendor"]`、`respect-gitignore = false`、`[lint] select = ["E4","E7","E9","F","I"]`。

### 3.3 CI 门禁（插件仓库的 `verify.yml` / `release.yml`）

两者都是调用官方可复用工作流的**薄封装**（`uses: Project-N-E-K-O/N.E.K.O/.github/workflows/plugin-market-{verify,release}.yml@<pinned-ref>`），`verify.yml` 在 push/PR/workflow_dispatch 触发，`release.yml` 在 `v*` tag 触发并要求 `contents: write` + `id-token: write` + `attestations: write`。

`verify.yml` 内部顺序：

1. **校验输入**：`plugin-id` 必须 `^[a-z][a-z0-9_]*$`；`plugin-directory` 必须是仓库内相对路径、拒绝符号链接与路径穿越；`package-name` 必须是纯 `.neko-plugin` 文件名。
2. **挂载**：把插件仓库 checkout 到 `plugin-repo/`、官方 N.E.K.O checkout 到 `neko/`，把插件源复制进 `neko/plugin/plugins/<id>/`；校验 `plugin.toml` 的 id 与输入一致、**tag 版本与 `plugin.toml.version` 一致**；release 模式还要求存在 `.github/workflows/release.yml` 且 builder 必须是官方 `Project-N-E-K-O/N.E.K.O`。
3. **Ruff check**（上述固定规则）。
4. **Sync plugin dependencies**：`sync <id> --clean`。
5. **Release check**：`check -r <id>`，输出留存为 `<id>.check-release.txt`（release 模式为 `<id>.market-release-check.txt`）。
6. **写 Market 证据** `market-evidence.json`：从包内 `manifest.toml` 复核 id/`package_type`/version 与源码一致、tag 与 manifest version 一致、`metadata.toml` 的 payload hash 是 64 位十六进制；记录 `source_commit`、`workflow_run_id/attempt`、`neko_repository/neko_ref/neko_commit`、包的 `sha256/size/payload_hash`。
7. 上传证据与验证产物为 artifacts。

### 3.4 其他验证入口

- Hosted TSX：`cd frontend/plugin-manager && npm run check-hosted-tsx -- plugin/plugins/<id>`；涉及 state/actions/权限/i18n 时用 `npm run test:hosted` / `test:hosted:e2e`；完整门禁 `scripts/check-hosted-ui.sh`（主要面向 MCP Adapter fixtures）。
- Markdown / Static UI：`check` 只验证 entry 路径存在，**不渲染**，需人工或浏览器检查。
- 插件测试：`cd plugin/plugins/<id> && uv run python -m pytest tests -q`；`check --release` 在有 `tests/` 时会自动跑。
- 平台侧：`uv run pytest plugin/tests -q`、带 `-c plugin/tests/pytest.ini` 的 unit/integration、E2E 需 `--run-plugin-e2e`。

### 3.5 安全扫描（默认暂停，可开启）

`check -r` 默认处于 **Market 旧版审核模式**：暂停源码/包安全扫描（含二进制与体积限制）。设置 `NEKO_PLUGIN_MARKET_SECURITY_CHECKS=1` 可启用：

- `package-security`：包内容扫描（`check -r`、`precheck`）。
- `source-security`：`check -r --market-release`、`publish <plugin>`、`publish github <plugin>` 在 git 能列出插件仓库已提交文件时扫描。
- `publish market <url>` 只通知 Market，**不做本地扫描**。
- 所有模式的 release check 都会校验包与 payload hash。

Market 侧扫描上限（`release_cmd.py` 对齐 `N.E.K.O-PluginMarket`）：源码归档 **32 MiB**、单文件 **2 MiB**、归档条目 **5000**、展开后 **128 MiB**；二进制按签名（`MZ`、`\x7fELF`、`PK\x03\x04` 等）或后缀（`.exe/.dll/.pyd/.so/.wasm/.zip/.whl/.pyc/.neko-plugin` 等）识别；图片/音视频/模型/字体等 asset 后缀走流式扫描，不受单文件 2 MiB 限制。

---

## 4. 审核（Market 首次审核 + 自动门禁 + 证据链）

### 4.1 人工审核：首次申请

在 <https://market.project-neko.cn/#/upload> 登录：

1. 填 GitHub 仓库地址（如 `https://github.com/<you>/n.e.k.o_plugin_hello_world`）。
2. 点「读取仓库信息」。
3. 确认插件名称、选分区与 **1–5 个标签**，介绍可选。
4. 点「提交审核申请」。
5. 在「我的插件」打开该申请，看**检查结果与审核意见**。

关键语义：

- 提交的是**当前分支解析出的完整 commit SHA**，Market 审核这份**不会移动的代码快照**；此时**没有**提交 `.neko-plugin` 包，也**没有**可下载版本。
- **一个插件只提交一次首次申请**；申请未关闭时不要为同一仓库重复建申请。
- **审核通过 ≠ 可安装**：通过只产生 Market 中的插件条目，仍需发布第一个版本才有下载按钮。
- `publish` **不能替代首次审核**，也不能把未通过审核的仓库直接发布。

### 4.2 审核中要修改：Revision

1. 继续改 `plugin/plugins/hello_world/` 源码。
2. 重跑 `neko-plugin check hello_world`。
3. 在插件自己的仓库 commit + push。
4. `git rev-parse HEAD` 复制新的**完整 commit SHA**。
5. 回**原申请**的「版本更新」区，填修复说明与新 commit。
6. 点「确认提交新 Revision」。

新 Revision **替换**待审快照，**不是**新插件版本，也**不会**创建 Market Version。申请一旦被关闭，作者不能自行提交 Revision；被拒绝的申请需要审核员先重新打开。

### 4.3 自动门禁（`check --release --market-release` / CI）

| 约束 | 值 / 行为 |
|---|---|
| plugin id | `^[a-z][a-z0-9_]*$`，≤ 100 字符；不合规为 **error** |
| version | ≤ 50 字符；不合规为 **error** |
| 仓库名 | 推荐 `n.e.k.o_plugin_<id>`；不符为 **warning** |
| `origin` | 必须存在且指向 GitHub，否则 **error** |
| tag / version | `GITHUB_REF_NAME` 去掉前导 `v`/`V` 后必须等于 `plugin.toml.version`，否则 **error**；缺 `GITHUB_REF_NAME` 为 warning |
| `release.yml` | 仓库根 `.github/workflows/release.yml` 必须存在，否则 **error** |
| 工作区 | 发布模式下有未提交/未跟踪文件为 **error** |
| `release.yml` 版本 | `publish` 会检查它是不是当前标准模板；不是则要求先 `setup-repo --upgrade-github-actions` |

CI 侧额外拒绝：非法 `plugin-id`、路径穿越/符号链接、`package-name` 含路径或通配符、`manifest.toml` 不唯一、包内 id/`package_type`/version 与源码或 tag 不一致、payload hash 缺失或非 64 位十六进制、release 模式的 builder 不是官方 N.E.K.O。

### 4.4 构建来源证据链（build provenance）

`plugin-market-release.yml` 把流程拆成 `release → evidence → attest` 三个 job，用 `.github/tests/test_market_build_provenance.py` 守约束：

- `release` job 权限仅 `contents: read`；**插件代码运行的 job 不能请求签名身份**。
- 传给后续 job 的值（`artifact-id`、`plugin-directory`、`package-name`、`neko-commit`）必须**在任何插件代码运行之前固定**，避免被插件内容篡改。
- `Write Market evidence` **不在**运行插件代码的 job 里；evidence job 的 checkout 不落凭据。
- `attest` job 才有 `contents: write / id-token: write / attestations: write`，且**不含任何 `run` 步骤**、所有 `uses` 都是 40 位 commit SHA 的 pinned action，通过 `attest-build-provenance` 对 `market-evidence.json` 与 `*.neko-plugin` 签名。
- 重试时只覆盖**已发布的证据 artifact**（`overwrite: true`），不覆盖 build / signing-input artifact，否则会破坏按 artifact id 的后续重试。
- 生成的 `release.yml` 调用方必须带 `id-token: write` 与 `attestations: write`。

### 4.5 发布后可核对什么

1. GitHub Releases 页 `v<version>` 下有 `<id>.neko-plugin`、`<id>.market-release-check.txt`、`market-evidence.json` 三个资产且可下载。
2. Market 插件详情的版本列表出现该版本，stable 的 latest 不再为空。
3. Market 保存的是 Release 中安装包的**地址与校验值**，开发者**不需要**手动上传 `.neko-plugin`。

### 4.6 常见失败

| 现象 | 处理 |
|---|---|
| Market 提示「找不到可发布插件」 | 确认首次审核**已通过**（不只是已申请）、Market 绑定的仓库 == `origin`、Release 由标准 `release.yml` 生成并通过验证 |
| 标准发布配置不是当前版本 | `setup-repo <id> --upgrade-github-actions --dry-run` 预览 → 去掉 `--dry-run` 执行 → 提交推送 `.github/workflows/` 与 `ruff.toml` → 重发 |
| Actions 失败且需改代码 | **换用新版本号**，commit/push，再发新 tag；不要让同一版本号指向另一份代码 |
| 插件目录没有自己的 `.git/` | 当前 `publish` 会停止；CLI 没有把「仅由外层 N.E.K.O 仓库跟踪」的目录自动转成可发布仓库的命令。不要靠复制目录/导入安装包/符号链接伪装 |

---

## 5. 官方命令集（照抄前先 `uv run neko-plugin --help` 确认）

| 用途 | 命令 |
|---|---|
| 建骨架 | `init <id> --type plugin --name "..."` |
| 补支撑文件 | `setup-repo <id> [--github-actions] [--upgrade-github-actions] [--dry-run] [--overwrite] [--git] [--remote]` |
| 建 GitHub 仓库 | `create-repo <id> [--owner] [--private]`（用 gh） |
| 依赖 | 写 `pyproject.toml` → `sync <id> [--clean] [--python]` |
| 检查 | `check` / `-s` / `-r` / `-r --market-release` |
| 固定 lint | `lint <id>` |
| 本地 CI 门禁 | `precheck <id> [--json] [--skip-tests]`（lint → sync --clean → check -r） |
| 包检查 | `check -r` 内含 inspect + payload hash 验证 |
| 构建 | `build <id> [-o] [-t] [--all] [--bundle]` |
| 安装 | `install` 仅兼容/导入指引；真实安装走 Plugin Center |
| 分析 | `analyze <id>...` |
| **发布** | **`publish <id>` / `publish github <id>` / `publish market <url>`** |

**命令边界**：`release_cmd.py` / `validate_cmd.py` 是内部实现模块，不是顶层命令；`deps` 不是顶层命令（`deps_cmd.py` 注册的是 `sync`）；没有 `release`、也没有 `add` 顶层命令；`init setup-repo` / `init create-repo` 这类二级写法不存在——它们都是顶层命令。`init` 生成物见 `plugin/neko_plugin_cli/templates/generator.py:174-176`：`ruff.toml`、`verify.yml`、`release.yml`。

---

## 6. 检查清单

```
构建
☐ 第三方依赖在 pyproject.toml，vendor/ 由 sync --clean 生成，无 requirements.txt
☐ 包内无 __pycache__ / .pytest_cache / .venv / dist / build
☐ build 产物为 .neko-plugin（或 bundle 为 .neko-bundle），manifest.toml 的 id/version 与源码一致
☐ check -r 的 payload_hash_verified=True

工作流
☐ 插件目录有自己的 .git/，origin 指向 n.e.k.o_plugin_<id> 的公开仓库
☐ git status --short 为空，当前 commit 已 push
☐ verify.yml / release.yml 是当前标准模板，ruff.toml 未被自定义破坏
☐ plugin.toml.version 是从未发布过的新版本号，tag 为 v<version>

验证
☐ check / --strict / lint / precheck 全部通过
☐ GitHub Actions「Verify N.E.K.O Plugin」通过
☐ Hosted TSX 改动跑过 check-hosted-tsx；UI/entry 改动有触发测试
☐ 理解 check 的盲点，未把 check 通过当作运行通过

审核
☐ 首次审核已提交且未被关闭；按审核意见用 Revision 提交新 commit SHA
☐ 审核**已通过**（不只是已申请）
☐ Release 三资产齐全可下载；market-evidence.json 与 attestation 生成
☐ Market 版本列表出现该版本，stable latest 已更新
```

---

## 7. 未验证与边界

- 本篇是**只读查询官方文档与源码**的结果，**未克隆、未下载**官方仓库，也**未在真实环境中跑过** `publish` → Release → Market 上架全链路；命令参数以 `uv run neko-plugin --help` 与目标版本源码为准。
- 官方 CI 的 lint 与测试链路已只读核对：`.github/workflows/plugin-market-verify.yml` 用 `uvx ruff==0.12.4 check --ignore-noqa --isolated --no-respect-gitignore --target-version py311 --line-length 120 --select E4,E7,E9,F,I --exclude vendor`，再把插件 checkout 进 N.E.K.O 源码树跑 `sync --clean` 与 `check -r`（那里才有 `plugin.sdk`）。本机已真跑这两条 ruff 入口、`uvx pytest -q -c tests/pytest.ini tests`（11 passed）、5 个 `.py` 编译；官方 main 的 `check` / `lint` / `precheck` / `publish` 与真宿主加载**仍未跑**。4.1.1 的 `check --strict`（0 error / 1 预期 warning）出自本地旧快照 CLI，**不算官方 main 验证**；`examples/minimal_plugin/README.md` 给出可复现清单，本技能包不声称已端到端跑通。发布与审核链路的逐条阻塞事实、前置条件与审核决策见仓库根目录 [`../../UNVERIFIED.md`](../../UNVERIFIED.md)（待审）。
- Market 的**人工审核标准**（审核员实际关注项）不在官方仓库中公开，本篇只覆盖可查到的自动门禁与流程语义。
- `NEKO_PLUGIN_MARKET_SECURITY_CHECKS=1` 的扫描默认暂停，Market 侧策略可能随时变化；发布前以 Market 页面的实际检查结果为准。
