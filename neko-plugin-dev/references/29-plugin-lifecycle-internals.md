# 29 — 插件生命周期（按官方源码重写）

> **依据**：`plugin/sdk/shared/core/decorators.py`（`@lifecycle` 定义）、`plugin/core/host.py`（钩子派发与定时器执行）、`docs/plugins/lifecycle-config.md`、`docs/plugins/decorators.md`、官方 `.agent/skills/neko-plugin/`。
>
> **修订说明**：本篇曾基于旧版本逆向，写出 `on_init` / `on_start` / `on_stop` / `on_unload` 四个**不存在的钩子**、`@lifecycle("...")` 位置参数写法、`self,,` 语法错误，以及 `ctx.trigger_event()` / `ctx.query_memory()` 两个**虚构 API**，还与 31 号文档自相矛盾。现已按官方源码整篇重写。**插件作者只需看 §1–§3**。

## 1. 唯一合法的生命周期 id

`@lifecycle` 的签名是 `id: Literal["startup", "shutdown", "reload", "freeze", "unfreeze", "config_change"]`（`decorators.py` 约 471 行），**必须用关键字参数 `id=`**，不接受自定义钩子名或位置参数。

| id | 触发时机 | 建议用途 |
|---|---|---|
| `startup` | 插件实例创建、entry 收集完成后 | 读配置、恢复状态、注册后台任务 |
| `shutdown` | 插件停止 / 进程退出前 | 落盘、取消后台任务、释放资源 |
| `reload` | 仅为兼容保留 | 不要依赖 |
| `freeze` / `unfreeze` | 冻结 / 解冻 | 暂停长循环、后台轮询 |
| `config_change` | 配置变更时 | 重载运行时配置 |

**不存在的东西**：`on_init`、`on_start`、`on_stop`、`on_unload`、`@lifecycle("on_init")` 位置参数写法、`ctx.trigger_event`、`ctx.query_memory`。跨插件没有事件广播 API，用 `self.plugins.call_entry(...)`。

## 2. Reload 与 config_change 的真实语义

- 管理面板的 **Reload 按钮是重启进程**（shutdown → startup），不是同进程热更新。`@lifecycle(id="reload")` 只是兼容保留，不要把状态迁移逻辑放进去。
- `config.update` 不会在同进程触发 `config_change`；`config_change` 由宿主以 **kwargs** 注入 `old_config` / `new_config` / `mode`，处理函数用 `**_` 或显式声明接收，不要写成必填位置参数。
- 运行时配置是明文 TOML（`<数据根>/plugins/<id>/config/plugin.toml`），不要把密钥写进日志或面板回显。

## 3. 正确的生命周期骨架

```python
from plugin.sdk.plugin import NekoPluginBase, neko_plugin, lifecycle, Ok


@neko_plugin
class MyPlugin(NekoPluginBase):
    @lifecycle(id="startup")
    async def on_startup(self, **_):
        await self._reload_config()
        return Ok({"status": "ready"})

    @lifecycle(id="shutdown")
    async def on_shutdown(self, **_):
        await self._cancel_background_tasks()
        return Ok({"status": "stopped"})

    @lifecycle(id="config_change")
    async def on_config_change(self, **_):
        await self._reload_config()
        return Ok({"status": "reloaded"})

    @lifecycle(id="freeze")
    async def on_freeze(self, **_):
        self._frozen = True
        return Ok({"status": "frozen"})
```

## 4. 常见陷阱（取代旧版「7 阶段状态机」）

1. **startup 里跨插件调用**：其他插件可能未就绪 → 挪到首个工作入口并做失败回退。
2. **startup 做耗时同步 I/O**：启动有超时（默认约 10 秒）→ 放 `asyncio.to_thread` 或 `create_task`。
3. **定时器写成同步 `def`**：宿主执行 `asyncio.run(fn())`，同步函数返回的 `Ok` 再被 await 会 TypeError → 必须 `async def`，且不要自建事件循环（见 `07-gotchas.md` #19 / #35）。
4. **freeze 后后台任务仍在跑**：长循环每轮检查 `self._frozen`。
5. **只写 `reload` 钩子**：Reload 是重启进程，等同没写。
6. **工具注册位置**：`@llm_tool` 只扫插件主类，别写进 Router。

## 5. 宿主内部（仅供理解，非契约）

- 宿主先收集 entry（`collect_entries()`，失败时回退扫描），再派发 startup。
- UI action 只从已注册的 `entry_map` 里收集（`host.py` 的 `_collect_ui_actions`），所以 `@ui.action` 必须叠加 `@plugin_entry`。
- 定时器由宿主起线程循环并 `asyncio.run(fn())` 执行，间隔由 `seconds` 控制；停止依赖 `threading.Event`。
- 进程间通信见 `37-zmq-transport-internals.md`，那属于宿主实现，插件代码不直接接触。

> 本篇不再复述「load / init / start / run / stop / unload 七阶段状态机」等未经源码证实的表述。若与官方源码冲突，一律以官方为准。
