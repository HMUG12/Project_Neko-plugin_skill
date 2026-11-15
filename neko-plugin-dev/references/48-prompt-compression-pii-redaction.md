# 48 · 提示词压缩与 PII 脱敏（来自 token-saviour + prompthakcer）

> 逆向自 vagkaratzas/token-saviour（token 成本模型）与 haKC-ai/prompthakcer（Chrome 扩展，正则规则引擎）。要点：4 层 token 成本模型（优化"输入层"才是大头）、正则提示词压缩（省 15–70%）、本地 PII/DLP 红挡。映射到 N.E.K.O 插件"发往外发 LLM/API 前先压缩再脱敏"。

## 1. 4 层 Token 成本模型（token-saviour：输入才是账单大头）

| 图层 | 含义 | 首选 | 忌用 |
|------|------|------|------|
| 代码读取 | 理解代码/调用路径 | 语义检索 | 整文件 dump |
| 命令输出 | 嘈杂 stdout | 摘要化输出 | 原始全文 |
| 散文输出 | 长篇解释 | 精简模式 | — |
| 代码输出 | 写代码 | YAGNI 最小代码 | 过度抽象 |

**核心结论**：~88% 的 token 消耗在"输入"（过度阅读/上下文），不是输出。插件设计启示：

- 用**语义检索**代替整文件塞上下文；
- 上下文**缓存 + 去重**（见 47）；
- 用户给的冗长 prompt **先压缩再发**外部 LLM。

## 2. 正则提示词压缩（prompthakcer rules-engine.js，CARE/CRAFT 框架，5 档）

规则类别（`analyze()` 顺序应用，返回优化文本 + token 节省统计）：

- **fluff**：删客套话（"Could you please help me" → ""）、冗余问候。
- **redundancy**：删重复表述。
- **verbosity**：长句压缩（"in order to" → "to"）。
- **qualifiers**：删填充词（just / really / simply / basically）。
- **structure / formatting / compression**：整合结构、清标点。
- 5 级强度：Light 15–25% → Medium → Heavy → Maximum 50–70%。
- 远程 `rules.json`（1h 缓存）+ 本地 `FALLBACK_RULES`（仅空白/标点修复，不依赖网络）。

**注意**：引擎对规则是"无感知纯文本转换"，不区分安全威胁；压缩只动自然语言，别碰 JSON/代码块（由调用方保证按代码特征跳过）。

## 3. 本地 PII / DLP 红挡（prompthakcer security 类别，100% 本地）

发往外发 LLM/API **之前**先做本地正则脱敏，**降低**敏感串外发风险（注意：正则脱敏**非完备**，只是降低概率，不是"绝不泄露"的保证）：

| 敏感类型 | 正则（示意） | 替换 |
|---------|------------|------|
| 信用卡 | `\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b` | `[REDACTED-CARD]` |
| 邮箱 | `\b[\w.+-]+@[\w-]+\.[\w.-]+\b` | `[REDACTED-EMAIL]` |
| SSN | `\b\d{3}-\d{2}-\d{4}\b` | `[REDACTED-SSN]` |
| OpenAI 风格 Key | `\bsk-[A-Za-z0-9_-]{16,}\b` | `[REDACTED-KEY]` |
| 通用 API Key/Ticket | `(?i)\b(api[_-]?key|token\|secret\|bearer)\b\s*[:=]\s*["']?[A-Za-z0-9_\-\.]{16,}` | `[REDACTED-KEY]` |

> **覆盖面声明**：以上规则只能命中**常见格式**。自定义格式的密钥、拆分/编码后的敏感串、非英文语境下的身份证号、银行卡带分隔符变体等**都可能漏过**。因此：① 不要把"已脱敏"当作"可以随便外发"；② 源头减少敏感数据进入 prompt 才是根本。

全部本地处理，提示词不出设备；可配置开关 + 自定义正则。

## 4. 映射到 N.E.K.O 插件（外发前深函数）

在调外部 LLM/API（如 42 的 firecrawl、47 的路由、或任意 `@llm_tool` 内）**之前**，跑：

```python
import re

class PromptHygiene:
    # 顺序即优先级：先挡更具体的（Key），再挡通用模式
    _PII = [
        (r"\bsk-[A-Za-z0-9_-]{16,}\b", "[REDACTED-KEY]"),
        (r"(?i)\b(api[_-]?key|token|secret|bearer)\b\s*[:=]\s*[\"']?[A-Za-z0-9_\-\.]{16,}", "[REDACTED-KEY]"),
        (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "[REDACTED-CARD]"),
        (r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", "[REDACTED-EMAIL]"),
        (r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED-SSN]"),
    ]
    # 客套/填充词压缩（Light 级别，保守）
    _FLUFF = [
        (r"(?i)\bcould you (please )?(help|tell|show|give)\b", ""),
        (r"(?i)\bplease\b", ""),
        (r"(?i)\bjust\b|\breally\b|\bsimply\b|\bbasically\b", ""),
        (r"(?i)\bin order to\b", "to"),
    ]

    def __init__(self, enable_redact=True, enable_compress=False):
        self.enable_redact = enable_redact
        self.enable_compress = enable_compress

    def transform(self, text: str) -> str:
        # 1. 先脱敏：降低外发风险（正则非完备，不等于"已安全"）
        if self.enable_redact:
            for pat, rep in self._PII:
                text = re.sub(pat, rep, text)
        # 2. 再压缩（仅自然语言）
        if self.enable_compress:
            for pat, rep in self._FLUFF:
                text = re.sub(pat, rep, text)
            text = re.sub(r"\s{2,}", " ", text).strip()
        return text
```

配合 `self.config`（SettingsField toggle）：`prompt_compress`、`pii_redact`，**默认脱敏开、压缩关**（压缩可能影响指令准确性，留给用户选）。

## 5. 反模式

- ❌ 把压缩用在结构化输入（JSON schema / 代码）→ 破坏格式。压缩只面向用户自然语言 prompt。
- ❌ 脱敏依赖远程服务（必须本地正则，否则敏感串先出站再回来已泄露）。
- ❌ 把"已跑正则脱敏"当作"可以放心外发"——覆盖面有限，漏网敏感串仍然存在（见 §3 覆盖面声明）。
- ❌ 忽视"输入层"优化，只在输出上抠 token（账单大头在输入，见 §1）。
- ❌ 把 prompthakcer 当注入防御用——它就是文本转换，**无注入检测**（注入防御见 43 + 47 的 prompt_guard）。
