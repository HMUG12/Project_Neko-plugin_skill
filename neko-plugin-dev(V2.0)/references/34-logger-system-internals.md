# 34 — Logger 日志系统内部机制

> **来源**：N.E.K.O-main `plugin/logging_config.py` + `plugin/core/plugin_logger.py` 深度逆向分析  
> **适用**：理解插件的日志系统架构，正确使用日志，排查日志不落地问题

---

## 1. 架构概览

```
┌──────────────────────────────────────────────────────┐
│                    插件代码                           │
│  self.logger.info("xxx")  /  log.info("xxx")         │
├──────────────────────────────────────────────────────┤
│              PluginLoggerAdapter (兼容层)              │
│  - loguru 风格 {} 兼容                                │
│  - bind / opt 支持                                    │
│  - 懒解析 NEKO_PLUGIN_SERVICE_NAME                   │
├──────────────────────────────────────────────────────┤
│            stdlib logging (底层引擎)                   │
│  - RobustLoggerConfig (日志落地)                       │
│  - Root bridge (第三方库日志捕获)                       │
│  - 敏感信息脱敏                                       │
├──────────────────────────────────────────────────────┤
│  我的文档/N.E.K.O/logs/N.E.K.O_Plugin_{id}_*.log      │
└──────────────────────────────────────────────────────┘
```

**核心设计原则**：底层全部使用 Python 标准库 `logging`，上层通过 `PluginLoggerAdapter` 提供 loguru 风格的兼容 API。

---

## 2. 插件中获取 Logger

### 方式一：使用 self.logger（推荐）

```python
@neko_plugin
class MyPlugin(NekoPluginBase):
    def __init__(self, ctx):
        super().__init__(ctx)
        # self.logger 由 SDK 自动注入，绑定插件 ID

    async def do_something(self):
        self.logger.info("处理完成")
        self.logger.warning("配置缺失，使用默认值")
        self.logger.error("连接外部服务失败")
        self.logger.debug(f"内部状态: {self._internal_state}")
        self.logger.exception("异常发生")  # 自动记录 traceback
```

### 方式二：使用 get_logger（模块级）

```python
from plugin.logging_config import get_logger

log = get_logger("my_component")  # → N.E.K.O.Plugin_xxx.my_component

log.info("组件初始化完成")
```

### 方式三：使用模块级 logger

```python
from plugin.logging_config import logger  # 已预配置的模块级 logger

logger.info("全局日志")
```

---

## 3. 两种日志风格兼容

`PluginLoggerAdapter` 同时支持两种风格：

```python
# ✅ loguru 风格（花括号）
logger.info("hello {}", "world")       # → "hello world"
logger.info("user: {name}", name="x")  # → "user: x"

# ✅ stdlib 风格（百分号）
logger.info("hello %s", "world")       # → "hello world"

# ✅ bind / opt（loguru 兼容）
bound = logger.bind(plugin_id="xxx")    # 返回绑定了额外上下文的 logger
opt_logger = logger.opt(exception=True) # 返回带异常标记的 logger
```

**底层实现**：通过 monkey-patch `logging.LogRecord.getMessage`，检测 `{}` 模式并回退到 `str.format()`。

---

## 4. 日志文件路径

```
我的文档/N.E.K.O/logs/N.E.K.O_Plugin_{plugin_id}_*.log
```

- **Windows**：`C:\Users\<用户名>\Documents\N.E.K.O\logs\`
- **macOS**：`~/Documents/N.E.K.O/logs/`
- **Linux**：`~/Documents/N.E.K.O/logs/`

### 重要注意事项

1. **不要基于 `cwd` 或 `__file__` 计算日志路径**——AppImage 中 squashfs 是只读的
2. 日志路径由 `RobustLoggerConfig` 统一管理
3. `NEKO_PLUGIN_SERVICE_NAME` 环境变量控制 logger 层次

---

## 5. 日志级别

```python
self.logger.debug("调试信息")       # 内部状态、变量值
self.logger.info("一般信息")        # 流程节点、操作完成
self.logger.warning("警告")         # 配置缺失、降级行为
self.logger.error("错误")           # 操作失败、异常
self.logger.exception("异常")       # 自动附加 traceback
```

---

## 6. 内部机制详解

### 6.1 懒解析 Logger

`PluginLoggerAdapter` 是**懒解析**的——它在每次 log 调用时根据 `NEKO_PLUGIN_SERVICE_NAME` 环境变量动态解析 logger 名称：

```python
# 伪代码
@property
def _logger(self):
    service_name = os.environ.get("NEKO_PLUGIN_SERVICE_NAME", "")
    return logging.getLogger(f"N.E.K.O.{service_name}")
```

**含义**：即使在 `NEKO_PLUGIN_SERVICE_NAME` 设置之前 import 模块级 logger，只要环境变量后续被设置，它仍能正常工作。

### 6.2 Root Bridge

框架将 service handler 复制到 root logger，使 uvicorn、aiohttp 等第三方库的日志也能落地：

```python
# plugin/logging_config.py
root_logger = logging.getLogger()
root_logger.handlers.clear()
root_logger.addHandler(service_handler)  # 继承 service handler
```

### 6.3 敏感信息脱敏

自动对以下模式进行正则脱敏：
- `password`
- `token`
- `api_key`
- `authorization`

```python
# 原始日志
logger.info("使用 api_key=sk-abc123xyz 连接")
# 脱敏后输出
# "使用 api_key=sk-abc***xyz 连接"
```

---

## 7. 关键陷阱

### 陷阱 34-1：使用 loguru

```python
# ❌ 错误：CI 会拒绝
from loguru import logger
logger.info("hello")

# ✅ 正确：使用框架提供的 logger
self.logger.info("hello")
```

**原因**：框架在 CI 中强制检查，loguru 被明确禁止。

### 陷阱 34-2：日志不落地

```python
# ❌ 可能不落地：使用 print 或自定义 logger
print("处理完成")
my_logger = logging.getLogger("custom")
my_logger.info("xxx")

# ✅ 正确：使用 self.logger 或 get_logger
self.logger.info("处理完成")
```

### 陷阱 34-3：异常日志丢失 traceback

```python
# ❌ 错误：使用 error 记录异常
try:
    risky_operation()
except Exception as e:
    self.logger.error(f"操作失败: {e}")  # traceback 丢失！

# ✅ 正确：使用 exception
try:
    risky_operation()
except Exception:
    self.logger.exception("操作失败")  # 自动附加完整 traceback
```

### 陷阱 34-4：日志路径硬编码

```python
# ❌ 错误：基于 cwd 计算日志路径
log_path = os.path.join(os.getcwd(), "logs", "my_plugin.log")

# ✅ 正确：使用 self.data_path 或框架提供的 logger
# 框架自动处理日志路径，不需要手动指定
self.logger.info("xxx")  # 自动落地到正确位置
```

---

## 8. 日志最佳实践

### 结构化日志

```python
# ✅ 推荐：结构化信息，便于搜索
self.logger.info("文件处理完成 | files=%d | bytes=%d | duration=%.2fs",
                 file_count, total_bytes, duration)

# ❌ 避免：纯文本描述
self.logger.info("文件处理完成了")
```

### 日志级别选择指南

| 场景 | 级别 | 示例 |
|------|------|------|
| 流程节点 | INFO | "开始扫描目录"、"扫描完成" |
| 配置降级 | WARNING | "API Key 未设置，使用默认值" |
| 操作失败 | ERROR | "连接外部服务失败" |
| 异常 | EXCEPTION | "处理消息时发生异常" |
| 内部调试 | DEBUG | "当前队列长度: 42" |

### 性能敏感日志

```python
# ✅ 正确：使用惰性求值
if self.logger.isEnabledFor(logging.DEBUG):
    self.logger.debug(f"详细状态: {expensive_computation()}")

# ❌ 避免：昂贵的字符串格式化
self.logger.debug(f"详细状态: {expensive_computation()}")  # 即使不输出也会计算
```

---

## 9. 调试日志

### 查看插件日志

```bash
# Windows
Get-Content "$env:USERPROFILE\Documents\N.E.K.O\logs\N.E.K.O_Plugin_my_plugin_*.log" -Tail 50

# macOS / Linux
tail -f ~/Documents/N.E.K.O/logs/N.E.K.O_Plugin_my_plugin_*.log
```

### 临时启用 DEBUG 级别

```python
# 在插件开发期间
import logging
logging.getLogger("N.E.K.O.Plugin_my_plugin").setLevel(logging.DEBUG)
```

---

## 相关文档

- [02-python-plugin](02-python-plugin.md) — Python 后端基础
- [24-error-handling-patterns](24-error-handling-patterns.md) — 错误处理中的日志
- [29-plugin-lifecycle-internals](29-plugin-lifecycle-internals.md) — 生命周期中的日志
