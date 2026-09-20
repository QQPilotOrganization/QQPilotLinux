<img alt="FishCakeQQ" src="../assets/FishCake.png" width="100">

# 模型后端

[← 返回目录](main.md)

FishCakeQQ 只负责“把聊天内容交给一个能回话的东西”，这个“东西”由
`config.ini` 的 `server_url` 决定。本篇介绍四种后端，以及如何验证它们。

---

## 总览

| 后端 | `server_url` | 联网 | 说明 |
|------|--------------|------|------|
| Ollama | `ollama` | 本机 | 本地大模型，推荐 |
| 内置模型 | `builtin` | 否 | TinyLangJaccard，极轻量 |
| Chat Completion | 任意 URL | 视情况 | 任意 OpenAI 兼容接口 |
| OneBot 直连 | `onebot` | 视情况 | 直接把对话交给一个 QQ 机器人框架 |

---

## Ollama（推荐）

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull huihui_ai/deepseek-r1-abliterated:8b
```

```ini
server_url = ollama
modelname = huihui_ai/deepseek-r1-abliterated:8b
api_key = 随便填一个非空值
```

- 实际请求地址：`http://localhost:11434/api/chat`
- 走的是 Ollama 的原生 `/api/chat` 协议，图片以纯 base64 数组随消息发送。
- 想把 Ollama 装在虚拟机 / 另一台机器上，参考 [useollamainVM](../useollamainVM/useOllamainVM.md)。

> 💡 显存有限时优先选 8B 级别；视觉多模态模型在窗口截图场景下效果通常不理想。

---

## 内置模型（TinyLangJaccard）

```ini
server_url = builtin
```

- 不需要联网、不需要任何模型文件。
- 用 Jaccard 相似度在本地数据集里找最接近的问答，属于“情绪陪伴级”的兜底方案。
- 数据来自 `datasetTiny.json`；如需自行生成，可运行 `prepareData.py` 后 `TinyLangJaccard.py`。
- 原理、数据来源与已知局限见 [tinyLangJaccardReadme](../tinyLangJaccardReadme.md)。

> 适合“只想先跑通流程”或断网环境；正经使用请换 Ollama / 在线模型。

---

## Chat Completion（OpenAI 兼容）

适用于任何提供 `/chat/completions` 的服务（本地 vLLM、LM Studio、各家云 API）。

```ini
server_url = https://api.example.com/v1
modelname = gpt-4.1-mini
api_key = sk-xxxxxxxx
forceollamaapi = False
```

- 关闭 `forceollamaapi` 时：请求 `<server_url>/chat/completions`。
- 打开 `forceollamaapi` 时：地址只需写到主机，程序自动拼 `/api/chat`。
- `api_key` 非空且地址不是 localhost 时，会带上 `Authorization: Bearer <api_key>`。

### 本地自测

仓库自带一个 Mock 服务器，用来确认请求结构是否正确：

```bash
uv run python mock_openai_server_openai.py
```

然后：

```ini
server_url = http://localhost:8000/v1
modelname = mock
api_key = test-key
```

它会把收到的请求打印出来，并返回一条固定回复。
也可以用 `testAPI.py` 直接对着当前配置发一次请求：

```bash
uv run python testAPI.py
```

---

## OneBot 直连

这是“把 FishCakeQQ 当成一个 QQ 客户端，接入现成的机器人框架（如 MaiBot /
NapCat 生态）”的模式。此时 FishCakeQQ 不再自己调用大模型，而是：

1. 把解析出的聊天消息翻译成 **OneBot v11 消息事件** 发出去；
2. 等待对方用 `send_private_msg` / `send_group_msg` / `send_msg` 把回复发回来；
3. 把回复当作答案粘贴进 QQ 并发送。

```ini
server_url = onebot
api_key = my-token            ; 作为 authorization
websocket_server = ws://localhost:3001
account_id = 123456           ; 机器人账号，需与 OneBot 端一致
reverse = False               ; False=主动连出去；True=本机监听等对方连入
```

### 正向 / 反向

| `reverse` | 行为 | 典型场景 |
|-----------|------|----------|
| `False`（正向） | FishCakeQQ 作为客户端连到 `websocket_server` | OneBot 框架提供了 WS 服务端 |
| `True`（反向） | FishCakeQQ 在 `websocket_server` 上开服务，等 OneBot 连入 | 框架以反向 WS 客户端方式接入 |

正向连接会带上握手头 `X-Client-Role: universal`、`X-Self-ID: <account_id>`，
以及 `Authorization: Bearer <api_key>`。

### 消息如何映射

- 每条用户消息按 `[time] / [username] / [content]` 解析（见 [配置详解](config.md#提示词)）。
- 用户名全部相同 → 私聊；出现多个用户名 → 群聊。
- 群聊里每个用户名会单独映射一个稳定的 `user_id`，避免不同的人被当成同一个。
- 收到的 `send_*_msg` 会被拼成一条回复；支持文本与 `image` 段（图片转成 `base64://`）。

### 协议实现

协议实现位于 `CompletionConnector/`（内嵌的 CompletionConnector），
`qqpilotTranslation.py` 负责 QQPilot 风格文本 ↔ OneBot 消息的互转，
`websocketConnector.py` 负责收发，`translateLayer.py` 负责调度。

> 更多背景可参考 OneBot v11 规范：<https://github.com/botuniverse/onebot-11>

---

## 该选哪一个？

| 你的情况 | 建议 |
|----------|------|
| 有一台能跑模型的机器，在意隐私 | `ollama` |
| 想零配置先跑通 | `builtin` |
| 已经有云端 / 自建 OpenAI 兼容服务 | 自定义 URL |
| 已经在用 MaiBot 等机器人框架 | `onebot` |

[← 返回目录](main.md)
