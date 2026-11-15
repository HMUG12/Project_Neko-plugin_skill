# 投稿与上架（官方工作流速查）

> **基线**：官方 `Project-N-E-K-O/N.E.K.O` main `acfbdbc`（2026-11-15 只读核对），依据 `docs/zh-CN/plugins/cli.md`、`docs/plugins/cli.md`、`plugin/neko_plugin_cli/cli.py`。**完整版见 [`neko-plugin-dev/references/51-build-publish-and-market-review.md`](neko-plugin-dev/references/51-build-publish-and-market-review.md)**。
>
> ⚠️ 本技能包只按官方 main 单一口径编写，不再并列旧快照。执行前用 `uv run neko-plugin --help` 确认命令集；官方命令集见 `SKILL.md §7.1` 与 `neko-plugin-dev/references/51-build-publish-and-market-review.md` §5。

## 前提

- 装好 **Git** 与 **uv**；在 N.E.K.O 源码根目录 `uv sync` 后 `uv run neko-plugin --help` 至少有 `init / check / sync / build / publish`。
- 插件源码直接在 `plugin/plugins/<plugin_id>/`，**该目录本身就是插件自己的 Git 仓库**（`init` 会建）。不要复制源码、不要符号链接、不要把安装包导回开发环境。
- 公开 GitHub 仓库名 `n.e.k.o_plugin_<plugin_id>`，创建时不要让 GitHub 自动加 README / `.gitignore` / License。

## 首次上架（六步）

```bash
# ① 校验与本地 CI 门禁（在 N.E.K.O 源码根目录）
uv run neko-plugin check <id>
uv run neko-plugin sync <id> --clean        # 仅当有第三方 Python 依赖
uv run neko-plugin check <id> --strict
uv run neko-plugin lint <id>                # 与 Market CI 相同的 pinned ruff
uv run neko-plugin precheck <id>            # lint → sync --clean → check -r

# ② 建仓库并推送（git 命令在插件自己的目录里执行）
uv run neko-plugin create-repo <id>         # 用 gh 建公开仓库并设为 origin
cd plugin/plugins/<id>
git add . && git commit -m "feat: first release"
git push -u origin main
cd ../../..

# ③ 等 GitHub Actions「Verify N.E.K.O Plugin」通过

# ④ Market 首次审核
# 打开 https://market.project-neko.cn/#/upload → 填仓库地址 → 读取仓库信息
# → 确认名称 / 选分区 / 选 1–5 个标签 → 提交审核申请 → 在「我的插件」看检查与审核意见
# 审核要求修改时：改源码 → check → commit/push → git rev-parse HEAD
# → 回原申请「版本更新」填修复说明 + 完整 commit SHA → 确认提交新 Revision

# ⑤ 审核通过后发布第一个可安装版本
uv run neko-plugin publish <id>

# ⑥ 核对 GitHub Releases 三资产 + Market 版本列表 / stable latest
```

`publish` 会依次：检查 `.git/` 与工作区干净 → 检查标准 `release.yml` 为当前版本 → 发布检查/测试/构建/payload hash → 确认 commit 已推到 `origin` → 按 `plugin.toml.version` 打 `v<version>` tag → 等 Release 生成 `<id>.neko-plugin`、`<id>.market-release-check.txt`、`market-evidence.json` 三个资产 → 通知 Market 发布到 stable。**只推 tag 不等于发布完成**。

## 关键语义（最容易搞错）

| 事项 | 事实 |
|---|---|
| 首次申请提交的是什么 | 当前分支解析出的**固定 commit 快照**，不是 `.neko-plugin` 包，也不是可下载版本 |
| 一个插件几次申请 | **只一次**；未关闭时不要为同一仓库重复建申请 |
| Revision | 替换待审快照，**不是新版本**、不创建 Market Version；申请关闭后需审核员重开才能再提交 |
| 审核通过 ≠ 可安装 | 通过只产生 Market 插件条目；要发布第一个版本才有下载按钮 |
| `publish` 能否替代审核 | **不能**；Market 只接受已审核通过、仓库匹配且标准发布验证成功的插件 |
| 后续版本 | 审核通过后不需重新申请：改源码 → 换**从未发布过**的新版本号 → check → commit/push → publish |
| latest 怎么切 | 按 **Market 中的发布时间**，不比较版本号大小；别在新版之后补发更旧版本 |
| beta / Changelog | `publish github <id>` 只生成 Release → Market 版本页「发布新版本」选渠道、填 Changelog。版本号全局唯一，不分 stable/beta |
| 撤回 | **单向**，版本不能恢复，也不能用相同版本号或同一 Release 重发；修复后用新版本号 |
| 发布中断 | Release 已成就重跑完整 `publish`；也可 `publish market <release-url>` 只重试通知。若需改代码/配置，必须换版本号 |

## 自动门禁（发布前自查）

- `plugin_id` 匹配 `^[a-z][a-z0-9_]*$`、≤100 字符；`version` ≤50 字符。
- 仓库名推荐 `n.e.k.o_plugin_<id>`；`origin` 必须存在且指向 GitHub。
- `GITHUB_REF_NAME`（tag）去掉前导 `v`/`V` 后必须等于 `plugin.toml.version`。
- 仓库根 `.github/workflows/release.yml` 必须存在且是**当前标准模板**；工作区无未提交/未跟踪文件。
- 标准工作流不是当前版本时：`setup-repo <id> --upgrade-github-actions --dry-run` 预览 → 去掉 `--dry-run` 执行 → 提交推送 `.github/workflows/` 与 `ruff.toml` → 重新发布。检测到无法识别的自定义内容会停止而不覆盖。

## 常见失败

| 现象 | 处理 |
|---|---|
| Market 提示找不到可发布插件 | 确认首次审核**已通过**、Market 绑定仓库 == `origin`、Release 由标准 `release.yml` 生成并通过验证 |
| 插件目录没有自己的 `.git/` | 当前 `publish` 会停止；CLI 没有自动转换命令，不要靠复制目录/导入安装包/符号链接伪装 |
| Actions 失败且需改代码 | 换用新版本号，commit/push，再发新 tag；不要让同一版本号指向另一份代码 |

> `check` 通过 ≠ 运行通过。真实宿主中加载、触发入口、打开面板保存、Reload 仍需单独验证。Market 的人工审核标准未在公开仓库披露。
>
> 本文件是仓库说明文件之一，已列入 `.gitignore` 白名单与 README 仓库结构图。
