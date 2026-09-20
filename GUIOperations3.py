import pyautogui
import pytweening
import pyperclip
import configparser
import time
import os
import subprocess
from windmouse.pyautogui_controller import PyautoguiMouseController
from windmouse.core import Coordinate

# Initialize the controller
mouse = PyautoguiMouseController(    
    max_step=55,            # Maximum speed (default: 15)
    damped_distance=12      # Distance where movement starts to slow (default: 12)
    )

# Set destination coordinates

def smoothMoveStart():
    global mouse
    mouse.move_to_target(
        tick_delay=0,      
        step_duration=0.001     
    )
from colorama import Fore
# from conversationStyleExtract import indentificationString
config = configparser.ConfigParser()
config.read('config.ini',encoding='utf-8')
scroll=config.getint('general','scroll')
autoFocusing=config.getboolean('general','autoFocusing')
width=config.getint('general','width')
height=config.getint('general','height')
wmctrlsh='''#!/bin/bash

while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    
    # 提取窗口 ID
    win_id=${line%% *}
    
    # 提取窗口标题（去掉前两列：ID 和 主机名）
    # 使用 awk 获取从第3列开始的所有内容作为标题
    win_title=$(echo "$line" | awk '{for(i=3;i<=NF;i++) printf "%s ", $i; print ""}' | sed 's/ *$//')
    
    # 判断标题是否完全等于 qq (忽略大小写)
    if [[ "${win_title,,}" == "qq" ]]; then
        wmctrl -i -r "$win_id" -e 0,0,0,WIDTH,HEIGHT
    fi
done < <(wmctrl -l)
'''
sh=wmctrlsh.replace('WIDTH',str(width))
sh=sh.replace('HEIGHT',str(height))
with open('left.sh', 'w',encoding='utf8') as f:
    f.write(sh)
try:
    subprocess.run(['chmod','+x','left.sh'])
except:
    pass

def focus():
    global wmctrlsh
    if autoFocusing:
        subprocess.run(['bash','./focus.sh'])
    subprocess.run(['bash','./left.sh'])

def mouse_move(x: int, y: int) -> bool:
    # pyautogui.moveTo(x, y)
    global mouse
    mouse.dest_position = (Coordinate(x), Coordinate(y))
    smoothMoveStart()
    
    return True
def mouse_down() -> bool:
    pyautogui.mouseDown()
    return True

def mouse_up() -> bool:
    pyautogui.mouseUp()
    return True

def click(x: int, y: int) -> bool:
    mouse.dest_position = (Coordinate(x), Coordinate(y))
    smoothMoveStart()
    pyautogui.click(x, y)
    return True

def dragFromTo0(x1: int, y1: int, x2: int, y2: int) -> bool:
    pyautogui.drag(x2 - x1, y2 - y1)
    return True

def scroll_up(delta: int =120) -> bool:
    pyautogui.scroll(delta)
    return True

def scroll_down(delta: int =120) -> bool:
    pyautogui.scroll(-delta)
    return True

def scroll_left(delta: int =120) -> bool:
    pyautogui.scroll(-delta)
    return True

def scroll_right(delta: int =120) -> bool:
    pyautogui.scroll(delta)
    return True


def press_key(key_name: str) -> bool:
    """
    按下单个键（支持字母、数字、功能键名）
    示例: press_key('A'), press_key('ENTER'), press_key('F1')
    """
    pyautogui.press(key_name)
    return True
def HotKey(modifier: str, key: str) -> bool:
    """
    按下组合键（支持字母、数字、功能键名）
    示例: hotkey('ctrl', 'c'), hotkey('alt', 'F4')
    """
    pyautogui.hotkey(modifier, key)
    return True

def tab() -> bool:
    """
    按下Tab键
    """
    pyautogui.press('tab')
    return True

def scrollUp(length: int = 120) -> bool:
    """
    向上滚动
    """
    for i in range(scroll):
        scroll_up(length)
        time.sleep(.1)
    return True
def scrollDown(length: int = 240) -> bool:
    """
    向下滚动
    """
    for i in range(scroll):
        scroll_down(length)
        time.sleep(.1)
    return True

def goto(x: int, y: int)-> bool:
    """
    移动鼠标到指定位置
    """
    mouse_move(x, y)
    return True
def getCenter(area: tuple[int, int, int, int]) -> tuple[int, int]:
    area2=list(area)
    pos1=area2[0]+((area2[3]-area2[1]) // 2)
    pos2=area2[1]+((area2[4]-area2[2]) // 2)
    return pos1,pos2
def clickCenter(area):
    click(*getCenter(area))
    
press=press_key
def PasteTextToSection(text:str,section: tuple[int, int, int, int]):
    pyperclip.copy(text)
    time.sleep(0.2)
    clickCenter(section)
    HotKey("ctrl","v")
    time.sleep(0.8)
    
def SendText(text:str,section: tuple[int, int, int, int]):
    temp=''
    print(Fore.GREEN,"发消息->" + text)

    for message in text.split("[[NEXT]]"):
        m=message.split("\n")
        for sentence in m[:-1]:
            PasteTextToSection(sentence,section)
            # clickCenter(section)
            press("enter")
            time.sleep(0.2)
            # pyperclip.copy(temp)
            # time.sleep(.2)
            # # click(commentSectionActualSize)
            # hotkey('ctrl', 'v')
        PasteTextToSection(m[-1],section)
        clickCenter(section)
        time.sleep(200)
        HotKey('ctrl','enter')
            
    # for i in text:
    #     if i=='\n':
    #         pyperclip.copy(temp)
    #         time.sleep(.2)
    #         temp=''
    #         hotkey('ctrl', 'v')
    #         press('enter')
    #         continue
    #     temp+=i
    # pyperclip.copy(temp)
    # time.sleep(.2)
    # hotkey('ctrl', 'v')

def dragFromTo(x1: int, y1: int, x2: int, y2: int):
    mouse_move(x1, y1)
    mouse_down()
    mouse_move(x2, y2)
    time.sleep(scroll)
    mouse_up()



    