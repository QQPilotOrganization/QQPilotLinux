<img alt="FishCakeQQ" src="../assets/FishCake.png" width="100">

# 配置详解

[← 返回目录](main.md)

所有设置都存放在项目根目录的 `config.ini` 的 `[general]` 段里。
可以直接用文本编辑器改，也可以在图形界面「运行设置」页改（两者等价）。

```ini
[general]
version = 2.0
language = zh_CN
name = neko
width = 1285
height = 720
maximagecount = 12
modelname = qwen3.5:0.8b
isvisionmodel = False
api_key =
server_url = ollama
scroll = 5
withimage = False
autologin = False
autofocusing = False
sendimagepossibility = 86
nt_data = None
atdetect = False
tab_times = 8
remote_server_timeout = 300
forceollamaapi = False
sleep = 2
websocket_server = ws://localhost:3001
account_id = 80586
reverse = False
system = ...
scale = 1.00
```

> 💡 值后面可以用 `;` 写行内注释，例如 `remote_server_timeout = 300 ;超时`，
> 程序会把它当注释而不是值。

---

## 基本

| 字段 | 默认 | 说明 |
|------|------|------|
| `version` | `2.0` | 版本号，仅在界面/日志里展示，不用改 |
| `language` | `zh_CN` | 界面与日志语言，对应 `localization/<语言>.json`，见 [本地化](localization.md) |
| `name` | `neko` | **机器人自己的 QQ 昵称**。程序用它判断一条消息是不是自己发的（`ownByMyself`），群聊时尤其重要，请与 QQ 里一致 |
| `scale` | `1.00` | 悬浮窗等界面的缩放系数。Linux 下由 `scaleToiniLinux.py` 固定为 `1.0` |

## 窗口

| 字段 | 默认 | 说明 |
|------|------|------|
| `width` | `1285` | 把 QQ 窗口调整到的宽度（像素） |
| `height` | `720` | 把 QQ 窗口调整到的高度（像素） |

> 程序启动时会把标题为 `qq` 的窗口移到左上角并调整到该尺寸。
> 改这两个值前，请确认屏幕放得下，否则界面会被裁切。

## 消息与解析

| 字段 | 默认 | 说明 |
|------|------|------|
| `scroll` | `5` | 框选聊天记录时按住鼠标拖动的时长（秒）；消息越多需要越大 |
| `maximagecount` | `12` | 每次最多解析几张图片；本地模型建议调小 |
| `withimage` | `False` | 回复为空时，是否允许改为发送图片 |
| `sendimagepossibility` | `86` | 上一条生效时，发送图片的概率（0–100） |
| `atdetect` | `False` | 打开后只处理被 **@** 的消息 |
| `tab_times` | `8` | 模板匹配失败时的 Tab 次数，可选 `7` / `8`。若框选时总是点到删除等按钮，请降低 |
| `nt_data` | `None` | 预留字段，当前代码未使用 |

## 模型与服务器

| 字段 | 默认 | 说明 |
|------|------|------|
| `server_url` | `ollama` | 后端选择，见下方「server_url 的取值」 |
| `modelname` | `qwen3.5:0.8b` | 传给模型的模型名 |
| `isvisionmodel` | `False` | 该模型是否支持图片；`False` 时不会发送任何图片 |
| `api_key` | *(空)* | 模型接口的 API Key；Ollama 可随意填。**OneBot 模式下它同时作为 authorization** |
| `forceollamaapi` | `False` | 强制按 Ollama 的 `/api/chat` 约定调用（地址只需写到域名） |
| `remote_server_timeout` | `300` | 等待模型/OneBot 回复的超时（秒）。本地模型或慢机器建议保持 300 |

### server_url 的取值

| 取值 | 行为 |
|------|------|
| `ollama` | 使用 `http://localhost:11434/api/chat` |
| `builtin` | 使用内置的 TinyLangJaccard 轻量模型（无需联网） |
| `onebot` | 直接用 OneBot v11 协议连接机器人后端，见 [模型后端](models.md#onebot-直连) |
| 其它任意地址 | 视为 OpenAI 兼容的 base URL，实际请求 `<server_url>/chat/completions` |

> **强制 Ollama API**（`forceollamaapi = True`）时，自定义地址只需写到主机，
> 程序会自动拼 `/api/chat`。例如填 `https://example.com` → `https://example.com/api/chat`；
> 关闭时填 `https://example.com/v1` → `https://example.com/v1/chat/completions`。

### OneBot 直连相关

| 字段 | 默认 | 说明 |
|------|------|------|
| `websocket_server` | `ws://localhost:3001` | OneBot v11 的 WebSocket 地址 |
| `account_id` | `80586` | 机器人账号，可随意填，但需与 OneBot 端一致 |
| `reverse` | `False` | `True`=反向（本机监听等 OneBot 连入）；`False`=正向（主动连出去） |

> 只有 `server_url = onebot` 时，这三项才生效。

## 行为

| 字段 | 默认 | 说明 |
|------|------|------|
| `autologin` | `False` | 启动后自动寻找登录按钮并点击（建议直接开 QQ 的自动登录） |
| `autofocusing` | `False` | 持续把 QQ 窗口置于最前，避免被别的窗口遮挡 |
| `sleep` | `2` | 预留字段，当前代码未使用 |

## 提示词

| 字段 | 说明 |
|------|------|
| `system` | System Prompt。支持多行；会在每次请求里作为第一条 `system` 消息发送。默认是一段 FishCake（鱼板）人格设定 |

`system` 里约定：把每条用户消息按

```plaintext
[time] （时间）
[username] （用户名）
[content] （内容）
```

的格式组织；回复只输出正文，用 `[[NEXT]]` 表示换行。

## 额外请求参数

除 `config.ini` 外，`extra.json` 会**合并进每次请求体**，用于设置 `temperature` 之类的字段：

```json
{
    "temperature": 0.8,
    "think": false
}
```

在图形界面里通过「运行设置 → 提示词 → 编辑 extra.json」，或「额外参数」页编辑。

---

## 手改配置示例

改成接入本地 Ollama：

```ini
server_url = ollama
modelname = huihui_ai/deepseek-r1-abliterated:8b
api_key = 随意
```

改成接入任意 OpenAI 兼容服务：

```ini
server_url = https://api.example.com/v1
modelname = gpt-4.1-mini
api_key = sk-xxxxxxxx
forceollamaapi = False
```

改成 OneBot 直连（反向）：

```ini
server_url = onebot
api_key = my-token
websocket_server = ws://localhost:3001
account_id = 123456
reverse = True
```

[← 返回目录](main.md)
