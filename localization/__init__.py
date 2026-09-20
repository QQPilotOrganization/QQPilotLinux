"""本地化（i18n）模块 —— 参照 QQPilot Rust 的 localization.rs 模式。

用法::

    from localization import t
    print(t("loading.start"))   # → "正在初始化"

翻译来源: ``localization/<language>.json``（如 ``zh_CN.json``）。
语言由 ``config.ini [general] language`` 决定，默认 ``zh_CN``。
若找不到对应翻译，返回 ``"X" + key``（与 Rust 版行为一致）。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_DIR = Path(__file__).resolve().parent

_cache: dict[str, str] = {}
_current_lang: str = ""


def _detect_language() -> str:
    """从 config.ini 读取 language，缺省 zh_CN。"""
    try:
        import configparser
        parser = configparser.ConfigParser(interpolation=None)
        config_path = _DIR.parent / "config.ini"
        if config_path.exists():
            parser.read(str(config_path), encoding="utf-8")
            return parser.get("general", "language", fallback="zh_CN")
    except Exception:
        pass
    return "zh_CN"


def _load(lang: str) -> dict[str, str]:
    """加载指定语言的 JSON 翻译文件。"""
    path = _DIR / f"{lang}.json"
    if not path.exists():
        # 回退到 zh_CN
        path = _DIR / "zh_CN.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data: dict[str, str] = json.load(f)
            return data
    except Exception:
        return {}


def init(lang: str | None = None) -> None:
    """初始化/切换语言。可重复调用。"""
    global _cache, _current_lang
    _current_lang = lang or _detect_language()
    _cache = _load(_current_lang)


def t(key: str, **kwargs: Any) -> str:
    """获取翻译。支持 ``{name}`` 占位符替换。

    ``t("error.timeout", seconds=30)``
    → 若 ``zh_CN.json`` 中 ``error.timeout`` = ``"超时（{seconds}秒）"``
    → 返回 ``"超时（30秒）"``。
    """
    if not _cache:
        init()
    text = _cache.get(key).replace("PROGRAM_NAME",_cache.get('program.name'))
    if text is None:
        return "X" + key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


def get_all() -> dict[str, str]:
    """返回当前语言的全部翻译键值对。"""
    if not _cache:
        init()
    return dict(_cache)


def current_language() -> str:
    """返回当前语言代码。"""
    if not _current_lang:
        init()
    return _current_lang


def available_languages() -> list[str]:
    """返回可用语言列表。"""
    langs: list[str] = []
    for f in _DIR.iterdir():
        if f.suffix == ".json" and not f.name.startswith("_"):
            langs.append(f.stem)
    return sorted(langs)


# 模块导入时自动初始化
init()
