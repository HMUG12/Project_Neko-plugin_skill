# 50 · 市场插件逆向工程（31 插件全景 + 可抄范式）

> 基于插件市场 `market.project-neko.cn` 全部 31 个已上架插件的 GitHub 源码深度逆向分析。
> 仓库已克隆到 `_crawled_repos/`，本文提炼**跨插件共性范式** + **每类插件的最佳实践**，全部带 file:line 出处，可直接抄。

---

## 一、市场全景（31 个插件一览）

| id | 插件 | 作者 | GitHub | 类型 | 规模 |
|----|------|------|--------|------|------|
| 32 | OpenBiliClaw 推荐兼容层 | nekopara | `Himifox/n.e.k.o_plugin_proactive_recommender` | 推荐/数据 | 15 py + tsx |
| 31 | 音乐歌单管理 | dustnunknown | `dustnunknown/n.e.k.o_plugin_custom_music_list` | 音乐 | 4 py |
| 30 | 更好的文本输出 | bai_de_hei_ban | `baideheiban/n.e.k.o_plugin_better_txt_output` | 文本处理 | 1 py + static UI |
| 29 | MO 更真实的副官 | Dawn_Meng | `Dawn-Meng/n.e.k.o_plugin_mo_realistic_adjutant` | 语音/陪伴 | 74 py |
| 28 | PVZ Agent | Old_tangyuan | `OldTangyuan/n.e.k.o_plugin_pvz_agent` | 游戏 | （仓库为空） |
| 27 | 尖塔2陪玩 | ZhaiJiu | `zhaijiunknow/n.e.k.o_plugin_sts2_autoplay` | 游戏 | 61 py |
| 26 | 酒狐插件 | ggg233m | `ggg233m/n.e.k.o_plugin_neko_tlm` | 聊天/互动 | 54 py |
| 25 | 应用启动器 | StarrySerendipity | `StarrySerendipity/n.e.k.o_plugin_app_launcher` | 系统工具 | 3 py |
| 24 | 伴学插件 | Momiji | `MomiJiSan/n.e.k.o_plugin_study_companion` | 教育/OCR | 103 py + 18 tsx |
| 23 | 猫娘命令操作器 | bxy | `baixiangyuan/n.e.k.o_plugin_shell_cmd` | 系统工具 | 4 py |
| 22 | 猫娘邮件 | bxy | `baixiangyuan/n.e.k.o_plugin_mail_all` | 邮件 | 4 py |
| 21 | 战雷猫娘副驾驶 | CN-Zephyr | `CN-Zephyr/n.e.k.o_plugin_neko_warthunder` | 游戏 | 133 py |
| 20 | NEKO Live | CN-Zephyr | `CN-Zephyr/n.e.k.o_plugin_neko_live` | 直播互动 | 298 py（最大） |
| 19 | 猫娘邮件秘书 | StarrySerendipity | `StarrySerendipity/n.e.k.o_plugin_neko_mail` | 邮件 | 8 py |
| 18 | 猫娘邮箱(Agently) | StarrySerendipity | `StarrySerendipity/n.e.k.o_plugin_neko_mail_agently` | 邮件 | 3 py |
| 17 | 塔罗牌占卜 | StarrySerendipity | `StarrySerendipity/n.e.k.o_plugin_tarot` | 娱乐 | 8 py + UI |
| 16 | 插件商店搜索 | xxynet | `xxynet/n.e.k.o_plugin_store_search` | 工具 | 4 py |
| 15 | Tavily 搜索 | xxynet | `xxynet/n.e.k.o_plugin_tavily_search` | 搜索 | 2 py |
| 14 | 网易邮箱助手 | StarrySerendipity | `StarrySerendipity/n.e.k.o_plugin_neko_163mail` | 邮件 | 9 py |
| 13 | 猫娘日记 | StarrySerendipity | `StarrySerendipity/n.e.k.o_plugin_neko_diary` | 生活记录 | 4 py + UI |
| 12 | Claude Code Adapter | StarrySerendipity | `StarrySerendipity/n.e.k.o_plugin_claude_code_adapter` | AI 集成 | 13 py |
| 11 | 联网搜索 | StarrySerendipity | `StarrySerendipity/n.e.k.o_plugin_web_searching` | 搜索 | 3 py + UI |
| 10 | 按键控制 | tpe | `ZhenMoon/n.e.k.o_plugin_keyboard_controller` | 系统/自动化 | 12 py + tsx |
| 9 | 猫娘备份插件 | nekopara | `Himifox/n.e.k.o_plugin_data_backup` | 工具 | 5 py |
| 8 | Codex Adapter | StarrySerendipity | `StarrySerendipity/n.e.k.o_plugin_codex_adapter` | AI 集成 | 9 py |
| 6 | 猫娘每日计划 | StarrySerendipity | `StarrySerendipity/n.e.k.o_plugin_catgirl_daily_planner` | 生活 | 3 py |
| 5 | 汐音阁 | StarrySerendipity | `StarrySerendipity/n.e.k.o_plugin_xiyin_pavilion` | 内容/UI | 10 py |
| 4 | Suno 音乐生成 | ZhaiJiu | `zhaijiunknow/n.e.k.o_plugin_suno_cn_music` | 音乐 | 3 py |
| 3 | 文本分析 | ZhaiJiu | `zhaijiunknow/n.e.k.o_plugin_writer_power_analysis` | 文本 | 25 py |
| 2 | BrowserSkill 浏览器控制 | ggg233m | `ggg233m/n.e.k.o_plugin_browser_skill` | 浏览器自动化 | 20 py |
| 1 | rvc_singer | Admin | `HMUG12/n.e.k.o_plugin_rvc_singer` | 音频/AI 唱歌 | 9 py + 独立程序 |

**关键统计**：
- 作者生态：`StarrySerendipity` 12 个、`ZhaiJiu` 3 个、`CN-Zephyr` 2 个、`bxy` 2 个、`xxynet` 2 个、`ggg233m` 2 个、`nekopara` 2 个
- SDK 版本：全部声明 `recommended = ">=0.1.0,<0.2.0"` + `supported = ">=0.1.0,<0.3.0"`
- 规模分布：小（1–9 py）18 个、中（10–30 py）6 个、大（54–298 py）7 个

---

## 二、跨插件共性范式（人人都在用的标准写法）

### 2.1 `plugin.toml` 标准骨架（31/31 插件一致）

```toml
[plugin]
id = "my_plugin"                    # 全部小写 + 下划线
name = "中文名"
description = "功能描述（含 Web UI 地址提示）"
short_description = "English summary"
keywords = [ "多语言关键词" ]        # 搜索优化：中文+英文+日文+韩文+俄文+葡文+西文
version = "0.1.0"
type = "plugin"
entry = "plugin.plugins.my_plugin:MyPlugin"

[plugin.author]
name = "作者名"

[plugin.sdk]
recommended = ">=0.1.0,<0.2.0"
supported = ">=0.1.0,<0.3.0"

[plugin.i18n]
default_locale = "zh-CN"
locales_dir = "i18n"

[plugin.store]
enabled = true

[plugin_runtime]
enabled = true
auto_start = false                  # 复杂插件 false，简单工具 true

# 自定义配置段：以小写插件 id 命名
[my_plugin]
key = "value"
```

出处示例：
- `n.e.k.o_plugin_neko_diary/plugin.toml` — 完整中文+英文+多语 keywords、`[neko_diary]` 自定义配置节（master_name/catgirl_name/default_mood/page_size）
- `n.e.k.o_plugin_app_launcher/plugin.toml` — 8 语言 locales、多行 keywords 数组
- `n.e.k.o_plugin_tarot/plugin.toml` — `auto_start = false`

### 2.2 UI 面板 / Guide 声明（12+ 插件）

```toml
[plugin.ui]
enabled = true

[[plugin.ui.panel]]
id = "main"
title = "面板名"
entry = "ui/panel.tsx"              # 或 "static/index.html"（纯静态）
context = "dashboard"               # 或自定义 context（如 "study"）
permissions = ["state:read", "config:read", "action:call"]

[[plugin.ui.guide]]
id = "quickstart"
title = "快速开始"
entry = "docs/quickstart.md"
mode = "markdown"
permissions = ["state:read"]
```

出处：
- `n.e.k.o_plugin_neko_live/plugin.toml` — 1 panel + 3 guide，`context = "dashboard"`
- `n.e.k.o_plugin_study_companion/plugin.toml` — **19 个 panel** + 1 docs，全部 `context = "study"`，权限按面板细化（`document:parse`、`config:write` 等）
- `n.e.k.o_plugin_better_txt_output/plugin.toml` — `entry = "static/index.html"` 纯静态 UI

### 2.3 版本管理：`previous_ids`（迁移兼容）

```toml
[plugin]
id = "neko_live"
previous_ids = ["neko_roast"]   # 旧 id 列表，平滑迁移用户数据
```

出处：`n.e.k.o_plugin_neko_live/plugin.toml:4-6`

---

## 三、六类插件的最佳实践拆解

### 3.1 系统/自动化类（keyboard_controller、shell_cmd、app_launcher）

**`keyboard_controller`（下载量最高插件）——三合一装饰器 + 防御性 win32**：

```python
# 三合一：AI 工具 + UI 按钮 + 服务入口 同一方法
@llm_tool(name="inject_input", description="...")
@ui.action(name="inject_input", label="注入输入")
@plugin_entry(name="inject_input", description="...")
async def _inject_input(self, steps, **_):
    ...
```

关键模式（`n.e.k.o_plugin_keyboard_controller/__init__.py`）：
1. **目标窗口锁定**：`set_target` 先定位窗口，注入前必须聚焦/置顶，拒绝反作弊进程（进程名/标题黑名单）
2. **提权检测**：目标进程提权等级高于宿主 → 拒绝注入
3. **状态持久化**：`target`、`command_require_confirmation`、`diary_enabled` 存 `self.store`，`unwrap_or(await self.store.get(...), default)`
4. **阻塞调用转协程**：win32 API 用 `asyncio.to_thread(...)` 包裹
5. **命令确认开关**：危险命令默认弹确认（store 标记位）
6. **参数规范化**：`_normalize_sequence` 把 `"按键1 按键2"` 字符串或 `[{"key":...}]` dict 列表统一为内部结构
7. **模块拆分**：`_win32_input.py` / `_screen_capture.py`（截图 OCR）/ `_template_match.py`（模板匹配）/ `_command_exec.py` / `_diary.py` / `_audio_analysis.py` / `_file_ops.py` / `_key_map.py`

**`shell_cmd`（猫娘命令操作器）**：
- 命令执行器独立模块，非绝对路径拒绝（呼应 09 权限 / 铁律 #9）
- 输出截断 + 错误分级返回给 LLM

### 3.2 邮件类（mail_all、neko_mail、neko_163mail、neko_mail_agently）

共性范式：
1. **IMAP 收件 + SMTP 发件**双通道，凭据走 `self.store`（不硬编码）
2. **`@timer_interval` 后台轮询新邮件**，有新邮件用 `push_message` 主动提醒（`visibility="co_stream"`）
3. **邮件列表/详情为 `@llm_tool`**，让 LLM 读信、回信、归档
4. **Agently 版**：`neko_mail_agently` 用 Agently 智能体编排邮件处理流程（17/18 的 LLM 工作流实战）

### 3.3 搜索/数据集成类（web_searching、tavily_search、store_search）

**`web_searching`（3 py + UI，极简却完整）**：
```python
@llm_tool(name="web_search", description="联网搜索（多引擎）")
async def search(self, query: str, engine: str = "auto", **_):
    # 引擎抽象：bing/zhihu/baidu，同域名结果去重
    # 空摘要回退：取正文前 N 字（fetch_page_content）
    # 结果结构化：title/url/snippet 返回给 LLM
```

模式要点：
1. **`@llm_tool` + 独立 `fetch_page_content` 工具**（抓任意 URL 正文）
2. 多引擎 + 同域名去重（防结果重复）
3. 搜索历史存 store，支持多轮追问去重
4. Tavily 版：官方 API 封装成单一 `@llm_tool`（API key 存 store，惰性校验）

### 3.4 教育/OCR 类（study_companion — 103 py 最完整架构）

`n.e.k.o_plugin_study_companion` 是**工程化天花板**，值得全文抄：

1. **按功能模块拆分 entry 文件**：`entry_checkin_entries.py`、`entry_pomodoro_entries.py`、`entry_memory_entries.py`、`entry_tutor_entries.py`、`entry_document_analysis_entries.py`、`entry_supervision_entries.py`...（每模块一组 `@llm_tool`/`@plugin_entry`）
2. **共享基础**：`entry_common.py`（公共工具）、`constants.py`（常量）、`json_utils.py`、`fsrs_bridge.py`（**FSRS 间隔重复算法**用于记忆卡片排期）
3. **模块间事件**：`entry_communication_*_events.py` 用事件解耦（番茄钟结束 → 提醒 → 记录）
4. **OCR 管线**：`ocr_reader` 段配置（backend_selection=rapidocr/tesseract、capture_backend=auto、PP-OCRv4 onnxruntime、多语言）
5. **监督引擎**：`study.supervision` 段（remind_interval、inactivity_timeout、idle_away_seconds），配合 `os_signals_enabled` 做屏幕/活跃度感知
6. **配置节**：`[study]`、`[study.pomodoro]`、`[study.supervision]`、`[study.checkin]`、`[study.awareness]`、`[llm]`、`[ocr_reader]`、`[rapidocr]`、`[fsrs]`、`[knowledge_contribution]`、`[doc_export]` —— **子节命名即分组，一行注释标 `# Deprecated`**
7. **UI 18+ 面板**：每个 `surfaces/*.tsx` 对应一个功能域，`context = "study"`，权限最小化

### 3.5 游戏控制类（neko_warthunder、sts2_autoplay、mo_realistic_adjutant）

**`neko_warthunder`（133 py）核心链路**：
```
data_layer（独立进程读遥测）→ threading 轮询 → 状态机（挂起/地面/空中/战斗）→ LLM 决策 → push_message 播报
```

模式：
1. **遥测读取独立进程**（防游戏反作弊检测 + 不阻塞插件主循环）
2. **UI 双通道**：`ui.context`（实时状态显示）+ `ui.action`（手动干预按钮）+ `plugin_entry`（AI 调用）
3. **状态机驱动播报**：每状态有专属提示词模板，避免 LLM 自由发挥
4. 错误恢复：连接丢失 → 指数退避重连

**`sts2_autoplay`**：`@timer_interval` 高频读屏 + 决策队列（`queue_limit` 防积压），Qt 浮层子进程渲染操作面板。

### 3.6 外部程序集成类（rvc_singer — Plugin A ←HTTP→ 程序 B）

`HMUG12/n.e.k.o_plugin_rvc_singer` 是最佳外部程序桥接范例：

1. **架构**：NEKO 插件（A）← HTTP → RVC Studio（独立桌面程序 B）
2. **HTTP 客户端**：`http_client.py` 连接池 + 健康检查（30s）+ 重试退避 + 任务去重
3. **队列引擎**：`queue_engine.py` 任务队列 + busy signal（B 忙时拒绝 + 排队），进度轮询
4. **错误分类**：区分程序未运行 / 连接失败 / 任务失败，分别给 AI 可执行建议（"请先启动 RVC Studio"）
5. **可选依赖降级**：`PySide6` 缺失时 no-op stub（插件仍可加载，仅 UI 降级）
6. **配置模块**：`config.py` + `paths.py` 集中管理端口、超时、目录
7. **patch_sdk_error**：`SdkError` 补 `.message` 属性兼容层（跨 SDK 版本防御）

---

## 四、可抄代码片段（直接复用）

### 4.1 三合一装饰器（AI + UI + Entry）

```python
@llm_tool(name="do_something", description="做某事（参数说明）")
@ui.action(name="do_something", label="做某事")
@plugin_entry(name="do_something", description="做某事")
async def _do_something(self, param: str, **_):
    try:
        result = await self._do(param)
        return self.Ok(result)
    except SdkError as e:
        return self.Err(str(e))
```

> 注意：`@ui.action` 在上、`@plugin_entry` 在下（铁律 #12），最上层可以是 `@llm_tool`。

### 4.2 后台轮询 + 主动提醒

```python
@timer_interval(interval_seconds=60)
async def _poll_new_items(self):
    if not self._enabled:
        return
    items = await self._fetch_new()
    for item in items:
        await self.ctx.push_message(
            content=f"新消息：{item.title}",
            visibility="co_stream",
            ai_behavior="auto",
        )
```

### 4.3 配置文件节 + 惰性读取

```python
async def _get_config(self):
    return {
        "master_name": self.config.get("neko_diary.master_name", "主人"),
        "page_size": self.config.get("neko_diary.page_size", 20),
    }
```

### 4.4 阻塞调用转协程

```python
import asyncio

async def _win32_call(self):
    result = await asyncio.to_thread(self._win32_inject, self._target_hwnd)
    if result is None:
        return self.Err("注入失败：窗口已关闭或未聚焦")
    return self.Ok("注入成功")
```

### 4.5 外部程序桥接（健康检查 + 重试）

```python
async def _call_external(self, payload: dict, retries: int = 3):
    for attempt in range(retries):
        try:
            async with self._session.post(self._base + "/runs", json=payload, timeout=30) as resp:
                if resp.status == 200:
                    return await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            if attempt == retries - 1:
                return self.Err("外部程序连接失败：请确认已启动")
            await asyncio.sleep(2 ** attempt)  # 指数退避
    return self.Err("外部程序连接失败")
```

---

## 五、踩坑与教训（市场实战总结）

| 坑 | 来源 | 对策 |
|----|------|------|
| 反作弊进程被注入检测 | keyboard_controller | 进程名/标题黑名单 + 提权检测 + 聚焦校验 |
| 外部程序未启动导致 AI 误报 | rvc_singer | 健康检查返回"请先启动"，错误分类给可执行建议 |
| 阻塞 win32 调用卡死事件循环 | keyboard_controller | `asyncio.to_thread` 包裹 |
| 邮件轮询频繁触发 | 邮件类插件 | `@timer_interval` 60s+ 间隔 + store 记录 last_seen |
| 搜索结果重复 | web_searching | 同域名去重 + 历史 store |
| SDK 版本差异 `.message` 缺失 | rvc_singer | `patch_sdk_error()` 兼容层 |
| 大型插件单文件爆炸 | study_companion | 按功能域拆分 `entry_*_entries.py` + 共享 `entry_common.py` |
| 迁移改名丢用户数据 | neko_live | `previous_ids` 声明旧 id |
| 游戏遥测阻塞主循环 | neko_warthunder | 独立 data_layer 进程 |

---

## 六、与既有文档的衔接

- 三合一装饰器 → 21（@llm_tool）+ 03（UI）+ 02（@plugin_entry）
- 外部程序桥接 → 23（外部协议）+ 26（Backend 设计）
- 邮件轮询/主动提醒 → 30（Push Message）+ 02（@timer_interval）
- 大型插件拆分 → 20（Router）+ 33（Entry 系统）+ 44（本地架构逆向）
- FSRS 记忆算法 → 46（持久记忆）+ 35（Store/DB）
- 游戏状态机 → 49（陪伴状态机）+ 19（LLM 工作流）
- OCR 管线 → 27（音频管线类比）+ 10（性能）
