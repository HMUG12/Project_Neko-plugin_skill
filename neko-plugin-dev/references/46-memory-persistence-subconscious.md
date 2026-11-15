# 46 · 持久记忆与潜意识式后台整理（来自 subconscious-skill）

> 逆向自 Square-Q/subconscious-skill（Python，约 30 文件）：给 AI Agent 装上"活潜意识"的认知架构。要点：5 阶段记忆管道、3 类记忆、重要性衰减/遗忘、whisper 极简注入。全部代码级结论，映射到 N.E.K.O 插件。

## 1. 三层认知架构（直接可用模型）

- **意识层（Conscious）**：当前会话主流程，写代码/工具调用，接收 whisper 注入。
- **前意识层（Preconscious）**：静态知识仓库（代码索引、文档、API）。
- **潜意识层（Subconscious）**：后台引擎——跨会话模式识别、联想、凝缩、遗忘、梦境，输出**不阻塞**主流程的 whisper。

NEKO 映射：意识 = 主插件 `@plugin_entry`/`@llm_tool`；前意识 = `self.bus`/`self.store` 知识；潜意识 = `@timer_interval` 后台任务 + `push_message` 注入。

## 2. 五阶段记忆管道（subconscious.py / consolidator.py 真实逻辑）

1. **编码（Encode）**：transcript → 结构化记忆片段，附 `importance` 0.0–1.0。
2. **联想（Associate）**：新记忆 ↔ 历史记忆做语义匹配，建关联图（因果/相似/对比）。
3. **凝缩（Condense）**：`condense(min_cluster=3)` —— 同类聚类 **≥3 条才压缩**为一条抽象 insight，丢弃个案特例。两种聚类：按标签重叠、`strength≥0.5` 强关联做连通分量 DFS。
4. **固化（Consolidate）**：被引用记忆 +0.1（reference boost），未被引用 -5%（decay 0.05），低于阈值 0.1 **归档（永不删除，只归档）**。
5. **预注入（Pre-inject）**：选 ≤3 条最高相关记忆，打包 whisper，每条 ≤80 字，下次会话开始注入。

`dream_process()`（空闲触发）：放宽阈值 `min_cluster=2`、提取程序记忆、跑 `forget_scan()`。

## 3. 三类记忆结构

- **情景（Episodic）**：`{time, project, context, key_decision, outcome, importance}` —— 具体事件。
- **语义（Semantic）**：`{concept, domain, definition, related_semantic_ids, source_episodic_ids}` —— 抽象知识。
- **程序（Procedural）**：`{pattern_name, trigger_conditions, action_flow, frequency, confidence}` —— 行为模式 / "你上次也这样"。

## 4. Whisper 铁律：话痨是潜意识的天敌

- 只在真有话说时开口；每条必含三要素：**信号来源 / 联想关系 / 具体建议**。
- 格式：`⚡ [subconscious whisper] 源：{类型}#{ID} 因：{关系} 提：{可操作建议}`。
- 注入频率上限：whisper 模式 3 条/次，dream 模式 1 条/次，off 模式 0。

## 5. 手动命令（→ 对应 `@ui.action`）

`/status` `/recall <关键词>` `/dream` `/forget <条件>` `/pin <ID>` `/off` `/whisper`。

## 6. 映射到 N.E.K.O 插件（store + 定时后台）

- 持久化：用 `self.store`（KV JSON）存 `mem_index` + 记忆条目；或用 `self.db`（SQLite）存三张表。
- 落盘：用 `@message`/`@on_event`/`@hook` 在会话关键节点调用 `encode()`。
- 后台整理：`@timer_interval`（必须 async def）跑 `dream_process()` 做凝缩+遗忘。
- 注入：`push_message(visibility=["chat"], ai_behavior="blind", ...)` 在空闲时以 whisper 形式主动提示（类似"主动聊天"）。
- 手动控制：`@ui.action` 暴露 recall/dream/forget/pin/reset，对应第 5 节命令。

## 7. 可抄骨架（最小记忆插件）

```python
@neko_plugin
class MemoryPlugin(NekoPluginBase):
    def __init__(self, ctx):
        super().__init__(ctx)
        self._idx: dict = {}      # id -> {type, importance, archived, tags, summary}
        self._lock = threading.Lock()

    @lifecycle(id="startup")
    async def on_startup(self, **_):
        # store.get 返回 Result，必须 unwrap_or；第二个参数不是默认值
        raw = unwrap_or(await self.store.get("mem_index"), "{}")
        self._idx = json.loads(raw) if isinstance(raw, str) else (raw or {})
        return Ok({"status": "ready"})

    async def _save_index(self):
        # store.set 是协程，必须 await（见 35-store-database-internals）
        await self.store.set("mem_index", json.dumps(self._idx))

    async def _encode(self, text, tags, mtype="episodic"):
        mid = f"{mtype}-{uuid.uuid4().hex[:8]}"
        with self._lock:
            self._idx[mid] = {"type": mtype, "importance": 0.6,
                              "tags": tags, "summary": text[:200], "archived": False}
        await self._save_index()
        return mid

    def _consolidate(self):
        # 纯 CPU 计算，交给 asyncio.to_thread；不要在同步函数里 await
        by_tag: dict[str, list[str]] = {}
        for mid, e in self._idx.items():
            if e["archived"]:
                continue
            for t in e["tags"]:
                by_tag.setdefault(t, []).append(mid)
        insights = []
        for t, ids in by_tag.items():
            if len(ids) >= 3:
                insights.append(f"[凝缩:{t}] {len(ids)} 条同类 → 抽象策略")
        for mid, e in self._idx.items():
            if not e["archived"]:
                e["importance"] = max(0.0, e["importance"] - 0.05)
                if e["importance"] < 0.1:
                    e["archived"] = True
        return insights

    @timer_interval(id="dream", seconds=3600, name="梦境整理", auto_start=True)
    async def _dream(self, **_):
        insights = await asyncio.to_thread(self._consolidate)   # 不阻塞事件循环
        await self._save_index()                                # 落盘在 async 侧
        if insights:
            self.ctx.push_message(
                source="memory", visibility=["chat"], ai_behavior="blind",
                parts=[{"type": "text", "text": "⚡ " + insights[0][:80]}],
                priority=2,
            )
        return Ok({"status": "dreamed"})

    @ui.action(id="recall")
    @plugin_entry(id="recall", name="回忆", description="按关键词检索记忆")
    async def recall(self, keyword: str = "", **_):
        hits = [m for m, e in self._idx.items()
                if not e["archived"] and keyword in " ".join(e["tags"])]
        return Ok({"hits": hits[:10]})

    @ui.action(id="reset_memory")
    @plugin_entry(id="reset_memory", name="重置记忆", description="清空记忆索引")
    async def reset(self, **_):
        self._idx = {}
        await self._save_index()
        return Ok({"status": "reset"})
```

要点：状态用 `self.store` 跨会话留存（35 篇），后台整理用 `@timer_interval`+`to_thread`（10 篇），主动注入用 `push_message`（11/30 篇）。

## 8. 反模式（从源码反推）

- ❌ 主流程里同步做重聚类（阻塞）→ 必须后台/线程。
- ❌ 把低分记忆直接 `del`（永不删除，只归档，便于误删回溯）。
- ❌ whisper 长篇大论（≤80 字，宁少勿滥）。
- ❌ 凝缩阈值 <3（过早抽象丢掉信号）。
