# -*- coding: utf-8 -*-
"""OneBot 11 消息体系（按概念分层实现）。

对应 onebot-11 文档的四个层次：
1. 消息段 MessageSegment   —— onebot-11/message/segment.md
   单个 {type, data}，如 {"type": "face", "data": {"id": "123"}}；text 段表示纯文本。
2. 消息的两种格式          —— onebot-11/message/string.md 与 array.md
   - MessageString：字符串格式（CQ 码），如 "[CQ:face,id=123]哈喽"
   - 消息段数组（array message）：List[MessageSegment]
   两者语义等价，可互相转换（ParseMessageString / BuildMessageString）。
3. 消息事件 MessageEvent   —— onebot-11/event/message.md
   事件上报的完整 JSON（time/self_id/post_type/message_type/sub_type/message_id/
   user_id/message/raw_message/font/sender，群聊另有 group_id/anonymous），
   其中 message 字段按配置为字符串格式或消息段数组。
4. 发送 API 的请求体       —— api/public.md send_private_msg 等
   BuildJsonFromMessageAsString / BuildJsonFromAListOfMessageSegment。
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

# ---------------------------------------------------------------------------
# 转义（string.md「转义」）
#   纯文本：& -> &amp;，[ -> &#91;，] -> &#93;
#   CQ 码参数值：额外 , -> &#44;
# ---------------------------------------------------------------------------

def _escape_text(text: Union[str, object]) -> str:
    """纯文本转义。先转 & 再转 [ ]，避免二次转义。"""
    return str(text).replace("&", "&amp;").replace("[", "&#91;").replace("]", "&#93;")


def _escape_cq_param(value: Union[str, object]) -> str:
    """CQ 码参数值转义（比纯文本多一个逗号）。"""
    return (str(value).replace("&", "&amp;").replace("[", "&#91;")
            .replace("]", "&#93;").replace(",", "&#44;"))


def _unescape(source: str) -> str:
    """还原转义。&#44; &#91; &#93; 先于 &amp;，避免被二次还原。"""
    return (source.replace("&#44;", ",").replace("&#91;", "[")
            .replace("&#93;", "]").replace("&amp;", "&"))


# ---------------------------------------------------------------------------
# CQ 码编解码（string.md「CQ 码格式」）
#   形如 [CQ:face,id=178]；功能名为 [CQ: 后第一个 , 或 ] 前的内容；
#   参数从第一个 , 到 ]，按 , 分割，每段第一个 = 前为参数名、之后为参数值。
#   因参数值中的裸 [ ] , 必须转义，可安全按 , 分割、按 ] 收尾。
# ---------------------------------------------------------------------------

def _encode_cq(msg_type: str, data: Optional[Dict[str, object]] = None) -> str:
    """消息段 -> CQ 码。data 为空时输出无参形式，如 [CQ:shake]。"""
    data = data or {}
    if not data:
        return f"[CQ:{msg_type}]"
    params = ",".join(
        f"{key}={_escape_cq_param(value)}"
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
    k = i + 4
    while k < len(source) and source[k] != ',' and source[k] != ']':
        k += 1
    if k >= len(source):          # 未闭合
        return None
    msg_type = source[i + 4:k]
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
            data[name] = _unescape(value)
    return i, msg_type, data, end + 1


def _decode_single_cq(source: str) -> Optional[Tuple[str, Dict[str, str]]]:
    """整串恰为一个 CQ 码时返回 (type, data)，否则返回 None。"""
    source = source.strip()
    token = _find_cq(source, 0)
    if token is None:
        return None
    start, msg_type, data, end = token
    if start != 0 or end != len(source):
        return None
    return msg_type, data


# ---------------------------------------------------------------------------
# 消息段（segment.md）
# ---------------------------------------------------------------------------

class MessageSegment:
    """单个消息段 {type, data}。

    text 段表示纯文本：转成字符串格式时直接输出文本（不包成 CQ 码），
    其余类型转成 [CQ:type,key=value,...]。
    """

    def __init__(self, type: str, data: Optional[Dict[str, str]] = None) -> None:
        self.type: str = type
        self.data: Dict[str, str] = dict(data) if data else {}

    def BuildJson(self) -> dict:
        """转为消息段 JSON {type, data}（array.md 的消息段格式）。"""
        return {"type": self.type, "data": dict(self.data)}

    @classmethod
    def FromJson(cls, segment: dict) -> "MessageSegment":
        """从消息段 JSON {type, data} 构造。"""
        data = segment.get("data")
        return cls(
            str(segment.get("type", "text")),
            dict(data) if isinstance(data, dict) else {},
        )
        
    @classmethod
    def EasyCreate(cls,Type: str,data: str) ->MessageSegment:
        data2={}
        onebot_type=Type
        if Type=='text':
            data2={'text':data}
        elif Type=='image' or Type=='image_url':
            onebot_type='image'  # chat completion 的 image_url 规范化为 OneBot 标准 image 段
            data2={'file':data}
        return cls(type=onebot_type,data=data2)
    
    
    @classmethod
    def FromMessageString(cls, source: str) -> "MessageSegment":
        """从字符串格式构造单个消息段。

        "[CQ:face,id=123]" -> face 段；纯文本 -> text 段。
        """
        parsed = _decode_single_cq(source)
        if parsed is None:
            return cls("text", {"text": source})
        msg_type, data = parsed
        return cls(msg_type, data)

    def ToMessageString(self) -> str:
        """转为字符串格式：text 段输出转义后的纯文本，其余输出 CQ 码。"""
        if self.type == "text":
            return _escape_text(self.data.get("text", ""))
        return _encode_cq(self.type, self.data)

    def ToPureString(self)->str:
        """只要文本"""
        return self.data.get("text", "")
    def __str__(self) -> str:
        return self.ToMessageString()

    def ToString(self) -> str:
        return str(self)

    def __eq__(self, other: object) -> bool:
        """消息段按值比较（type 与 data 均相等）。"""
        return (isinstance(other, MessageSegment)
                and self.type == other.type and self.data == other.data)

    def __hash__(self) -> int:
        return hash((self.type, frozenset(self.data.items())))

    def __repr__(self) -> str:
        return f"MessageSegment({self.type!r}, {self.data!r})"


# ---------------------------------------------------------------------------
# 消息的两种格式（string.md / array.md）
# ---------------------------------------------------------------------------

MessageString = str  # 字符串格式消息，如 "[CQ:face,id=123]哈喽"
MessageArray = List[MessageSegment]  # 数组格式消息（消息段数组）


def ParseMessageString(message: MessageString) -> MessageArray:
    """字符串格式消息 -> 消息段数组（array.md）。非法/未闭合的 [CQ: 视为纯文本。"""
    segments: List[MessageSegment] = []
    pos = 0
    while True:
        token = _find_cq(message, pos)
        if token is None:
            break
        start, msg_type, data, end = token
        if start > pos:
            text = _unescape(message[pos:start])
            if text:
                segments.append(MessageSegment("text", {"text": text}))
        segments.append(MessageSegment(msg_type, data))
        pos = end
    if pos < len(message):
        text = _unescape(message[pos:])
        if text:
            segments.append(MessageSegment("text", {"text": text}))
    return segments


def BuildMessageString(segments: MessageArray) -> MessageString:
    """消息段数组 -> 字符串格式消息（string.md）。"""
    return "".join(segment.ToMessageString() for segment in segments)


# ---------------------------------------------------------------------------
# 消息事件（event/message.md）
# ---------------------------------------------------------------------------

class MessageEvent:
    """消息事件。

    私聊与群聊事件共用字段：time / self_id / post_type / message_type / sub_type /
    message_id / user_id / message / raw_message / font / sender；
    群聊事件另有 group_id 与 anonymous。
    message 字段可为 MessageString 或消息段数组，BuildJson 时统一序列化。
    """

    def __init__(self, **kwargs) -> None:
        self.time: Optional[int] = kwargs.get("time")
        self.self_id: Optional[int] = kwargs.get("self_id")
        self.post_type: str = kwargs.get("post_type", "message")
        self.message_type: str = kwargs.get("message_type", "private")
        self.sub_type: str = kwargs.get("sub_type", "friend")
        self.message_id: Optional[int] = kwargs.get("message_id")
        self.group_id: Optional[int] = kwargs.get("group_id")
        self.user_id: Optional[int] = kwargs.get("user_id")
        self.anonymous: Optional[dict] = kwargs.get("anonymous")
        self.message: Union[MessageString, MessageArray, None] = kwargs.get("message")
        self.raw_message: Optional[str] = kwargs.get("raw_message")
        self.font: Optional[int] = kwargs.get("font")
        self.sender: Optional[dict] = kwargs.get("sender")

    def BuildJson(self,) -> dict:
        """组装事件上报 JSON（event/message.md 字段表）。message 为段数组时转成数组。"""
        data: Dict[str, object] = {}
        if self.time is not None:
            data["time"] = self.time
        if self.self_id is not None:
            data["self_id"] = self.self_id
        data["post_type"] = self.post_type
        data["message_type"] = self.message_type
        data["sub_type"] = self.sub_type
        if self.message_id is not None:
            data["message_id"] = self.message_id
        if self.group_id is not None:
            data["group_id"] = self.group_id
        if self.user_id is not None:
            data["user_id"] = self.user_id
        if self.anonymous is not None:
            data["anonymous"] = self.anonymous
        if self.message is not None:
            data["message"] = self._message_to_json(self.message)
        if self.raw_message is not None:
            data["raw_message"] = self.raw_message
        if self.font is not None:
            data["font"] = self.font
        if self.sender is not None:
            if isinstance(self.sender,dict):
                data["sender"] = self.sender
            elif isinstance(self.sender,Sender):
                data["sender"]=self.sender.ToDict()
        return data

    @classmethod
    def FromJson(cls, data: dict) -> "MessageEvent":
        """从事件上报 JSON 构造。message 为数组时解析成 MessageSegment 列表。"""
        message = data.get("message")
        if isinstance(message, list):
            message = [MessageSegment.FromJson(segment) for segment in message]
        return cls(**{**data, "message": message})

    @staticmethod
    def _message_to_json(message: Union[MessageString, MessageArray]) -> object:
        if isinstance(message, list):
            return [segment.BuildJson() for segment in message]
        return message
    
    def __repr__(self) -> str:
        return f"MessageEvent({self.message_type!r}, message={self.message!r})"


# ---------------------------------------------------------------------------
# 发送消息 API 的请求体（api/public.md send_private_msg 等）
# ---------------------------------------------------------------------------

def BuildJsonFromMessageAsString(message: MessageString, userID: int) -> dict:
    """以字符串格式消息构造 send_private_msg 的请求体（string.md）。"""
    return {"user_id": userID, "message": message}


def BuildJsonFromAListOfMessageSegment(listOfMessageSegment: List[MessageSegment], userID: int) -> dict:
    """以消息段数组构造 send_private_msg 的请求体（array.md）。"""
    return {"user_id": userID, "message": [segment.BuildJson() for segment in listOfMessageSegment]}

@dataclass
class Sender():
    UserID:int
    nickname:str=""
    sex:str=""
    age:int=0
    
    def __repr__(self) -> str:
        return f"{self.nickname}[{self.UserID}|{self.sex}|{self.age}]"
    def ToDict(self):
        return{'user_id':self.UserID,'nickname':self.nickname,'sex':self.sex,'age':self.age}