# 未完成事项与阻塞说明（待审）

> **状态：待审** — 本文只陈述「哪些没做、为什么、需要什么条件」，**不把任何一项标记为已通过、已豁免或可接受**，也不冒充实测。
> 对应版本：`4.3.1`（正文与待审结论自 4.3.0 起未变；4.3.0 定稿为 commit `d55bd0b` / tag `v4.3.0`）
> 唯一事实基线：官方 `Project-N-E-K-O/N.E.K.O` main `acfbdbc`（2026-11-15 只读核对）
> 审核目的：逐条判断「做不了」是否成立、是否存在更省力的替代路径、哪一条其实只是指令边界而非技术不可行。

---

## 0. 结论先行

4.3.0 把**能在本机跑的都跑了**：官方 `init` 底层生成函数实际执行、pinned `ruff==0.12.4` 两种入口、`pytest` 11 项、仓库自检 CI、全仓链接与语法检查。**没做的是需要 N.E.K.O 运行时或 Market 平台才能成立的部分。**

但有一条必须单独挑出来，不能混进「做不了」里充数：**完整官方 main 源码树技术上可以下载，本轮没做是因为此前明确要求「不需要下相关文件和克隆仓库」**。它属于指令边界，单列为 U-05，由审核决定是否解除。把这条伪装成环境限制是不诚实的。

---

## 1. 已完成，不要误列为缺口

| 事项 | 实际执行的命令 / 动作 | 结果 | 证据 |
|---|---|---|---|
| 官方 `init` 生成物 | 实际执行官方 main `generator.py` 的 `generate_plugin()` / `generate_repo_support_files()`（用官方支持的 `entry_point_override` 对齐类名） | 7 份支撑文件**逐字节一致**，sha256 存入自检脚本 | [`examples/minimal_plugin/README.md`](neko-plugin-dev/examples/minimal_plugin/README.md) |
| 官方 pinned lint | `uvx ruff==0.12.4 check --config ruff.toml .` 与官方 CI 原命令 `--isolated --select E4,E7,E9,F,I --exclude vendor` | 两种入口均 `All checks passed!`；真跑抓出并修掉 `routers/notes.py` 的 I001 | 同上 |
| 静态契约测试 | `uvx pytest -q -c tests/pytest.ini tests` | **11 passed**（10 项契约 + 1 项 smoke） | `tests/test_plugin_contract.py` / `tests/test_smoke.py` |
| 语法 / 链接 / 配置 | `python scripts/verify_skill.py` | 5 个 `.py` 编译通过、YAML 与 TOML 可解析、全仓相对链接 0 失效 | [`scripts/verify_skill.py`](scripts/verify_skill.py) |
| 仓库自动化规范（issue #1） | 新增自检脚本 + `.github/workflows/verify-skill.yml` | 本机 8 项硬门禁全通过 | 同上 |
| 事实口径收拢（issue #2） | 只读核对官方 main 后逐篇改写 | 两个 issue 均已回复并关闭，远端 open issues 归零 | [`CHANGELOG.md`](CHANGELOG.md) |

**这些不能替代什么**：静态检查看不见运行时行为——entry 是否真被宿主 `await`、面板 action 是否真暴露、配置是否跨 Reload 生效、`push_message` 的 `submitted=True` 之后宿主是否消费。lint 与契约测试证明的是「代码形状符合官方契约」，不是「插件在宿主里能跑」。

---

## 2. 未完成事项总表

| 编号 | 事项 | 分类 | 是否尝试过 | 结论 |
|---|---|---|---|---|
| U-01 | 真实宿主加载 / 面板保存 / Reload / 消息消费 | A 环境缺失 | 未尝试（无宿主） | 当前不可执行 |
| U-02 | 官方 main `check -r` / `--market-release` | A 环境缺失 | 未尝试（无源码树） | 当前不可执行 |
| U-03 | 官方 main `lint` / `precheck` / `sync --clean` | A 环境缺失 | **部分替代**：lint 的 ruff 部分已真跑 | 门禁链未完整执行 |
| U-04 | `publish` → GitHub Release → Market 首次审核 / 上架 | A 平台缺失 + 外部副作用 | 未尝试 | 当前不可执行 |
| U-05 | 获取完整官方 main 源码树 | **B 指令边界** | 未尝试（受明确限制） | **能做但按指令没做** |
| U-06 | 向真实 Market 提交首次审核申请 | C 主动不做（不可逆） | 未尝试 | 不应由本仓库代做 |
| U-07 | 在真实宿主写配置 / 用户数据 | C 主动不做（污染） | 未尝试 | 应在隔离实例做 |
| U-08 | 真实打包导入链 `.neko-plugin` → 插件中心导入 | A 环境缺失 | 未尝试 | 当前不可执行 |

分类口径：**A** = 本机/账号/平台确实缺东西；**B** = 技术可行但受此前指令约束，需审核决定是否解除；**C** = 有副作用或不可逆，主动不做，与能力无关。

---

## 3. 逐条说明

### U-01 真实宿主加载与交互

- **要验证什么**：宿主能加载 `minimal_plugin`、`startup` 执行、面板能打开、点保存后 `config.update()` 真的落盘、Reload 后 `config.dump(timeout=5.0)` 读回新值、`push_message` 返回 `submitted=True` 之后宿主是否真的消费并显示。
- **为什么静态检查不够**：`check` 的盲点（运行时 entry 是否 `async def`、UI action 与 `@plugin_entry` 叠加后是否真的暴露、配置是否跨 Reload 生效、消息是否被宿主消费）只有运行才暴露。`submitted=True` 按官方定义只表示 SDK 本地提交路径已接管，不代表送达。
- **阻塞事实（本机可复核）**：没有 N.E.K.O 宿主进程与运行时；`command -v neko-plugin` → `NOT INSTALLED`；示例内嵌在技能包仓库中，不是被宿主管理的插件目录；本机 Python 3.13.14、`uv 0.11.3` 有，但仅够跑 lint/测试。
- **已做的替代**：静态契约测试 10 项覆盖形状；`__init__.py` 按官方 `lifekit` 插件的 `config.dump()` / `config.update()` 写法改写；`config.example.toml` 改用 `[minimal_plugin]` 命名空间；`push_message` 判 `PushMessageResult.submitted` 与 `reason`。
- **解除条件**：一个可运行的官方 main 版本 N.E.K.O 宿主；把 `minimal_plugin` 放进宿主插件目录；宿主所需配置/模型依赖就绪；一次可观察的会话。
- **复现步骤与通过判据**：见 [`examples/minimal_plugin/README.md`](neko-plugin-dev/examples/minimal_plugin/README.md)「在真宿主上跑通一次」。判据为：① 宿主日志无加载异常；② 面板可见且可提交；③ 保存后配置文件中出现新的 `greeting`；④ Reload 后界面回显新值；⑤ 触发消息后会话里确实出现内容，且 `reason` 为空。
- **不做的风险**：配置落盘与消息消费两段仍是「按官方源码推导」，未经运行证实。相关文档已标注为源码推导，不写成实测结论。

### U-02 官方 main `check -r` / `--market-release`

- **要验证什么**：发布态校验，尤其是 `metadata.payload.hash` 对规范化 `payload/` 的 sha256 一致性（`payload_hash_verified=True`）。
- **阻塞事实**：官方 CI `plugin-market-verify.yml` 的真实调用是 `uv run python -m plugin.neko_plugin_cli.cli check -r <id>`，前提是把插件 checkout 进 **N.E.K.O 源码树**（那里才有 `plugin.sdk`）。本机通过 Contents API 只读取回 40 个单文件到临时目录，**没有源码树、没有可导入的 `plugin` 包、没有依赖环境**。
- **必须澄清的一条历史记录**：4.1.1 的 `check --strict`（0 error / 1 个「非独立插件仓库」预期 warning）出自工作区旧快照 `N.E.K.O-main (1)`。该快照的 `commands/` 只有 12 个模块，**没有** `lint_cmd.py` / `precheck_cmd.py` / `publish_cmd.py`，与官方 main 命令集不同。因此该结果**不计入**官方 main 验证凭据，已在 `SKILL.md` / 51 篇 / `CHANGELOG.md` 标注。
- **解除条件**：完整官方 main 源码树（见 U-05）+ `uv sync` 装好依赖 + 插件置于源码树内。
- **通过判据**：`check -r` 输出 0 error 且 `payload_hash_verified=True`；`check -r --market-release` 无门禁失败。

### U-03 官方 main `lint` / `precheck` / `sync --clean`

- **要验证什么**：`precheck` 三门禁链 `lint` → `sync --clean` → `check -r`，以及 `vendor/` 依赖隔离是否干净。
- **阻塞事实**：`lint` / `precheck` 是 `neko-plugin` CLI 子命令，本机 CLI 未安装；`sync --clean` 与 `check -r` 同样需要官方源码树（U-02）。
- **已做的替代**：本机用 `uvx ruff==0.12.4` **按官方 CI 原命令**真跑了 lint 的等价部分（pinned 版本、`--isolated`、同一 select / line-length / exclude 参数），但**没有**跑 `sync --clean` 与 `check -r`。这一层只能叫「lint 已真跑」，不能叫「precheck 已通过」。
- **解除条件**：同 U-02，另需网络或本地缓存以安装插件依赖到 `vendor/`。
- **通过判据**：`uv run neko-plugin precheck minimal_plugin --json` 三段全绿。

### U-04 `publish` → GitHub Release → Market 首次审核 / 上架

- **要验证什么**：`release → evidence → attest` 三 job 的来源证明链、`market-evidence.json`、GitHub Release 三资产（`.neko-plugin` / `.market-release-check.txt` / `market-evidence.json`）、Market 自动门禁与人工审核结果。
- **阻塞事实**：`publish` 要求插件是**自己的独立 GitHub 仓库**（推荐 `n.e.k.o_plugin_<id>`）、`origin` 指向 GitHub、工作区干净、`v<version>` tag 与 `plugin.toml.version` 一致、存在 `.github/workflows/release.yml`。示例内嵌在技能包仓库里，不满足独立仓库前提；本机也没有 Market 平台可达性与审核账号。
- **外部副作用**：`publish` 会创建真实 tag、GitHub Release 并向 Market 提交申请，不可在本仓库里「试一下」。
- **已做的替代**：只读核对 `publish_cmd.py` / `plugin-market-release.yml` / Market 审核规则并写入 [51 篇](neko-plugin-dev/references/51-build-publish-and-market-review.md)；示例 `release.yml` 由官方生成器产出、字节一致且含 `id-token: write` / `attestations: write`。
- **不做的风险**：51 篇中发布与审核章节是**源码/文档推导**，不是实测记录；`NEKO_PLUGIN_MARKET_SECURITY_CHECKS=1` 的真实扫描行为、Market 人工审核标准同样未实测。

### U-05 获取完整官方 main 源码树 —— **不是做不了**

- **事实**：GitHub zipball / clone 技术上完全可行，本机 `git` 与网络也可用（`http.version=HTTP/1.1` 可绕过代理下的 HTTP/2 问题）。
- **为什么没做**：此前对本任务的明确限制是「查询猫娘计划文档/仓库（**不需要下相关文件和克隆仓库**）」。本轮沿用该边界，只通过 Contents API 逐文件只读取回 40 个源文件用于事实核对与执行生成器。
- **影响范围**：它是 U-02 / U-03 的**直接前置**；解除后这两条大概率可以补跑。但**不会**解决 U-01（仍需宿主运行时）与 U-04（仍需 Market 平台、独立插件仓库与账号）。
- **解除后需要同步修改**：本文、`README.md` 版本基线表中的「只读查询（未克隆、未下载仓库）」措辞、`CHANGELOG.md` 的核对方式记录。
- **审核判断点**：这一条应作为「限制是否解除」来审，而不是作为「环境不允许」来接受。

### U-06 向真实 Market 提交首次审核申请

- **主动不做**：一个插件只提交一次首次申请，提交会占用 id、进入审核队列并开启 Revision 流程；在示例连宿主都没跑过的情况下把未验证代码推给人工审核，不应由文档仓库代做。
- **关联**：Market 审核通过 ≠ 可安装；`publish` 不能替代首次审核；Revision 是替换待审快照、不是新版本。这些规则来自官方只读文档，未经平台实证。

### U-07 在真实宿主写配置 / 用户数据

- **主动不做**：U-01 的面板保存验证会向宿主写入 `[minimal_plugin]` 配置，可能影响真实用户环境。应在隔离实例或临时 profile 中执行，并把写入范围限定在示例插件命名空间内。

### U-08 打包导入链 `.neko-plugin` → 插件中心导入

- **要验证什么**：`build` 产出的 `.neko-plugin` ZIP 结构、`manifest.toml` / `metadata.toml` / `sign.toml` / `payload/`、以及通过插件中心「导入」完成真实安装。
- **阻塞事实**：需要官方 CLI 与宿主插件中心；新版 `install` 是兼容命令，**拒绝直接写运行时目录**，因此没有「本机一条命令装好」的捷径。
- **关联**：`check -r` 的 payload hash 校验（U-02）是这一条的静态前置，也未跑。

---

## 4. 不是缺口、不要误审的四项

1. **「4.1.1 的 `check --strict` 没算数」** —— 不是漏做，是**做了但口径不适用**（旧快照 CLI），已明确降级为历史记录，见 U-02。
2. **「旧快照那套直接删」** —— 没有物理删除 `REVIEW_FIXES.md` / `CHANGELOG.md`，而是声明「历史存档、不参与当前规则判定」。AI 的规则判定路径已只剩官方 main 一条，删文件会丢掉「为什么曾经判错」的追溯链。
3. **issue #1 / #2 已关闭** —— 不是待办。两条都已留逐项说明评论后关闭，远端 open issues 为 0。
4. **「文档写得多」≠「验证做得多」** —— 本轮新增文档只有本文；真跑证据是生成器、ruff、pytest、自检 CI，不是新写的规则篇章。

---

## 5. 本机环境实测记录（可复核）

| 检查 | 结果 |
|---|---|
| `command -v neko-plugin` | `NOT INSTALLED` |
| `uv --version` | `0.11.3` |
| `python --version` | `3.13.14` |
| 官方 main 源码树 | **不存在**；临时目录仅 40 个通过 Contents API 只读取回的单文件，无 `plugin/` 包结构 |
| 工作区 `N.E.K.O-main (1)` | 旧快照；`commands/` 12 个模块（`check_cmd.py` / `deps_cmd.py` / `release_cmd.py` 等），**无** `lint_cmd.py` / `precheck_cmd.py` / `publish_cmd.py` |
| N.E.K.O 宿主进程 / Market 凭据 | 无 |
| 官方 CI 真实调用 | `uvx ruff==0.12.4 check ...` → `uv run --with pip python -m plugin.neko_plugin_cli.cli sync <id> --clean` → `uv run python -m plugin.neko_plugin_cli.cli check -r <id>` |

---

## 6. 审核决策清单

以下四项是**待审决策**，不是向用户索要信息；每项都给出两种走向的后果，便于直接批注。

- **决策 1 · 是否解除「不下载官方完整源码树」限制（U-05）**：解除 → 可补跑 U-02 / U-03，并同步修订 README 基线表与 CHANGELOG；不解除 → 维持「只读核对」口径，U-02 / U-03 继续记为未验证。
- **决策 2 · 是否提供 N.E.K.O 宿主与 Market 环境（U-01 / U-04 / U-08）**：提供 → 按示例 README 清单跑完整链路并回填实测结果；不提供 → 维持当前边界，文档继续标注「源码推导」。
- **决策 3 · 是否接受把 U-01～U-08 记为已知限制**：接受 → 建议在 `README.md` 发布前检查清单中保留一条「未完成事项见本文」的硬性引用，防止后续版本把缺口悄悄抹掉；不接受 → 需要指定可替代的验证手段。
- **决策 4 · U-06 / U-07 的主动不做是否成立**：这两条与能力无关，是副作用控制；若判定应做，需要在隔离实例与测试 Market 环境下执行，不应在真实环境试跑。

---

## 7. 维护约定

- 每次版本变更后必须复核本清单：完成的项要移入 §1 并附上命令与结果，新发现的缺口要补编号，不允许直接删行。
- `scripts/verify_skill.py` 第 8 项硬门禁会检查本文存在、状态行仍为「待审」、`U-xx` 编号唯一且不少于 6 条，防止把未完成项悄悄标成完成。
- 本文与 `REVIEW_FIXES.md` / `CHANGELOG.md` 同属说明性文档，不参与「规则区旧口径残留」扫描；AI 判定插件写法时不应以本文为依据。
- 相关声明原先散见于 `README.md`、`SKILL.md`、`references/README.md`、51 篇、`examples/README.md`、示例 README 与 `n.e.k.o_plugin_example/README.md`；**本文是唯一汇总入口**，各处保留简短链接指向这里。
