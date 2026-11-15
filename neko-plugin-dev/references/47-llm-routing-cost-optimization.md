# 47 · LLM 路由与成本优化（来自 NadirClaw + llm-router）

> 逆向自 NadirRouter/NadirClaw（Python，LLM 路由器/优化器）与 timholm/llm-router（Go，成本优化反向代理）。要点：复杂度分类路由、验证器门控级联（cheap→verify→escalate）、语义缓存、飞行中去重、健康感知后端。映射到 N.E.K.O 做"智能 LLM 路由插件"。

## 1. 复杂度分类 → 三档模型（llm-router classifier.go 真实打分）

提取信号 → 加权 0–100 → 按阈值切三档：

| 信号 | 加分规则 | 上限 |
| 估算 token（char\*13/40） | <200:+5 / <1000:+15 / <4000:+25 / ≥4000:+35 | 35 |
| 对话轮数 | ≤2:+0 / ≤6:+8 / >6:+15 | 15 |
| 系统提示复杂度 | 有且>500:+10 / 有≤500:+5 | 10 |
| JSON 模式 | +10 | 10 |
| 工具调用 | +15 | 15 |
| 代码特征（```/func /def /class /import /SELECT） | +10 | 10 |
| 推理线索（step by step / analyze / pros and cons） | +15 | 15 |

`score ≤ Tier1Max→tier1（便宜）`；`≤ Tier2Max→tier2`；否则 tier3（强）。

NEKO 映射：`classify()` 纯函数，按 score 选 `self.config` 里配置的模型档；推理/代码/工具类请求自动升档。

## 2. 验证器门控级联（NadirClaw cascade.py）

**先调最便宜层 → 启发式验证器打分 → ≥阈值返回，否则升级到贵层。**

- `DEFAULT_ACCEPTANCE_THRESHOLD = 0.80`（启发式验证器弱，边界一律升级）。
- `KILL_SWITCH_THRESHOLD = 3`：连续 3 次验证器报错 → 熔断为"仅便宜层"。
- **Fail-open**：验证器任何异常 → 视为"接受"，直接返回便宜层答案，级联永不阻塞用户。
- 规则引擎 `set_threshold` 只能**抬高**阈值，不能降低；命中规则入审计日志。
- N 层级联：`adjacent`（逐层）或 `jump`（直跳顶层），受 `max_escalations` 限制。

NEKO 映射：封装为 `dispatch(cheap_fn, strong_fn, verifier)`，外部 SDK 调用塞进 `asyncio.to_thread`（10 篇）。

## 3. 语义缓存（零依赖，无需 embedding）

- NadirClaw：`SemanticCache` LRU + hash，TTL，线程安全。
- llm-router：`SemanticCache` 用 **Jaccard 相似度**（归一化词集合）替代嵌入：
  - `extractWords`：小写、非字母数字切分、过滤长度≤2 词 + 停用词（the/and/for…）。
  - `jaccardSimilarity(A,B)=|A∩B|/|A∪B|`；`similarityThresh=0.85`，`TTL=300s`，`maxSize=1000`，`sync.RWMutex` 读多写少，Put 时 LRU 淘汰最旧。
- 仅基于词面，无法捕捉同义改写（需 embedding sidecar 补充）。

NEKO 映射：用 `self.store` 或进程内 `dict` 存 `{hash: {words, response, model, ts}}`；命中返回缓存省 token/钱；按 TTL + LRU 淘汰。

## 4. 飞行中请求去重（llm-router dedup.go）

- `HashRequest`：只对**语义内容**（`messages`+`tools`+`response_format`）做 sha256，**排除** 临时字段（stream/temperature）。
- `Deduplicator.Do(key, fn)`：若同 key 已在飞行中 → 等待其 `done` channel（带 `window` 超时）；否则自己执行并把结果广播给等待者。
- 灵感来自 ParrotServe 请求合并。

NEKO 映射：用 `asyncio.Lock` + `dict[key: Future]` 合并并发相同请求，避免重复昂贵调用。

## 5. 健康感知后端池（llm-router README）

后端有 degraded/down 状态、负载均衡、延迟 EMA；分类失败时 **fail-closed** 落到最安全/最强档而非崩溃。

## 6. 顺带：NadirClaw 的提示注入守卫（详见 43 安全篇）

仅扫描 **user + tool** 角色（信任 system + assistant），7 类启发式模式，action=log/warn/block，边界 fail-safe。外发前 **PII 红挡**（见 48）。

## 7. 可抄骨架（分类 + 缓存 + 去重 + 级联）

```python
import asyncio, hashlib, json, re, time

class LLMRouter:
    def __init__(self, cfg):
        self.tiers = cfg["tiers"]            # {1: "cheap-model", 3: "strong-model"}
        self.cache: dict = {}                # hash -> (ts, words, resp)
        self.cache_ttl = cfg.get("cache_ttl", 300)
        self.sim_thresh = cfg.get("sim_thresh", 0.85)
        self._inflight: dict = {}            # key -> Future
        self._lock = asyncio.Lock()

    # ── 1. 复杂度分类（照抄 classifier.go 加权）──
    def classify(self, messages, tools, want_json) -> int:
        score = 0
        chars = sum(len(m.get("content", "")) for m in messages)
        est = chars * 13 // 40
        score += 35 if est >= 4000 else 25 if est >= 1000 else 15 if est >= 200 else 5
        score += 15 if len(messages) > 6 else 8 if len(messages) > 2 else 0
        sysmsg = next((m["content"] for m in messages if m.get("role") == "system"), "")
        score += 10 if len(sysmsg) > 500 else 5 if sysmsg else 0
        score += 10 if want_json else 0
        score += 15 if tools else 0
        blob = " ".join(m.get("content", "") for m in messages).lower()
        if re.search(r"```|func |def |class |import |select ", blob):
            score += 10
        if re.search(r"step by step|analyze|pros and cons|reason through", blob):
            score += 15
        return 1 if score <= 30 else 2 if score <= 60 else 3

    # ── 2. 语义缓存（Jaccard，零依赖）──
    @staticmethod
    def _words(text):
        return {w for w in re.split(r"\W+", text.lower()) if len(w) > 2}
    def _similar(self, a, b):
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)
    def _cache_get(self, messages):
        words = self._words(" ".join(m.get("content", "") for m in messages))
        now = time.time()
        for h, (ts, w, resp) in list(self.cache.items()):
            if now - ts > self.cache_ttl:
                self.cache.pop(h, None)
                continue
            if self._similar(words, w) >= self.sim_thresh:
                return resp
        return None
    def _cache_put(self, messages, resp):
        words = self._words(" ".join(m.get("content", "") for m in messages))
        h = hashlib.sha256(" ".join(m.get("content", "") for m in messages).encode()).hexdigest()[:16]
        self.cache[h] = (time.time(), words, resp)
        if len(self.cache) > 1000:            # 超量清最旧（LRU 近似）
            self.cache.pop(next(iter(self.cache)))

    # ── 3. 飞行中去重 ──
    def _key(self, messages, tools):
        canon = json.dumps({"m": messages, "t": tools}, sort_keys=True)
        return hashlib.sha256(canon.encode()).hexdigest()[:16]
    async def _dedup(self, key, fn):
        async with self._lock:
            fut = self._inflight.get(key)
            first = fut is None
            if first:
                fut = asyncio.get_event_loop().create_future()
                self._inflight[key] = fut
        if first:
            try:
                res = await fn()
                fut.set_result(res)
            except Exception as e:
                fut.set_exception(e)
            finally:
                self._inflight.pop(key, None)
            return await fut
        return await fut

    # ── 4. 级联分发（cheap → verify → escalate）──
    async def dispatch(self, messages, tools, call_llm):
        # call_llm(model, messages, tools) -> str，内部用 asyncio.to_thread 包同步 SDK
        cheap = self.tiers.get(1, self.tiers.get(3))
        strong = self.tiers.get(3, cheap)
        ans = await asyncio.to_thread(call_llm, cheap, messages, tools)
        if self._verify(ans) >= 0.80:        # 阈值边界一律升级
            return ans
        return await asyncio.to_thread(call_llm, strong, messages, tools)

    @staticmethod
    def _verify(text) -> float:
        # 启发式：非空且有一定长度即给高分；异常由调用方 fail-open
        return 0.9 if text and len(text) > 10 else 0.0
```

> 注意：生产用 `asyncio.Event` 实现去重更稳；此处只为展示"分类 / 缓存 / 去重 / 级联"四件套结构。

## 8. 反模式

- ❌ 所有请求都打最强模型（先用便宜层 + 验证升级，省 30–70% 成本）。
- ❌ 缓存 key 含 temperature/stream（同语义不同参数导致缓存失效）。
- ❌ 验证器异常时阻塞请求（必须 fail-open）。
- ❌ 把语义缓存当精确缓存（Jaccard 只捕词面，同义改写会 miss）。
