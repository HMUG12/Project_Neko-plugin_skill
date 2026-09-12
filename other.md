# 提交前准备

在向 N.E.K.O 插件仓库投稿之前，请确保以下内容已经准备并验证通过：

1. 可公开访问的 GitHub 插件仓库
   - 请准备一个可以公开访问（public）的 GitHub 仓库，仓库中包含插件的全部源代码与发布所需的文件。

2. 仓库命名规范
   - 仓库名必须遵循格式：`n.e.k.o_plugin_<plugin_id>`（例如：`n.e.k.o_plugin_example`）。

3. 根目录需要包含 plugin.toml
   - 仓库根目录必须包含 `plugin.toml` 文件，且该文件包含插件的基本元数据（如 id、name、version、author 等）。

4. 本地检查（强烈建议）
   - 提交前建议在 N.E.K.O 本体目录中运行以下命令进行本地校验：

```bash
uv run neko-plugin check --release /path/to/plugin-repo
```

该命令会对插件仓库进行自动检查，提示缺失文件或不符合投稿要求的项，便于在提交前修正。

---
