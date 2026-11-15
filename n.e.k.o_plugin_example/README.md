# n.e.k.o_plugin_example

本目录是 **市场仓库命名示例**，只放说明文件，不是一个可加载的插件。

官方要求市场仓库名为 `n.e.k.o_plugin_<plugin_id>`，且**仓库根目录**包含 `plugin.toml`、`pyproject.toml`、`README.md`、`tests/` 等发布支撑文件。真实插件请放在 `n.e.k.o_plugin_<plugin_id>/` 自己的仓库里，或用 `uv run neko-plugin init-repo <plugin_id>` 生成。

> 旧版本说明里提到的 `main.py` 与 `scripts/verify_plugin.py` 在本仓库中并不存在，已删除相应描述。

本地校验（在 N.E.K.O 本体目录执行）：

```bash
uv run neko-plugin check <plugin_id> --strict
uv run neko-plugin check <plugin_id> --release --market-release
```

可复制的最小插件示例见技能包内的 `neko-plugin-dev/examples/minimal_plugin/`；投稿流程见仓库根 `OTHER.md`。

本目录已列入 `.gitignore` 白名单与 README 仓库结构图。
