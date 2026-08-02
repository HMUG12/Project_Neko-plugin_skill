# 48 · 提示词压缩与 PII 脱敏（来自 token-saviour + prompthakcer）

> 逆向自 vagkaratzas/token-saviour（token 成本模型）与 haKC-ai/prompthakcer（Chrome 扩展，正则规则引擎）。要点：4 层 token 成本模型（优化"输入层"才是大头）、正则提示词压缩（省 15–70%）、本地 PII/DLP 红挡。映射到 N.E.K.O 插件"发往外发 LLM/API 前先压缩再脱敏"。

## 1. 4 层 Token 成本模型（token-saviour：输入才是账单大头）

| 图层 | 含义 | 首选 | 忌用 |
| 代码读取输入 | 理解代码/调用路径 | 语义检索 | 整文件 dump |
| 命令输出输入 | 嘈杂 stdout | 摘要化输出 | 原始全文 |
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

发往外发 LLM/API **之前**先正则脱敏，绝不把原始密钥/隐私送出去：

| 敏感类型 | 正则（示意） | 替换 |
| 信用卡 | `\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b` | `[REDACTED-CARD]` |
| 邮箱 | `\b[\w.+-]+@[\w-]+\.[\w.-]+\b` | `[REDACTED-EMAIL]` |
| SSN | `\b\d{3}-\d{2}-\d{4}\b` | `[REDACTED-SSN]` |
| API Key | `(sk\|api\|token\|key)[-_ ]?[A-Za-z0-9]{20,}`（示意） | `[REDACTED-KEY]` |

全部本地处理，提示词不出设备；可配置开关 + 自定义正则。

## 4. 映射到 N.E.K.O 插件（外发前深函数）

在调外部 LLM/API（如 42 的 firecrawl、47 的路由、或任意 `@llm_tool` 内）**之前**，跑：

```python
import re

class PromptHygiene:
    _PII = [
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
        # 1. 先脱敏（绝不外泄原始敏感串）
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
- ❌ 忽视"输入层"优化，只在输出上抠 token（账单大头在输入，见 §1）。
- ❌ 把 prompthakcer 当注入防御用——它就是文本转换，**无注入检测**（注入防御见 43 + 47 的 prompt_guard）。
