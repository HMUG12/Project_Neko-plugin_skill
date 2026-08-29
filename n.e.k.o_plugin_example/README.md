# n.e.k.o_plugin_example

这是一个由 Project_Neko-plugin_skill 参考仓库自动生成的最小示例插件。

包含文件：
- plugin.toml: 插件元数据
- main.py: 插件入口示例

如何本地校验：
1. 在 N.E.K.O 本体目录中运行：

```bash
uv run neko-plugin check --release /path/to/n.e.k.o_plugin_example
```

2. 或在仓库根目录直接运行 CI 校验脚本：

```bash
python scripts/verify_plugin.py
```
