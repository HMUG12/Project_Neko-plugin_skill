"""静态契约测试：防止示例回退到已知错误写法。

不依赖 N.E.K.O 运行时，可在普通 Python 环境执行：
    pytest examples/minimal_plugin/tests
完整的插件校验请用 uv run neko-plugin check minimal_plugin --strict。
"""
import re
from pathlib import Path

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


def test_push_message_result_is_checked():
    src = _read("__init__.py")
    assert 'result["submitted"]' in src
    assert 'result.get("reason")' in src


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


def test_official_init_support_files():
    """示例支撑文件必须等价于官方 neko-plugin init / generator.py 的产物。"""
    ruff = _read("ruff.toml")
    assert "managed-template: plugin-market-actions-v1" in ruff
    assert 'target-version = "py311"' in ruff
    assert 'select = ["E4", "E7", "E9", "F", "I"]' in ruff
    for name in ("verify.yml", "release.yml"):
        wf = _read(f".github/workflows/{name}")
        assert "managed-template: plugin-market-actions-v1" in wf
        assert "uses: Project-N-E-K-O/N.E.K.O/.github/workflows/plugin-market-" in wf
        assert "plugin-id: minimal_plugin" in wf
        # 旧式「挂进 N.E.K.O 树再 check -r」模板已废弃
        assert "Mount plugin into N.E.K.O tree" not in wf
    release = _read(".github/workflows/release.yml")
    assert "id-token: write" in release and "attestations: write" in release


def test_config_is_persisted_and_read_back():
    """面板保存必须落盘；startup / config_change 必须重读 config.example.toml 的值。"""
    src = _read("__init__.py")
    assert "await self.config.update(" in src
    assert "await self.config.dump(timeout=5.0)" in src
    assert "await self._reload_config()" in src
    assert 'async def on_config_change(self, **_)' in src
    example = _read("config.example.toml")
    assert "[minimal_plugin]" in example and "greeting" in example
