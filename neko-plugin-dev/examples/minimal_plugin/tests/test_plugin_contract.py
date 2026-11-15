"""静态契约测试：防止示例回退到已知错误写法。

不依赖 N.E.K.O 运行时，可在普通 Python 环境执行：
    pytest examples/minimal_plugin/tests
完整的插件校验请用 uv run neko-plugin check minimal_plugin --strict。
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_push_message_is_not_awaited():
    src = _read("__init__.py")
    assert not re.search(r"await\s+.*push_message\(", src)


def test_push_message_uses_parts():
    src = _read("__init__.py")
    assert "parts=" in src
    assert "content=" not in src


def test_timer_is_async_and_has_no_event_loop():
    src = _read("__init__.py")
    assert re.search(r"@timer_interval\([^)]*\)\s*\n\s*async def", src)
    assert "new_event_loop" not in src


def test_ui_action_is_stacked_with_entry():
    src = _read("__init__.py")
    assert re.search(r"@ui\.action\([\s\S]{0,200}?\)\s*\n\s*@plugin_entry\(", src)


def test_router_inherits_plugin_router():
    src = _read("routers/notes.py")
    assert "class NotesRouter(PluginRouter)" in src
    # 只禁止真正的装饰器用法；注释里提到 @llm_tool 不算误用
    assert not re.search(r"^\s*@llm_tool", src, re.M)


def test_no_inline_dependency_table():
    src = _read("plugin.toml")
    assert "[plugin.dependencies]" not in src


def test_supporting_files_exist():
    for rel in ("pyproject.toml", "README.md", "config.example.toml"):
        assert (ROOT / rel).is_file(), f"missing {rel}"
