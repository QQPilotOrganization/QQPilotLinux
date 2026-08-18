import importlib
import configparser
import load
from colorama import Fore
import base64
import os
from typing import List, Optional, Dict, Any, Tuple
import time
import requests
import json
import re
from chatContent import ChatContent

# ================= 配置加载（对齐 Answer.cs 构造函数） =================
config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')


def _cfg(key: str) -> str:
    return config['general'][key]


modelName: str = _cfg('modelname')
serverUrl: str = _cfg('server_url')
isVisionModel: bool = _cfg('isvisionmodel').lower() == 'true'
maxImageCount: int = int(_cfg('maximagecount'))
remoteServerTimeout: int = int(_cfg('remote_server_timeout'))
forceOllamaAPI: bool = config.getboolean('general', 'forceollamaapi', fallback=False)
apiKey: str = _cfg('api_key')
# 系统提示从 config.ini 的 system 键读取（沿用旧版方式）
sysPmpt: str = config.get('general', 'system', fallback='')

useOllama = False
builtInLanguageModel = False
tinylm = None

# 后端选择（对齐 Answer.cs 构造函数）
if forceOllamaAPI:
    useOllama = True
    serverUrl+='/api/chat'
elif serverUrl.lower() == 'ollama':
    serverUrl = 'http://localhost:11434/api/chat'
    useOllama = True
elif serverUrl.lower() == 'builtin':
    builtInLanguageModel = True
# 否则 server_url 是用户自定义的 base URL（如 http://192.168.1.100:8000/v1）

MAX_LENGTH = 2048  # 对齐 C#；非流式请求，未用于截断

# extra.json 中的字段会合并进请求体并覆盖同名键（对齐 C#）
extra: Dict[str, Any] = {}
try:
    with open('extra.json', 'r', encoding='utf-8') as f:
        extra = json.loads(f.read())
except Exception:
    pass

# ================= 工具函数 =================

def _image_to_base64(path: str) -> str:
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def isTime(text: str) -> Tuple[bool, List[str]]:
    """对齐 Answer.cs 的 IsTime：校验小时 0-23、分钟 0-59"""
    pattern1 = r'\(?([0-2]?[0-9]):([0-5][0-9])\)?'
    pattern2 = r'\(?([0-2]?[0-9])\.([0-5][0-9])\)?'
    valid_times: List[str] = []
    for pattern in (pattern1, pattern2):
        for m in re.finditer(pattern, text):
            try:
                h = int(m.group(1))
                minute = int(m.group(2))
            except ValueError:
                continue
            if 0 <= h <= 23 and 0 <= minute <= 59:
                valid_times.append(f'{h:02d}:{minute:02d}')
    return len(valid_times) > 0, valid_times


def _concatenate_text(text_list: List[ChatContent], images: List[str]) -> List[Dict[str, Any]]:
    """对齐 Answer.cs 的 ConcatenateText。

    - 只收集同时出现在全局 images 列表（已按 MaxImageCount 截断）中的图片；
    - 只有用户消息携带图片，assistant 消息只带文本；
    - 既没有文本、也没有可发送的图片 → 整条消息跳过（纯图片消息必须保留）；
    - Ollama 用纯 base64 数组；OpenAI 兼容 API 用 data: URI 分段数组。
    """
    messages: List[Dict[str, Any]] = []

    for t in text_list:
        image_b64: List[str] = []        # 纯 base64 —— Ollama 使用
        image_data_urls: List[str] = []  # data: URI —— OpenAI 兼容 API 使用
        for img in t.imagePaths:
            if img not in images:
                continue
            b64 = _image_to_base64(img)
            mime = 'image/png' if img.lower().endswith('.png') else 'image/webp' if img.lower().endswith('.webp')  else 'image/jpeg'
            image_b64.append(b64)
            image_data_urls.append(f'data:{mime};base64,{b64}')

        has_text = bool(t.text)
        attach_images = (not t.ownByMyself) and len(image_b64) > 0

        if not has_text and not attach_images:
            continue

        text = str(t) if has_text else ''

        message: Dict[str, Any] = {
            'role': 'assistant' if t.ownByMyself else 'user',
        }

        if useOllama:
            # Ollama /api/chat 格式：images 是与 content 平级的【纯 base64】数组（不带 data: 前缀）
            message['content'] = text
            if attach_images:
                message['images'] = image_b64
        else:
            # OpenAI 兼容格式：content 可以是字符串，也可以是分段数组
            if not attach_images:
                message['content'] = text
            else:
                parts: List[Any] = [{'type': 'text', 'text': text}]
                for url in image_data_urls:
                    parts.append({'type': 'image_url', 'image_url': {'url': url}})
                message['content'] = parts

        messages.append(message)

    return messages


# ================= 核心推理函数 =================
def getAnswer(text: List[ChatContent], systemPrompt: str = 'auto') -> Tuple[Optional[str], int]:
    totalTokens = 0
    if text is None or len(text) == 0:
        return '', 0

    # 内置模型（对齐 Answer.cs Builtin 分支：从后往前找第一条非空、非自己发的消息）
    if builtInLanguageModel:
        global tinylm
        for t in reversed(text):
            if not t.text or t.ownByMyself:
                continue
            if tinylm is None:
                tinylm = importlib.import_module('TinyLangJaccard')
            return tinylm.answer(t.text), 0
        return '', 0

    # 系统提示（"auto" → config.ini 的 system；"" / "None" → 空；否则用传入值）
    if systemPrompt == 'auto':
        final_system_prompt = sysPmpt
    elif systemPrompt == '' or systemPrompt == 'None':
        final_system_prompt = ''
    else:
        final_system_prompt = systemPrompt

    # 收集图片：从后往前，跳过自己的消息，直到 MaxImageCount（对齐 C#）
    image_list: List[str] = []
    if isVisionModel:
        for t in reversed(text):
            if not t.ownByMyself:
                for img in t.imagePaths:
                    if os.path.exists(img):
                        image_list.append(img)
                        if len(image_list) >= maxImageCount:
                            break
                    else:
                        print(f'× 没有找到图片 {img}')
                if len(image_list) >= maxImageCount:
                    break

    # 构建 messages
    messages: List[Dict[str, Any]] = []
    if final_system_prompt:
        messages.append({'role': 'system', 'content': final_system_prompt})
    messages += _concatenate_text(text, image_list)

    # 构造请求体（对齐 C#）
    request_body: Dict[str, Any] = {
        'model': modelName,
        'messages': messages,
        'stream': False,
    }
    for k, v in extra.items():
        request_body[k] = v

    # 调试：写出完整请求体（对齐 C# dest.json）
    try:
        with open('dest.json', 'w', encoding='utf-8') as f:
            json.dump(request_body, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    # Headers（对齐 C#：API_KEY 非空且不是 localhost 时才带 Bearer）
    headers = {'Content-Type': 'application/json'}
    if apiKey and 'localhost' not in serverUrl and '127.0.0.1' not in serverUrl:
        headers['Authorization'] = f'Bearer {apiKey}'

    url = serverUrl if useOllama else f'{serverUrl}/chat/completions'

    start_time = time.time()
    try:
        print(f'Sending request to: {url}')

        resp = requests.post(url, json=request_body, headers=headers, timeout=remoteServerTimeout)
        response_body = resp.content.decode('utf-8', errors='replace')

        if resp.status_code < 200 or resp.status_code >= 300:
            print(f'API Error: {resp.status_code} - {response_body}')
            return None, 0

        print('\n\nResponse:\n')
        print(response_body)

        doc = json.loads(response_body)

        if useOllama:
            answer_text = doc.get('message', {}).get('content')
        else:
            answer_text = doc.get('choices', [{}])[0].get('message', {}).get('content')

        # Token 用量（对齐 C#：只读 prompt_tokens / completion_tokens / total_tokens，缺失为 0）
        usage = doc.get('usage')
        if usage is not None:
            prompt_tokens = usage.get('prompt_tokens', 0) or 0
            completion_tokens = usage.get('completion_tokens', 0) or 0
            total_tokens = usage.get('total_tokens', 0) or 0
            print(f'Token 用量: 输入 {prompt_tokens} | 输出 {completion_tokens} | 总计 {total_tokens}')
            totalTokens = total_tokens

        # 推理内容（Deepseek reasoning_content / Ollama thinking，对齐 C#）
        try:
            reason = doc.get('choices', [{}])[0].get('message', {}).get('reasoning_content')
            if reason is None:
                reason = doc.get('message', {}).get('thinking')
        except Exception:
            reason = None
        if reason is not None:
            print(f'{Fore.LIGHTBLACK_EX}<think>\n{reason}\n</think>{Fore.RESET}')

        elapsed = time.time() - start_time
        print(f'用时 {elapsed:.2f}s')

        if answer_text is not None:
            answer_text = answer_text.strip()
        print(answer_text if answer_text is not None else '')

        return answer_text, totalTokens

    except Exception as e:
        print(f'HTTP request failed: {e}')
        return None, 0


def get_answer_as_string(text: str, system_prompt):
    return getAnswer([ChatContent(username='', imagePaths=[], text=text, time='', ownByMyself=False)], system_prompt)


# ================= 测试入口 =================
if __name__ == '__main__':
    c = ChatContent(
        username='', imagePaths=[],
        text='解释图片\n2\n3\n4\n5',
        time=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
        ownByMyself=False,
    )
    c2 = ChatContent(
        username='', imagePaths=[r'D:\Pictures\111.PNG'],
        text='12345',
        time=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
        ownByMyself=True,
    )
    c3 = ChatContent(
        username='', imagePaths=[],
        text='678910',
        time=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
        ownByMyself=False,
    )

    # 测试 Ollama（对齐 C# Test()）
    useOllama = True
    serverUrl = 'http://localhost:8080/api/chat'
    modelName = 'qwen3.5:0.8b'

    print('\n=== Testing Ollama ===')
    answer = getAnswer([c, c2, c3])
    print(f'Answer: {answer}')

    # 测试 Built-in
    print('\n=== Testing Built-in Model ===')
    builtInLanguageModel = True
    answer = getAnswer([c, c2, c3])
    print(f'Answer: {answer}')

    # 测试 OpenAI Compatible
    print('\n=== Testing OpenAI Compatible API ===')
    builtInLanguageModel = False
    useOllama = False
    serverUrl = 'http://localhost:8000/v1'
    apiKey = '21r234242'
    answer = getAnswer([c, c2, c3])
    print(f'Answer: {answer}')
