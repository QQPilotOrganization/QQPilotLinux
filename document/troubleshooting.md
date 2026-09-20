<img alt="FishCakeQQ" src="../assets/FishCake.png" width="100">

# 排错指南

[← 返回目录](main.md)

按“症状 → 原因 → 处理”组织。先看终端日志（运行 `./run.sh` 的那个窗口），
大部分问题会在里面直接写明。

---

## 图形界面打不开

**症状**：`./menu.sh` 报错退出，或提示“WebView 后端可能没装好”。

Linux 上 pywebview 需要一个 WebView 后端：

```bash
uv sync                                  # 安装 pyproject 里的 pywebview[qt]
# 若 Qt 仍起不来，补系统库：
sudo apt install libnss3 libxkbcommon-x11-0 libxcb-cursor0
```

或改用 GTK 后端：

```bash
sudo apt install gir1.2-webkit2-4.1 python3-gi
uv pip install "pywebview[gtk]"
```

界面能打开但文字显示成 `Xui.nav.launch` 这样的形式，说明翻译键缺失，
见 [本地化](localization.md#自检工具)。

---

## 一启动就提示 Wayland

**症状**：日志出现 `wayland下可能无法正常使用`。

`pyautogui` 依赖 X11 的坐标与输入模型，Wayland 下无法工作。
请在登录界面选择 **X11 / Xorg** 会话，详见 [Wayland](Wayland.md)。

---

## 窗口找不到 / 坐标全错

**症状**：程序启动后没有移动 QQ 窗口，或点击位置明显不对。

排查：

1. 确认终端里 `wmctrl -l` 能列出标题为 `qq` 的窗口：

   ```bash
   sudo apt install wmctrl
   wmctrl -l | grep -i qq
   ```

2. QQ 窗口标题必须正好是 `qq`。若你的客户端标题不同，
   需要修改 `GUIOperations3` 生成的 `left.sh` 中的匹配条件。

3. 系统**显示缩放必须是 100%**。Fractional scaling 会让所有坐标整体偏移。

4. 分辨率建议 1920×1080；`config.ini` 的 `width`/`height` 不要超过屏幕。

---

## 找不到“复制”按钮 / 总点到删除键

**症状**：日志出现 `使用模板匹配查找复制按钮失败`，或框选时按到了别的按钮。

| 处理 | 说明 |
|------|------|
| 检查主题 | 必须是**浅色主题**，深色主题下模板匹配失效 |
| 检查字体/缩放 | 字体大小改回最小，显示缩放 100% |
| 调整 `tab_times` | 若总是点到删除，把它在 `7` / `8` 之间换一个 |
| 排查 QQ 更新 | 新版本可能改变布局；先确认旧版是否正常 |

---

## 提取不到消息

**症状**：日志出现 `没有提取到消息。`，然后跳过本轮。

| 可能原因 | 处理 |
|----------|------|
| 框选时长太短，没选中内容 | 增大 `config.ini` 的 `scroll` |
| 剪贴板后端缺失 | `sudo apt install xclip` |
| 窗口被遮挡/最小化 | 保持 QQ 前台；可开 `autofocusing` |
| 聊天区被压缩 | 把联系人面板拖到最窄、字体调到最小 |

---

## 一直“等待语言模型生成答案”然后失败

**症状**：日志出现 `语言模型生成答案失败` 或超时。

1. 单独验证接口是否可用：

   ```bash
   uv run python mock_openai_server_openai.py   # 另开一个终端
   uv run python testAPI.py                     # 对着当前配置发一次请求
   ```

2. 检查 `server_url` 与 `forceollamaapi` 是否匹配：

   - Ollama 原生：`server_url = ollama`
   - OpenAI 兼容：`server_url = https://host/v1`
   - 强制 Ollama API：`server_url = https://host`（不要带 `/v1`）

3. 本地模型较慢时把 `remote_server_timeout` 调大（如 `600`）。

4. 需要鉴权的服务确认 `api_key` 正确；非 localhost 地址会自动带
   `Authorization: Bearer`。

---

## 答案为空、机器人不发消息

**症状**：请求成功但 `result` 为空，日志出现 `答案未生成,退出会话`。

- 模型确实回了空内容：换个模型或调低 `temperature`（写在 `extra.json`）。
- 期望“答不上来就发图”：把 `withimage` 打开，并设置 `sendimagepossibility > 0`。
- 扩展在 `before_sending_the_message_by_AI_generated` 里把答案改成了空字符串：
  检查扩展逻辑。

---

## OneBot 连不上

| 症状 | 检查 |
|------|------|
| 一直重连 | `websocket_server` 地址/端口是否正确；`reverse` 是否与对方期望一致 |
| 对方拒绝握手 | `account_id` 是否与 OneBot 端一致；`api_key` 是否正确 |
| 消息发出去了但没回复 | 对方是否用 `send_private_msg` / `send_group_msg` / `send_msg` 回执 |
| 群聊认错人 | 确认 `system` 提示词里的 `[username]` 格式未被改动 |

反向模式（`reverse = True`）下本机监听 `websocket_server` 的端口，
请确认防火墙没有拦截，且端口未被占用。

---

## 扩展导致异常

**症状**：启动阶段打印 `加载错误 <文件> <异常>`。

- 该扩展会被跳过，其它扩展照常加载；按提示修好该文件即可。
- 确认扩展直接放在 `Extensions/` 下（子目录不加载）。
- 确认 `description` 变量存在，且钩子函数签名正确。
- 参考 [扩展开发](extensions.md) 里的最小模板。

---

## 日志与状态

| 位置 | 内容 |
|------|------|
| 运行 `./run.sh` 的终端 | 每一步的坐标、状态、错误（最全） |
| 右下角悬浮窗 | 当前动作（右键可关闭） |
| `log.txt` | 主程序写入的日志文件 |
| 界面「升级助手」页日志区 | 升级过程 |

贴 Issue 时请附上终端输出（可去掉个人信息）。

---

## 还是不行？

- 对照 [使用](usage.md) 再核对一遍 QQ 设置；
- 确认没有第二个程序在抢占鼠标/键盘；
- 提交 Issue：<https://github.com/FishCakeQQOrganization/FishCakeQQLinux/issues>，
  附上发行版、桌面环境、Python 版本与完整日志。

[← 返回目录](main.md)
