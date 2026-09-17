"""JSON 编辑器（原 jsonEdit.py）

原先的 tkinter JSON 编辑器已合并进统一 Web 界面（pywebview 渲染）的
“额外参数”页。``Open(file)`` 保留为兼容入口。

注意：本函数会启动一个 pywebview 窗口（阻塞），只能从主线程调用；
它用于独立打开 jsonEdit.py 的场景。统一界面内部的“编辑 extra.json”
按钮直接切换到该页，不会再调用这里。
"""
from webui import run_ui


def Open(file: str = "") -> None:
    """打开统一界面的“额外参数”页，编辑指定文件（默认 extra.json）。"""
    run_ui("json", file or "extra.json")


if __name__ == "__main__":
    Open("")
