"""
WebSocket 连接器：连接 OneBot 11 客户端（正向 / 反向两种模式）

设计要点（相对旧版修正）：
- 线程安全：Flask（entry.py）线程只负责"入队"，真正的收发在独立 daemon 线程，
  不再跨线程混用 asyncio 事件循环。
- 发送不阻塞：SendMessage() 立即入队返回，WS 线程循环里把队列消息发出去，
  不再依赖"收到消息时才捎带发送"。
- 自动启动：模块导入即启动连接线程（daemon），entry.py 无需额外调用。
- 断线重连：正向模式断开后按间隔自动重连。
- 编码安全日志：stdout 可能是 cp1252，中文打印会抛 UnicodeEncodeError 杀死
  daemon 线程，统一用 _log 兜底。
- 兼容旧接口：SetMessageReceiveBuffer / SendMessage / message_receive_buffer 保持不变。
"""
import json
import queue
import threading
import time
from typing import Callable, Optional

import json5
import websockets
from websockets.sync.client import connect
from websockets.sync.server import serve
from config import LoadConfig

from clr import *


from log2 import LogColored
# import logging
# logging.basicConfig(level=logging.DEBUG)

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
# config = json5.loads(open('config.json5', 'r', encoding='utf8').read())
serverUrl: str = LoadConfig()['websocket_server']
reverse: bool = LoadConfig().get('reverse', False)
authorization: str = LoadConfig().get('authorization', '')
reconnect_interval: float = LoadConfig().get('reconnect_interval',0.01)

# ---------------------------------------------------------------------------
# 全局状态
# ---------------------------------------------------------------------------
# 事件处理器（由 translateCompletion 注册），收到 JSON 后回调
_event_handler: Optional[Callable] = None

# 待发送队列（entry.py 线程入队，WS 线程发送）
send_queue: "queue.Queue[dict]" = queue.Queue()

# 消息接收缓冲区（旧接口，entry.py 用 SetMessageReceiveBuffer 替换引用）
message_receive_buffer: list[str] = []

# 反向模式下的已连接客户端
connected_clients: list = []


def set_event_handler(handler: Optional[Callable]):
    """注册事件处理器，收到 OneBot 消息时以解析后的 dict 调用"""
    global _event_handler
    _event_handler = handler


def get_event_handler() -> Optional[Callable]:
    return _event_handler


# ---------------------------------------------------------------------------
# 收发核心
# ---------------------------------------------------------------------------

def _on_message(raw: str):
    """处理一条收到的原始消息：入缓冲区 + 解析 JSON 后回调事件处理器"""
    message_receive_buffer.append(raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        LogColored("[WebSocket] JSON 解析错误:", e,Fore.RED)
        return
    if _event_handler is not None:
        try:
            _event_handler(data)
        except Exception as e:  # 处理器异常不能杀死 WS 线程
            LogColored("[WebSocket] 事件处理器异常:", e,Fore.RED)


def _drain_send_queue(ws) -> None:
    """把待发送队列里的消息全部发出"""
    while not send_queue.empty():
        try:
            message = send_queue.get_nowait()
            LogColored(f"[WebSocket]发送{Fore.RESET}{message}",Fore.LIGHTCYAN_EX)
            
        except queue.Empty:
            break
        ws.send(json.dumps(message, ensure_ascii=False))


def _recv_loop(ws, poll_interval: float = 0.05) -> None:
    """单连接的收发循环：非阻塞轮询接收 + 发送队列排空"""
    while True:
        _drain_send_queue(ws)
        try:
            raw = ws.recv(timeout=poll_interval)
        except TimeoutError:
            continue  # 超时没消息，继续轮询
        except websockets.exceptions.ConnectionClosed:
            LogColored("[WebSocket] 连接已关闭",Fore.YELLOW)
            return
        _on_message(raw)


# ---------------------------------------------------------------------------
# 正向模式（reverse=False）：主动连接 OneBot 服务端
# ---------------------------------------------------------------------------

def _client_loop():
    headers = {}
    if authorization:
        headers['Authorization'] = f'Bearer {authorization}'
    # OneBot 反向 WS 服务端（aiocqhttp / CQHttp 等）握手必需头：
    # - X-Client-Role：连接角色（universal = 一条连接同时提供事件与 API）
    # - X-Self-ID：当前机器人账号，缺失时服务端抛 KeyError → 400
    headers['X-Client-Role'] = 'universal'
    headers['X-Self-ID'] = str(LoadConfig().get('account_id', '10001'))
    while True:
        try:
            LogColored("[WebSocket] 连接", serverUrl,Fore.RESET)
            # print(headers)
            with connect(serverUrl, additional_headers=headers, max_size=None) as ws:
                
                LogColored("[WebSocket] 已连接",Fore.RESET)
                _recv_loop(ws)
        except Exception as e:
            LogColored("[WebSocket] 连接失败:", e,Fore.RED)
        LogColored(f"[WebSocket] {reconnect_interval}s 后重连 ...",Fore.LIGHTRED_EX)
        time.sleep(reconnect_interval)


# ---------------------------------------------------------------------------
# 反向模式（reverse=True）：等待 OneBot 客户端连接进来
# ---------------------------------------------------------------------------

# 心跳推送间隔（秒）：远小于 OneBot 客户端的超时阈值（napcat-adapter 为
# interval*2 = 60s），保持其"消息网关已激活路由"状态不因心跳超时被撤销。
HEARTBEAT_INTERVAL_SEC: float = 10.0
# 心跳元事件中的 self_id，与 get_login_info 应答保持一致（translateCompletion）
BOT_SELF_ID: int = int(LoadConfig().get("account_id",55555))


def _push_heartbeat(ws) -> None:
    """向单个 OneBot 客户端推送 heartbeat 元事件（OneBot 11 标准格式）。"""
    ws.send(json.dumps({
        "post_type": "meta_event",
        "meta_event_type": "heartbeat",
        "interval": 30000,  # 毫秒，符合 OneBot 11 标准
        "status": {"online": True, "good": True},
        "self_id": BOT_SELF_ID,
    }, ensure_ascii=False))


def _start_heartbeat(ws) -> "threading.Event":
    """为单个连接启动心跳推送 daemon 线程，返回 stop 事件。"""
    stop = threading.Event()

    def _loop():
        while not stop.wait(HEARTBEAT_INTERVAL_SEC):
            try:
                _push_heartbeat(ws)
            except Exception:
                return  # 连接已断开，停止推送

    threading.Thread(target=_loop, daemon=True, name="websocket-heartbeat").start()
    return stop


def _handle_client(ws):
    """反向模式下单个客户端的处理（sync server 为每个连接起独立线程）"""
    # 连接有效时缓存远端地址；连接关闭后访问 ws.remote_address 会抛 OSError 10038
    try:
        remote = ws.remote_address
    except Exception:
        remote = "unknown"
    LogColored("[WebSocket] 客户端连接:", remote,Fore.LIGHTGREEN_EX)
    connected_clients.append(ws)
    stop_heartbeat = _start_heartbeat(ws)
    try:
        _recv_loop(ws)
    finally:
        stop_heartbeat.set()
        if ws in connected_clients:
            connected_clients.remove(ws)
        LogColored("[WebSocket] 客户端断开:", remote,Fore.LIGHTBLUE_EX)


def _server_loop():
    host, port = serverUrl.split(':')[1:]
    host='ws:'+host
    LogColored("[WebSocket] 反向服务器启动:", host, port,Fore.LIGHTGREEN_EX)
    with serve(_handle_client, "localhost", int(port), max_size=None) as server:
        server.serve_forever()


# ---------------------------------------------------------------------------
# 对外接口
# ---------------------------------------------------------------------------

def SendMessage(message: dict) -> None:
    """发送一条消息（立即入队返回，不阻塞调用线程）"""
    send_queue.put(message)
    LogColored("[WebSocket]添加到了消息队列",Fore.LIGHTGREEN_EX)


def SendMessageString(message: str) -> None:
    """旧接口：发送 JSON 字符串"""
    try:
        send_queue.put(json.loads(message))
    except json.JSONDecodeError:
        LogColored("[WebSocket] SendMessageString: 非法 JSON", message[:100],Fore.RED)


websocketSendMessage = SendMessageString  # 兼容旧命名


def SetMessageReceiveBuffer(src: list) -> None:
    """旧接口：替换接收缓冲区引用（entry.py 使用）"""
    global message_receive_buffer
    message_receive_buffer = src


def has_active_connection() -> bool:
    """是否有可用的连接"""
    if reverse:
        return len(connected_clients) > 0
    return True  # 正向模式下连接线程自管理，简化处理


# ---------------------------------------------------------------------------
# 启动
# ---------------------------------------------------------------------------

_thread: Optional[threading.Thread] = None


def start() -> threading.Thread:
    """在 daemon 线程中启动 WebSocket（重复调用只启动一次）"""
    global _thread
    if _thread is not None and _thread.is_alive():
        return _thread
    target = _server_loop if reverse else _client_loop
    _thread = threading.Thread(target=target, daemon=True, name="websocket-connector")
    _thread.start()
    LogColored("[WebSocket] 线程已启动（", "反向" if reverse else "正向", "模式）",Fore.YELLOW)
    return _thread


# 模块导入即自动启动（entry.py import 后即可收发）
start()


if __name__ == '__main__':
    # 单独运行时保持进程存活
    threading.Event().wait()
