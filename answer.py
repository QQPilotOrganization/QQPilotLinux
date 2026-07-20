import importlib
import configparser
import load
from colorama import Fore
import base64
import os
from typing import List, Optional, Dict, Any
import time
import httpx
import requests
import json
import re
from chatContent import ChatContent

# ================= 配置加载 =================
config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')

modelName: str = config['general']['modelName']
server_url: str = config['general']['server_url']
isVisionModel: bool = config.getboolean('general', 'isVisionModel')
maxImageCount = config.getint('general', 'maxImageCount')
remoteServerTimeout = config.getint('general', 'remote_server_timeout')
API_KEY = config['general']['API_KEY']

if API_KEY == 'None':
    API_KEY = None

useOllama = False
builtInLanguageModel = False
ollama_module = None
tinylm = None

MAX_LENGTH = 5000


if server_url == 'builtin':
    builtInLanguageModel = True
    tinylm = importlib.import_module('TinyLangJaccard')


# ================= 工具函数 =================
def _imageToBase64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def isTime(text):
    pattern = r'\(?([0-2]?[0-9]):([0-5][0-9])\)?'
    pattern2 = r'\(?([0-2]?[0-9]).([0-5][0-9])\)?'
    matches = re.findall(pattern, text)
    matches.extend(re.findall(pattern2, text))
    valid_times = []
    for hour_str, minute_str in matches:
        hour = int(hour_str)
        minute = int(minute_str)
        if 0 <= hour <= 23:
            valid_times.append(f"{hour:02d}:{minute:02d}")
    return len(valid_times) > 0, valid_times


def concatenateText(text: list[ChatContent], images):
    message = []
    textList = text
    for t in textList[:-1]:
        if str(t) == '':
            continue
        if t.empty or t.text=="【空】":
            continue
        role = "assistant" if t.ownByMyself else "user"
        message.append({"role": role, "content": str(t)})

    if len(textList) < 1:
        textList = ['']

    last_content = str(textList[-1])
    if isVisionModel and images:
        valid_images = [p for p in images if os.path.exists(p)]
        message.append({"role": "user", "content": last_content, "images": valid_images})
    else:
        message.append({"role": "user", "content": last_content})

    if len(message) < 1:
        message.append({"role": "user", "content": "_"})
    return message


def _print_token_usage(usage: Dict[str, Any], backend: str = "API"):
    """参照 C# 实现打印 Token 用量"""
    if not usage:
        return
    
    prompt_tokens = usage.get('prompt_tokens', usage.get('input_tokens', 0))
    completion_tokens = usage.get('completion_tokens', usage.get('output_tokens', 0))
    total_tokens = usage.get('total_tokens', prompt_tokens + completion_tokens)
    
    print(f"\n[{backend}] Token 用量 | 输入: {prompt_tokens} | 输出: {completion_tokens} | 总计: {total_tokens}")


# ================= 核心推理函数 =================
def getAnswer(text: list[ChatContent], systemPrompt: str = 'auto') -> tuple[Optional[str],int]:
    totalTokens=0
    if len(text) == 0:
        return "",0

    # 内置模型处理
    if builtInLanguageModel:
        for t in text[::-1]:
            if t.text == '' or t.ownByMyself:
                continue
            return tinylm.answer(t.text),0 # type: ignore
        return '',0

    # 获取系统提示
    system_prompt = config.get('general', 'system')
    if systemPrompt != 'auto':
        system_prompt = systemPrompt if systemPrompt and system_prompt != 'None' else ''

    # 收集图片
    imageList = []
    imageCount = 0
    for t in text:
        if not t.ownByMyself:
            for i in t.imagePaths:
                if os.path.exists(i):
                    imageList.append(i)
                    imageCount += 1
                    if imageCount >= maxImageCount:
                        break
                else:
                    print(f"× 没有找到图片 {i}")
            if imageCount >= maxImageCount:
                break

    startTime = time.time()

    # ========== Ollama 后端 (使用 requests) ==========
    if useOllama:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages += concatenateText(text, imageList)

        ollama_url = "http://localhost:11434/api/chat"
        payload = {
            "model": modelName,
            "messages": messages,
            "stream": True
        }
        
        print(f"Ollama request: {json.dumps(payload, ensure_ascii=False)[:200]}...")
        
        try:
            result = ''
            length = 0
            # Ollama 流式响应中每个 chunk 可能包含 eval_count 等，但完整 usage 通常在最后一个 chunk
            final_eval_info = {}
            
            with requests.post(ollama_url, json=payload, stream=True, timeout=remoteServerTimeout) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line.decode('utf-8'))
                    token = chunk.get('message', {}).get('content', '')
                    
                    if token:
                        result += token
                        length += len(token)
                        print(token, end='', flush=True)
                        if length >= MAX_LENGTH:
                            break
                    
                    # 捕获最后一个 chunk 中的统计信息
                    if 'eval_count' in chunk:
                        final_eval_info = chunk
            
            print()  # 换行
            
            # Ollama 的 token 统计字段与 OpenAI 不同，做映射
            if final_eval_info:
                usage_map = {
                    'prompt_tokens': final_eval_info.get('prompt_eval_count', 0),
                    'completion_tokens': final_eval_info.get('eval_count', 0),
                    'total_tokens': final_eval_info.get('prompt_eval_count', 0)+final_eval_info.get('eval_count', 0)
                }
                totalTokens=final_eval_info.get('prompt_eval_count', 0)+final_eval_info.get('eval_count', 0);
                _print_token_usage(usage_map, backend="Ollama")
                
            print(f'用时{time.time()-startTime:.2f}s')
            return result,totalTokens
            
        except Exception as e:
            print(f"Ollama request failed: {e}")
            return None,0

    # ========== OpenAI 兼容后端 (使用 requests) ==========
    else:
        headers = {"Content-Type": "application/json"}
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 构建消息体
        if not (isVisionModel and imageList):
            for t in text:
                role = "assistant" if t.ownByMyself else "user"
                messages.append({"role": role, "content": str(t)})
            if messages and messages[-1]["role"] == "assistant":
                messages.append({"role": "user", "content": ""})
        else:
            for t in text[:-1]:
                role = "assistant" if t.ownByMyself else "user"
                messages.append({"role": role, "content": str(t)})

            last_t = text[-1]
            final_content: List[Dict] = [{"type": "text", "text": str(last_t)}]
            for img_path in imageList:
                if not os.path.isfile(img_path):
                    print(f"[ERROR] Image file not found: {img_path}")
                    continue
                b64_image = _imageToBase64(img_path)
                mime_type = "image/jpeg" if img_path.lower().endswith(('.jpg', '.jpeg')) else "image/png"
                final_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{b64_image}"}
                })
            messages.append({"role": "user", "content": final_content})

        api_url = f"{server_url.rstrip('/')}/chat/completions"
        payload = {
            "model": modelName,
            "messages": messages,
            "max_tokens": MAX_LENGTH,
            "temperature": 0.7,
            "stream": True  # 使用流式以实时输出
        }

        print(f"OpenAI compatible request: {json.dumps(payload, ensure_ascii=False)[:200]}...")

        try:
            result = ''
            usage_data = None
            
            with requests.post(api_url, json=payload, headers=headers, stream=True, timeout=remoteServerTimeout) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    decoded = line.decode('utf-8')
                    if not decoded.startswith('data:'):
                        continue
                    data_str = decoded[len('data:'):].strip()
                    if data_str == '[DONE]':
                        break
                    
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    
                    # 提取内容
                    delta = chunk.get('choices', [{}])[0].get('delta', {})
                    token = delta.get('content', '')
                    if token:
                        result += token
                        print(token, end='', flush=True)
                    
                    # 部分 API 在最后一个 chunk 返回 usage
                    if 'usage' in chunk and chunk['usage']:
                        usage_data = chunk['usage']

            print()
            
            # 如果流式没返回 usage，尝试从非流式获取（可选优化）
            # 这里直接使用流式中获取到的，或者打印提示
            
            if usage_data:
                totalTokens=usage_data.get('total_tokens', 0)
                _print_token_usage(usage_data, backend="OpenAI-Compatible")
            else:
                print("[INFO] 当前 API 流式响应未返回 Token 用量信息")
                
            print(f'用时{time.time()-startTime:.2f}s')
            return (result.strip() if result else None),totalTokens

        except Exception as e:
            print(f"[ERROR] Failed to get answer: {e}")
            return None,0


def get_answer_as_string(text: str, system_prompt):
    return getAnswer([ChatContent(username='', imagePaths=[], text=text, time='', ownByMyself=False)], system_prompt)


# ================= 测试入口 =================
if __name__ == '__main__':
    c = ChatContent(
        username='', imagePaths=[], 
        text='解释图片\n2\n3\n4\n5',
        time=f'{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}',
        ownByMyself=False
    )
    c2 = ChatContent(
        username='', imagePaths=[r"D:\Pictures\111.PNG"],
        text='12345',
        time=f'{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}',
        ownByMyself=True
    )
    c3 = ChatContent(
        username='', imagePaths=[],
        text='678910',
        time=f'{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}',
        ownByMyself=False
    )

    # 测试 Ollama
    useOllama = True
    modelName = 'jingyaogong/minimind2:latest'
    print("\n=== Testing Ollama ===")
    answer = getAnswer([c, c2, c3])
    print(f"Answer: {answer}")

    # 测试 Vision
    print("\n=== Testing Ollama Vision ===")
    isVisionModel = True
    answer = getAnswer([c, c2, c3])
    print(f"Answer: {answer}")

    # 测试 Built-in
    print("\n=== Testing Built-in Model ===")
    useOllama = False
    builtInLanguageModel = True
    answer = getAnswer([c, c2, c3])
    print(f"Answer: {answer}")

    # 测试 OpenAI Compatible
    print("\n=== Testing OpenAI Compatible API ===")
    builtInLanguageModel = False
    server_url = 'http://localhost:8000/v1'
    API_KEY = '21r234242'
    answer = getAnswer([c, c2, c3])
    print(f"Answer: {answer}")