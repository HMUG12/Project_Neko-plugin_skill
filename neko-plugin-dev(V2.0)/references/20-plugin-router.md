# 20 - PluginRouter：拆分大型插件

## 概述

当插件功能越来越多，把所有入口点都写在一个 `__init__.py` 里会变得难以维护。**PluginRouter** 让你把入口点按功能分组到不同文件中，同时它们仍然属于同一个插件。

### 什么时候需要 Router

| 信号 | 说明 |
|------|------|
| 插件有 **5 个以上**入口点 | 单一文件管理困难 |
| 不同入口点属于**不同功能模块** | 如"天气"、"路线"、"美食"各一组 |
| 多人协作开发同一个插件 | 各自负责不同 Router 文件 |
| `__init__.py` 超过 **300 行** | 需要按功能拆分 |

**如果你的插件只有 1-3 个入口点，直接写在主文件里就好，不需要 Router。**

---

## 目录结构示例

以"生活助手"插件为例，12 个功能模块：

```
plugin/plugins/lifekit/
├── __init__.py              ← 主插件：注册所有 router
├── plugin.toml
├── _geo.py                  ← 共享：地理位置解析
├── _api.py                  ← 共享：API 调用工具
├── _chat.py                 ← 共享：推送消息到聊天
└── routers/
    ├── __init__.py          ← 导出所有 router
    ├── current.py           ← 当前天气
    ├── hourly.py            ← 逐小时预报
    ├── travel.py            ← 出行建议
    ├── locations.py         ← 地点管理
    ├── trip.py              ← 路线规划
    ├── nearby.py            ← 附近搜索
    ├── food.py              ← 美食推荐
    ├── recipe.py            ← 菜谱
    ├── air_quality.py       ← 空气质量
    ├── currency.py          ← 汇率换算
    ├── countdown.py         ← 倒计时
    └── unit_convert.py      ← 单位换算
```

在插件管理面板中，用户看到的是**一个**"生活助手"插件，下面有 12+ 个入口点。他们不需要知道代码是怎么组织的。

---

## 第一步：创建 Router 文件

```python
# routers/countdown.py

from plugin.sdk.plugin import plugin_entry, Ok, Err, SdkError
from plugin.sdk.shared.core.router import PluginRouter


class CountdownRouter(PluginRouter):
    """倒计时功能。"""

    def __init__(self):
        super().__init__(name="countdown")

    @plugin_entry(
        id="countdown",
        name="倒计时",
        description="计算距离某个日期还有多少天",
    )
    async def countdown(self, target_date: str, label: str = ""):
        from datetime import datetime, date
        try:
            target = datetime.strptime(target_date, "%Y-%m-%d").date()
            days = (target - date.today()).days
        except ValueError:
            return Err(SdkError("日期格式错误，请使用 YYYY-MM-DD"))
        label = label or target_date
        return Ok({"summary": f"距离 {label} 还有 {days} 天", "days": days})

    @plugin_entry(
        id="days_between",
        name="日期间隔",
        description="计算两个日期之间相隔多少天",
    )
    async def days_between(self, start_date: str = "", end_date: str = ""):
        from datetime import datetime
        try:
            d1 = datetime.strptime(start_date, "%Y-%m-%d").date()
            d2 = datetime.strptime(end_date, "%Y-%m-%d").date()
            days = abs((d2 - d1).days)
        except ValueError:
            return Err(SdkError("日期格式错误"))
        return Ok({"summary": f"共 {days} 天", "days": days})
```

**关键点：**
1. 继承 `PluginRouter`
2. `super().__init__(name="countdown")` 给 router 一个名字（用于调试日志）
3. 用 `@plugin_entry` 定义入口点，写法和主插件里完全一样

---

## 第二步：在主插件中注册

```python
# __init__.py

from plugin.sdk.plugin import NekoPluginBase, neko_plugin, lifecycle, Ok
from .routers.countdown import CountdownRouter
from .routers.weather import WeatherRouter

@neko_plugin
class LifeKitPlugin(NekoPluginBase):

    def __init__(self, ctx):
        super().__init__(ctx)

        # 注册 routers — 必须在 __init__ 中
        self.include_router(CountdownRouter())
        self.include_router(WeatherRouter())

    @lifecycle(id="startup")
    async def on_startup(self):
        self.logger.info("生活助手已启动")
        return Ok({"status": "ready"})
```

`self.include_router()` 把 router 中定义的所有入口点注册到当前插件下。

---

## Router 里能访问什么

Router 被注册后，会自动绑定到主插件。以下属性都可用：

```python
from plugin.sdk.plugin import unwrap

class MyRouter(PluginRouter):

    @plugin_entry(id="example", name="示例", description="演示 router 能力")
    async def example(self):
        # 日志
        self.logger.info("Router 中打日志")

        # 读取配置
        cfg = await self.config.dump()

        # 使用存储
        unwrap(await self.store.set("key", "value"))

        # 调用其他插件
        result = await self.plugins.call_entry("other:entry")

        # 访问数据库
        async with unwrap(await self.db.session()) as session:
            cursor = await session.execute("SELECT * FROM notes")
            rows = cursor.fetchall()

        # 访问主插件的自定义属性/方法
        plugin = self.main_plugin
        data = await plugin.some_shared_method()

        return Ok({"done": True})
```

| 属性 | 来源 |
|------|------|
| `self.logger` | 主插件的 logger |
| `self.config` | 主插件的 config |
| `self.store` | 主插件的 store |
| `self.db` | 主插件的 db |
| `self.plugins` | 主插件的 plugins |
| `self.plugin_id` | 主插件的 ID |
| `self.main_plugin` | 主插件实例本身 |

> **Router 不是独立进程**，它和主插件运行在同一个进程中，共享所有资源。

---

## 共享逻辑

多个 router 需要用到相同的工具函数时，放在主插件或单独的模块中：

```python
# _geo.py — 共享：地理位置解析
async def resolve_location(city_name):
    """解析城市名称为经纬度坐标。"""
    # ... 解析逻辑 ...
    return {"lat": 39.9, "lng": 116.4}, None


# routers/current.py
class WeatherRouter(PluginRouter):

    @plugin_entry(id="get_weather", name="查天气", description="查询天气")
    async def get_weather(self, city: str = ""):
        plugin = self.main_plugin
        # 调用主插件上的共享方法
        location, error = await plugin._resolve_location(city)
        if not location:
            return Err(SdkError(error))
        # ... 使用 location 查询天气 ...


# __init__.py — 主插件定义共享方法
@neko_plugin
class LifeKitPlugin(NekoPluginBase):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.include_router(WeatherRouter())

    async def _resolve_location(self, city_name):
        """共享：所有 router 都可以通过 self.main_plugin._resolve_location() 调用。"""
        from ._geo import resolve_location
        return await resolve_location(city_name)
```

---

## 带前缀的 Router

避免 ID 冲突，可以给某个 router 的所有入口加一个前缀：

```python
self.include_router(CountdownRouter(), prefix="time_")
```

这样 `countdown` 入口的实际 ID 变成 `time_countdown`。

> **大多数情况下不需要前缀** — 只要确保不同 router 里的入口 ID 不重复就行。

---

## 运行时移除

```python
# 只从 router 列表移除
self.exclude_router(my_router_instance)

# 按名字同样如此
self.exclude_router("countdown")
```

> **注意：** `exclude_router()` 只从 router 列表移除。入口点是在宿主构建 dispatch table 时收集的，之后再移除 router **不会自动让已经收集的入口不可调用**。如需运行时启用/禁用功能，请使用宿主扩展控制（`DISABLE_EXTENSION` / `ENABLE_EXTENSION`），或在入口逻辑里用自己的配置判断。

---

## 完整最小示例

两个 router 的插件：

```python
# routers/greet.py
from plugin.sdk.plugin import plugin_entry, Ok
from plugin.sdk.shared.core.router import PluginRouter

class GreetRouter(PluginRouter):
    def __init__(self):
        super().__init__(name="greet")

    @plugin_entry(id="hello", name="Hello", description="Say hello")
    async def hello(self, name: str = "World"):
        return Ok({"message": f"Hello, {name}!"})


# routers/math.py
from plugin.sdk.plugin import plugin_entry, Ok, Err, SdkError
from plugin.sdk.shared.core.router import PluginRouter

class MathRouter(PluginRouter):
    def __init__(self):
        super().__init__(name="math")

    @plugin_entry(id="add", name="加法", description="两数相加")
    async def add(self, a: float, b: float):
        return Ok({"result": a + b})

    @plugin_entry(id="divide", name="除法", description="两数相除")
    async def divide(self, a: float, b: float):
        if b == 0:
            return Err(SdkError("不能除以零"))
        return Ok({"result": a / b})


# __init__.py
from plugin.sdk.plugin import NekoPluginBase, neko_plugin
from .routers.greet import GreetRouter
from .routers.math import MathRouter

@neko_plugin
class MyPlugin(NekoPluginBase):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.include_router(GreetRouter())
        self.include_router(MathRouter())
```

这个插件在面板中会显示三个入口点：`hello`、`add`、`divide`。

---

## 最佳实践

1. **按功能模块拆分** — 每个 Router 负责一个功能域（如天气、笔记、计算）
2. **共享逻辑放主插件** — 通过 `self.main_plugin.shared_method()` 调用
3. **`__init__` 中注册** — Router 必须在 `super().__init__(ctx)` 之后、`__init__` 返回之前注册
4. **保持入口 ID 唯一** — 跨 Router 的 entry id 不能重复
5. **Router 文件保持简洁** — 只包含入口点定义，业务逻辑提取到共享模块
6. **不用 Router 当功能开关** — 用 `exclude_router` 不能阻止已注册的入口被调用

---

## 相关文档

- [02 - Python 插件核心](02-python-plugin.md) — 入口点基础
- [14 - 多面板架构](14-multi-panel-architecture.md) — 多面板与多 Context
