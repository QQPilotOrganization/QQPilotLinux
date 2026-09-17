"""统一 Web 界面的后端：pywebview 宿主 + Python<->JS API。

约定
====
- 前端在 ``web/index.html``、``web/style.css``、``web/app.js``，通过
  ``window.pywebview.api.*`` 调用本模块 :class:`Api` 的公开方法；
- 方法参数/返回值都必须是 JSON 可序列化对象；
- 耗时操作（升级、导入图片）在 pywebview 的工作线程里执行，并通过
  ``window.UI.emit(event, payload)`` 把进度推回前端。
"""
from __future__ import annotations

import ast
import configparser
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import webview

# ---------------------------------------------------------------------------
# 路径与常量
# ---------------------------------------------------------------------------
WEBUI_DIR = Path(__file__).resolve().parent
ROOT = WEBUI_DIR.parent  # QQPilotLinux 根目录
WEB_DIR = WEBUI_DIR / "web"

CONFIG_FILE = ROOT / "config.ini"
TOKEN_FILE = ROOT / "tokencount.txt"
EXTENSIONS_DIR = ROOT / "Extensions"
IMAGES_DIR = ROOT / "Images"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".svg"}

# config.ini [general] 的兜底默认值（对齐原 Option5.init_default_config）
DEFAULTS: dict[str, str] = {
    "version": "w",
    "name": "neko",
    "width": "1285",
    "height": "720",
    "scale": "1.0",
    "maximagecount": "1",
    "modelname": "huihui_ai/deepseek-r1-abliterated:8b",
    "isvisionmodel": "False",
    "api_key": "abcd",
    "server_url": "builtin",
    "scroll": "4",
    "withimage": "True",
    "autologin": "False",
    "autofocusing": "True",
    "sendimagepossibility": "40",
    "nt_data": "None",
    "atdetect": "False",
    "remote_server_timeout": "300",
    "tab_times": "8",
    "forceollamaapi": "False",
    "sleep": "0",
    "websocket_server": "ws://localhost:3001",
    "account_id": "80586",
    "reverse": "True",
    "system": "",
}

SERVER_MODES = ("ollama", "builtin", "onebot")


# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------
def _strip_inline_comment(value: str) -> str:
    """config.ini 里习惯写 ``; 说明`` 行内注释，这里统一剥掉。"""
    return value.split(";", 1)[0].split("#", 1)[0].strip()


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _is_linux() -> bool:
    return platform.system() == "Linux"


# ---------------------------------------------------------------------------
# config.ini 读写
# ---------------------------------------------------------------------------
def _read_config() -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    if CONFIG_FILE.exists():
        try:
            parser.read(CONFIG_FILE, encoding="utf-8")
        except Exception:
            pass
    if not parser.has_section("general"):
        parser.add_section("general")
    for key, value in DEFAULTS.items():
        if not parser.has_option("general", key):
            parser.set("general", key, value)
    return parser


def _raw(parser: configparser.ConfigParser, key: str) -> str:
    """取原始值（不剥注释）—— system 这类多行文本必须用原始值。"""
    try:
        return parser.get("general", key)
    except Exception:
        return DEFAULTS.get(key, "")


def _value(parser: configparser.ConfigParser, key: str) -> str:
    return _strip_inline_comment(_raw(parser, key))


def _read_tokens() -> int:
    try:
        return int(TOKEN_FILE.read_text(encoding="utf-8").strip() or 0)
    except Exception:
        return 0


def _write_tokens(value: int) -> None:
    TOKEN_FILE.write_text(str(int(value)), encoding="utf-8")


# ---------------------------------------------------------------------------
# 扩展描述解析（对齐原 extensionViewer）
# ---------------------------------------------------------------------------
def _extract_description(path: Path) -> str:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "description":
                        if isinstance(node.value, ast.Constant):
                            return str(node.value.value).replace("\n", " ")
        return "无描述"
    except Exception as exc:  # noqa: BLE001
        return f"解析错误：{exc}"


# ---------------------------------------------------------------------------
# JS API
# ---------------------------------------------------------------------------
class Api:
    """暴露给前端的接口集合（方法名即 JS 端 ``pywebview.api.<name>``）。"""

    def __init__(self, page: str = "launch", json_target: str = "") -> None:
        self._window: Optional[webview.Window] = None
        self.page = page
        self.json_target = json_target
        self._proc: Optional[subprocess.Popen] = None

    # -- 宿主 ---------------------------------------------------------------
    def attach(self, window: "webview.Window") -> None:
        self._window = window

    def _emit(self, event: str, payload: Any = None) -> None:
        """把事件推回前端：window.UI.emit(event, payload)。"""
        if self._window is None:
            return
        try:
            self._window.evaluate_js(
                "window.UI && window.UI.emit("
                f"{json.dumps(event)}, {json.dumps(payload, ensure_ascii=False)}"
                ")"
            )
        except Exception:  # noqa: BLE001 - 窗口已关闭时静默
            pass

    # -- 引导 ---------------------------------------------------------------
    def bootstrap(self) -> dict:
        """前端加载后第一件事：拿到当前页面与运行态。"""
        return {
            "page": self.page,
            "jsonTarget": self.json_target,
            "app": self.app_info(),
        }

    def app_info(self) -> dict:
        parser = _read_config()
        return {
            "title": "QQPilot",
            "version": _value(parser, "version"),
            "platform": platform.system(),
            "root": str(ROOT),
            "running": self.is_running(),
            "onebot": _value(parser, "server_url").lower() == "onebot",
            "tokens": _read_tokens(),
        }

    # -- 运行设置 -----------------------------------------------------------
    def get_config(self) -> dict:
        parser = _read_config()
        server_url = _value(parser, "server_url")
        mode = server_url.lower()
        if mode not in SERVER_MODES:
            mode = "custom"
        return {
            "name": _value(parser, "name"),
            "width": _value(parser, "width"),
            "height": _value(parser, "height"),
            "maximagecount": _value(parser, "maximagecount"),
            "modelname": _value(parser, "modelname"),
            "isvisionmodel": _as_bool(_value(parser, "isvisionmodel")),
            "api_key": _value(parser, "api_key"),
            "server_mode": mode,
            "custom_server_url": server_url if mode == "custom" else "",
            "forceollamaapi": _as_bool(_value(parser, "forceollamaapi")),
            "scroll": _value(parser, "scroll"),
            "withimage": _as_bool(_value(parser, "withimage")),
            "autologin": _as_bool(_value(parser, "autologin")),
            "autofocusing": _as_bool(_value(parser, "autofocusing")),
            "sendimagepossibility": int(float(_value(parser, "sendimagepossibility") or 0)),
            "atdetect": _as_bool(_value(parser, "atdetect")),
            "remote_server_timeout": _value(parser, "remote_server_timeout"),
            "tab_times": _value(parser, "tab_times") or "8",
            "system": _raw(parser, "system"),
            "websocket_server": _value(parser, "websocket_server"),
            "account_id": _value(parser, "account_id"),
            "reverse": _as_bool(_value(parser, "reverse")),
            "tokens": _read_tokens(),
        }

    def save_config(self, payload: dict) -> dict:
        """校验并写回 config.ini。返回 {ok, fields:{key:message}, message}。"""
        payload = payload or {}
        fields: dict[str, str] = {}

        def require_number(key: str, label: str) -> None:
            raw = str(payload.get(key, "")).strip()
            try:
                float(raw)
            except (TypeError, ValueError):
                fields[key] = f"{label}需要是数字"

        require_number("width", "窗口宽度")
        require_number("height", "窗口高度")
        require_number("maximagecount", "解析图片数")
        require_number("scroll", "框选消息时长")
        require_number("remote_server_timeout", "远程服务器超时")

        try:
            possibility = int(payload.get("sendimagepossibility", 0))
            if not 0 <= possibility <= 100:
                raise ValueError
        except (TypeError, ValueError):
            fields["sendimagepossibility"] = "发送图片概率需要在 0–100 之间"

        server_mode = str(payload.get("server_mode", "")).lower()
        custom_url = str(payload.get("custom_server_url", "")).strip()
        if server_mode == "custom" and not custom_url:
            fields["custom_server_url"] = "请填写服务器地址"
        if server_mode == "onebot":
            if not str(payload.get("websocket_server", "")).strip():
                fields["websocket_server"] = "请填写 OneBot WebSocket 地址"

        tab_times = str(payload.get("tab_times", "8")).strip()
        if tab_times not in ("7", "8"):
            fields["tab_times"] = "只能是 7 或 8"

        if fields:
            return {"ok": False, "fields": fields, "message": "有字段需要修正"}

        parser = _read_config()
        general = parser["general"]

        def put(key: str, value: Any) -> None:
            general[key] = str(value)

        put("name", payload.get("name", ""))
        put("width", str(payload.get("width", "")).strip())
        put("height", str(payload.get("height", "")).strip())
        put("maximagecount", str(payload.get("maximagecount", "")).strip())
        put("modelname", payload.get("modelname", ""))
        put("isvisionmodel", bool(payload.get("isvisionmodel")))
        put("api_key", payload.get("api_key", ""))
        put("forceollamaapi", bool(payload.get("forceollamaapi")))
        put("scroll", str(payload.get("scroll", "")).strip())
        put("withimage", bool(payload.get("withimage")))
        put("autologin", bool(payload.get("autologin")))
        put("autofocusing", bool(payload.get("autofocusing")))
        put("sendimagepossibility", int(possibility))
        put("atdetect", bool(payload.get("atdetect")))
        put("remote_server_timeout", str(payload.get("remote_server_timeout", "")).strip())
        put("tab_times", tab_times)
        put("system", str(payload.get("system", "")).strip())
        put("websocket_server", str(payload.get("websocket_server", "")).strip())
        put("account_id", str(payload.get("account_id", "")).strip())
        put("reverse", bool(payload.get("reverse")))

        if server_mode == "custom":
            put("server_url", custom_url or "custom")
        else:
            put("server_url", server_mode)

        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as handle:
                parser.write(handle)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "fields": {}, "message": f"写入失败：{exc}"}

        return {"ok": True, "fields": {}, "message": "设置已保存"}

    def reset_tokens(self) -> dict:
        _write_tokens(0)
        return {"ok": True, "tokens": 0, "message": "计数器已归零"}

    # -- 额外参数（JSON） ---------------------------------------------------
    def read_json(self, path: str = "") -> dict:
        target = self._resolve(path or self.json_target or "extra.json")
        if target is None:
            return {"ok": False, "error": "路径无效"}
        if not target.exists():
            return {"ok": True, "path": str(target), "text": "{\n    \n}\n", "exists": False}
        try:
            return {"ok": True, "path": str(target), "text": target.read_text(encoding="utf-8"), "exists": True}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "path": str(target), "error": str(exc)}

    def write_json(self, payload: dict) -> dict:
        payload = payload or {}
        target = self._resolve(payload.get("path", "") or self.json_target or "extra.json")
        if target is None:
            return {"ok": False, "message": "路径无效"}
        text = str(payload.get("text", ""))
        try:
            json.loads(text or "{}")
        except json.JSONDecodeError as exc:
            return {"ok": False, "message": f"JSON 解析失败：第 {exc.lineno} 行 {exc.msg}"}
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "message": f"写入失败：{exc}"}
        return {"ok": True, "path": str(target), "message": f"已保存 {target.name}"}

    # -- 文件与目录 ---------------------------------------------------------
    def pick_folder(self, title: str = "选择文件夹") -> dict:
        if self._window is None:
            return {"ok": False, "error": "窗口未就绪"}
        try:
            result = self._window.create_file_dialog(
                webview.FOLDER_DIALOG, directory=str(ROOT)
            )
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        if not result:
            return {"ok": True, "path": ""}
        path = result[0]
        if isinstance(path, (list, tuple)):
            path = path[0]
        return {"ok": True, "path": str(path)}

    def open_path(self, path: str = "") -> dict:
        target = self._resolve(path or ".")
        if target is None or not target.exists():
            return {"ok": False, "error": "路径不存在"}
        try:
            if _is_linux():
                subprocess.Popen(["xdg-open", str(target)])
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(target)])
            else:
                os.startfile(str(target))  # type: ignore[attr-defined]
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    # -- 扩展管理 -----------------------------------------------------------
    def list_extensions(self) -> dict:
        EXTENSIONS_DIR.mkdir(exist_ok=True)
        items: list[dict] = []
        for path in sorted(EXTENSIONS_DIR.glob("*.py")):
            if path.name.startswith("__"):
                continue
            items.append({
                "name": path.stem,
                "description": _extract_description(path),
                "enabled": True,
            })
        for path in sorted(EXTENSIONS_DIR.glob("*.disabled")):
            items.append({
                "name": path.name[: -len(".disabled")],
                "description": "该扩展当前被禁用",
                "enabled": False,
            })
        items.sort(key=lambda item: (not item["enabled"], item["name"].lower()))
        return {"ok": True, "items": items, "dir": str(EXTENSIONS_DIR)}

    def set_extension(self, name: str, enabled: bool) -> dict:
        name = str(name or "").strip()
        if not name or "/" in name or "\\" in name or ".." in name:
            return {"ok": False, "message": "扩展名无效"}
        enabled_path = EXTENSIONS_DIR / f"{name}.py"
        disabled_path = EXTENSIONS_DIR / f"{name}.disabled"
        try:
            if enabled and disabled_path.exists():
                if enabled_path.exists():
                    return {"ok": False, "message": f"{name} 已存在启用的同名扩展"}
                disabled_path.rename(enabled_path)
                message = f"已启用 {name}"
            elif not enabled and enabled_path.exists():
                if disabled_path.exists():
                    return {"ok": False, "message": f"{name} 已存在禁用的同名扩展"}
                enabled_path.rename(disabled_path)
                message = f"已禁用 {name}"
            else:
                return {"ok": False, "message": "扩展状态已变化，请刷新后重试"}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "message": f"操作失败：{exc}"}
        result = self.list_extensions()
        result["message"] = message
        return result

    # -- 升级助手 -----------------------------------------------------------
    def start_upgrade(self, dest: str) -> dict:
        dest = str(dest or "").strip()
        if not dest:
            return {"ok": False, "message": "请先选择目标文件夹"}
        dest_path = Path(dest).expanduser()
        if not dest_path.parent.exists():
            return {"ok": False, "message": f"父目录不存在：{dest_path.parent}"}
        try:
            self._emit("upgrade:log", {"text": f"开始升级 → {dest_path}"})
            copied = self._copy_tree_for_upgrade(ROOT, dest_path)
            self._emit("upgrade:log", {"text": f"完成，共处理 {copied} 个文件"})
            return {"ok": True, "message": "升级完成", "copied": copied}
        except Exception as exc:  # noqa: BLE001
            self._emit("upgrade:log", {"text": f"升级失败：{exc}"})
            return {"ok": False, "message": f"升级失败：{exc}"}

    def _merge_config_files(self, src_ini: Path, dst_ini: Path) -> None:
        if not dst_ini.exists():
            shutil.copy2(src_ini, dst_ini)
            self._emit("upgrade:log", {"text": f"复制 config.ini → {dst_ini}"})
            return
        src_config = configparser.ConfigParser(interpolation=None)
        src_config.read(src_ini, encoding="utf-8")
        dst_config = configparser.ConfigParser(interpolation=None)
        dst_config.read(dst_ini, encoding="utf-8")
        for section in src_config.sections():
            if not dst_config.has_section(section):
                dst_config.add_section(section)
            for key, value in src_config.items(section):
                if not dst_config.has_option(section, key):
                    dst_config.set(section, key, value)
        with open(dst_ini, "w", encoding="utf-8") as handle:
            dst_config.write(handle)
        self._emit("upgrade:log", {"text": f"合并 config.ini（保留目标已有值）→ {dst_ini}"})

    def _copy_tree_for_upgrade(self, src_dir: Path, dst_dir: Path) -> int:
        dst_dir.mkdir(parents=True, exist_ok=True)
        count = 0
        skip_dirs = {".venv", "__pycache__", ".git", "releaseBuild", "Images"}
        for src_file in src_dir.rglob("*"):
            if any(part in skip_dirs for part in src_file.relative_to(src_dir).parts):
                continue
            if not src_file.is_file():
                continue
            rel = src_file.relative_to(src_dir)
            dst_file = dst_dir / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            count += 1
            name = rel.name.lower()
            if name == "config.ini":
                self._merge_config_files(src_file, dst_file)
            elif name in ("system.txt", "extra.json") and dst_file.exists():
                self._emit("upgrade:log", {"text": f"保留用户配置 → {dst_file}"})
            else:
                shutil.copy2(src_file, dst_file)
                self._emit("upgrade:log", {"text": f"复制 {rel}"})
        return count

    # -- 图片导入 -----------------------------------------------------------
    def import_images(self, source: str) -> dict:
        source = str(source or "").strip()
        if not source or not os.path.isdir(source):
            return {"ok": False, "message": "请选择有效的源文件夹"}
        target = IMAGES_DIR
        target.mkdir(parents=True, exist_ok=True)
        files = [
            name for name in os.listdir(source)
            if os.path.isfile(os.path.join(source, name))
            and os.path.splitext(name)[1].lower() in IMAGE_EXTENSIONS
        ]
        if not files:
            self._emit("images:log", {"text": "未找到任何支持的图片文件"})
            return {"ok": True, "success": 0, "failure": 0, "message": "未找到任何支持的图片文件"}
        success = failure = 0
        for name in files:
            self._emit("images:log", {"text": f"正在复制 {name}"})
            try:
                shutil.copy2(os.path.join(source, name), os.path.join(target, name))
                success += 1
            except Exception as exc:  # noqa: BLE001
                failure += 1
                self._emit("images:log", {"text": f"失败 {name}：{exc}"})
        message = f"完成，成功 {success} 张，失败 {failure} 张"
        self._emit("images:log", {"text": message})
        return {"ok": True, "success": success, "failure": failure, "message": message}

    # -- 启动台 -------------------------------------------------------------
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def launch(self) -> dict:
        if self.is_running():
            return {"ok": True, "message": "QQPilot 已在运行", "running": True}
        try:
            if _is_linux():
                cmd = ["bash", "./run.sh"]
            else:
                cmd = [sys.executable, "ScreenshotToUILayout.py"]
            self._proc = subprocess.Popen(cmd, cwd=str(ROOT))
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "message": f"启动失败：{exc}", "running": False}
        return {"ok": True, "message": "已启动 QQPilot", "running": True}

    def stop(self) -> dict:
        if not self.is_running():
            return {"ok": True, "message": "QQPilot 未在运行", "running": False}
        assert self._proc is not None
        try:
            self._proc.terminate()
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "message": f"停止失败：{exc}", "running": True}
        return {"ok": True, "message": "已请求停止", "running": False}

    # -- 窗口 ---------------------------------------------------------------
    def close_window(self) -> dict:
        if self._window is not None:
            self._window.destroy()
        return {"ok": True}

    # -- 内部 ---------------------------------------------------------------
    def _resolve(self, path: Optional[str]) -> Optional[Path]:
        if path is None:
            return None
        text = str(path).strip()
        if not text:
            return None
        candidate = Path(text).expanduser()
        if not candidate.is_absolute():
            candidate = ROOT / candidate
        try:
            return candidate.resolve()
        except Exception:  # noqa: BLE001
            return candidate


def run_ui(page: str = "launch", json_target: str = "") -> None:
    """启动统一界面（必须在主线程调用）。"""
    if platform.system() == "Windows":
        # 让 WebView2 跟随系统缩放，避免高分屏下界面发虚
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:  # noqa: BLE001
            pass

    api = Api(page=page, json_target=json_target)
    window = webview.create_window(
        "QQPilot",
        url=str(WEB_DIR / "index.html"),
        js_api=api,
        width=1180,
        height=780,
        min_size=(960, 640),
        background_color="#101A21",
    )
    api.attach(window)
    try:
        webview.start()
    except Exception as exc:  # noqa: BLE001
        hint = ""
        if platform.system() == "Linux":
            hint = (
                "\nLinux 还需要一个 WebView 后端（任选其一）：\n"
                "  uv pip install \"pywebview[qt]\"        # 纯 pip，最简单\n"
                "  sudo apt install gir1.2-webkit2-4.1 python3-gi && "
                "uv pip install \"pywebview[gtk]\"\n"
            )
        raise SystemExit(f"无法启动 Web 界面：{exc}{hint}") from exc
