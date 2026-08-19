# examples · 可运行示例插件（端到端融合 40–45，可扩展 46–50）

本目录是一个**完整、可参考**的 N.E.K.O 插件样例，把 `references/40–45` 的融合精髓拼成真实骨架。它不是一个玩具 demo，而是照抄即用的模板。

## 目录结构

```
examples/web_assistant/
├── plugin.toml            # [plugin] + [[plugin.ui.panel]] + [web_assistant] 配置段
├── __init__.py            # 主类：@neko_plugin + startup/shutdown/config_change(**_)→Ok/Err + include_router
├── routers/
│   ├── __init__.py
│   └── web.py             # WebRouter：scrape_page / web_search(@llm_tool) / refresh_status + SSRF 守卫
└── ui/
    └── settings.tsx       # 设置面板（反 AI 味写法）
```

## 它示范了什么（对应 skill 篇章）

| 精髓 | 落点 | 对应篇章 |
|------|------|---------|
| 深函数封装 | `scrape_page`/`web_search` 只取参→调 `_call_firecrawl`→`Ok`/`Err` | `40` §5 / `42` §2 |
| Router 子包拆分 | 业务逻辑在 `routers/web.py`，主类只 `include_router` | `44` §1 范式 A |
| 设置面板 | `self.config.dump()/update()` + `@ui.context` + `@ui.action` | `03` / `44` §3 |
| @llm_tool 联网 | firecrawl 官方 SDK 包在 `to_thread` 里 | `42` §4.5 / `45` §3 |
| SSRF 守卫 | `_is_safe_url` 解析 IP 判内网+云元数据（进阶版） | `43` §4 / `45` §4 |
| 防御性入口 | `try/except → Err`，异常不冒泡 | `44` §6 / `45` §5 |
| @llm_tool 防 TypeError | `query: Any = None` + 入口内校验 | `44` §5 |
| 反 AI 味 UI | 单主操作、无嵌套卡片、对比度达标、无 emoji 装饰 | `41` §2 + §2.5 |

## 怎么用

1. 把 `web_assistant/` 复制到你的 `plugins/` 目录（或作为新插件起点）。
2. 按真实框架的 import 约定微调顶部 import（本例沿用 `02-python-plugin.md` 的 `from plugin.sdk.plugin import ...`）。
3. `plugin.toml` 的 `entry = "plugin.plugins.web_assistant:WebAssistantPlugin"` 改成你实际的包路径。
4. 在设置面板填入 Firecrawl API Key，即可用 `scrape_page` / `web_search` 两个能力。

## 想扩展时

- 加第二个业务域 → 新建 `routers/xxx.py` 并在 `__init__.py` 的 `include_router` 注册（继续范式 A）。
- 配置项想自动出面板 → 改用 `Settings(PluginSettings)` + `SettingsField(hot=True)`（见 `44` §3）。
- 几十个正交能力 → 升级到 Mixin 合成（见 `44` §1 范式 B，galgame_plugin / neko_roast）。
- 想加持久记忆/后台"梦境"整理 → 看 `46`（store + `@timer_interval` 后台整理）。
- 想对接多模型/外部 LLM 并省钱 → 看 `47`（复杂度路由 / 验证器级联 / 语义缓存 / 飞行中去重）。
- 想外发 LLM/API 前压缩降 token + 本地脱敏 → 看 `48`。
- 想做角色陪伴/好感度 persona → 看 `49`（数值状态机 + 聊天指令，安全版）。

> 回到主文档：`../SKILL.md` · 速查：`../references/45-fusion-quick-reference.md`
