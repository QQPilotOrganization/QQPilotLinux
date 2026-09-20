<img alt="FishCakeQQ" src="../assets/FishCake.png" width="100">

# Wayland

[← 返回目录](main.md)

![s](ODF.png) **结论先放前面：FishCakeQQ 必须在 X11 下运行，Wayland 会话下无法工作。**

---

## Wayland 是什么

Wayland 是 X11 窗口系统协议的替代方案，目标更简单、更易开发与维护。

- 应用（Wayland 客户端）通过 **libwayland** 与 **compositor**（合成器）通信，
  由合成器负责显示与输入。
- 与 X11 不同，Wayland 没有唯一的服务端：每个桌面环境（GNOME、KDE…）
  自带各自的合成器实现，窗口管理与交互行为更多由合成器决定。

更多资料：

- 架构与 FAQ：<https://wayland.freedesktop.org/>
- 协议与实现：<https://gitlab.freedesktop.org/wayland/wayland>

---

## 为什么 FishCakeQQ 用不了 Wayland

FishCakeQQ 依赖两条 X11 时代的能力：

1. **绝对坐标的鼠标控制**：`pyautogui` 通过 X11 直接把指针移动到屏幕坐标并点击。
   Wayland 出于安全考虑**不允许客户端设置全局光标位置**，移动会失败或落在错误位置。
2. **窗口直接操作**：程序用 `wmctrl` 查找并移动标题为 `qq` 的窗口。
   Wayland 下 `wmctrl` 通常看不到真实窗口，也无法移动它们。

因此 FishCakeQQ 在 Wayland 下会表现为：鼠标不动、点击错位、找不到窗口。

---

## 怎么切回 X11

在登录界面（GDM / SDDM / LightDM）：

- 点击用户名旁的齿轮/会话选择；
- 选择 **“GNOME on Xorg”**、**“Plasma (X11)”**、**“Xfce Session”** 等带 X11/Xorg 的选项；
- 登录后确认：

  ```bash
  echo $XDG_SESSION_TYPE      # 应输出 x11
  ```

> 部分发行版默认隐藏 X11 会话；可在 `~/.config` 或登录管理器设置里开启。

---

## 常见追问

**Q：能不能把 FishCakeQQ 改成支持 Wayland？**
A：需要改用 `ydotool` / `libei` 之类需要特权或额外守护进程的输入方案，
并且窗口管理也无法用 `wmctrl`，属于另一套实现，目前不支持。

**Q：WSL 里跑呢？**
A：WSL 的图形转发同样不是 X11 桌面环境，鼠标与窗口都不具备，
请直接用 Windows 版或安装真正的 Linux 桌面。

**Q：远程桌面（VNC / RDP）呢？**
A：只要远端会话本身是 X11，一般可用；纯 Wayland 的远程会话仍不行。

[← 返回目录](main.md)
