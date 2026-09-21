#!/bin/bash
# qq-move.sh
# 将标题 == qq（不区分大小写）的窗口移动到 (0,0)，大小 1285x720，并激活到最前
TARGET="qq"
GEO="0,0,0,1285,720"   # gravity,X,Y,W,H

# ---- 依赖检查 ----
if ! command -v wmctrl >/dev/null 2>&1; then
    echo "错误: 未安装 wmctrl，请先执行: sudo apt install wmctrl" >&2
    exit 1
fi

if [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
    echo "警告: 当前是 Wayland 会话，wmctrl 可能无法控制窗口。" >&2
fi

# ---- 查找窗口 ----
wid=""
while IFS= read -r line; do
    id=$(awk '{print $1}' <<<"$line")
    title=$(awk '{for(i=4;i<=NF;i++) printf "%s%s", $i, (i<NF?" ":"")}' <<<"$line")
    if [ "${title,,}" = "${TARGET,,}" ]; then
        wid="$id"
        break
    fi
done < <(wmctrl -l)

if [ -z "$wid" ]; then
    echo "未找到标题为 '$TARGET' 的窗口" >&2
    exit 2
fi

# ---- 若已最大化，先取消，否则 -e 可能被忽略 ----
wmctrl -i -r "$wid" -b remove,maximized_vert,maximized_horz 2>/dev/null || true

# ---- 移动 + 调整大小 ----
wmctrl -i -r "$wid" -e "$GEO"

# ---- 激活到最前 ----
wmctrl -i -a "$wid"
