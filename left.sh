#!/bin/bash

while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    
    win_id=${line%% *}
    
    win_title=$(echo "$line" | awk '{for(i=3;i<=NF;i++) printf "%s ", $i; print ""}' | sed 's/ *$//')
    
    if [[ "${win_title,,}" == "qq" ]]; then
        wmctrl -i -r "$win_id" -e 0,0,0,1285,720
    fi
done < <(wmctrl -l)
