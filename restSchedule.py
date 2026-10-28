"""休息时间表判定（参照 Windows 版 ``rest_schedule.rs``）。

``rest_schedule`` 用英文（或中文）逗号分隔若干小时，例如 ``1,2,3,4,5``；
当前本地小时命中其中任意一个时，程序进入休息、不工作。

- 空串、``None``、``False`` 视为不启用；
- 无法解析的项会被忽略；
- 单数字和补零写法等价（``1`` 与 ``01`` 都表示 1 点）。
"""
from __future__ import annotations

import time


def inRestSchedule(schedule: str) -> bool:
    """当前本地小时是否在休息时间表内。"""
    if not schedule:
        return False
    hour = time.localtime().tm_hour
    for part in str(schedule).replace("，", ",").split(","):
        part = part.strip()
        if not part or part.lower() in ("none", "false"):
            continue
        try:
            if int(part) == hour:
                return True
        except ValueError:
            continue
    return False


def parseSchedule(schedule: str) -> list[int]:
    """把时间表解析成排好序的小时列表（用于展示/调试，非法项忽略）。"""
    hours: set[int] = set()
    for part in str(schedule or "").replace("，", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            hour = int(part)
        except ValueError:
            continue
        if 0 <= hour <= 23:
            hours.add(hour)
    return sorted(hours)
