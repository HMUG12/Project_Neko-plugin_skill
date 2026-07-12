# 13. 云端 API 集成模式

> 基于 `ai_singer` 插件集成阿里云百炼 CosyVoice SDK 的实战经验。
> 涵盖第三方 SDK 初始化、端点配置、错误诊断、轮询等待、健康检查等通用模式。

---

## 13.1 适用场景

- 插件需要对接第三方云端 API（AI 模型、SaaS 服务、云平台等）
- 需要使用第三方 Python SDK（`dashscope`、`openai`、`boto3` 等）
- 需要处理 API 端点配置（workspace 专属域名、多地域支持）
- 需要在插件面板中实时显示云端连接状态

---

## 13.2 第三方 SDK 可选导入模式

插件依赖的第三方 SDK 可能未安装在用户环境中，需要优雅降级：

```python
# ✅ 正确：try/except 可选导入
try:
    import dashscope
    from dashscope.audio.tts_v2 import VoiceEnrollmentService, SpeechSynthesizer
    HAS_SDK = True
except ImportError:
    dashscope = None
    VoiceEnrollmentService = None
    SpeechSynthesizer = None
    HAS_SDK = False
```

**在 plugin.toml 中声明依赖**：
```toml
[plugin.dependencies]
python = ["dashscope>=1.20.0"]
```

**在所有 API 调用入口检查可用性**：
```python
async def create_voice(self, audio_url: str, prefix: str) -> tuple:
    if not HAS_SDK:
        return False, "", "dashscope SDK 未安装，请执行: pip install dashscope"
    if not self.api_key:
        return False, "", "API Key 未配置"
    if not self.workspace_id:
        return False, "", "Workspace ID 未配置"
    # 每次调用前重新初始化端点（配置可能已变更）
    self._init_dashscope()
    # ... 实际调用
```

**要点**：
- 每次 API 调用前都做 `_init_sdk()` 以确保端点是最新的
- 检查项按优先级排序：SDK 可用 → API Key → 其他必需参数
- 返回 `tuple` 格式便于上层统一处理：`(success, result, error_message)`

---

## 13.3 端点配置模式（Workspace / 多租户）

### 问题背景

部分云平台使用 workspace（业务空间/租户）概念，要求 API 调用通过专属域名端点。例如阿里云百炼 CosyVoice：
- 标准端点 `dashscope.aliyuncs.com` 不支持声音复刻 API
- 必须使用 workspace 专属端点 `{workspace_id}.{region}.maas.aliyuncs.com`

### 配置结构

```python
class CloudBackend:
    """云端后端封装类，管理 SDK 初始化、端点配置和所有 API 调用"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._log = config.get("_log", lambda msg: None)
        self._init_sdk()

    def _init_sdk(self):
        """初始化 SDK 全局配置

        关键：每次 API 调用前都应调用此方法，因为配置可能在运行时变更。
        """
        if not HAS_SDK:
            self._log("[Backend] SDK 未安装")
            return

        ws = self.workspace_id
        r = self.region

        # API Key 始终设置
        external_sdk.api_key = self.api_key

        if ws and r:
            # 两者都使用 Workspace 专属端点
            external_sdk.base_http_api_url = (
                f"https://{ws}.{r}.maas.aliyuncs.com/api/v1"
            )
            external_sdk.base_websocket_api_url = (
                f"wss://{ws}.{r}.maas.aliyuncs.com/api-ws/v1/inference"
            )
        else:
            self._log("[Backend] Workspace ID 或 Region 为空，使用默认端点")

    # 配置项通过 property 从 config 读取，支持运行时更新
    @property
    def api_key(self) -> str:
        return self.config.get("api_key", "")

    @property
    def workspace_id(self) -> str:
        return self.config.get("workspace_id", "")

    @property
    def region(self) -> str:
        return self.config.get("region", "cn-beijing")
```

**关键教训**：

1. **不要假设标准域名支持所有功能**。先用官方文档确认你的 API 调用需要什么端点。
2. **SDK 的 `workspace` 参数 vs URL 子域名**：部分 SDK 同时支持两种方式传递 workspace 信息，但官方推荐 URL 子域名方式，因为它不需要额外 header。
3. **不要在构造时固化端点**。在 `__init__` 中调用 `_init_sdk()` 建立初始配置，在每次 API 调用前也调用一次，因为 `save_api_config` 可能更新了配置但未重新构造 backend 对象。
4. **日志记录当前端点**：出问题时能快速确认实际请求的目标 URL。

### 错误排查流程

```python
# 记录端点信息便于排查
self._log(f"[Backend] endpoint: base_http={sdk.base_http_api_url}, workspace={self.workspace_id}")
```

常见错误及诊断：

| 错误 | HTTP 码 | 含义 | 排查方向 |
|------|---------|------|---------|
| `IllegalEndpoint` | 400 | 端点格式无效 | workspace ID 格式（应为 `ws-xxx`）、region 是否正确 |
| `AccessDenied` | 403 | 无权限访问 | API Key 是否属于该 workspace、workspace 是否开通服务 |
| `InvalidApiKey` | 401 | Key 无效 | Key 是否正确、是否已过期 |

---

## 13.4 多级错误诊断模式

云端 API 的错误信息通常很技术化，直接展示给用户无意义。需要在每个调用点做**模式匹配 + 针对性提示**：

```python
try:
    result = service.create_voice(target_model=self.model, prefix=prefix, url=url)
except Exception as e:
    err_str = str(e)

    # 模式匹配：识别已知错误类型
    if "IllegalEndpoint" in err_str or "Workspace endpoint is invalid" in err_str:
        return False, "", (
            f"Workspace 端点无效。\n"
            f"当前配置：workspace={self.workspace_id}, region={self.region}\n"
            f"端点 URL：{sdk.base_http_api_url}\n\n"
            "请检查：\n"
            "1. Workspace ID 是否正确（控制台 → 业务空间，格式 ws-xxxxxxxxxxxxx）\n"
            "2. API Key 的地域是否与 Region 一致\n"
            "3. 该业务空间是否已开通相关服务"
        )

    if "AccessDenied" in err_str or "403" in err_str:
        return False, "", (
            f"Workspace 访问被拒绝 (403)。\n"
            f"当前配置：workspace={self.workspace_id}, region={self.region}\n\n"
            "请检查：\n"
            "1. API Key 是否在【当前业务空间】中创建（非主账号或其它空间）\n"
            "2. 前往控制台 → 业务空间 → API-KEY 管理，确认 Key 属于本空间\n"
            "3. 确认该业务空间已开通相关服务"
        )

    # 兜底：返回原始错误
    return False, "", f"创建失败: {err_str}"
```

**设计原则**：

1. **错误消息三要素**（来自 AI 友好设计）：发生了什么 + 为什么 + 怎么做
2. **包含当前配置上下文**：让用户能自我检查配置是否正确
3. **给出具体操作指引**：告诉用户去哪里、怎么操作，而非"请检查配置"
4. **兜底返回原始错误**：未知错误保留原文便于排查

---

## 13.5 健康检查模式

插件需要在多处判断云端连接状态（设置面板、主面板、AI 入口），统一健康检查方法：

```python
async def health_check(self) -> tuple:
    """返回 (ok: bool, message: str)"""
    if not HAS_SDK:
        return False, "SDK 未安装"
    if not self.api_key:
        return False, "API Key 未配置"
    if not self.workspace_id:
        return False, "Workspace ID 未配置"

    self._init_sdk()
    try:
        service = self._make_service()
        # 使用轻量 API 验证连接（如 list 操作，而非创建操作）
        items = service.list_items(page_index=0, page_size=1)
        count = len(items) if isinstance(items, list) else 0
        return True, f"已连接 @ {self.region}（{count} 个资源）"
    except Exception as e:
        err_str = str(e)
        # 同样做模式匹配
        if "IllegalEndpoint" in err_str:
            return False, f"端点无效，请检查 Workspace ID 和 Region"
        if "AccessDenied" in err_str:
            return False, f"访问被拒绝（403），请确认 API Key 属于当前空间"
        return False, f"连接失败: {err_str}"
```

**健康检查的调用时机**：

| 位置 | 目的 | 备注 |
|------|------|------|
| `on_startup` | 启动时检测云端状态 | 结果记入日志 |
| `provide_dashboard` / `provide_settings` context | UI 面板展示连接状态 | 每次面板刷新时调用 |
| `check_setup` AI 入口 | 前置检查，告知 AI 是否可用 | 结果影响 AI 后续行为 |
| `save_api_config` 保存后 | 验证新配置是否有效 | **关键**：保存后立即验证，避免用户误以为"已可用" |
| 定时器 | 定期检测（如每 5 分钟） | 检测服务可用性变化 |

---

## 13.6 保存后立即验证模式

这是从 ai_singer 开发中提炼出的**最重要教训**：

```python
@ui.action(label="💾 保存配置", refresh_context=True)
async def save_api_config(self, config: dict = None, **_):
    # 1. 更新配置
    self._config["api_key"] = config.get("api_key", "")
    # ...

    # 2. 持久化到 settings 系统
    await self.ctx.update_own_config({"settings": new_settings})

    # 3. 重新初始化后端（端点可能变了）
    self._init_backend()

    # 4. ⚠️ 关键：保存后立即做健康检查！
    cv_ok, cv_msg = await self._backend.health_check()

    if not cv_ok:
        return Ok({
            "success": True,
            "cosyvoice_ok": False,
            "message": f"配置已保存，但云端连接失败: {cv_msg}",
            "warning": cv_msg,
        })

    return Ok({
        "success": True,
        "cosyvoice_ok": True,
        "message": "配置已保存，云端连接正常",
    })
```

**UI 端处理**：
```tsx
<ActionButton
  action={saveAction}
  values={{ config: buildConfig() }}
  onResult={(result) => {
    const r = result as { cosyvoice_ok?: boolean; warning?: string }
    if (r?.cosyvoice_ok === false) {
      alert("⚠️ 配置已保存，但云端连接失败！\n\n" + r.warning)
    } else {
      alert("✅ 配置已保存！")
    }
  }}
>
  保存配置
</ActionButton>
```

**为什么这很重要**：

- 用户填写完 API Key → 点击保存 → 看到"保存成功" → 以为一切就绪
- 切到主面板 → 显示"不可用" → 困惑："刚才明明显示可用的啊？"
- **根本原因**：保存操作只验证了"写入成功"，没有验证"配置是否正确"
- **解决方案**：保存后立即调用健康检查，在返回值中明确告知真实连接状态

---

## 13.7 Backend 对象模式

将云端 API 调用逻辑封装为独立的 Backend 类，与插件主类解耦：

```python
class CloudBackend:
    """云端后端 — 封装所有第三方 SDK 调用逻辑"""

    name = "my_service"
    display_name = "我的云服务"

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._log = config.get("_log", lambda msg: None)
        self._cache: Dict[str, str] = {}
        self._init_sdk()

    # --- SDK 初始化 ---
    def _init_sdk(self): ...

    # --- 配置属性 ---
    @property
    def api_key(self) -> str: ...
    @property
    def model(self) -> str: ...

    # --- 业务 API ---
    async def create_resource(self, ...) -> tuple: ...
    async def list_resources(self) -> list: ...
    async def delete_resource(self, id: str) -> bool: ...

    # --- 健康检查 ---
    async def health_check(self) -> tuple: ...

    # --- 清理 ---
    async def close(self): ...
```

**插件主类中创建和管理 Backend**：

```python
class MyPlugin(NekoPluginBase):
    def __init__(self, ctx):
        super().__init__(ctx)
        self._config: Dict[str, Any] = {}
        self._backend: Optional[CloudBackend] = None

    def _init_backend(self):
        """重新创建 Backend（配置变更时调用）"""
        cfg = {
            **self._config,
            "_log": lambda msg: self.logger.info(msg),
            "_data_path": lambda p: str(self.data_path(p)),
        }
        old = self._backend
        self._backend = CloudBackend(cfg)
        # 异步关闭旧 backend（如有关闭连接的逻辑）
        if old:
            asyncio.create_task(old.close())
```

**Backend 模式的好处**：

1. **职责分离**：插件主类管生命周期/配置/路由，Backend 管 SDK 调用
2. **可测试**：Backend 可独立测试，不依赖 N.E.K.O 运行时
3. **可替换**：未来换服务商只需替换 Backend 类，主类不变
4. **日志注入**：通过 `_log` 回调将 Backend 日志接入插件日志系统

---

## 13.8 轮询等待模式

部分云端 API 是异步的（提交任务 → 轮询结果），如声音克隆：

```python
async def create_and_wait(self, input_data, prefix: str) -> tuple:
    """提交异步任务并轮询等待完成"""
    # 1. 提交
    try:
        result_id = service.create_task(target_model=self.model, prefix=prefix, data=input_data)
        self._log(f"[Backend] 提交成功, task_id={result_id}")
    except Exception as e:
        return self._diagnose_error(e)

    # 2. 轮询
    max_attempts = 30       # 最大轮询次数
    poll_interval = 10      # 每次间隔（秒）
    for attempt in range(max_attempts):
        try:
            task_info = service.query_task(task_id=result_id)
            status = task_info.get("status", "")
            self._log(f"[Backend] 轮询 {attempt+1}/{max_attempts}: status={status}")

            if status == "OK":
                self._cache[prefix] = result_id
                return True, result_id, ""

            elif status == "FAILED":
                return False, "", f"任务失败: {task_info.get('error', '未知错误')}"

            await asyncio.sleep(poll_interval)

        except Exception as e:
            self._log(f"[Backend] 轮询异常: {e}")
            await asyncio.sleep(poll_interval)

    return False, "", "轮询超时，任务未能完成"
```

**轮询设计要点**：

1. **设定上限**：防止无限等待
2. **记录日志**：每次轮询记录状态，便于排查超时问题
3. **区分终态**：OK（成功）、FAILED（失败）、UNDEPLOYED（处理失败）等
4. **异常不中断轮询**：单次轮询异常继续等待，避免网络抖动导致失败
5. **使用 `asyncio.sleep`**：不阻塞事件循环

---

## 13.9 plugin.toml 配置项设计

```toml
# 云端配置项
[settings]
api_key = ""
workspace_id = ""
region = "cn-beijing"
model = "default-model"
speech_rate = 1.0
pitch_rate = 1.0

[plugin.dependencies]
python = ["your-sdk>=1.0.0"]
```

**配置项设计原则**：

1. **敏感信息用空字符串**：API Key 等默认为空
2. **提供合理默认值**：region、model 等给默认值减少用户配置负担
3. **声明 Python 依赖**：让 N.E.K.O 能在安装时提示用户
4. **数值型配置注意默认值**：0 是有效值还是"未设置"要区分

---

## 13.10 检查清单

- [ ] 第三方 SDK 用 try/except 导入，设置 `HAS_SDK` 标志
- [ ] plugin.toml 中 `[plugin.dependencies]` 声明 Python 依赖
- [ ] 每个 API 调用前检查 SDK 可用、API Key 存在
- [ ] Backend 封装为独立类，与插件主类解耦
- [ ] `_init_sdk()` 在每次 API 调用前调用（配置可能已变）
- [ ] 错误处理用模式匹配给出针对性指引
- [ ] 错误消息包含当前配置上下文
- [ ] 健康检查方法返回 `(bool, str)` 元组
- [ ] `save_api_config` 保存后立即做健康检查
- [ ] 健康检查结果在返回值中明确传递（`cosyvoice_ok` / `connected` 等字段）
- [ ] UI 端根据健康检查结果区分成功/失败提示
- [ ] 轮询操作设上限 + 日志 + 区分终态
- [ ] 异步任务用 `asyncio.sleep` 不阻塞事件循环
- [ ] 旧 Backend 对象异步关闭（`asyncio.create_task(old.close())`）
