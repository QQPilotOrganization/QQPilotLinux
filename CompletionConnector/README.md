# QQPilotLinux 内嵌 CompletionConnector

本目录是 [CompletionConnector](https://github.com/Na2Cr2O7/CompletionConnector)
（含 [CompletionConnector-For-QQPilot](https://github.com/Na2Cr2O7/CompletionConnector-For-QQPilot)
的 `qqpilotTranslation.py` 与 `config.json5`）在 QQPilotLinux 内的源码副本。

QQPilotLinux 在 `config.ini` 中设置 `server_url = onebot` 后，**直接用 OneBot v11
协议连接 OneBot 端**（不额外起 HTTP 服务），协议实现即复用本包：

- `websocketConnector.py`：按 `websocket_server` / `reverse` 连接或监听 OneBot
  （正向 / 反向 WebSocket）；
- `translateLayer.py` + `qqpilotTranslation.py`：把 QQPilot 的消息翻译成 OneBot
  消息事件，并把 OneBot 的 `send_*_msg` 回复翻译回文本。

调用入口是 QQPilotLinux 根目录的 `onebotConnector.py`：

- `answer.py` 在 `server_url = onebot` 时调用 `onebotConnector.start()` 启动连接；
- `answer.getAnswer()` 调用 `onebotConnector.get_answer(ChatContents)`，把会话内容
  发给 OneBot 端并等待其回复作为答案。

## 配置来源

`config.py` 优先读取 QQPilotLinux 根目录的 `config.ini`：

| config.ini              | CompletionConnector | 说明                                  |
| ----------------------- | ------------------- | ------------------------------------- |
| `api_key`               | `authorization`     | OneBot 鉴权（即原 config.json5 的值） |
| `websocket_server`      | `websocket_server`  | OneBot v11 WebSocket 地址             |
| `account_id`            | `account_id`        | 机器人账号                            |
| `reverse`               | `reverse`           | True=反向，False=正向                 |
| `name`                  | `nickname`          | 机器人昵称                            |
| `remote_server_timeout` | `timeout`           | 等待 OneBot 回复的超时（秒）          |

翻译实现固定为 `qqpilotTranslation`。

未找到 `config.ini` 时回退到本目录的 `config.json5`（可独立运行本包）。

## 依赖

`websockets`、`colorama`、`pillow`，`json5`（可选，仅 config.json5 回退时用），
见 QQPilotLinux 的 `requirements.txt` / `pyproject.toml`。
