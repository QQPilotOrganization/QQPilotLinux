<img alt="FishCakeQQ" src="../assets/FishCake.png" width="120">

# FishCakeQQ

###### 适用于带有 **图形桌面环境** 的 Linux 系统（如 xfce4 等）。纯窗口管理器（如 i3、dwm）未经测试，可能无法正常运行。


# 由于 pyautogui 不支持 ![s](ODF.png) **[Wayland](Wayland.md)**，请在 X11 下运行。

> 推荐使用LMDE。

FishCakeQQ 是一个全自动的 QQ 聊天机器人，通过以下流程实现智能回复：

> **复制聊天内容 → 解析消息（含图片/表情包）→ 调用 LLM 生成回复 → 模拟输入并发送**

全程 **不调用 QQ 内部接口、不 Hook 进程、不注入动态链接库**，极大降低账号封禁风险。

---

## 文档目录

| 文档 | 内容 |
|------|------|
| [安装](install.md) | 系统要求、QQ 设置、`uv` / Python 3.14、依赖与首次运行 |
| [使用](usage.md) | 启动界面、运行机器人、完整工作流程与注意事项 |
| [配置详解](config.md) | `config.ini` 每一个字段的含义与取值 |
| [模型后端](models.md) | Ollama、内置模型、Chat Completion、OneBot 直连 |
| [图形界面](webui.md) | pywebview 统一界面各页面说明 |
| [扩展开发](extensions.md) | 扩展模板、钩子函数、扩展 API、启用与停用 |
| [本地化](localization.md) | 多语言机制、新增文案与语言、自检工具 |
| [排错指南](troubleshooting.md) | 常见问题与排查步骤 |
| ![alt text](ODF.png)[Wayland](Wayland.md) | 为什么必须在 X11 下运行 |
| [架构说明](architecture.md) | 目录结构、模块职责与数据流（开发者） |
| [贡献指南](contributing.md) | 开发环境、代码规范、提交与发布（开发者） |
| [角色设定](../characterset.md) | 看板娘「鱼板 FishCake」的外观、性格与台词 |

---

## 特性

- **纯视觉自动化**：截图 + 模板匹配 + 剪贴板，不碰 QQ 协议。
- **窗口自动化**：驱动鼠标键盘完成选取、复制、粘贴、发送。
- **多种后端**：本地 Ollama、内置轻量模型、任意 OpenAI 兼容接口，或直接接入 OneBot 机器人。
- **可扩展**：`Extensions/` 下的 Python 文件可以在收消息、截图后、发送前挂载自己的逻辑。
- **图形界面**：设置、扩展、升级、图片导入等在同一个 pywebview 网页界面里完成。
- **可本地化**：全部界面与日志文案走 `localization/`，方便翻译成其它语言。

## 推荐配置

- 1920×1080 分辨率
- 8 GB RAM
- 4 GB 磁盘
- 至少一个桌面环境（Cinnamon、Xfce4、KDE、GNOME、Mate、LXQt 等）

## 快速开始

```bash
git clone https://github.com/QQPilotOrganization/QQPilotLinux.git
cd FishCakeQQLinux
sudo apt install xclip
sudo apt install python3-tk python3-xlib
sudo apt install libnss3 libxkbcommon-x11-0 libxcb-cursor0
uv sync            # 安装依赖（含 pywebview[qt]）
./menu.sh          # 打开图形界面，先做设置
./run.sh           # 启动机器人
```

> 详细步骤见 [安装](install.md) 与 [使用](usage.md)。

---

## 免责声明

本软件 **仅限技术学习与研究用途**，严禁用于：

- 自动骚扰、刷屏、诈骗等恶意行为
- 违反《QQ 软件许可协议》的操作
- 任何违法违规场景

使用者须自行承担因使用本软件引发的一切法律责任，作者概不负责。
