#!/bin/bash
# 仅将标题== qq（不区分大小写）的窗口置于最前（激活）

TARGET="qq"

# 获取窗口列表，格式：0x03a00007  0 hostname 窗口标题
wmctrl -l | while read -r id _ _ title; do
    # 去空格后做不区分大小写比较
    if [ "${title,,}" = "$TARGET" ]; then
        wmctrl -i -a "$id"
    fi
done