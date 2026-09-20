<img alt="FishCakeQQ" src="../assets/FishCake.png" width="100">

# 本地化

[← 返回目录](main.md)

FishCakeQQ 的所有界面与日志文案都存放在 `localization/` 里，代码中不出现硬编码文本。
这套机制参照 Windows 版 `localization.rs` 的做法。

---

## 语言文件

```
localization/
├─ __init__.py     读取与查询接口
├─ zh_CN.json      中文翻译表（当前唯一语言）
└─ check.py        自检工具
```

- 文件名即语言代码：`zh_CN.json`、`en_US.json`……
- 语言由 `config.ini` 的 `[general] language` 选择，缺省 `zh_CN`。

---

## 后端用法

```python
from localization import t

print(t("ui.nav.launch"))                       # 启动台
print(t("answer.token_usage",
        input=120, output=340, total=460))      # 支持 {name} 占位符
```

- 找不到键时返回 `"X" + key`（例如 `Xui.nav.launch`），
  这样漏翻的地方会在界面上直接暴露出来——与 Rust 版行为一致。
- `get_all()` 返回整张翻译表；`current_language()` / `available_languages()`
  分别是当前语言与可用语言列表。

---

## 前端用法

启动界面时，Python 会把整张翻译表通过 `bootstrap()` 交给前端：

```js
const boot = await window.pywebview.api.bootstrap();
state.translations = boot.translations;   // { "ui.nav.launch": "启动台", ... }

T("ui.nav.launch");                        // 取翻译
T("ui.ext.count", { count: 3 });          // 占位符替换
```

- `app.js` 里的 `T()` 与后端的 `t()` 行为一致。
- HTML 静态文案用属性占位，加载后由 `applyStaticI18n()` 填充：

  ```html
  <nav id="nav" aria-label="" data-i18n-aria-label="ui.nav.aria"></nav>
  <h1 id="pageTitle"></h1>
  ```

- CSS 里的可见文案（如控制台占位符）通过自定义属性注入：

  ```css
  .console:empty::before { content: var(--console-empty, ""); }
  ```

---

## 新增一条文案

1. 在 `localization/zh_CN.json` 加键值：

   ```json
   "ui.settings.my_feature": "我的新功能"
   ```

2. 在代码里引用它：

   ```python
   from localization import t
   label = t("ui.settings.my_feature")
   ```

   前端则：

   ```js
   el("span", { text: T("ui.settings.my_feature") });
   ```

3. 跑一次自检（见下）确认没有漏键。

### 键命名约定

按“区域.用途”分层，便于查找与批量翻译：

| 前缀 | 范围 | 例 |
|------|------|----|
| `program.` / `default.` / `info.` | 通用信息 | `program.welcome` |
| `warning.` / `error.` | 警告与错误 | `error.answer_failed` |
| `config.` | 配置校验 | `config.possibility_error` |
| `ui.nav.` / `ui.launch.` / `ui.settings.` / `ui.ext.` / `ui.upgrade.` / `ui.images.` / `ui.json.` | 图形界面各页 | `ui.settings.width` |
| `docklog.` / `screenshot.` | 悬浮窗与运行时日志 | `screenshot.qq_window` |
| `cc.` | 内嵌 CompletionConnector | `cc.connected` |

---

## 自检工具

```bash
uv run python -m localization.check
```

它会做三项体检：

1. **缺失**：代码里 `t("...")` / `T("...")` 用到、但 JSON 里没有的键（会失败）；
2. **未使用**：JSON 里有、但代码没引用的键（仅提示）；
3. **硬编码**：`.py` / `.js` / `.html` / `.css` 里残留的中文字面量（会失败）。

排除项：docstring、`if __name__ == "__main__"` 里的测试夹具、
`Extensions/`、`download/`、`useollamainVM/` 等目录。
也就是说，**只要自检通过，就代表没有硬编码文案、也没有漏翻**。

---

## 新增一种语言

1. 复制 `localization/zh_CN.json` 为 `localization/en_US.json`；
2. 逐条翻译其中的值（键不要改）；
3. 把 `config.ini` 改成：

   ```ini
   language = en_US
   ```

4. 重新启动程序。界面与日志都会切换语言；
   若某条没翻到，会显示成 `X<key>` 提醒你补上。

[← 返回目录](main.md)
