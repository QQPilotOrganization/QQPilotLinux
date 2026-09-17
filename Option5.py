"""运行设置（原 Option5.py）

原先的 tkinter 设置窗口已合并进统一 Web 界面（pywebview 渲染）的
“运行设置”页；本文件保留为入口，由 ``option.sh`` 调用。

界面与 config.ini 的读写都在 :mod:`webui.app` 里。
"""
from webui import run_ui


def main() -> None:
    run_ui("settings")


if __name__ == "__main__":
    main()
