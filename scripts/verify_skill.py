#!/usr/bin/env python3
"""技能包仓库自检：确定性门禁，本机与 CI 都可执行。

用法：python scripts/verify_skill.py

只依赖 Python 3.11+ 标准库。检查项：
  1. 全部 Markdown 的相对链接
  2. py / toml / json 语法
  3. SKILL.md frontmatter（行数、description 长度、单一基线声明）
  4. 示例的官方 init 生成物 sha256（防止支撑文件被改回旧版模板）
  5. 示例必备文件齐全
  6. 示例静态契约测试（直接调用 test_*，不依赖 pytest）
  7. 规则区旧口径残留：只报告、不判失败，需人工 triage（反例/勘误语境会命中）

官方生成物 hash 来自实际执行官方 main `generator.py` 的
`generate_plugin()` / `generate_repo_support_files()`（commit acfbdbc），
生成时使用 `entry_point_override="plugin.plugins.minimal_plugin:MinimalPlugin"`。
官方模板升级后这些 hash 会变，属预期：重新跑生成器并同步更新本表即可。
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "neko-plugin-dev" / "SKILL.md"
EXAMPLE = ROOT / "neko-plugin-dev" / "examples" / "minimal_plugin"
ARCHIVE_NAMES = {"REVIEW_FIXES.md", "CHANGELOG.md", "UNVERIFIED.md"}

OFFICIAL_INIT_SHA256 = {
    "ruff.toml": "b4303b147c481bc7ec6e96a0a68e7fb3c71d653fe1277c40ad48b4bac8b55efe",
    ".github/workflows/verify.yml": "48c2a6f662ca78178991294e31faa647922c5d417d7342f5f1eedbf9bd868e3e",
    ".github/workflows/release.yml": "1476165962786c3cf27c63d107d6771e190f7aebc1b1bd17bbe501dee21a838d",
    ".gitignore": "8fe1127ae54ed619ff52ab4449bba597d78aab7bd21e31683184b33fb6c58b6e",
    ".vscode/settings.json": "ba3aab557e84ce819b1c8b6651e48f452ff47f8b69c1643a1d68e92fda9953f3",
    ".vscode/tasks.json": "f257d0b74ebdce5171e1bc45508b8eae3ef8981e0f425738d541842de872f293",
    "tests/test_smoke.py": "34a02e266a33831c3cc4954c7a23a63e8f60febf2f09de10e2256eb2d677267a",
}

REQUIRED_EXAMPLE_FILES = [
    "plugin.toml", "config.example.toml", "pyproject.toml", "__init__.py",
    "README.md", "ruff.toml", ".github/workflows/verify.yml",
    ".github/workflows/release.yml", "tests/test_smoke.py",
    "tests/test_plugin_contract.py", "tests/pytest.ini",
]

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
RESIDUE_PATTERNS = [
    (r"neko-plugin\s+add\b", "旧 add 命令"),
    (r"push_message.*->\s*None", "push_message -> None"),
    (r"256\s*(?:KiB|KB)", "256 KiB 旧上限"),
    (r"0-2\s*[=＝].*低|9-10\s*[=＝].*紧急", "priority 自拟分档"),
    (r"extension\s*类型|type\s*=\s*\"extension\"", "Extension 类型"),
    (r"\[plugin\.host\]", "旧 [plugin.host]"),
    (r"框架从不注入\s*ctx", "ctx 注入错误表述"),
    (r"schema\.py:103", "旧 schema.py 行号"),
    (r"旧快照|两版|A/B\s*双口径|双口径", "双口径措辞"),
    (r"await\s+\w*\.?push_message\(", "await push_message"),
    (r"只(?:用|有)\s*pickle|2\s*条通道|6\s*个\s*(?:channel\s*)?tag", "旧 ZMQ 描述"),
    (r"(?<!await )self\.store\.set\(", "store.set 缺 await"),
]

failures: list[str] = []
passed: list[str] = []


def result(ok: bool, name: str, detail: str = "") -> None:
    (passed if ok else failures).append(f"{name}: {detail}" if detail else name)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def all_files(suffix: str) -> list[Path]:
    return sorted(p for p in ROOT.rglob(suffix) if ".git" not in p.parts)


def check_links() -> None:
    print("[1] 相对链接")
    broken = []
    for f in all_files("*.md"):
        for lineno, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for m in LINK_RE.finditer(line):
                href = m.group(1).split("#")[0].strip()
                if not href or href.startswith(("http://", "https://", "mailto:", "data:", "/")):
                    continue
                if not (f.parent / href).resolve().exists():
                    broken.append(f"{f.relative_to(ROOT)}:{lineno} -> {href}")
    result(not broken, "链接", f"{len(broken)} 条失效" if broken else "0 条失效")
    for b in broken[:15]:
        print("       ", b)


def check_syntax() -> None:
    print("[2] 语法")
    bad = []
    py_files = all_files("*.py")
    for f in py_files:
        try:
            compile(f.read_text(encoding="utf-8", errors="replace"), str(f), "exec")
        except SyntaxError as e:
            bad.append(f"{f.relative_to(ROOT)}: {e}")
    cfg_files = all_files("*.toml") + all_files("*.json")
    for f in cfg_files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
            tomllib.loads(text) if f.suffix == ".toml" else json.loads(text)
        except Exception as e:
            bad.append(f"{f.relative_to(ROOT)}: {type(e).__name__}: {e}")
    result(not bad, "语法", f"{len(py_files)} py + {len(cfg_files)} toml/json，{len(bad)} 失败"
           if bad else f"{len(py_files)} py + {len(cfg_files)} toml/json 全部通过")
    for b in bad[:15]:
        print("       ", b)


def check_frontmatter() -> None:
    print("[3] SKILL.md frontmatter")
    text = SKILL.read_text(encoding="utf-8")
    fm = text.split("---", 2)[1] if text.startswith("---") else ""
    desc = ""
    for line in fm.splitlines():
        if line.startswith("description:"):
            val = line.split(":", 1)[1].strip()
            desc = val[1:-1] if val.startswith('"') and val.endswith('"') else val
            break
    lines = len(text.splitlines())
    result(lines < 500 and 0 < len(desc) < 1024, "行数与 description",
           f"{lines} 行 / {len(desc)} 字符")
    result("单一基线" in text or "唯一基线" in text, "单一基线声明")


def check_official_init() -> None:
    print("[4] 官方 init 生成物字节一致")
    mismatch = []
    for rel, expected in OFFICIAL_INIT_SHA256.items():
        f = EXAMPLE / rel
        actual = hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else ""
        if actual != expected:
            mismatch.append(rel)
    result(not mismatch, "sha256", f"{len(OFFICIAL_INIT_SHA256)} 份全部一致"
           if not mismatch else f"不一致: {', '.join(mismatch)}")


def check_example_files() -> None:
    print("[5] 示例必备文件")
    missing = [n for n in REQUIRED_EXAMPLE_FILES if not (EXAMPLE / n).is_file()]
    result(not missing, "文件齐全", f"{len(REQUIRED_EXAMPLE_FILES)} 项"
           if not missing else f"缺少: {', '.join(missing)}")


def check_contract_tests() -> None:
    print("[6] 示例静态契约测试")
    test_file = EXAMPLE / "tests" / "test_plugin_contract.py"
    spec = importlib.util.spec_from_file_location("neko_contract_test", test_file)
    if spec is None or spec.loader is None:
        result(False, "加载测试模块")
        return
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tests = sorted((n, getattr(module, n)) for n in dir(module) if n.startswith("test_") and callable(getattr(module, n)))
    failed = []
    for name, fn in tests:
        try:
            fn()
        except Exception as e:
            failed.append(f"{name}: {type(e).__name__}: {e}")
    result(not failed and bool(tests), "契约测试", f"{len(tests) - len(failed)}/{len(tests)} 通过")
    for f in failed[:15]:
        print("       ", f)


def scan_residue() -> None:
    print("[7] 规则区旧口径残留（仅报告，人工 triage）")
    rule_files = [f for f in all_files("*.md") if f.name not in ARCHIVE_NAMES]
    hits = []
    for f in rule_files:
        for lineno, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for pattern, label in RESIDUE_PATTERNS:
                if re.search(pattern, line, re.I):
                    hits.append((str(f.relative_to(ROOT)), lineno, label))
                    break
    print(f"  [INFO] 命中 {len(hits)} 行；多为「不要 await / 已废弃 / 不再并列旧快照」等反例或声明语境")
    for f, lineno, label in hits[:12]:
        print(f"       {f}:{lineno} [{label}]")
    if len(hits) > 12:
        print(f"       ... 其余 {len(hits) - 12} 行省略")


def check_unverified_manifest() -> None:
    """未完成事项清单必须存在且仍标为待审，防止把缺口悄悄标成完成。"""
    print("[8] 未完成事项清单")
    path = ROOT / "UNVERIFIED.md"
    if not path.is_file():
        result(False, "未完成事项清单", "UNVERIFIED.md 缺失")
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    ids = re.findall(r"^### (U-\d{2})\b", text, re.M)
    ok = (
        "状态：待审" in text
        and "不冒充实测" in text
        and len(ids) >= 6
        and len(ids) == len(set(ids))
    )
    result(ok, "未完成事项清单", f"{len(ids)} 条待审项 / 状态待审 / 编号唯一" if ok else "状态行或编号异常")


def main() -> int:
    print(f"verify_skill.py — {ROOT}")
    check_links()
    check_syntax()
    check_frontmatter()
    check_official_init()
    check_example_files()
    check_contract_tests()
    scan_residue()
    check_unverified_manifest()
    print()
    if failures:
        print(f"==> FAILED ({len(failures)} 项)")
        for f in failures:
            print("   -", f)
        return 1
    print(f"==> 全部通过（{len(passed)} 项硬门禁）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
