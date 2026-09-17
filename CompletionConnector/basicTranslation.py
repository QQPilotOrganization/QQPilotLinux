"为来自一般的Chat Completion请求的翻译实现"

from typing import List

import Message2
from completion import CompletionContent


def ToMessageEvent(newMessages  :List[CompletionContent],allMessages:List[CompletionContent])->List[Message2.MessageEvent]:
    messageEvents:List[Message2.MessageEvent]=[]
    for message in newMessages:
        if message.Type=="image_url":
            messageSegment=Message2.MessageSegment.EasyCreate(message.Type,message.typeContent)
            event=Message2.MessageEvent(message=[messageSegment],raw_message=messageSegment.ToMessageString(),post_type='message',message_type='private',
                                        sender=Message2.Sender(1,"user"))
            continue
            
        messageSegment=Message2.MessageSegment.EasyCreate(message.Type,message.typeContent)
        event=Message2.MessageEvent(message=[messageSegment],raw_message=messageSegment.ToMessageString(),post_type='message',message_type='private',
                                    sender=Message2.Sender(1,"user"))
        messageEvents.append(event)
    return messageEvents


def ToChatCompletionMessageContent(segment: Message2.MessageSegment):
    """OneBot 消息段 → OpenAI content 段（多模态数组元素）"""
    t = segment.type
    d = segment.data
    if t == "text":
        return {"type": "text", "text": d.get("text", "")}
    if t == "image":
        url = d.get("url", "") or d.get("file", "")
        if url.startswith("base64://"):
            url = "data:image/png;base64," + url[len("base64://"):]
        return {"type": "image_url", "image_url": {"url": url}}
    # 其余段（face / at / reply 等）文本化，保留 CQ 码语义
    return {"type": "text", "text": segment.ToMessageString()}