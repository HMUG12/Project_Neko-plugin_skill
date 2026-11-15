# 42 · 网页数据集成：把"联网抓取/搜索"封装进插件

> 融合来源：**firecrawl/firecrawl**（LLM 友好的网页抓取 / 爬取 / 搜索 API，提供 REST 与 Python/TS/JS SDK，以及 MCP 服务器）。
>
> 场景：你的插件需要"读网页、搜资料、批量爬站点"——例如资讯聚合、竞品监控、文档问答、网页转结构化数据。Firecrawl 是这类能力的成熟实现，本文讲**如何把它作为后端能力封装进 NEKO 插件**，并给出可直接套用的模式。

---

## 1 · 核心能力（对应插件需求）

| 能力 | Firecrawl 端点 | 插件用途 |
|------|----------------|----------|
| 单页抓取 | `POST /v1/scrape` | 把某个 URL 转成 markdown/HTML/结构化 JSON |
| 批量爬取 | `POST /v1/crawl` + `GET /v1/crawl/{id}` | 监控整站、归档资料 |
| 网页搜索 | `POST /v1/search` | 联网检索后喂给 LLM 工具 |
| 结构化抽取 | `scrape` 带 `jsonOptions.schema` | 按 JSON Schema 抽出字段（价格、标题、评论…） |
| 深度研究 | `POST /v1/deep-research` | 多步检索+综合，生成报告 |
| LLM 提取 | `POST /v1/extract` | 从多源提取结构化信息 |

> 其余端点（`map` / `batch scrape` / `generate llms.txt` 等）按需查阅官方文档。

---

## 2 · 封装原则（YAGNI + 深模块）

- **只暴露用户要的字段**：entry 参数 = `{ url }` 或 `{ query }`，不要暴露 `formats`/`onlyMainContent` 等内部开关（除非是高级设置）。
- **内部复杂度藏起来**：把"构造请求→调用→解析→限流重试"收进一个深函数 `async def _fetch(url, **opts)`，entry 只调它并返回 `Ok({"output": ...})` / `Err(...)`。
- **密钥走配置**：API Key 放 `plugin.toml` 的 `[settings]` 或环境变量，**绝不硬编码**（`09-permission-system.md`、`43-security-hardening.md`）。

---

## 3 · 模式 A：把抓取暴露成 `@llm_tool`

最适合"让 AI 在对话里按需联网"的插件。注意 `@llm_tool` 用 `name=`/`parameters=`，返回普通 `dict`（`{"output":..., "is_error":...}`）——见 `02-python-plugin.md`、`19-llm-workflow-design.md`。

```python
from neko_framework import llm_tool  # 伪导入，按本仓库实际命名

@llm_tool(
    name="web_search",
    description="联网搜索并召回与 query 相关的网页摘要，用于补充实时信息。",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "limit": {"type": "integer", "default": 5, "description": "返回条数"},
        },
        "required": ["query"],
    },
)
async def web_search(self, query: str, limit: int = 5) -> dict:
    try:
        data = await self._firecrawl_search(query, limit)  # 深函数：含 key/重试/超时
        return {"output": data, "is_error": False}
    except Exception as e:  # 捕获后转 Err，别让异常沉默（24-error-handling-patterns.md）
        self.logger.error("web_search failed: %s", e)
        return {"output": f"搜索失败：{e}", "is_error": True}
```

---

## 4 · 模式 B：把抓取做成 `@plugin_entry`（按钮触发）

适合"用户点一下，抓取并展示"的插件，UI 用 `api.call` 调此 entry，结果用 `JsonView`/`Table` 展示（`03-ui-settings.md`、`15-rich-ui-components.md`、`41-ui-design-quality.md`）。

```python
@plugin_entry(
    name="scrape_url",
    description="抓取指定 URL，返回清洁的 markdown 正文。",
    input_schema={
        "type": "object",
        "properties": {"url": {"type": "string", "description": "目标网页 URL"}},
        "required": ["url"],
    },
)
async def scrape_url(self, url: str):
    # 1) 校验 URL，防 SSRF（见 43-security-hardening.md）
    if not self._is_safe_url(url):
        return Err("不安全的 URL，已拒绝。")
    # 2) 深函数调用
    try:
        md = await self._firecrawl_scrape(url)
        return Ok({"output": md})
    except Exception as e:
        return Err(f"抓取失败：{e}")
```

---

## 4.5 · 用官方 Python SDK（推荐，少写样板）

Firecrawl 官方 Python SDK（`pip install firecrawl-py`，当前 `__version__ = "4.34.0"`）已封装好鉴权、超时、重试。优先用它，而不是手搓 `aiohttp` 请求。

**实例化**（密钥走配置，不硬编码）：
```python
from firecrawl import Firecrawl   # v2 客户端

api_key = (await self.config.dump()).get("firecrawl", {}).get("api_key")
api_url = (await self.config.dump()).get("firecrawl", {}).get("api_url")  # 自建/代理时填
fc = Firecrawl(api_key=api_key, api_url=api_url)
```

**抓取**（返回对象含 `.markdown` / `.html` / `.metadata_dict`）：
```python
doc = fc.scrape("https://docs.firecrawl.dev", formats=["markdown"])
print(doc.markdown)
```

**搜索**（返回对象含 `.web` 列表）：
```python
res = fc.search(query="What is the capital of France?", limit=5)
for r in res.web:
    print(r.title, r.url)
```

**结构化抽取**（按 schema 抽字段——这是 Firecrawl 的杀手锏）：
```python
from pydantic import BaseModel

class Price(BaseModel):
    value: float
    currency: str

schema = Price.model_json_schema()   # 或手写 dict
data = fc.extract(
    urls=["https://shop.example/item"],
    prompt="Extract the product price.",
    schema=schema,
)
```

**批量 / 站点地图**（长任务，返回 job 对象）：
```python
job = fc.crawl("https://docs.firecrawl.dev", limit=3, poll_interval=1, timeout=120)
print(job.status, job.completed, "/", job.total)

batch = fc.batch_scrape(["https://a", "https://b"], formats=["markdown"])
links = fc.map("https://firecrawl.dev").links
```

> SDK 是**同步阻塞**的。在 NEKO 插件里务必用 `asyncio.to_thread(lambda: fc.scrape(...))` 包起来，避免卡住事件循环（`10-performance.md`）。异步客户端 `AsyncFirecrawl` 也可用，但当前 v2 同步客户端最稳。

---

## 5 · 深函数模板（含超时/重试/限流）

```python
import asyncio, aiohttp

async def _firecrawl_scrape(self, url: str, max_retries: int = 2) -> str:
    api_key = (await self.config.dump()).get("firecrawl_api_key")
    if not api_key:
        raise RuntimeError("缺少 firecrawl_api_key 配置")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"url": url, "formats": ["markdown"], "onlyMainContent": True, "timeout": 30}
    for attempt in range(max_retries + 1):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post("https://api.firecrawl.dev/v1/scrape",
                                  headers=headers, json=payload, timeout=35) as r:
                    r.raise_for_status()
                    js = await r.json()
                    return js["data"]["markdown"]
        except Exception as e:
            if attempt == max_retries:
                raise
            await asyncio.sleep(1.5 * (attempt + 1))  # 退避
    raise RuntimeError("未知错误")
```

> 注意：优先用 §4.5 的官方 SDK（已含超时/重试）。若必须手搓 REST，确认 NEKO 允许的 HTTP 客户端（`aiohttp`/`httpx`）是否已内置；异步调用务必 `await`，否则静默无响应（`25-concurrency-race-conditions.md`）。

---

## 6 · 配置项（plugin.toml）

用 `SettingsField` 声明式模型（见 `44-local-plugin-architecture.md` §3），配置段名与 `model_config = {"toml_section": "my_plugin"}` 对应，写在 `plugin.toml` 的 `[my_plugin]` 下：

```toml
[my_plugin]
firecrawl_api_key = ""      # 用户填入自己的 Key（hot=True 会自动出设置面板）
firecrawl_api_url = ""      # 自建/代理地址，留空用官方
search_limit = 5            # 默认返回条数（用户可调）
timeout = 30                # 单页超时（秒）
```

UI 侧用 Hosted UI settings 面板收集（`03-ui-settings.md`）。**不要**把 Key 写进代码或提交到仓库。运行时用 `await self.config.dump()` 读取整段，再用 `self.config.update({"my_plugin": {...}})` 写回（`44-local-plugin-architecture.md` §3）。

---

## 7 · 质量与合规清单

- [ ] API Key 走配置/环境变量，未硬编码、未提交（见 `43-security-hardening.md`）。
- [ ] URL 入口做了 SSRF/协议校验（仅 `http(s)`，拒绝内网地址）。
- [ ] 调用有超时 + 有限重试 + 退避；失败时返回 `Err`/带 `is_error` 的 dict，不静默。
- [ ] `@llm_tool` 写法正确（`name=`/`parameters=`，返回 `dict`）。
- [ ] 大结果做截断/分页，避免一次塞爆上下文或 UI。
- [ ] 遵守 Firecrawl 的速率限制与 robots/合规要求（作为插件作者需知会用户）。

> 交叉阅读：`13-cloud-api-integration.md`（通用云 API 集成）、`09-permission-system.md`（密钥与权限）、`43-security-hardening.md`（SSRF/注入）、`19-llm-workflow-design.md`（工具设计）。
