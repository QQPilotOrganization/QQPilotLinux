
<div align="center">
<img alt="示例截图" src="./assets/FishCake.png" width="120" >
 <h1> FishCakeQQ</h1>

<h6>使用纯视觉 + 窗口自动化实现 QQ 消息自动回复，<b>零 API 依赖、零注入、低封号风险。</b>
</h6>


</div> 

[文档](document/main.md) |
[Windows版本](https://github.com/QQPilotOrganization/QQPilot) | 
[Android版本](https://github.com/QQPilotOrganization/QQPilotPocketEdition)

<!-- 
## 1.5.15

对于强制使用Ollama API，填写类似https://example.com 即可，会自动定向到 https://example.com/api/chat。
否则填写https://example.com/v1 定向到 https://example.com/v1/chat/completions/


> 使用纯视觉 + 窗口自动化实现 QQ 消息自动回复，**零 API 依赖、零注入、低封号风险**。  
> 适用于带有 **图形桌面环境** 的 Linux 系统（如 xfce4 等）。纯窗口管理器（如 i3、dwm）未经测试，可能无法正常运行。

> ****由于pyautogui不支持wayland，请在x11下运行。****


##  项目简介

FishCakeQQ 是一个全自动的 QQ 聊天机器人，通过以下流程实现智能回复：

> **复制聊天内容 → 解析消息（含图片/表情包）→ 调用 LLM 生成回复 → 模拟输入并发送**

全程 **不调用 QQ 内部接口、不 Hook 进程、不注入动态链接库**，极大降低账号封禁风险。

<div align="center">

<img alt="示例截图" src="./assets/banner1.png" >
</div>

----
## 推荐配置

 - 1920x1080 分辨率
 - 8GB RAM
 - 4GB ROM
 - 至少一个桌面环境(Xfce4 、KDE 、Gnome 、Cinnamon 、Mate 、LXQt 等)

> 纯窗口管理器（如 i3、dwm）未经测试，可能无法正常运行。

## 📦 准备工作

### 1. 安装 QQ for Linux
前往官方页面下载并安装：
👉 [https://im.qq.com/linuxqq/index.shtml](https://im.qq.com/linuxqq/index.shtml)

确保能正常启动并登录。

## ⚙️ QQ 设置

| 设置项             |                     |
|--------------------|---------------------------|
| **发送消息**          | **Ctrl+Enter**             |
| 联系人面板宽度     | 拖动至 **最窄**            |
|主题|**浅色主题**|

> 🔍 FishCakeQQ 通过 UI 坐标识别消息，任何界面变动（如缩放、深色主题）都可能导致识别失败。
---

### 2. 安装 `uv`（Python 包 & 版本管理工具）

`uv` 是由 Astral 开发的超快 Python 工具链，用于替代 `pip` + `pyenv`。

```bash
# 官方安装（可能较慢）
curl -LsSf https://astral.sh/uv/install.sh | sh

```

> 安装后请重启终端。

---

### 3. 安装 Python 3.13+（带 Tkinter 支持）

⚠️ **不要使用系统自带的 Python**！很多发行版默认 Python 缺少 `tkinter`，会导致 GUI 相关功能失败。

```bash
# 设置国内镜像加速 Python 二进制下载
export UV_PYTHON_INSTALL_MIRROR=https://mirror.nju.edu.cn/github-release/indygreg/python-build-standalone

# 安装 Python 3.14（FishCakeQQ 推荐版本）
uv python install 3.14

# 验证安装
uv python list
```

---

## 🛠️ 安装 FishCakeQQ

### 4. 下载FishCakeQQ

```bash
git clone https://github.com/FishCakeQQOrganization/FishCakeQQLinux.git
cd FishCakeQQLinux
```

---

### 5. 创建虚拟环境并激活

```bash
uv venv ./venv
source ./venv/bin/activate
chmod +x ./*.sh  # 确保脚本可执行
```

---

### 6. 安装 Python 依赖

```bash
# 使用清华源加速 pip 安装
uv sync -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 7. 安装系统依赖

FishCakeQQ 依赖以下系统组件：

```bash
# 用于 pyperclip（剪贴板操作）
sudo apt install xclip

# 用于 pyautogui（模拟键盘/鼠标）
sudo apt install python3-tk python3-xlib

# （可选）如果你使用截图功能，确保有屏幕捕获权限
# 某些桌面环境（如 Wayland）可能需要额外配置
```

> 💡 **Wayland 用户注意**：`pyautogui` 在 Wayland 下无法工作。建议切换到 **X11 会话**。

---

## ▶️ 运行 FishCakeQQ

项目提供三个核心脚本：

| 脚本 | 功能 |
|------|------|
| `menu.sh` | 启动台 |
| `option.sh` | 配置模型类型、API 地址、截图区域等 |
| `ExtensionManager.sh` | 管理自定义扩展模块 |
| `run.sh` | 启动主程序 |

```bash
./menu.sh    # 首次运行建议先配置
./run.sh       # 启动机器人
```

---

## 🖥️ 统一图形界面（pywebview）

原先 6 个独立的 tkinter 窗口已合并为一个网页界面，由 [pywebview](https://pywebview.flowrl.com/) 渲染：

| 页面 | 原来的入口 | 现在 |
|------|-----------|------|
| 启动台 | `menu.sh` | 启动/停止主程序，查看版本与 Token 用量 |


> Linux 上 pywebview 需要额外的 WebView 后端，任选其一：
> `uv pip install "pywebview[qt]"`（纯 pip，推荐，安装指令已经包含），或安装 GTK 后端
> `sudo apt install gir1.2-webkit2-4.1 python3-gi` 后再 `uv pip install "pywebview[gtk]"`。

---


## 🧠 推荐：启用本地大模型（Ollama）

为提升隐私与响应速度，建议使用本地 LLM：

```bash
# 安装 Ollama（参考 https://ollama.com/）
curl -fsSL https://ollama.com/install.sh | sh

# 拉取推荐模型（8B 平衡版）
ollama pull huihui_ai/deepseek-r1-abliterated:8b

# 在 option.sh 中选择 "Ollama" 作为模型类型，并填写模型名
```

---

正常运行时应该如下
![alt text](./assets/running.png)



---

## 最后
~~安装neofetch之类的程序查看你的Linux发行版版本并炫耀~~
   


## 🎉 完成！

现在你可以让 FishCakeQQ在Linux下自动监听 QQ 消息、调用大模型生成回复，并自动发送！

🌟 **小贴士**：  
- 确保 QQ 窗口处于 **前台且未最小化**。   

--- 

✅ 祝你使用愉快！

## 🛠️ 编译说明（开发者）

本项目基于 **Python 3.14** 开发，依赖见 `pyproject.toml`（用 `uv sync` 安装/更新）。
图形界面基于 pywebview：`webui/app.py` 提供 Python↔JS 桥，`webui/web/` 是纯静态前端。

---

## 🌐 本地化（i18n）

参照 Windows 版 `localization.rs` 的做法，所有面向用户的文案都走 `localization` 包，
代码里不再出现硬编码文本。

- 翻译文件：`localization/<语言>.json`（当前为 `zh_CN.json`）；
- 语言由 `config.ini` 的 `[general] language` 选择，缺省 `zh_CN`；
- 后端用法：`from localization import t`，然后 `t("key")` / `t("key", name=value)`；
- 前端用法：`bootstrap()` 会把整张翻译表交给 JS，页面里用 `T("key")`；
- 找不到翻译时返回 `"X" + key`（与 Rust 版一致，方便一眼看出漏翻）。

新增一条文案：先在 `localization/zh_CN.json` 加键值，再在代码里引用该键。
可以跑自检确认没有漏键、也没有残留硬编码：

```bash
uv run python -m localization.check   # 缺失/未使用/硬编码 三项体检
```

要加新语言，复制一份 `zh_CN.json` 改成如 `en_US.json`，再把 `config.ini` 的
`language` 改过去即可（前端会跟随 `bootstrap()` 返回的语言）。

---

## 🛡️ 免责声明

本软件 **仅限技术学习与研究用途**，严禁用于：
- 自动骚扰、刷屏、诈骗等恶意行为  
- 违反《QQ 软件许可协议》的操作  
- 任何违法违规场景

使用者须自行承担因使用本软件引发的一切法律责任，作者概不负责。

---

## 📄 开源协议

本项目采用 [GPL3 License](LICENSE)。欢迎 Star ⭐、Fork 🍴 与贡献代码！

---

## 🙌 贡献与反馈

- 🐞 发现 Bug？ → 提交 [Issue](https://github.com/FishCakeQQOrganization/FishCakeQQLinux/issues)  
- 💡 想改进功能？ → 提交 Pull Request  
- 🌍 有新语言/模型建议？ → 欢迎讨论！


让我们一起打造更安全、智能的视觉自动化工具！









 -->
