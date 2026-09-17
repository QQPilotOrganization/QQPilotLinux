"""OneBot 直连桥接（``server_url = onebot`` 时使用）

QQPilotLinux 直接使用 OneBot v11 协议连接 OneBot 端（如 NapCat / MaiBot），
不再额外起一个 HTTP 服务再转发。协议实现参考 CompletionConnector，
直接复用其 WebSocket 收发与消息翻译逻辑：

- ``websocketConnector``：按 ``config.ini`` 的 ``websocket_server`` /
  ``reverse`` 连接或监听 OneBot（正向 / 反向 WebSocket）；
- ``translateLayer`` + ``qqpilotTranslation``：把 QQPilot 的消息翻译成
  OneBot 消息事件，并把 OneBot 的 ``send_*_msg`` 回复翻译回文本。

``answer.getAnswer`` 在 ``server_url = onebot`` 时调用 :func:`get_answer`，
把当前会话内容直接发给 OneBot，等待它的回复作为答案。
"""
import base64
import os
import sys

_PACKAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'CompletionConnector')

_started = False


def _ensure_on_path() -> None:
    """把内嵌包目录放到 sys.path 最前，让包内的扁平 import 生效"""
    if _PACKAGE_DIR not in sys.path:
        sys.path.insert(0, _PACKAGE_DIR)


def start() -> bool:
    """启动 OneBot 直连（重复调用只初始化一次）。

    导入 ``websocketConnector`` 即自动启动连接/监听线程，
    导入 ``translateLayer`` 即注册事件处理器。
    """
    global _started
    if not _started:
        _ensure_on_path()
        import websocketConnector  # noqa: F401  导入即启动 WS 线程
        import translateLayer  # noqa: F401      导入即注册事件处理器
        _started = True
    return _started


# ---------------------------------------------------------------------------
# QQPilot ChatContent -> OneBot 消息
# ---------------------------------------------------------------------------

def _tagged_text(content) -> str:
    """把 QQPilot 的用户消息拼成 qqpilotTranslation 期望的带标签文本。

    与 QQPilot（Windows）的 ChatContent 格式保持一致：
    ``[time]\\n...\\n[username]\\n...\\n[content]\\n...``。
    """
    return (
        f"[time]\n{content.time} \n\n "
        f"[username] \n {content.username} \n\n "
        f"[content] \n {content.text}\n"
    )


def _image_to_file(path: str) -> "str | None":
    """图片文件 -> OneBot image 段的 ``file`` 值（base64:// 形式）。"""
    try:
        import CompressImage
        with open(path, 'rb') as f:
            raw = base64.b64encode(f.read()).decode('ascii')
        data_uri = CompressImage.CompressImage(f'data:image/png;base64,{raw}')
        b64 = data_uri.split(',', 1)[1] if ',' in data_uri else raw
        return 'base64://' + b64
    except Exception:
        return None


def _iter_completion_contents(content):
    """把一条 ChatContent 拆成 CompletionConnector 的 CompletionContent 列表。"""
    from completion import CompletionContent

    if content.text:
        yield CompletionContent('text', _tagged_text(content))
    for path in getattr(content, 'imagePaths', []) or []:
        if not os.path.exists(path):
            continue
        file_value = _image_to_file(path)
        if file_value:
            yield CompletionContent('image_url', file_value)


def _reply_to_text(reply: dict) -> str:
    """从翻译后的 chat completion 响应里取出文本内容。"""
    content = (
        reply.get('choices', [{}])[0]
        .get('message', {})
        .get('content')
    )
    if isinstance(content, list):
        return ''.join(
            part.get('text', '') for part in content if isinstance(part, dict)
        )
    return content or ''


def get_answer(chatContents, timeout: "float | None" = None) -> "str | None":
    """把会话内容发给 OneBot 端，等待并返回它的回复文本。

    Args:
        chatContents: ``List[ChatContent]``，即 answer.getAnswer 收到的会话。
        timeout: 等待 OneBot 回复的秒数，默认取 config.ini 的
            ``remote_server_timeout``。

    Returns:
        回复文本；没有新消息或超时无回复返回 None。
    """
    start()

    import IncomingMessageDBConnector
    import translateLayer
    import websocketConnector
    from config import GetTimeout

    if timeout is None:
        timeout = GetTimeout()

    # 只把"用户发送的"消息发给 OneBot；已发送过的通过 sqlite 去重。
    incomingDB = IncomingMessageDBConnector.IncomingMessageDB()
    newMessages: list = []
    everyMessages: list = []
    for content in chatContents or []:
        if getattr(content, 'ownByMyself', False):
            continue  # AI 自己的消息不回发给 OneBot
        for item in _iter_completion_contents(content):
            everyMessages.append(item)
            if not incomingDB.MessageExists(item.typeContent):
                newMessages.append(item)

    if not newMessages:
        return None

    events = translateLayer.ToMessageEvent(newMessages, everyMessages)
    for event in events:
        websocketConnector.SendMessage(event.BuildJson())

    reply = translateLayer.WaitForAllReplies(timeout=float(timeout))
    if reply is None:
        return None
    return _reply_to_text(reply)
