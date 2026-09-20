<img alt="FishCakeQQ" src="../assets/FishCake.png" width="100">

# 扩展开发

[← 返回目录](main.md)

>扩展功能已经停止维护

扩展就是 `Extensions/` 目录下的普通 Python 文件。程序启动时会加载其中所有
`.py`，在固定时机调用它们定义的钩子函数。

---

## 目录与状态

```
Extensions/
├─ template/ExtensionTemplate.py   模板（放这里不会被加载）
├─ test/…                          测试用
├─ AutoSummary.py                  启用中
└─ sB.disabled                     已停用（.disabled 不会被加载）
```

- 只有**直接放在 `Extensions/` 下**、且以 `.py` 结尾的文件会被加载；
  子目录不会被扫描，所以模板可以安心放在 `template/`。
- 停用扩展：把 `Something.py` 改名为 `Something.disabled` 即可。
  图形界面「扩展管理」页的启用/停用按钮就是在做这件事。

> ⚠️ 扩展是任意 Python 代码，能读写文件、发起网络请求。**只加载你信任的扩展**，
> 否则可能拖慢程序、导致故障，甚至破坏文件。

---

## 最小扩展

```python
from extensionAPIs import *


def after_receiving_messages(messages: List[ChatContent]) -> None:
    # 收到消息后调用
    text = ""
    for m in messages:
        text += m.report() + "\n"
    notify(text, "看看收到了什么")


def before_sending_the_message_by_AI_generated(answer: str) -> str:
    # 发送前调用：可以修改答案；必须返回字符串
    return answer.replace("喵", "喵～")


def after_screenshot() -> None:
    # 每次截图后调用
    pass


description = "一个示例扩展"
```

`description` 会被「扩展管理」页读取并显示，建议写一句话说明用途。

---

## 钩子函数

| 钩子 | 调用时机 | 参数 | 返回值 |
|------|----------|------|--------|
| `after_receiving_messages` | 解析出本轮消息之后、请求模型之前 | `messages: List[ChatContent]` | 返回新的消息列表可覆盖原列表；返回 `None` 表示不修改 |
| `before_sending_the_message_by_AI_generated` | 拿到模型答案之后、真正发送之前 | `answer: str` | **必须返回字符串**（原样返回即不修改） |
| `after_screenshot` | 每次全屏截图之后 | 无 | 无 |

- 三个钩子都是可选的：没定义就被跳过，不算错误。
- `after_receiving_messages` 会被传入“本轮解析出的消息”，你可以读它们、
  过滤它们，或返回一份新的列表替换掉。
- `before_sending_the_message_by_AI_generated` 是**逐扩展接力**的：上一个扩展的
  返回值会成为下一个扩展的输入，最终结果被发送。
- 扩展抛出的异常会被记录到日志（`logging.error`），不会让主程序崩溃。

---

## 扩展 API

`extensionAPIs.py` 暴露了下面这些名字（`from extensionAPIs import *` 即可使用）：

| 名称 | 说明 |
|------|------|
| `ChatContent` | 一条聊天消息：`username`、`text`、`time`、`imagePaths`、`ownByMyself` |
| `notify(text, title="")` | 弹出一个消息框 |
| `get_answer_as_string(question, system_prompt)` | 用当前配置的模型回答一个问题 |

`ChatContent` 的字段：

```python
class ChatContent:
    username: str        # 发送者昵称
    text: str            # 正文
    time: str            # 时间
    imagePaths: list[str]# 消息里的图片路径
    ownByMyself: bool    # 是不是机器人自己发的

    def report(self) -> str:
        """拼成一行便于阅读/展示的文本"""
```

---

## 示例：自动总结消息

仓库里的 `Extensions/AutoSummary.disabled` 演示了“收到消息后调用模型做总结，
再用消息框展示”：

```python
from extensionAPIs import *


def after_receiving_messages(messages: List[ChatContent]):
    text = ""
    for i in messages:
        text += i.report() + "\n"
    summary = get_answer_as_string(f"总结消息:{text}", False)
    notify(str(summary), "消息总结")
    return messages


description = "自动总结消息扩展：收到消息后，使用消息框显示总结的消息"
```

把文件名改成 `AutoSummary.py` 即可启用。

---

## 调试

- 直接在扩展里 `print(...)`，输出会出现在运行 `./run.sh` 的终端里。
- 想看钩子是否被调用，参考 `Extensions/test/` 下的示例（会打印参数）。
- 加载失败时，启动阶段会打印：

  ```
  随意加载扩展可能导致运行缓慢，程序故障，甚至有可能破坏文件
  加载错误  <文件名>  <异常>
  ```

  报错不影响其它扩展加载。

---

## 小贴士

- 扩展只会在**启动时**加载一次；改完代码要重启程序。
- 需要联网或读写文件时，记得处理异常，否则会被记为加载/调用错误。
- 钩子里不要 `time.sleep` 太久，会拖慢整个回复循环。

[← 返回目录](main.md)
