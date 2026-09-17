"""升级助手（原 LUpgrade.py）

原先的 tkinter 升级窗口已合并进统一 Web 界面（pywebview 渲染）的
“升级助手”页；本文件保留为入口，由 ``LUpgrade.sh`` 调用。

升级逻辑（复制代码 + 合并 config.ini + 保留个人配置）在 :mod:`webui.app`。
"""
from webui import run_ui


def main() -> None:
    run_ui("upgrade")


if __name__ == "__main__":
    main()
