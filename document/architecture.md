<img alt="FishCakeQQ" src="../assets/FishCake.png" width="100">

# 架构说明

[← 返回目录](main.md)

面向想读源码 / 改源码的人。先说清楚“哪个文件干什么”，再说数据怎么流动。

---

## 目录结构

```
FishCakeQQLinux/
├─ ScreenshotToUILayout.py   主程序：整个自动回复循环
├─ menu.py                   图形界面入口（webui）
├─ positions.py              UI 相对坐标与换算
├─ image.py                  全屏截图
├─ Vision.py                 模板匹配（OpenCV）
├─ GUIOperations3.py         鼠标/键盘/剪贴板等窗口操作
├─ conversationStyleExtract.py  聊天文本 → ChatContent
├─ chatContent.py            消息数据模型
├─ answer.py                 后端选择与请求模型
├─ TinyLangJaccard.py        内置轻量模型
├─ prepareData.py            生成内置模型数据集
├─ extensionLoader.py        扩展加载与调用
├─ extensionAPIs.py          暴露给扩展的 API
├─ dockLog.py                右下角悬浮状态窗
├─ messagebox.py             跨平台消息框
├─ load.py                   启动动画
├─ localization/             本地化（t / 翻译表 / 自检）
├─ webui/                    统一图形界面（pywebview + 前端）
├─ onebotConnector.py        OneBot 直连桥（Python 侧入口）
├─ CompletionConnector/      内嵌的 OneBot 协议实现
├─ sysDetect.py              平台判断
├─ scaleToiniLinux.py        Linux 下强制 scale=1.0
├─ config.ini                配置
├─ extra.json                额外请求参数
├─ Extensions/               扩展目录
├─ assets/                   图标与截图
└─ document/                 本套文档
```

---

## 模块职责

### 主循环

| 模块 | 职责 |
|------|------|
| `ScreenshotToUILayout.py` | 定位 QQ 窗口 → 计算坐标 → 找红点 → 打开会话 → 框选复制 → 解析 → 请求模型 → 发送；循环往复 |
| `positions.py` | 定义各 UI 元素相对窗口的坐标（`*_RELATIVE_*`），并提供 `toActualSize` / `toActualPoint` 换算成绝对坐标 |
| `image.py` | `fullScreenShot()` 截图并保存为 `screenshot.png` |
| `Vision.py` | `FindTemplates()` 在截图中查找模板图，返回坐标 |
| `GUIOperations3.py` | `click` / `dragFromTo` / `HotKey` / `PasteTextToSection` / `SendText`；必要时生成并调用 `left.sh`、`focus.sh` 操作窗口 |

### 消息

| 模块 | 职责 |
|------|------|
| `conversationStyleExtract.py` | `ParseChatLog()` 把剪贴板里的聊天文本切成消息列表，提取 `<img src=...>` 里的图片路径 |
| `chatContent.py` | `ChatContent` 数据类：`username` / `text` / `time` / `imagePaths` / `ownByMyself`，以及 `report()` / `__str__()` |

### 模型

| 模块 | 职责 |
|------|------|
| `answer.py` | 读配置决定后端；`_concatenate_text()` 拼 OpenAI 风格 `messages`；`getAnswer()` 发请求并解析回复与 token |
| `TinyLangJaccard.py` | 内置模型：Jaccard 相似度检索 |
| `prepareData.py` | 由 `train.jsonl` 生成 `datasetTiny.json` / `tokenizer.json` |

### 扩展

| 模块 | 职责 |
|------|------|
| `extensionLoader.py` | 启动时加载 `Extensions/*.py`；`callEveryExtension(name, *args)` 依次调用钩子并传递返回值 |
| `extensionAPIs.py` | 暴露 `ChatContent`、`notify`、`get_answer_as_string` |

### 界面与本地化

| 模块 | 职责 |
|------|------|
| `webui/app.py` | pywebview 宿主；`Api` 类把配置读写、扩展、升级、图片导入暴露给前端 |
| `webui/web/` | 前端（HTML/CSS/JS），通过 `window.pywebview.api.*` 调用后端 |
| `dockLog.py` | tkinter 悬浮窗，独立线程运行，`setText()` 更新状态 |
| `messagebox.py` | 统一消息框 |
| `localization/` | `t()` 查询翻译；`check.py` 自检缺键与硬编码 |

### OneBot 直连

| 模块 | 职责 |
|------|------|
| `onebotConnector.py` | Python 侧入口：`start()` 起连接，`get_answer(ChatContents)` 收发一轮 |
| `CompletionConnector/websocketConnector.py` | 正向/反向 WebSocket 收发 |
| `CompletionConnector/translateLayer.py` | 调度翻译、等待回复 |
| `CompletionConnector/qqpilotTranslation.py` | QQPilot 文本 ↔ OneBot 消息事件互转，维护 user/group 映射 |

### 平台与辅助

| 模块 | 职责 |
|------|------|
| `sysDetect.py` / `scaleToiniLinux.py` | 平台判断；Linux 下把 `scale` 固定为 1.0 |
| `load.py` | 终端启动动画 |
| `mock_openai_server_openai.py` | 本地 Mock 模型，验证请求格式 |
| `testAPI.py` | 对着当前配置发一次请求 |
| `serverForNya2PtCl6.py` | 一个把 HTTP 请求转发的兼容层（可选） |
| `focus.py` / `getWindow.py` / `download/` | Windows 版遗留，Linux 下不使用 |

---

## 数据流

```
                       ┌────────────────────────────┐
                       │  QQ for Linux (X11 窗口)    │
                       └────────────┬───────────────┘
      截图                         │ 鼠标/键盘
        │                           │
        ▼                           │
  image.fullScreenShot()            │
        │                           │
        ▼                           │
  Vision.FindTemplates()  ──红点──▶ GUIOperations3.click()
        │                                   │
        │                              框选 + Ctrl+C
        │                                   │
        │                                   ▼
        │                            剪贴板（pyperclip）
        │                                   │
        │                                   ▼
        │                     conversationStyleExtract.ParseChatLog()
        │                                   │
        │                                   ▼
        │                            List[ChatContent]
        │                                   │
        │                       extensionLoader(after_receiving_messages)
        │                                   │
        ▼                                   ▼
   answer.getAnswer() ◀──────────── 拼请求（system + messages）
        │
        ├── Ollama / 内置 / Chat Completion / OneBot
        │
        ▼
   回复文本 ──▶ extensionLoader(before_sending_the_message_by_AI_generated)
        │
        ▼
   GUIOperations3.SendText() ──▶ Ctrl+Enter 发送
        │
        └───────────────▶ 回到“截图”继续循环
```

---

## 线程模型

| 线程 | 内容 |
|------|------|
| 主线程 | 自动回复循环；`menu.py` 里则是 pywebview 事件循环 |
| 悬浮窗线程 | `dockLog` 的 tkinter 窗口（daemon） |
| OneBot 线程 | WebSocket 连接/监听（daemon） |
| pywebview 工作线程 | `Api` 的方法（升级、复制图片等耗时任务） |

> 因此 `dockLog.setText()` 与 `websocketConnector.SendMessage()` 都是线程安全的入队操作，
> 真正的 UI 更新 / 网络发送在各自线程里完成。

---

## 运行时产物

程序运行会生成 / 修改这些文件（已在 `.gitignore` 中排除大部分）：

| 文件 | 说明 |
|------|------|
| `tokencount.txt` | 累计 token 用量 |
| `log.txt` | 主程序日志 |
| `screenshot.png` | 最近一次截图 |
| `dest.json` | 最近一次请求体（调试用） |
| `left.sh` / `focus.sh` | 窗口操作脚本 |
| `ChatManager.db` / `IncomingMessage.sqlite3` | OneBot 模式下消息去重与会话映射 |
| `Images/` | 导入的图片素材 |

---

## 配置与本地化的读取时机

- `config.ini`：模块导入时读取（`answer.py`、`dockLog.py` 等），
  所以改配置后需要**重启程序**（界面保存后建议重启）。
- `localization`：导入 `localization` 时读取一次并缓存；
  语言变更同样需要重启。

[← 返回目录](main.md)
