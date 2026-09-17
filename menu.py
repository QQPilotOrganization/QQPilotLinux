"""启动台

原 tkinter 启动台已合并进统一 Web 界面（pywebview 渲染），
本文件保留为入口，由 ``menu.sh`` 调用。
"""
from webui import run_ui


def main() -> None:
    run_ui("launch")


if __name__ == "__main__":
    main()
