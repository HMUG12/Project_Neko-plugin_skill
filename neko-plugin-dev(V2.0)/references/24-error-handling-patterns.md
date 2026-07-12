# 错误处理与诊断模式大全

> 基于 `ai_singer` + `music_pusher` + `qq_auto_reply` 多插件实战提取。覆盖从 Python 后端到前端 UI 的完整错误处理链路。

---

## 一、核心原则

```
错误分三层：
1. 系统层 → 记录日志 + 通用错误消息（不暴露内部细节）
2. 业务层 → 诊断分析 + 修复建议（帮助用户自助解决）
3. UI 层   → 分层渲染（成功/降级/失败 各自有对应 UI）
```

---

## 二、Python 后端模式

### 2.1 惰性导入 + 错误缓存（不重复重试）

> 来源：`ai_singer/__init__.py` L20-56

当导入可能失败的第三方库时，缓存失败结果避免反复重试：

```python
_dashscope_module = None
_dashscope_import_error = None

def _get_dashscope():
    """惰性导入 dashscope，首次失败后缓存错误，不再重试。"""
    global _dashscope_module, _dashscope_import_error

    if _dashscope_module is not None:
        return _dashscope_module          # 已成功，直接返回

    if _dashscope_import_error is not None:
        raise ImportError(_dashscope_import_error)  # 已失败，重放错误

    try:
        import dashscope as _mod
        _dashscope_module = _mod
        return _mod
    except ImportError as e:
        _dashscope_import_error = str(e)
        raise
```

**为什么不用简单的 `try: import`？**
- 每次 import 都触发文件系统查找和可能的网络请求
- 在网络不可用时，缓存失败结果避免了在健康检查等循环中反复触发昂贵的 import 操作
- 错误消息被保存，后续调用可以获取相同的诊断信息

**适用场景**：任何 `try/except ImportError` 的第三方库导入。

---

### 2.2 多级错误诊断（关键字匹配 + 修复建议）

> 来源：`ai_singer/__init__.py` L199-222

捕获异常后，不直接返回原始错误，而是**按关键字分类并给出诊断步骤**：

```python
try:
    voice_id = service.clone_voice(...)
    return True, voice_id, ""
except Exception as e:
    err_str = str(e).lower()

    # 逐级匹配 → 分类诊断
    if "illegalendpoint" in err_str or "workspace endpoint is invalid" in err_str:
        return False, "", (
            f"Workspace 端点无效。\n"
            f"当前配置：workspace={self.workspace_id}, region={self.region}\n"
            f"端点 URL：{dashscope_mod.base_http_api_url}\n\n"
            "请检查：\n"
            "1. Workspace ID 是否正确（在阿里云控制台 → 业务空间 查看）\n"
            "2. API Key 的地域是否与 Region 一致\n"
            "3. 该业务空间是否已开通 CosyVoice 语音服务"
        )

    if "accessdenied" in err_str or "403" in err_str:
        return False, "", (
            "API Key 无权访问该资源。\n"
            f"请确认 API Key 归属的业务空间包含当前 workspace={self.workspace_id}"
        )

    # 兜底
    return False, "", f"未知错误：{e}"
```

**模式要点**：
- 每个错误分支返回 **(False, 空数据, 详细错误消息)**
- 错误消息包含**当前配置值**（workspace/region），方便用户对照检查
- 错误消息包含**可操作的步骤**（去控制台 → 查看某页面 → 确认某设置）
- 关键字匹配使用小写化 + `in` 运算符，覆盖驼峰/下划线变体

**诊断消息模板**：
```
{问题描述}。
当前配置：{key1}={val1}, {key2}={val2}

请检查：
1. {可操作步骤1}
2. {可操作步骤2}
3. {可操作步骤3}
```

---

### 2.3 轮询重试模式（带状态日志 + 特殊状态快速失败）

> 来源：`ai_singer/__init__.py` L224-248

```python
max_attempts = 30
poll_interval = 10  # 秒

for attempt in range(max_attempts):
    voice_info = service.query_voice(voice_id=voice_id)
    status = voice_info.get("status", "")

    self._log(f"[CosyVoice] 轮询 {attempt+1}/{max_attempts}: status={status}")

    if status == "OK":
        return True, voice_id, ""
    elif status == "UNDEPLOYED":
        # 特殊状态 → 立即失败，不继续等待
        return False, "", "音色处理失败（UNDEPLOYED），请检查音色名称是否有效"
    elif status == "FAILED":
        return False, "", f"音色处理失败：{voice_info.get('message', '未知原因')}"

    _time.sleep(poll_interval)

return False, "", f"轮询超时（{max_attempts * poll_interval}秒），音色未能就绪"
```

**模式要点**：
- 每个周期记录状态（方便调试）
- **不是所有状态都继续等待**：`UNDEPLOYED` / `FAILED` 等终态立即返回
- 超时消息包含实际等待时间
- `_time.sleep()` 而非 `asyncio.sleep()`（因为可能在同步上下文中）

---

### 2.4 Ok/Err 模式的分层返回

```python
# 成功
return Ok({"status": "ready", "mimo_ok": True})

# 业务错误（用户可修复）
return Err(code="SETUP_INCOMPLETE", message="请先在设置面板配置 MiMo API Key")

# 系统错误（需要开发者关注）
return Err(code="BACKEND_ERROR", message=f"MiMo 后端异常：{e}")
```

**code 字段设计原则**：
- 使用大写下划线格式：`SETUP_INCOMPLETE`, `BACKEND_ERROR`, `PERMISSION_DENIED`
- 前端可以按 code 做不同的 UI 渲染
- message 是给用户看的（中文），code 是给程序判断的

---

### 2.5 保存后即时验证（健康检查）

> 来源：`ai_singer/__init__.py` L1195-1210

用户保存配置后立即做连通性验证，而非等到下次调用时才发现问题：

```python
@plugin_entry(id="save_api_config", ...)
async def save_api_config(self, *, config: dict, _ctx=None):
    # 1. 保存配置
    new_settings = {**current_settings, **config}
    await self.ctx.update_own_config({"settings": new_settings})

    # 2. 重新初始化后端
    self._config.update(config)
    self._init_backend()

    # 3. 即时健康检查
    mimo_ok, mimo_msg = await self._mimo.health_check()

    return Ok({
        "saved": True,
        "mimo_ok": mimo_ok,
        "mimo_warning": mimo_msg if not mimo_ok else "",
    })
```

前端收到 `mimo_ok === false` 后弹窗警告，让用户立即知道配置有问题。

---

### 2.6 定时器中的异步健康检查

> 来源：`ai_singer/__init__.py` L1297-1313

`@timer_interval` 在独立线程中运行（非 async），需要创建独立事件循环：

```python
@timer_interval(id="backend_health_check", seconds=300, auto_start=True)
def _on_health_check(self, **_):
    """每 5 分钟检查后端连通性。在独立线程中运行。"""
    loop = asyncio.new_event_loop()
    try:
        mimo_ok, mimo_msg = loop.run_until_complete(self._mimo.health_check())
        return Ok({
            "mimo_ok": mimo_ok,
            "mimo_warning": mimo_msg if not mimo_ok else "",
        })
    finally:
        loop.close()
```

**关键点**：
- `new_event_loop()` + `run_until_complete()` + `close()` 三步
- `finally` 中确保 loop 被关闭（防止资源泄漏）
- 不要在定时器中直接 `await`（签名是 `def` 不是 `async def`）

---

## 三、前端 UI 模式

### 3.1 分层渲染（成功 / 降级 / 失败）

> 来源：`ai_singer/ui/panel.tsx` L432-491

```tsx
// 4 种渲染路径
if (result.success) {
    if (result.merged_audio_url && result.lyric_lines?.length > 0) {
        // 路径 1：完整成功 → LyricPlayer 播放器
        return <LyricPlayer audioUrl={result.merged_audio_url} lines={result.lyric_lines} />;
    }
    if (result.merged_audio_url) {
        // 路径 2：有音频但无歌词 → 降级到普通 audio 播放器
        return <audio src={result.merged_audio_url} controls />;
    }
    // 路径 3：成功但无音频 → 提示去历史记录查看
    return <Alert type="info">演唱完成，请在历史记录中查看</Alert>;
}
// 路径 4：失败
return <Alert type="error">演唱失败：{result.error}</Alert>;
```

**分层策略**：
```
完整成功（音频 + 歌词） → 最优体验
部分成功（音频但无歌词） → 降级体验（可用）
逻辑成功（数据已保存）   → 引导到其他入口
失败                    → 明确错误提示
```

---

### 3.2 按钮防重复提交

> 来源：`music_pusher/data/static_ui/index.html` 多处

```javascript
async function handleAction(btn, actionFn) {
    btn.disabled = true;
    btn.textContent = "处理中...";
    try {
        await actionFn();
    } catch (err) {
        showToast(`操作失败：${err.message}`, "error");
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}
```

**关键点**：
- `disabled = true` 阻止重复点击
- 修改按钮文字提供视觉反馈
- `finally` 中恢复（确保即使异常也能恢复按钮）
- 不要用 `btn.onclick = null` 来防止重复（恢复麻烦）

---

### 3.3 Toast 错误通知

> 来源：`music_pusher/data/static_ui/index.html` L1117-1128

```javascript
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    // 2.4 秒后自动淡出
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transition = "opacity 0.22s";
        setTimeout(() => toast.remove(), 220);
    }, 2400);
}
```

**CSS 配合**：
```css
#toast-container {
    position: fixed;
    top: 24px;
    right: 24px;
    z-index: 9999;
    pointer-events: none;  /* 不阻挡下方元素交互 */
    display: flex;
    flex-direction: column;
    gap: 10px;
}
.toast { pointer-events: auto; }  /* toast 本身可交互（点击关闭等） */
```

---

### 3.4 RPC 超时控制

> 来源：`music_pusher/data/static_ui/index.html` L1293-1349

```javascript
async function callEntry(entryId, args = {}, timeoutMs = 90000) {
    // 1. 创建任务
    const runResp = await fetch(`${RUNS_URL}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entry_id: entryId, args })
    });
    const { run_id } = await runResp.json();

    // 2. 轮询状态（带超时）
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
        await sleep(230);
        const resp = await fetch(`${RUNS_URL}/${run_id}`);
        const run = await resp.json();

        if (run.status === "completed") return run;
        if (run.status === "failed") throw new Error(run.error || "执行失败");
        if (run.status === "canceled") throw new Error("任务已取消");
        if (run.status === "timeout") throw new Error("任务超时");
    }
    throw new Error(`操作超时（${timeoutMs / 1000}秒）`);
}
```

**超时策略**：
- 不同操作使用不同超时：普通 30s，唱歌 90s，文件操作 20s
- 轮询间隔 230ms（约每秒 4 次），不阻塞 UI
- 失败/取消/超时分别抛出不同错误

---

### 3.5 响应解包（防止嵌套 data）

> 来源：`music_pusher/data/static_ui/index.html` L1275-1291

```javascript
function unwrapPluginResponse(raw, maxDepth = 10) {
    let current = raw;
    for (let i = 0; i < maxDepth; i++) {
        if (current && typeof current === "object" && "data" in current) {
            current = current.data;  // 解包一层
        } else {
            break;
        }
    }

    if (current && typeof current === "object" && current.success === false) {
        throw new Error(current.error || current.message || "未知错误");
    }

    return current;
}
```

**为什么需要递归解包**：N.E.K.O 的 RPC 响应可能被多层 `{data: {data: {...}}}` 包裹。

---

## 四、通用模式速查

| 场景 | 模式 | 来源 |
|------|------|------|
| 第三方库可能不存在 | 惰性导入 + 错误缓存 | ai_singer |
| API 返回错误 | 关键字匹配 + 诊断建议 | ai_singer |
| 异步操作需要等待 | 轮询 + 状态日志 + 终态快速失败 | ai_singer |
| 配置保存后验证 | 保存 → 重新初始化 → 健康检查 → 返回结果 | ai_singer |
| 定时器中做异步操作 | new_event_loop → run_until_complete → close | ai_singer |
| UI 结果有多种可能 | 分层渲染（完整/降级/引导/失败） | ai_singer |
| 按钮防止重复点击 | disabled + finally 恢复 | music_pusher |
| 非阻塞错误提示 | Toast + 自动淡出 | music_pusher |
| 长时间 RPC 调用 | 轮询 + 超时 + 不同操作不同超时 | music_pusher |
| 响应数据解包 | 递归解包 data + success 检查 | music_pusher |

---

## 五、错误码设计规范

```python
# 推荐格式：{DOMAIN}_{ISSUE}
SETUP_INCOMPLETE       # 配置未完成
BACKEND_UNAVAILABLE    # 后端不可用
BACKEND_TIMEOUT        # 后端超时
PERMISSION_DENIED      # 权限不足
FILE_NOT_FOUND         # 文件不存在
INVALID_PARAM          # 参数无效
RATE_LIMITED           # 被限流
EXTERNAL_API_ERROR     # 外部 API 错误
```

**命名规则**：
- 全大写 + 下划线
- DOMAIN 在前（SETUP / BACKEND / PERMISSION / FILE / ...）
- 不要用数字错误码（`1001` 等），字符串更可读

---

## 六、错误消息设计三要素

每个面向用户的错误消息应包含：

```
1. 发生了什么（What）
2. 当前状态是什么（Context）
3. 用户该怎么做（Action）
```

**反例**（只有 What）：
```
"API 调用失败"  ← 用户不知道该怎么办
```

**正例**（What + Context + Action）：
```
"MiMo API 连接失败（ConnectionRefusedError）。
当前端点：https://api.xiaomimimo.com/v1
请检查：1. 网络连接是否正常 2. API Key 是否有效 3. 端点 URL 是否正确"
```
