"""QQPilotLinux 统一 Web 界面（pywebview 渲染）

把原先 6 个独立的 tkinter 工具窗口合并成一个网页界面：

- 启动台（原 menu.py）
- 运行设置（原 Option5.py）
- 扩展管理（原 extensionViewer.py）
- 升级助手（原 LUpgrade.py）
- 图片导入（原 ImageImport.py）
- 额外参数（原 jsonEdit.py 的 extra.json 编辑器）

入口：``webui.run_ui(page)``，由各工具脚本调用（保持原文件名不变）。
后端逻辑在 :class:`webui.app.Api`，通过 pywebview 的 js_api 暴露给前端。
"""
from .app import run_ui

__all__ = ["run_ui"]
