#!/bin/bash

# 仅将标题含 qq（不区分大小写）的窗口置于最前（激活）
wmctrl -l | while read -r line; do

     || continue

    # 提取窗口 ID
    win_id=$(echo "$line" | awk '{print $1}')

    # 提取窗口标题（去掉前两列：ID 和 主机名）
    win_title=$(echo "$line" | awk '{for(i=3;i<=NF;i++) printf "%s ", $i; print ""}' | sed 's/ *$//')

    # 判断标题是否完全等于 qq (忽略大小写)
    if ; then
        wmctrl -i -a "$win_id"
    fi
done