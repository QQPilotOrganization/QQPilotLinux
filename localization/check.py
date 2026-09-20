"""本地化自检工具（对应 Rust 版 localization.rs 里生成/核对键集合的测试）。

用法::

    python -m localization.check          # 检查
    python -m localization.check --list   # 顺便列出所有键

它会做三件事：

1. 收集代码里通过 ``t("key")`` / ``T("key")`` 用到的键；
2. 与 ``localization/*.json`` 里定义的键对比，报告**缺失**（用而未定义，会失败）
   与**未使用**（定义而未用，仅提示）；
3. 扫描仍是硬编码中文的字符串字面量（docstring、``if __name__ == "__main__"``
   里的测试夹具、以及生成脚本目录除外），有则失败。

退出码非 0 表示有问题，可直接接进 CI。
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCALIZATION_DIR = ROOT / "localization"

# 不参与扫描的目录
SKIP_PARTS = {
    "localization", ".venv", "__pycache__", "releaseBuild",
    "QQPilot-1.5.10", "download", "useollamainVM", "Extensions", "node_modules",
}

_HAN = re.compile(r"[\u4e00-\u9fff]")
_JS_CALL = re.compile(r"\b[Tt]\(\s*\"([^\"]+)\"\s*[,)]")
_HTML_ATTR = re.compile(r"data-i18n(?:-aria-label)?=\"([^\"]+)\"")
_JS_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
# 只去掉整行注释；行内 // 可能是字符串里的 URL（如 http://...），不能一概剥掉
_JS_LINE_COMMENT = re.compile(r"^[ \t]*//.*$", re.MULTILINE)
_CSS_CONTENT = re.compile(r'content:\s*"([^"]*)"')


# ---------------------------------------------------------------------------
# 键的收集
# ---------------------------------------------------------------------------
def _py_used_keys(tree: ast.AST) -> set[str]:
    keys: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        if name not in ("t", "_t"):
            continue
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            keys.add(node.args[0].value)
    return keys


def used_keys() -> set[str]:
    keys: set[str] = set()
    for path in ROOT.rglob("*.py"):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        try:
            keys |= _py_used_keys(ast.parse(path.read_text(encoding="utf-8-sig")))
        except Exception:  # noqa: BLE001
            continue
    for path in list(ROOT.rglob("*.js")) + list(ROOT.rglob("*.html")):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8-sig")
        keys |= set(_HTML_ATTR.findall(text))
        text = _JS_BLOCK_COMMENT.sub("", text)
        text = _JS_LINE_COMMENT.sub("", text)
        keys |= set(_JS_CALL.findall(text))
    return keys


def defined_keys() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for path in sorted(LOCALIZATION_DIR.glob("*.json")):
        with open(path, "r", encoding="utf-8") as handle:
            result[path.stem] = json.load(handle)
    return result


# ---------------------------------------------------------------------------
# 硬编码扫描
# ---------------------------------------------------------------------------
def _docstring_ids(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                ids.add(id(body[0].value))
    return ids


def _main_guard_ids(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if isinstance(test, ast.Compare) and isinstance(test.left, ast.Name) and test.left.id == "__name__":
            ids.update(id(sub) for sub in ast.walk(node))
    return ids


def hardcoded_python() -> list[str]:
    findings: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        skip = _docstring_ids(tree) | _main_guard_ids(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                    and id(node) not in skip and _HAN.search(node.value):
                findings.append(f"{path.relative_to(ROOT)}:{node.lineno}: {node.value!r}")
    return findings


def hardcoded_js() -> list[str]:
    findings: list[str] = []
    for path in list(ROOT.rglob("*.js")) + list(ROOT.rglob("*.html")):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        text = _JS_BLOCK_COMMENT.sub("", path.read_text(encoding="utf-8-sig"))
        text = _JS_LINE_COMMENT.sub("", text)
        for lineno, line in enumerate(text.splitlines(), 1):
            if _HAN.search(line):
                findings.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")
    return findings


def hardcoded_css() -> list[str]:
    """CSS 里 content: "..." 的可见文案（应改用 --i18n 变量注入）。"""
    findings: list[str] = []
    for path in sorted(ROOT.rglob("*.css")):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            for match in _CSS_CONTENT.finditer(line):
                if _HAN.search(match.group(1)):
                    findings.append(f"{path.relative_to(ROOT)}:{lineno}: {match.group(1)!r}")
    return findings


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def run(list_keys: bool = False) -> int:
    used = used_keys()
    defined = defined_keys()
    all_defined: set[str] = set()
    for table in defined.values():
        all_defined |= set(table)

    missing = sorted(used - all_defined)
    unused = sorted(all_defined - used)
    hard = hardcoded_python() + hardcoded_js() + hardcoded_css()

    print(f"语言文件: {', '.join(sorted(defined)) or '(无)'}")
    print(f"使用中的键: {len(used)}    已定义的键: {len(all_defined)}")
    if list_keys:
        print("已定义键:")
        for key in sorted(all_defined):
            print(f"  {key}")

    if missing:
        print(f"\n❌ 缺失 {len(missing)} 个翻译（代码在用但 JSON 里没有）:")
        for key in missing:
            print(f"  {key}")
    if unused:
        print(f"\n⚠️  未使用 {len(unused)} 个翻译（JSON 里有但代码没引用）:")
        for key in unused:
            print(f"  {key}")
    if hard:
        print(f"\n❌ 仍有 {len(hard)} 处硬编码文本:")
        for item in hard:
            print(f"  {item}")

    ok = not missing and not hard
    print("\n✅ 本地化检查通过" if ok else "\n检查未通过")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run("--list" in sys.argv))
