<img alt="FishCakeQQ" src="../assets/FishCake.png" width="100">

# 安装

[← 返回目录](main.md)

本篇从零开始，把 FishCakeQQ 装到一台有图形桌面的 Linux 机器上。

---

## 1. 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | 带图形桌面环境的 Linux（Xfce4、KDE、GNOME、Cinnamon、Mate、LXQt…） |
| 显示服务 | **X11**（Wayland 下 `pyautogui` 无法工作，见 [Wayland](Wayland.md)） |
| 分辨率 | 推荐 1920×1080，且**系统显示缩放保持 100%** |
| 内存 | 推荐 8 GB（使用本地大模型时越多越好） |
| Python | **3.14**（`pyproject.toml` 要求 `>=3.14`） |
| 磁盘 | 约 4 GB（含 Python 与依赖；模型另计） |

> ⚠️ 纯窗口管理器（i3、dwm 等）没有完整桌面环境，坐标与窗口管理行为不可预期，未经测试。
> ⚠️ WSL 不支持：请直接用 Windows 版，或装一台真正的 Linux 桌面。

---

## 2. 安装并设置 QQ for Linux

1. 从官网下载安装 QQ for Linux：<https://im.qq.com/linuxqq/index.shtml>
2. 登录一次，确认能正常收发消息。
3. 按下面的表格调好 QQ 客户端设置，这些设置直接决定识别的成功率：

| QQ 设置项 | 取值 | 原因 |
|-----------|------|------|
| 发送消息快捷键 | **Ctrl + Enter** | FishCakeQQ 用 `Ctrl+Enter` 发送 |
| 联系人面板宽度 | 拖到 **最窄** | 保证聊天区坐标稳定 |
| 主题 | **浅色** | 深色主题会让模板匹配失效 |
| 自动更新 | **关闭** | 更新会改变界面布局 |
| 字体大小 | **最小** | 单屏能容纳更多消息 |
| 系统显示缩放 | **100%** | 缩放会整体错位 |

> 🔍 FishCakeQQ 完全依赖 UI 坐标识别界面。任何布局变动（缩放、换主题、改字体）都可能导致识别失败。

---

## 3. 安装 `uv` 与 Python

`uv` 是 Astral 推出的 Python 工具链，用来替代 `pip` + `pyenv`。

```bash
# 官方安装脚本（国内可能较慢）
curl -LsSf https://astral.sh/uv/install.sh | sh
```

安装后**重开一个终端**。

然后安装带 Tkinter 的 Python 3.14：

```bash
# 国内加速 Python 二进制下载（可选）
export UV_PYTHON_INSTALL_MIRROR=https://mirror.nju.edu.cn/github-release/indygreg/python-build-standalone

uv python install 3.14
uv python list        # 确认 3.14 已安装
```

> ⚠️ **不要直接用发行版自带的 Python**：很多系统的 Python 不带 `tkinter`，
> 而悬浮状态窗（`dockLog.py`）与消息框（`messagebox.py`）仍然依赖 tkinter。

---

## 4. 获取 FishCakeQQ

```bash
git clone https://github.com/FishCakeQQOrganization/FishCakeQQLinux.git
cd FishCakeQQLinux
chmod +x ./*.sh      # 让 run.sh / menu.sh 等可执行
```

---

## 5. 创建虚拟环境并安装依赖

```bash
uv venv ./venv
uv sync              # 按 pyproject.toml 安装全部依赖
```

`uv sync` 会装上运行所需的 Python 包，其中包括图形界面要用的 `pywebview[qt]`
（Windows 上对应 EdgeChromium，Linux 上对应 Qt WebEngine）。

主要依赖一览：

| 依赖 | 用途 |
|------|------|
| `pyautogui` / `windmouse` | 鼠标键盘模拟与平滑移动 |
| `pyperclip` | 剪贴板读写 |
| `opencv-python` | 截图与模板匹配 |
| `pillow` | 图片处理 |
| `requests` | 调用模型接口 |
| `colorama` | 终端彩色日志 |
| `tqdm` | 计时进度条 |
| `pywebview[qt]` | 统一图形界面 |
| `websockets` / `json5` / `flask` | OneBot 直连与辅助服务 |

---

## 6. 安装系统依赖（可选但推荐）

```bash
# pyperclip 的剪贴板后端
sudo apt install xclip

# pyautogui 需要的 X11 / tkinter 组件
sudo apt install python3-tk python3-xlib

# Qt 版 pywebview 在部分发行版上还需要这些运行库
sudo apt install libnss3 libxkbcommon-x11-0 libxcb-cursor0
```

> 只用 GTK 后端的话：`sudo apt install gir1.2-webkit2-4.1 python3-gi`。

---

## 7. 首次运行

```bash
./menu.sh     # 打开图形界面：先做设置
./run.sh      # 启动机器人
```

- `./menu.sh` 打开统一界面（启动台 / 运行设置 / 扩展管理 / 升级助手 / 图片导入 / 额外参数）。
- `./run.sh` 启动主程序；也可以直接在界面的「启动台」页点「启动 QQPilot」。

界面能打开但内容为空、或报 “WebView 后端可能没装好”，见
[排错指南](troubleshooting.md#图形界面打不开)。

---

## 8. 下一步

- 配置模型与服务器：[配置详解](config.md)、[模型后端](models.md)
- 了解运行方式：[使用](usage.md)
- 装扩展：[扩展开发](extensions.md)

[← 返回目录](main.md)
