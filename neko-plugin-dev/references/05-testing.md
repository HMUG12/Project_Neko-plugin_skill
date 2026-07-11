# 单元测试指南

## 核心挑战

N.E.K.O 插件依赖 `plugin.sdk.plugin` 模块，该模块只在 N.E.K.O 运行时存在。测试时**必须 Mock 整个 SDK 模块**。

## Mock SDK 模板

```python
# -*- coding: utf-8 -*-
import os, sys, tempfile, shutil, sqlite3, asyncio, threading
from unittest.mock import MagicMock

# ── 1. 模拟 SDK 模块 ──
class _FakeSDK:
    @staticmethod
    def neko_plugin(cls):
        cls._is_neko_plugin = True
        return cls

    @staticmethod
    def lifecycle(**kw):
        def deco(fn):
            fn._lifecycle = kw
            return fn
        return deco

    @staticmethod
    def plugin_entry(**kw):
        def deco(fn):
            fn._entry = kw
            return fn
        return deco

    @staticmethod
    def timer_interval(**kw):
        def deco(fn):
            fn._timer = kw
            return fn
        return deco

    @staticmethod
    def ui_action(**kw):
        def deco(fn):
            fn._ui_action = kw
            return fn
        return deco

    class ui:
        @staticmethod
        def context(**kw):
            def deco(fn):
                fn._ui_context = kw
                return fn
            return deco
        action = staticmethod(lambda **kw: lambda fn: fn)

    tr = staticmethod(lambda x: x)
    Ok = lambda val: _Ok(val)
    Err = lambda err: _Err(err)
    unwrap = lambda x: x
    SdkError = type("SdkError", (Exception,), {
        "__init__": lambda self, msg: setattr(self, "message", msg)
    })
    NekoPluginBase = type("NekoPluginBase", (), {})

class _Ok:
    def __init__(self, v): self.value = v
    def __bool__(self): return True

class _Err:
    def __init__(self, e): self.error = e
    def __bool__(self): return False

# ── 2. 注入到 sys.modules ──
class _FakePluginModule:
    sdk = type("sdk", (), {"plugin": _FakeSDK})()
    def __getattr__(self, name):
        if name == "sdk": return self.sdk
        raise AttributeError(name)

sys.modules["plugin"] = _FakePluginModule()
sys.modules["plugin.sdk"] = _FakePluginModule.sdk
sys.modules["plugin.sdk.plugin"] = _FakeSDK

# ── 3. 导入插件 ──
sys.path.insert(0, r"<插件源码目录>")
from __init__ import YourPluginClass

# 注意：Err 是函数不是类型，_Err 是实际的类
ErrClass = _Err
```

## Fake 对象模板

```python
class FakeLogger:
    def info(self, *a, **kw): pass
    def warning(self, *a, **kw): pass
    def error(self, *a, **kw): pass
    def debug(self, *a, **kw): pass

class FakeI18n:
    def t(self, key, default="", **kw):
        return default.format(**kw) if default else key

class FakeConfig:
    def __init__(self, settings=None):
        self._settings = settings or {"settings": {}}
    async def dump(self):
        return self._settings

class FakeDB:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
    async def session(self):
        return FakeSession(self.conn)

class FakeSession:
    def __init__(self, conn):
        self.conn = conn
    async def execute(self, sql, params=None):
        return self.conn.execute(sql, params or [])
    async def commit(self):
        self.conn.commit()
    async def close(self):
        pass

class FakeContext:
    _last_config = {}
    async def update_own_config(self, cfg):
        FakeContext._last_config = cfg
```

## 工厂函数

```python
def make_plugin(settings=None):
    """创建插件实例，注入所有 Fake 依赖"""
    p = YourPluginClass.__new__(YourPluginClass)

    # 注入依赖
    p.logger = FakeLogger()
    p.i18n = FakeI18n()
    p.config = FakeConfig(settings or {"settings": {}})
    p.db = FakeDB()
    p.ctx = FakeContext()

    # 注入配置项默认值
    p.my_setting = False
    p.my_list = []

    # 注入内部状态
    p._running = False
    p._frozen = False

    # Mock 不需要的方法
    p.push_message = MagicMock()
    p.report_status = MagicMock()

    return p
```

## 测试用例模板

```python
class TestMyPlugin:
    # ── 同步测试 ──
    def test_sync_method(self):
        p = make_plugin()
        result = p.some_method()
        assert result == expected
        print("✓ test_sync_method")

    # ── 异步测试 ──
    async def test_async_method(self):
        p = make_plugin()
        result = await p.async_method(param="value", _ctx=None)
        assert not isinstance(result, ErrClass)
        print("✓ test_async_method")

    # ── 权限检查 ──
    async def test_permission_denied(self):
        p = make_plugin()
        p.enable_ops = True
        p.allow_read = False
        result = await p.read_file(file_path="C:\\test.txt", _ctx=None)
        assert isinstance(result, ErrClass)
        print("✓ test_permission_denied")

    # ── 临时文件测试 ──
    async def test_with_tempfile(self):
        tmpdir = tempfile.mkdtemp()
        try:
            f = os.path.join(tmpdir, "test.txt")
            with open(f, "w") as fh: fh.write("hello")
            p = make_plugin()
            p.scan_paths = [tmpdir]
            result = await p.do_something(f, _ctx=None)
            assert result.value["ok"] is True
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        print("✓ test_with_tempfile")
```

## 测试运行器

```python
async def run_all():
    t = TestMyPlugin()
    tests = [
        t.test_sync_method,
        t.test_async_method,
        t.test_permission_denied,
        t.test_with_tempfile,
    ]
    passed = failed = 0
    for fn in tests:
        try:
            if asyncio.iscoroutinefunction(fn):
                await fn()
            else:
                fn()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"\n✗ FAIL {fn.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"\n✗ ERROR {fn.__name__}: {type(e).__name__}: {e}")

    print(f"\n{'='*50}")
    print(f"总计: {passed+failed}  通过: {passed}  失败: {failed}")
    print(f"{'='*50}")
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(run_all())
    sys.exit(0 if success else 1)
```

## 测试覆盖检查清单

| 测试类别 | 应覆盖的内容 |
|---------|-------------|
| 权限检查 | 每种权限的拒绝、允许、范围外、保护路径 |
| 配置项 | 默认值、空值、更新后生效 |
| 文件操作 | 创建、复制、移动、删除、粘贴、覆盖、不覆盖 |
| 撤销 | 每种操作的撤销、空栈、满栈 |
| 路径处理 | 绝对路径、相对路径（应拒绝）、不存在路径 |
| 边界条件 | 空参数、空列表、空数据库 |
| 生命周期 | startup/shutdown/reload/config_change/freeze/unfreeze |
| 集成测试 | 多步骤操作链（创建→移动→撤销） |

## 注意事项

1. **Err 是函数不是类型** — 用 `isinstance(x, ErrClass)` 而非 `isinstance(x, Err)`
2. **临时文件用 `tempfile.mkdtemp()`** — 测试后用 `shutil.rmtree` 清理
3. **异步方法用 `_ctx=None` 调用** — 模拟 SDK 行为
4. **测试完成后删除测试文件** — 避免污染工作区
5. **Mock 的 SDK 对象必须与真实 SDK 签名一致** — 否则装饰器会报错