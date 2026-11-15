# 后端对象设计模式

> 基于 `ai_singer` 插件的 CosyVoiceBackend / MiMoTTSBackend 完整设计提取。涵盖 Backend 对象的生命周期、配置传播、健康检查、同步/异步桥接。

---

## 一、Backend 对象模式概述

当一个插件需要对接外部 API/服务时，推荐创建一个独立的 Backend 类来封装所有相关逻辑：

```
Plugin 类
  ├── _init_backend()     ← 工厂方法
  ├── _mimo: MiMoTTSBackend   ← 后端实例
  └── sing() / check_setup()  ← 使用后端的入口点

MiMoTTSBackend 类
  ├── __init__(config)         ← 接收配置字典
  ├── health_check()           ← 连通性检查
  ├── synthesize()             ← 核心业务方法
  └── _log()                   ← 日志代理
```

**好处**：
- 插件类保持简洁（只做编排）
- Backend 可以独立测试
- 更换后端只需替换 Backend 类

---

## 二、Backend 类设计模板

```python
class MiMoTTSBackend:
    """MiMo TTS 后端封装。"""

    def __init__(self, config: dict):
        # 1. 从配置中提取所需参数
        self.api_key = config.get("mimo_api_key", "")
        self.base_url = config.get("mimo_base_url", "https://api.xiaomimimo.com/v1")
        self.voice = config.get("mimo_voice", "冰糖")
        self.enabled = config.get("mimo_enabled", True)

        # 2. 保存日志代理
        self._log = config.get("_log", lambda msg: None)

        # 3. 初始化客户端（惰性）
        self._client = None

    # ========== 健康检查 ==========

    async def health_check(self) -> tuple[bool, str]:
        """检查后端是否可用。返回 (可用, 消息)。"""
        if not self.api_key:
            return False, "MiMo API Key 未配置"
        if not self.enabled:
            return False, "MiMo 后端已禁用"

        try:
            client = self._get_client()
            # 发起一个最小请求验证连通性
            models = await asyncio.to_thread(client.models.list)
            return True, ""
        except Exception as e:
            return False, f"MiMo 连接失败：{e}"

    # ========== 核心业务 ==========

    async def synthesize(self, text: str, voice: str = None,
                         context: str = None, output_path: str = None
                         ) -> bytes:
        """将文本合成为语音。返回音频字节。"""
        voice = voice or self.voice
        client = self._get_client()

        # 同步调用 → asyncio.to_thread
        audio_bytes = await asyncio.to_thread(
            self._synthesize_sync, text, voice, context
        )

        # 可选：保存到文件
        if output_path:
            await asyncio.to_thread(self._save_audio, audio_bytes, output_path)

        return audio_bytes

    # ========== 私有方法 ==========

    def _get_client(self):
        """惰性初始化客户端。"""
        if self._client is None:
            import openai
            self._client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._client

    def _synthesize_sync(self, text: str, voice: str, context: str) -> bytes:
        """同步 TTS 调用（在线程池中执行）。"""
        # ... 实际的 API 调用 ...
        pass

    def _save_audio(self, audio_bytes: bytes, path: str):
        """保存音频到磁盘。"""
        with open(path, "wb") as f:
            f.write(audio_bytes)
```

---

## 三、配置传播模式

### 3.1 _log lambda 注入

> 来源：`ai_singer/__init__.py` L520-522

```python
def _init_backend(self):
    """创建后端实例，注入日志代理。"""
    cfg = {**self._config, "_log": lambda msg: self.logger.info(msg)}
    self._mimo = MiMoTTSBackend(cfg)
```

**为什么用 lambda**：
- Backend 不直接依赖 N.E.K.O 的 `self.logger`
- 通过 `_log` 回调，Backend 可以独立于 N.E.K.O 运行（方便测试）
- 所有 Backend 日志统一通过插件的 logger 输出

### 3.2 配置来源合并

```python
DEFAULT_CONFIG = {
    "mimo_api_key": "",
    "mimo_base_url": "https://api.xiaomimimo.com/v1",
    "mimo_voice": "冰糖",
}

async def on_startup(self, **_):
    # 1. 加载持久化配置
    cfg = await self.config.dump()
    settings = cfg.get("settings", {})

    # 2. 合并：DEFAULT_CONFIG 作为基线，settings 覆盖
    for key in self.DEFAULT_CONFIG:
        if key in settings:
            self._config[key] = settings[key]

    # 3. 初始化后端
    self._init_backend()
```

**合并策略**：
- `DEFAULT_CONFIG` → 硬编码默认值
- `settings`（持久化） → 用户修改过的值
- 只覆盖存在的 key，不引入未知配置

---

## 四、健康检查模式

### 4.1 返回格式

```python
async def health_check(self) -> tuple[bool, str]:
    """
    返回：
        (True, "")          → 一切正常
        (False, "原因")     → 不可用，附带原因
    """
```

**为什么用 tuple 而非 dict**：
- 调用方可以直接解包：`ok, msg = await backend.health_check()`
- 两个字段足够表达所有状态
- 避免 `result["ok"]` 的字典访问开销

### 4.2 调用时机

```
1. 启动时（on_startup）          → 记录日志，不阻塞
2. 配置保存后（save_api_config）  → 即时反馈给用户
3. 定时检查（timer_interval）    → 每 N 分钟
4. 核心操作前（sing 入口）       → 快速检查，避免无意义调用
```

### 4.3 健康检查的检查项

```python
async def health_check(self) -> tuple[bool, str]:
    # 1. 配置完整性
    if not self.api_key:
        return False, "API Key 未配置"

    # 2. 功能开关
    if not self.enabled:
        return False, "后端已禁用"

    # 3. 网络连通性
    try:
        await self._ping()
    except ConnectionError:
        return False, "无法连接到 API 端点"

    # 4. 认证有效性
    try:
        await self._verify_auth()
    except AuthError:
        return False, "API Key 无效或已过期"

    # 5. 配额/限流
    try:
        await self._check_quota()
    except QuotaError:
        return False, "API 配额已用完"

    return True, ""
```

---

## 五、同步/异步桥接模式

### 5.1 asyncio.to_thread 包装

当第三方 SDK 只提供同步接口时：

```python
# ❌ 错误：在 async 方法中直接调用同步阻塞方法
async def synthesize(self, text):
    client = openai.OpenAI(...)
    return client.audio.speech.create(...)  # 阻塞事件循环！

# ✅ 正确：通过 asyncio.to_thread 放到线程池
async def synthesize(self, text):
    client = self._get_client()
    return await asyncio.to_thread(
        lambda: client.audio.speech.create(
            model="tts-1",
            voice=self.voice,
            input=text,
        )
    )
```

### 5.2 文件 I/O 的 asyncio.to_thread

```python
# 写入
await asyncio.to_thread(self._merge_wav_files, wav_paths, output_path)

# 读取
data = await asyncio.to_thread(lambda: open(path, "rb").read())

# 删除
await asyncio.to_thread(os.remove, target_path)
```

### 5.3 定时器中的桥接

> 详见 [24-error-handling-patterns.md §2.6](24-error-handling-patterns.md)

---

## 六、多后端共存模式

当一个插件需要对接多个后端时：

```python
class AiSingerPlugin(NekoPlugin):
    def _init_backends(self):
        cfg = {**self._config, "_log": lambda msg: self.logger.info(msg)}
        self._mimo = MiMoTTSBackend(cfg)
        # 可扩展：self._cosyvoice = CosyVoiceBackend(cfg)

    async def health_check_all(self):
        results = {}
        mimo_ok, mimo_msg = await self._mimo.health_check()
        results["mimo"] = {"ok": mimo_ok, "msg": mimo_msg}
        return results
```

**后端切换策略**：
```python
async def synthesize(self, text, backend="mimo"):
    if backend == "mimo":
        return await self._mimo.synthesize(text)
    elif backend == "cosyvoice":
        return await self._cosyvoice.synthesize(text)
    raise ValueError(f"未知后端：{backend}")
```

---

## 七、Backend 对象设计检查清单

- [ ] Backend 通过 `__init__(config: dict)` 接收配置
- [ ] 配置参数从 dict 中用 `.get()` 读取，有默认值
- [ ] 日志通过注入的 `_log` lambda 输出
- [ ] 客户端惰性初始化（`_get_client()` 方法）
- [ ] 有 `health_check()` 方法返回 `(bool, str)`
- [ ] 同步 API 调用通过 `asyncio.to_thread` 桥接
- [ ] 文件 I/O 通过 `asyncio.to_thread` 执行
- [ ] Backend 类不依赖 N.E.K.O SDK（可独立测试）
- [ ] 多后端时使用统一的接口签名
