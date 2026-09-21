<img alt="FishCakeQQ" src="../assets/FishCake.png" width="100">

# 贡献指南

[← 返回目录](main.md)

欢迎提交 Issue 与 Pull Request。本篇是开发者视角的约定。

---

## 开发环境

```bash
git clone https://github.com/QQPilotOrganization/QQPilotLinux.git
cd FishCakeQQLinux
uv venv ./venv
uv sync              # 安装全部依赖（含 pywebview[qt]）
```

- Python 版本以 `pyproject.toml` 为准（当前 `>=3.14`）。
- 依赖改动请改 `pyproject.toml`，并同步 `uv.lock`（`uv lock`）。
- 不要在项目里再新增 `requirements.txt`。

常用命令：

```bash
uv run menu.py                                  # 打开图形界面
uv run python ScreenshotToUILayout.py           # 运行机器人
uv run python -m localization.check             # 本地化体检
uv run python mock_openai_server_openai.py      # 本地 Mock 模型
```

---

## 代码规范

- 跟随现有文件的风格：4 空格缩进、中文注释、类型标注优先。
- 新增文件请在文件头写一句说明用途。
- 面向用户的字符串**一律不要硬编码**——见下一节。
- 提交前至少跑通：

  ```bash
  uv run python -m localization.check
  # 语法自检
  uv run python -m py_compile $(git ls-files '*.py')
  ```

---

## 本地化是硬性要求

FishCakeQQ 的所有可见文案都在 `localization/<语言>.json` 里，代码中不允许出现硬编码文本。

新增文案的流程：

1. 加键值到 `localization/zh_CN.json`；
2. 后端用 `t("key")`，前端用 `T("key")`；
3. 跑 `python -m localization.check`，必须输出 `✅ 本地化检查通过`。

键命名与自检规则见 [本地化](localization.md)。

> 自检会把 `.py` / `.js` / `.html` / `.css` 里的中文字面量当作错误。
> docstring、`__main__` 里的测试夹具、`Extensions/` 等目录会被豁免。

---

## 常见改动指引

### 加一个配置项

1. 在 `config.ini` 加上默认值；
2. 需要的话在 `webui/app.py` 的 `get_config` / `save_config` 里读写；
3. 在 `webui/web/app.js` 的「运行设置」页加上对应控件（文案走 `T()`）；
4. 在 `document/config.md` 补一行说明。

### 加一个界面页面

1. `webui/app.py` 里加对应的 `Api` 方法，并用 `_t()` 返回文案；
2. `webui/web/app.js` 里加 `PAGES` 条目与渲染函数；
3. 文案统一加进 `localization/zh_CN.json`。

### 加一个模型后端

- 在 `answer.py` 里按 `server_url` 分支；
- 请求体尽量对齐 OpenAI 风格，复用 `_concatenate_text`；
- 在 `document/models.md` 补文档。

### 加一种语言

复制 `localization/zh_CN.json` 为 `<lang>.json`，翻译值、保留键，
在文档里补一句即可。

---

## 提交与 PR

- 分支名建议 `feat/...`、`fix/...`、`docs/...`。
- 提交信息用中文或英文都可，但请写清楚“做了什么、为什么”。
- PR 描述里附上：改动范围、验证方式、必要时截图。
- 涉及界面的改动，请贴一张新界面截图。

---

## 报告问题

提 Issue 时请附上：

- 发行版与桌面环境（`echo $XDG_SESSION_TYPE` 的结果）；
- Python 版本（`uv run python -V`）；
- 复现步骤；
- 终端完整日志（可去掉个人信息）。

---

## 发布

- 版本号写在 `config.ini` 的 `version` 里。
- 「升级助手」页可以把当前目录同步到另一个安装目录，
  并自动合并 `config.ini`、保留个人配置——发布前可用它自测。

---

## 许可

本项目采用 [GPL3 License](../LICENSE)。提交代码即表示同意以同一协议发布。

[← 返回目录](main.md)
