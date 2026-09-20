"""
Chat Completion API 与 OneBot 11 协议的双向翻译器

出站（chat completion → OneBot 11 消息事件）：
    ToMessageEvent() 是统一接口，按 config.json5 的 translation_impl 选择实现：
    - "qqpilot"（默认）：qqpilotTranslation.ToMessageEvent
      —— 解析 [time]/[username]/[content] 结构，用 ChatManager 聚为私聊/群聊，
        映射稳定的 user_id / group_id（加 1000000000 偏移避免与真实 QQ 号冲突）
    - "basic"：basicTranslation.ToMessageEvent
      —— 简单实现，全部按私聊处理
    所有实现的签名一致：(newMessages, allMessages) -> List[Message2.MessageEvent]，
    新增实现只需实现同签名的 ToMessageEvent 并登记到 _IMPL_MODULES。

入站（OneBot 11 → chat completion 回复）：
    HandleIncomingEvent(): 收到 OneBot 端发来的 send_private_msg / send_group_msg /
    send_msg API 调用时，翻译成 OpenAI chat completion 响应
    （choices[0].message.content），经 WaitForReply() 交给 entry.py 返回给 QQPilot。

用法（entry.py）：
    events = TranslateLayer.ToMessageEvent(newMessages, allMessages)
    for event in events: websocketConnector.SendMessage(event.BuildJson())
    reply = TranslateLayer.WaitForReply(timeout=30)
"""
import importlib
import queue
import time
import uuid
from typing import Any, List, Optional, Union


import Message2
from completion import CompletionContent

from log2 import LogColored
from version import VERSION
import websocketConnector
from clr import *
from config import LoadConfig
from localization import t

# 出站翻译实现登记表：config 中的名字 → 可导入的模块名。
# 新增实现时在此登记，并在该模块内实现 ToMessageEvent(newMessages, allMessages)。
_DEFAULT_IMPL = "qqpilotTranslation"



# 当前选中的实现名（config.json5 的 translation_impl 字段）
_translation_implement: str = LoadConfig().get('translation_impl', _DEFAULT_IMPL)


def get_translation_implement() -> str:
    """返回当前配置的翻译实现名（"qqpilot" / "basic" / ...）"""
    return _translation_implement


def get_translator_module():
    """延迟导入并返回当前选中的翻译实现模块（避免模块间循环导入）"""
    # module_name = _IMPL_MODULES.get(_translation_implement, _IMPL_MODULES[_DEFAULT_IMPL])
    return importlib.import_module( get_translation_implement())


def ToMessageEvent(
    newMessages: List[CompletionContent],
    allMessages: List[CompletionContent],
) -> List[Message2.MessageEvent]:
    """统一接口：把 chat completion 消息翻译为 OneBot 11 消息事件列表。

    实际逻辑委托给 config.json5 中 translation_impl 指定的实现模块
    （qqpilotTranslation / basicTranslation），两者签名一致。
    """
    module = get_translator_module()
    LogColored("[TranslateLayer] " + t("cc.to_onebot"),Fore.RESET)
    return module.ToMessageEvent(newMessages, allMessages)


# ---------------------------------------------------------------------------
# 入站：OneBot 11 send_*_msg → chat completion 回复
# ---------------------------------------------------------------------------

# OneBot 端允许的"发消息"动作（收到这些动作即视为 AI 回复）
SEND_ACTIONS = ("send_private_msg", "send_group_msg", "send_msg")


def ToChatCompletionMessageContent(segment: Message2.MessageSegment)-> dict[str, Union[str,Any]]:
    module=get_translator_module()
    LogColored("[TranslateLayer] " + t("cc.to_chatcompletion"),Fore.RESET)
    
    return module.ToChatCompletionMessageContent(segment)

def _parse_onebot_message(message) -> List[Message2.MessageSegment]:
    """把 OneBot message（字符串或消息段数组）统一解析为消息段列表"""
    if isinstance(message, list):
        return [Message2.MessageSegment.FromJson(seg) for seg in message]
    return Message2.ParseMessageString(str(message))


def TranslateOutgoingMessageRequestFirst(request: dict)  -> None | List[dict[str, str | Any]]:#-> Optional[dict]:
    """把 OneBot send_private_msg / send_group_msg / send_msg 调用翻译为
    OpenAI chat completion -> choices->message。

    Args:
        request: {"action": "send_private_msg", "params": {"user_id":..., "message": ...}}

    Returns:
        {OpenAI 格式响应 dict；非发送动作返回 None}
    """
    action = request.get("action")
    if action not in SEND_ACTIONS:
        return None

    params = request.get("params", {}) or {}
    segments = _parse_onebot_message(params.get("message", ""))

    content: List[dict[str, str | Any]] = [ToChatCompletionMessageContent(seg) for seg in segments]
    return content
def TranslateOutgoingMessageRequestNext(content: List[dict[str, str | Any]]) -> Optional[dict]:
    """把 OpenAI chat completion -> choices->message 翻译为 OpenAI 格式响应 dict

    Args:
        content: TranslateOutgoingMessageRequestFirst 产出的 content 段列表

    Returns:
        OpenAI 格式响应 dict；content 为空返回 None
    """
    if not content:
        return None
    # 纯文本时合并为字符串（OpenAI 兼容性最好），否则保留多模态数组
    if all(isinstance(c, dict) and c.get("type") == "text" for c in content):
        content = "".join(c["text"] for c in content)  # type: ignore

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "onebot-11",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


# ---------------------------------------------------------------------------
# 事件处理与回复等待（供 websocketConnector / entry.py 使用）
# ---------------------------------------------------------------------------

# 翻译好的 chat completion 回复队列（OneBot send_*_msg → 此队列）
translatedReplyQueue: "queue.Queue[dict[str, str | Any]]" = queue.Queue()


def _default_action_data(action: str):
    """常见动作的默认 data，让 OneBot 端（如 NapCat）路由激活/状态查询得到正常响应。

    未列出的动作返回 None（data: null 仍为成功响应）。
    """
    if action == "get_login_info":
        # NapCat 路由激活必需：缺少 data 会反复重试，最终降级为只接收
        return {"user_id":int(LoadConfig().get("account_id",14514)), "nickname": LoadConfig().get("nickname","nickname")}
    if action == "get_version_info":
        return {"app_name": "CompletionConnector", "app_version": VERSION, "protocol_version": "v11"}
    if action == "get_status":
        return {"online": True, "good": True}
    return None


def _reply_success(data: dict) -> None:
    """对 OneBot 端的 API 调用回一个成功响应（原样回显 echo）。"""
    websocketConnector.SendMessage({
        "status": "ok",
        "retcode": 0,
        "data": _default_action_data(str(data.get("action"))),
        "echo": data.get("echo"),
    })


def HandleIncomingEvent(data: dict) -> None:
    """处理从 OneBot 端收到的消息（注册为 websocketConnector 的事件处理器）。

    - 收到 send_*_msg API 调用 → 翻译为 chat completion 回复入队，并回执给 OneBot 端
    - 收到其他 API 调用（get_login_info 等）→ 回成功响应，避免客户端等待/重试
    - 其余（事件、API 响应）仅记录
    """
    if not isinstance(data, dict):
        return

    # 1) OneBot 端调用发消息 API → 视为 AI 回复
    if data.get("action") in SEND_ACTIONS:
        response: None | List[dict[str, str | Any]] = TranslateOutgoingMessageRequestFirst(data)
        if response is not None:
            for rs in response:
                translatedReplyQueue.put(rs)
            # 给 OneBot 端回执，避免其等待超时
            websocketConnector.SendMessage({
                "status": "ok",
                "retcode": 0,
                "data": {"message_id": int(time.time() * 1000) % (2 ** 31)},
                "echo": data.get("echo"),
            })
        return

    # 2) 其他 API 调用（get_login_info / get_version_info / ...）→ 通用成功响应
    if data.get("action"):
        _reply_success(data)
        LogColored("[TranslateLayer] " + t("cc.api_replied") + ":", data.get("action"),Fore.MAGENTA)
        return

    # 3) 元事件（心跳/生命周期）仅记录
    if data.get("post_type") == "meta_event":
        meta_type = data.get("meta_event_type")
        if meta_type == "lifecycle":
            LogColored(f"[TranslateLayer] {t('cc.lifecycle')}: {data.get('sub_type')}",Fore.RESET)
        return

    # 4) 其余事件（消息/通知/请求）记录
    if data.get("post_type") == "message":
        LogColored(f"[TranslateLayer] {t('cc.message_event')}: {data.get('raw_message')}",Fore.RESET)


def WaitForReply(timeout: float = 30.0) -> Optional[dict]:
    """阻塞等待 OneBot 端的第一条回复段（翻译后的 chat completion 响应）。

    注意：多段消息时只取第一条段；需要合并全部段请用 WaitForAllReplies。

    Returns: OpenAI 格式响应 dict；超时返回 None
    """
    # 清空队列中的旧消息，防止缓存失效
    while not translatedReplyQueue.empty():
        try:
            translatedReplyQueue.get_nowait()
        except queue.Empty:
            break
    
    try:
        return TranslateOutgoingMessageRequestNext([translatedReplyQueue.get(timeout=timeout)])

    except queue.Empty:
        return None


def WaitForAllReplies(timeout: float = 30.0) -> Optional[dict]:
    """阻塞等待 OneBot 端的全部回复段并合并为一条 chat completion 响应。

    Returns: OpenAI 格式响应 dict；超时无任何回复返回 None
    """
    # 清空队列中的旧消息，防止缓存失效
    while not translatedReplyQueue.empty():
        try:
            translatedReplyQueue.get_nowait()
        except queue.Empty:
            break
    
    result: List[dict[str, str | Any]] = []
    # 至少等一条回复段；超时无回复返回 None
    try:
        result.append(translatedReplyQueue.get(timeout=timeout))
    except queue.Empty:
        return None
    # 收集其余段（非阻塞，取完即止）
    while not translatedReplyQueue.empty():
        try:
            result.append(translatedReplyQueue.get_nowait())
        except queue.Empty:
            break
    return TranslateOutgoingMessageRequestNext(result)

def Initialize() -> None:
    """注册事件处理器（模块导入时自动调用）"""
    websocketConnector.set_event_handler(HandleIncomingEvent)
    LogColored("[TranslateLayer] " + t("cc.translator_ready") + ":", _translation_implement,Fore.LIGHTRED_EX)


Initialize()
