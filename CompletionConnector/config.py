"""CompletionConnector 配置加载（QQPilotLinux 内嵌版）

与上游 CompletionConnector 共用同一份源码，只替换了配置来源：

1. 优先读取 QQPilotLinux 根目录的 ``config.ini``（``server_url = onebot``
   时启用内嵌桥接），字段映射：

   ==========================  =========================================
   config.ini                  CompletionConnector
   ==========================  =========================================
   api_key                     authorization（OneBot 鉴权）
   websocket_server            websocket_server（反向 WS 监听地址）
   account_id                  account_id（机器人账号）
   reverse                     reverse（正向 / 反向 WebSocket）
   name                        nickname（机器人昵称）
   remote_server_timeout       timeout（等待 OneBot 回复的超时秒数）
   ==========================  =========================================

2. ``config.ini`` 里没有的键，回退到同目录的 ``config.json5``（独立运行
   模式仍可直接运行本包，此时完全由 ``config.json5`` 决定）。
"""
import configparser
import os

try:  # 仅在独立运行（config.json5）时需要
    import json5
except ImportError:  # pragma: no cover - QQPilotLinux 运行时可无 json5
    json5 = None

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIG_JSON5 = os.path.join(_BASE_DIR, 'config.json5')

# config.ini 中与本包同名的键（无需映射，直接透传）
_PASSTHROUGH_KEYS = ('websocket_server', 'account_id', 'reverse')


def _strip_inline_comment(value: str) -> str:
    """去掉 config.ini 里的行内注释（如 ``abcd ; authorization``）。

    configparser 默认不识别行内注释，而 QQPilotLinux 的 config.ini 习惯用
    ``;`` 在值后面写说明，这里统一剥掉，避免 api_key 等把注释一起带上。
    """
    return value.split(';', 1)[0].split('#', 1)[0].strip()


def _find_config_ini():
    """在 CWD（QQPilotLinux 根目录）和本包目录的上一层查找 config.ini"""
    candidates = [
        os.path.join(os.getcwd(), 'config.ini'),
        os.path.join(os.path.dirname(_BASE_DIR), 'config.ini'),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _load_ini(path: str) -> dict:
    parser = configparser.ConfigParser()
    parser.read(path, encoding='utf-8')
    if not parser.has_section('general'):
        return {}
    general = parser['general']

    def get(key: str, default: str = '') -> str:
        value = general.get(key, default)
        return _strip_inline_comment(value)

    cfg: dict = {}
    # api_key -> authorization
    if general.get('api_key', None) is not None:
        cfg['authorization'] = get('api_key')
    # 同名键直接透传
    for key in _PASSTHROUGH_KEYS:
        if general.get(key, None) is not None:
            cfg[key] = get(key)
    if cfg.get('reverse') is not None:
        cfg['reverse'] = str(cfg['reverse']).strip().lower() in ('1', 'true', 'yes', 'on')
    # 其余映射
    if general.get('name', None) is not None:
        cfg['nickname'] = get('name')
    if general.get('remote_server_timeout', None) is not None:
        try:
            cfg['timeout'] = int(get('remote_server_timeout') or 200)
        except ValueError:
            pass
    # 内嵌桥接固定使用 QQPilot 专用的翻译实现
    cfg['translation_impl'] = 'qqpilotTranslation'
    return cfg


def _load_json5() -> dict:
    if json5 is None:
        return {}
    try:
        with open(_CONFIG_JSON5, 'r', encoding='utf8') as f:
            return json5.loads(f.read())
    except Exception:
        return {}


def LoadConfig() -> dict:
    cfg = _load_json5()
    ini_path = _find_config_ini()
    if ini_path is not None:
        ini_cfg = _load_ini(ini_path)
        if ini_cfg:
            cfg.update(ini_cfg)
    return cfg


def GetTimeout():
    return int(LoadConfig().get('timeout', 150))
