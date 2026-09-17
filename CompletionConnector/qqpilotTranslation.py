"为来自QQPilot请求的翻译实现"

from dataclasses import dataclass
import re
import sqlite3

import Message2
from completion import CompletionContent
from typing import Any, List, Optional, Union

import DBConnector
class ChatManager(DBConnector.DB):
    def __init__(self) -> None:
        super().__init__('ChatManager.db')
        self._init_tables()
        

    def _init_tables(self):
        """初始化数据库表结构"""
        # 1. 消息主表：保证消息内容全局唯一
        self.execute('''CREATE TABLE IF NOT EXISTS Messages (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            content TEXT NOT NULL UNIQUE
                        );''')
        self.execute('''CREATE TABLE IF NOT EXISTS Groups (
                            group_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT DEFAULT '' -- 可选，用于标记群名
                        );''')

        self.execute('''CREATE TABLE IF NOT EXISTS PrivateChat (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT DEFAULT '' 
                        );''')
        
        # 3. 关联表：消息与群的对应关系
        self.execute('''CREATE TABLE IF NOT EXISTS Message_Group_Relation (
                            message_id INTEGER NOT NULL,
                            group_id INTEGER NOT NULL,
                            PRIMARY KEY (message_id, group_id),
                            FOREIGN KEY (message_id) REFERENCES Messages(id) ON DELETE CASCADE,
                            FOREIGN KEY (group_id) REFERENCES Groups(group_id) ON DELETE CASCADE
                        );''')
        
        # 创建索引以加速查询
        self.execute('CREATE INDEX IF NOT EXISTS idx_msg_content ON Messages(content);')
        self.execute('CREATE INDEX IF NOT EXISTS idx_rel_group ON Message_Group_Relation(group_id);')

    def _get_or_create_message_id(self, content: str) -> int:
        """获取消息ID，如果不存在则创建"""
        row = self.fetchone("SELECT id FROM Messages WHERE content = ?", (content,))
        if row:
            return row[0]
        
        self.execute("INSERT INTO Messages (content) VALUES (?)", (content,))
        return self.cursor.lastrowid  # type: ignore # lastrowid 才是刚插入行的 ID（total_changes 是累计变更数）

    def _get_new_group_id(self) -> int:
        """创建一个新群并返回其ID"""
        self.execute("INSERT INTO Groups DEFAULT VALUES")
        return self.cursor.lastrowid  # type: ignore # 安全地获取刚插入行的ID


    def GetPrivateChatID(self, input_string):
        """
        获取字符串对应的ID，如果不存在则创建
        返回: (id, is_new) 其中is_new表示是否是新创建的
        """
        # 去除首尾空格，避免不必要的差异
        input_string = input_string.strip()
        
        # 先查询是否存在
        self.cursor.execute('SELECT id FROM PrivateChat WHERE name = ?', (input_string,))
        result = self.cursor.fetchone()
        
        if result:
            # 字符串存在，返回现有ID
            return result[0], False
        else:
            # 字符串不存在，插入新记录
            try:
                self.cursor.execute('INSERT INTO PrivateChat (name) VALUES (?)', (input_string,))
                self.conn.commit()
                # 获取刚插入的ID
                new_id = self.cursor.lastrowid
                return new_id, True
            except sqlite3.IntegrityError:
                # 如果并发插入导致冲突，重新查询
                self.cursor.execute('SELECT id FROM PrivateChat WHERE name = ?', (input_string,))
                result = self.cursor.fetchone()
                return result[0], False
    def GetGroupID(self, messages: List[str]) -> int:
        """
        核心逻辑：
        输入一段字符串数组，判断它们是否属于某个已有群。
        规则：
        1. 统计输入中每条消息在当前数据库中已存在的归属情况。
        2. 如果有一个群包含了输入中至少10%的消息，则整个数组视为该群的消息。
        3. 如果没有这样的群，则创建一个新群，并将所有消息保存到新群中。
        
        返回最终的 group_id
        """
        if not messages:
            raise ValueError("Messages list cannot be empty")

        # 步骤1: 将消息去重并获取它们的ID，同时记录原始顺序以便后续处理（虽然这里主要看集合）
        unique_msgs = list(set(messages))
        msg_ids = []
        for msg in unique_msgs:
            mid = self._get_or_create_message_id(msg)
            msg_ids.append(mid)
        
        total_unique_count = len(msg_ids)
        if total_unique_count == 0:
            # 极端情况，虽然不太可能发生
            new_gid = self._get_new_group_id()
            return new_gid

        # 步骤2: 查询这些消息当前已经属于哪些群
        placeholders = ','.join(['?'] * len(msg_ids))
        query = f"""
            SELECT r.group_id, COUNT(r.message_id) as count 
            FROM Message_Group_Relation r 
            WHERE r.message_id IN ({placeholders})
            GROUP BY r.group_id
        """
        rows = self.fetchall(query, msg_ids)
        
        # 构建 {group_id: count} 字典
        group_counts = {}
        for gid, count in rows:
            group_counts[gid] = count

        # 步骤3: 判断是否有群满足 >= 10% 的条件
        target_group_id = None
        
        if group_counts:
            # 计算比例并找到最大比例的群
            best_gid = None
            max_ratio = 0.0
            
            for gid, count in group_counts.items():
                ratio = count / total_unique_count
                if ratio > max_ratio:
                    max_ratio = ratio
                    best_gid = gid
            
            # 检查最高比例是否 >= 10%
            if max_ratio >= 0.1:
                target_group_id = best_gid

        # 步骤4: 如果没有符合条件的群，或者之前没有匹配过任何群，则创建新群
        if target_group_id is None:
            target_group_id = self._get_new_group_id()

        
        insert_query = "INSERT OR IGNORE INTO Message_Group_Relation (message_id, group_id) VALUES (?, ?)"
        params = [(mid, target_group_id) for mid in msg_ids]
        self.cursor.executemany(insert_query, params)
        self.conn.commit()

        return target_group_id

def parse_messages(raw_text: str)->QQPilotMessage:
    """
    从原始文本中解析出所有 QQPilotMessage 对象
    
    Args:
        raw_text: 包含多条或单条消息的原始字符串
    Returns:
        Message 对象列表
    """
    # 正则说明：
    # \[time\]\s*(.+?)\s*      -> 匹配 [time] 标签后的时间值（非贪婪）
    # \[username\]\s*(.+?)\s*  -> 匹配 [username] 标签后的用户名
    # \[content\]\s*(.+?)\s*$  -> 匹配 [content] 标签后的内容，直到字符串末尾或下一个标签前
    pattern = re.compile(
        r'\[time\]\s*(.+?)\s*'
        r'\[username\]\s*(.+?)\s*'
        r'\[content\]\s*(.+?)(?=\s*\[time\]|$)',
        re.DOTALL  # DOTALL 使 . 能匹配换行符，防止内容中包含换行时截断
    )

    messages = []
    for match in pattern.finditer(raw_text):
        msg = QQPilotMessage(
            time=match.group(1).strip(),
            username=match.group(2).strip(),
            content=match.group(3).strip()
        )
        messages.append(msg)
        break
    if len(messages)==0:
        return QQPilotMessage("","","")
    return messages[0]

def all_equal(lst):
    if not lst:
        return True  # 空列表视为所有元素相等
    return all(s == lst[0] for s in lst)


@dataclass
class QQPilotMessage:
    """保存单条消息的数据类"""
    time: str
    username: str
    content: str

    def __repr__(self):
        return f"QQPilotMessage(time='{self.time}', username='{self.username}', content='{self.content}')"

def ToMessageEvent(newMessages  :List[CompletionContent],allMessages:List[CompletionContent])->List[Message2.MessageEvent]:
    # allMessagesStr=[message.typeContent for message in allMessages]
    chatManager=ChatManager()
    # groupID=gcm.GetGroupID(allMessagesStr)
    allMessagesQM=[parse_messages(message.typeContent) for message in allMessages if message.Type=="text"]
    id=0
    group=False
    if all_equal([qmsg.username for qmsg in allMessagesQM]):
        # 私聊
        id,_=chatManager.GetPrivateChatID(allMessagesQM[0].username) 
        if id is None:
            id=0
        
    else:
        id=chatManager.GetGroupID([message.typeContent for message in allMessages])
        group=True
    id+=1000000000
    print(id)
    # messageSegments:Message2.MessageArray=[]
    messageEvents:List[Message2.MessageEvent]=[]
    for message in newMessages:
        if message.Type=="image_url":
            messageSegment=Message2.MessageSegment.EasyCreate(message.Type,message.typeContent)
            # 图片消息无 username，sender 用会话 id 占位
            event=Message2.MessageEvent(message=[messageSegment],raw_message=messageSegment.ToMessageString(),post_type='message',message_type='group' if group else 'private',sender=Message2.Sender(id,""))
            if group:
                event.group_id=id
            else:
                event.user_id=id
            messageEvents.append(event)  
            continue
            
        qQPilotMessage=parse_messages(message.typeContent)
        messageSegment=Message2.MessageSegment.EasyCreate(message.Type,qQPilotMessage.content)
        # sender.user_id 按发送者 username 独立分配：
        # 群聊时若所有发送者共用群 id，不同的人会被当成同一个人（AstrBot 等
        # 后端会误判会话/权限）。这里为每个 username 单独映射一个 ID（+偏移）。
        if group and qQPilotMessage.username:
            sender_id, _ = chatManager.GetPrivateChatID(qQPilotMessage.username)
            sender_id = int(sender_id) + 1000000000
        else:
            sender_id = id
        event=Message2.MessageEvent(message=[messageSegment],raw_message=messageSegment.ToMessageString(),post_type='message'
                                    ,message_type='group' if group else 'private',
                                    
                                    sender=Message2.Sender(sender_id,qQPilotMessage.username))
        
        if group:
            event.group_id=id
        else:
            event.user_id=id
        messageEvents.append(event)
    return messageEvents


def ToChatCompletionMessageContent(segment: Message2.MessageSegment) -> dict[str, Union[str,Any]]:
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
    return {"type": "text", "text": segment.ToPureString()}