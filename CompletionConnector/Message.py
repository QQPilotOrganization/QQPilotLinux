# -*- coding: utf-8 -*-
"""OneBot 11 消息格式工具（依据 onebot-11/message/string.md 与 segment.md）。

提供：
- CQ 码字符串 <-> 消息段数组（OneBot array message）互转
- 从 CQ 码字符串生成 message 的 JSON（可直接作为 send_private_msg 等 API 的 message 参数）
- Message / MessageType 对象的段级封装
"""
import json
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union


class MessageType(Enum):
    Text = "text"
    Face = "face"
    Image = "image"
    Record = "record"
    Video = "video"
    At = "at"
    Rps = "rps"
    Dice = "dice"
    Shake = "shake"
    Poke = "poke"
    Anonymous = "anonymous"
    Share = 'share'
    Contact = "contact"
    Location = "location"
    Music = "music"
    Reply = "reply"
    Forward = "forward"
    Node = "node"  # segment.md：合并转发自定义节点（user_id/nickname/content 或 id）
    Xml = "xml"
    Json = "json"


# ---------------------------------------------------------------------------
# 转义（string.md「转义」小节）
#   纯文本：& -> &amp;，[ -> &#91;，] -> &#93;
#   CQ 码参数值：额外 , -> &#44;
# ---------------------------------------------------------------------------

def escape_text(text: Union[str, object]) -> str:
    """纯文本转义。先转 & 再转 [ ]，避免二次转义。"""
    return str(text).replace("&", "&amp;").replace("[", "&#91;").replace("]", "&#93;")


def escape_cq_param(value: Union[str, object]) -> str:
    """CQ 码参数值转义（比纯文本多一个逗号）。"""
    return (str(value).replace("&", "&amp;").replace("[", "&#91;")
            .replace("]", "&#93;").replace(",", "&#44;"))


def unescape(source: str) -> str:
    """还原转义。&#44; &#91; &#93; 先于 &amp;，避免被二次还原。"""
    return (source.replace("&#44;", ",").replace("&#91;", "[")
            .replace("&#93;", "]").replace("&amp;", "&"))


# ---------------------------------------------------------------------------
# CQ 码编解码（string.md「CQ 码格式」）
#   形如 [CQ:face,id=178]；功能名为 [CQ: 后第一个 , 或 ] 前的内容；
#   参数从第一个 , 到 ]，按 , 分割，每段第一个 = 前为参数名、之后为参数值。
#   因参数值中的裸 [ ] , 必须转义，可安全按 , 分割、按 ] 收尾。
# ---------------------------------------------------------------------------

def encode_cq(msg_type: str, data: Optional[Dict[str, object]] = None) -> str:
    """消息段 -> CQ 码。data 为空时输出无参形式，如 [CQ:shake]。"""
    data = data or {}
    if not data:
        return f"[CQ:{msg_type}]"
    params = ",".join(
        f"{key}={escape_cq_param(value)}"
        for key, value in data.items()
        if value is not None
    )
    return f"[CQ:{msg_type},{params}]"


def _find_cq(source: str, start: int) -> Optional[Tuple[int, str, Dict[str, str], int]]:
    """从 start 起扫描下一个合法 CQ 码。

    返回 (起始下标, 功能名, 参数 dict, 结束下标+1)；格式非法时返回 None（视为文本）。
    """
    i = source.find("[CQ:", start)
    if i == -1:
        return None
    j = i + 4
    k = j
    while k < len(source) and source[k] != ',' and source[k] != ']':
        k += 1
    if k >= len(source):          # 未闭合
        return None
    msg_type = source[j:k]
    if not msg_type:
        return None
    if source[k] == ']':          # 无参数
        return i, msg_type, {}, k + 1
    end = source.find(']', k + 1)  # 参数值中裸 ] 必须转义，故首个 ] 即收尾
    if end == -1:
        return None
    data: Dict[str, str] = {}
    for part in source[k + 1:end].split(','):
        name, sep, value = part.partition('=')
        name = name.strip()
        if sep and name:          # 无 = 的段按文档忽略
            data[name] = unescape(value)
    return i, msg_type, data, end + 1


def decode_cq(source: str) -> Optional[Tuple[str, Dict[str, str]]]:
    """解析单个 CQ 码（整串只能是一个 CQ 码，不含前后文本）。

    返回 (功能名, 参数 dict)，解析失败或混有文本时返回 None。
    """
    source = source.strip()
    token = _find_cq(source, 0)
    if token is None:
        return None
    start, msg_type, data, end = token
    if start != 0 or end != len(source):
        return None
    return msg_type, data


# ---------------------------------------------------------------------------
# CQ 码字符串 <-> 消息段数组 互转（segment.md / string.md）
#   消息段数组即 OneBot 的 array message：
#   [{"type": "text", "data": {"text": "..."}}, {"type": "face", "data": {"id": "178"}}]
# ---------------------------------------------------------------------------

def string_to_segments(source: str) -> List[Dict[str, object]]:
    """字符串格式（CQ 码）-> 消息段数组。非法/未闭合的 [CQ: 视为纯文本。"""
    segments: List[Dict[str, object]] = []
    pos = 0
    while True:
        token = _find_cq(source, pos)
        if token is None:
            break
        start, msg_type, data, end = token
        if start > pos:
            text = unescape(source[pos:start])
            if text:
                segments.append({"type": "text", "data": {"text": text}})
        segments.append({"type": msg_type, "data": data})
        pos = end
    if pos < len(source):
        text = unescape(source[pos:])
        if text:
            segments.append({"type": "text", "data": {"text": text}})
    return segments


def segments_to_string(segments: Union[List[dict], List["Message"]]) -> str:
    """消息段数组 -> 字符串格式（CQ 码）。text 段走纯文本转义，其余走 CQ 码。"""
    parts: List[str] = []
    for segment in segments:
        if isinstance(segment, dict):
            msg_type = segment.get("type")
            data = segment.get("data") or {}
        elif hasattr(segment, "to_segment"):  # Message 对象
            seg = segment.to_segment()
            msg_type = seg.get("type")
            data = seg.get("data") or {}
        else:
            continue
        if msg_type == "text":
            parts.append(escape_text(data.get("text", ""))) # type: ignore
        else:
            parts.append(encode_cq(str(msg_type), data)) # type: ignore
    return "".join(parts)


# ---------------------------------------------------------------------------
# 字符串格式 -> message 的 JSON（可直接作为 OneBot API 的 message 参数）
# ---------------------------------------------------------------------------

def string_to_message(source: str) -> List[Dict[str, object]]:
    """从字符串生成 message（消息段数组，即 OneBot array message）。"""
    return string_to_segments(source)


def string_to_message_json(source: str, **json_kwargs) -> str:
    """从字符串生成 message 的 JSON 字符串。

    默认 ensure_ascii=False 保持中文可读、无缩进便于直接请求 API；
    可通过 json_kwargs 覆盖，如 string_to_message_json(s, indent=2)。
    """
    json_kwargs.setdefault("ensure_ascii", False)
    return json.dumps(string_to_segments(source), **json_kwargs)


def message_to_string(message: Union[str, List[dict], List["Message"]]) -> str:
    """message（JSON 字符串或消息段数组）-> 字符串格式（CQ 码）。"""
    if isinstance(message, str):
        return segments_to_string(json.loads(message))
    return segments_to_string(message)


# ---------------------------------------------------------------------------
# Message 类：单消息段的封装（保留原 __init__ 签名，扩展 dict 支持）
# ---------------------------------------------------------------------------

# segment.md 中各类型 data 的主字段（构造时把单个 content 字符串放进去）
_TYPE_PRIMARY_FIELD: Dict[MessageType, str] = {
    MessageType.Text: "text",
    MessageType.Face: "id",
    MessageType.Image: "file",
    MessageType.Record: "file",
    MessageType.Video: "file",
    MessageType.At: "qq",
    MessageType.Poke: "id",
    MessageType.Share: "url",
    MessageType.Contact: "type",
    MessageType.Location: "lat",
    MessageType.Music: "type",
    MessageType.Reply: "id",
    MessageType.Forward: "id",
    MessageType.Node: "id",
    MessageType.Xml: "data",
    MessageType.Json: "data",
    # 无参数类型：Rps / Dice / Shake / Anonymous
}


class Message:
    def __init__(self, Type: MessageType, content: Union[str, Dict[str, str]] = "") -> None:
        self.MessageType: MessageType = Type
        if isinstance(content, dict):
            self.data: Dict[str, str] = {str(k): str(v) for k, v in content.items()}
        else:
            self.data: Dict[str, str] = {}
            field = _TYPE_PRIMARY_FIELD.get(self.MessageType)
            if field and content:
                self.data[field] = str(content)

    # -- 与消息段数组互转 --
    def to_segment(self) -> Dict[str, object]:
        """转为一个消息段 {type, data}。"""
        return {"type": self.MessageType.value, "data": dict(self.data)}

    @classmethod
    def from_segment(cls, segment: dict) -> "Message":
        """从消息段 {type, data} 构造。未知类型回退为 text。"""
        try:
            msg_type = MessageType(segment.get("type", "text"))
        except ValueError:
            msg_type = MessageType.Text
        data = segment.get("data") or {}
        return cls(msg_type, dict(data) if isinstance(data, dict) else str(data))

    # -- 与 CQ 码字符串互转 --
    def to_cq(self) -> str:
        """转为字符串格式：text 段输出纯文本（转义后），其余输出 CQ 码。"""
        return segments_to_string([self.to_segment()])

    @classmethod
    def from_cq(cls, source: str) -> "Message":
        """从单个 CQ 码构造；整串必须恰为一个 CQ 码。"""
        parsed = decode_cq(source)
        if parsed is None:
            raise ValueError(f"不是合法的单个 CQ 码: {source!r}")
        msg_type, data = parsed
        return cls(MessageType(msg_type), data)

    def __str__(self) -> str:
        return self.to_cq()

    def __repr__(self) -> str:
        return f"Message({self.MessageType!r}, {self.data!r})"
