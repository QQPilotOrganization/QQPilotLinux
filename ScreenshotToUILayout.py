from colorama import Fore
import Vision
import sysDetect
if sysDetect.isLinux():
    import scaleToiniLinux
import load
import dockLog
load.startLoading(Fore.GREEN,"正在初始化")
floatingTextApp=dockLog.start_floating_window()
dockLog.setText("正在初始化-按右键关闭浮窗")
from typing import Any, Generator, Literal
from random import randint
import subprocess
import platform
# import upload
TOKENCOUNTFILE = 'tokencount.txt'




import image

import logging

logger :logging.Logger = logging.getLogger("L")
logger.setLevel(logging.INFO)
consoleHandler = logging.StreamHandler()
consoleHandler.setLevel(logging.INFO)
fileHandler = logging.FileHandler("log.txt",encoding='utf8')
fileHandler.setLevel(logging.INFO)
# logging.basicConfig(level=logging.INFO,)
formatter=logging.Formatter('%(asctime)s [%(levelname)s] %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
consoleHandler.setFormatter(formatter)
fileHandler.setFormatter(formatter)
logger.addHandler(consoleHandler)
logger.addHandler(fileHandler)

import time
import configparser
from conversationStyleExtract import * 

import threading


import positions
import answer
# import enhance
import pyperclip

from GUIOperations3 import *
        

import extensionLoader


load.stopLoading()

logger.info(f"{Fore.GREEN}初始化完成{Fore.RESET}")
dockLog.setText("初始化完成")


autoFocusShouldRun=True
def autoFocus():
    global autoFocusShouldRun
    while autoFocusShouldRun:
        focus()
        logger.debug("Focusing...")
        time.sleep(4)

t=None



if __name__ == '__main__':
    try:

        time.sleep(1)

        config=configparser.ConfigParser()
        config.read('config.ini',encoding='utf-8')
        size: tuple[int, int]=int(config.get('general','width')),int(config.get('general','height'))

        scale=float(config.get('general','scale'))
        scrollTries=int(config.get('general','scroll'))
        withImage=config.getboolean('general','withImage')
        autoLogin=config.getboolean('general','autoLogin')
        # autoFocusing=config.get('general','autoFocusing')
        sendImagePossibility=config.get('general','sendImagePossibility')
        isVisionModel=config.getboolean('general','isVisionModel')
        ATDetect=config.getboolean('general','ATDetect')
        tab_times=config.getint('general','tab_times')
        userName=config.get('general','name')

        print(f"{Fore.YELLOW}QQPilot {config.get('general','version')}{Fore.RESET}",end='\t')
        print(f"{Fore.CYAN}{platform.platform()}{Fore.RESET}")
        sendImagePossibility=int(sendImagePossibility)

        logger.info(f"欢迎您,{userName}。")
        logger.info("自动聚焦功能已开启")
        t=threading.Thread(target=autoFocus)
        t.start()
        if autoLogin:
            logger.info("自动登录功能已开启")
            logger.info("正在尝试登录...")
            dockLog.setText("正在尝试登录...")
            for _ in range(4):

                image.fullScreenShot()
                i=image.containsBlue()
                if i==[0,0]:
                    time.sleep(1)
                    continue
                click(*i)
                time.sleep(2)
            time.sleep(1)
                

        
        
        size=(int(size[0]*scale),int(size[1]*scale))

        logger.debug(f"size with scale: {size}, scale: {scale}")



        positionRect: tuple[Literal[0], Literal[0], int, int]=(0,0,*size)


        logger.debug(f"QQ窗口位置: {positionRect}")

        chatListActualSize: tuple[int, int, int, int]=positions.toActualSize(positions.CHAT_LIST_BBOX_RELATIVE_SIZE,size)
        logger.debug(f"聊天列表实际大小: {chatListActualSize}")

        conversationActualSize: tuple[int, int, int, int]=positions.toActualSize(positions.CONVERSATION_BBOX_RELATIVE_SIZE,size)
        logger.debug(f"聊天区域实际大小: {conversationActualSize}")

        commentSectionActualSize: tuple[int, int, int, int]=positions.toActualSize(positions.COMMENT_SECTION_BBOX_RELATIVE_SIZE,size)
        logger.debug(f"输入框实际大小: {commentSectionActualSize}")

        sendButtonActualSize: tuple[int, int, int, int]=positions.toActualSize(positions.SEND_BUTTON_BBOX_RELATIVE_SIZE,size)
        logger.debug(f"发送按钮实际大小: {sendButtonActualSize}")

        exitConversationActualSize: tuple[int, int, int, int]=positions.toActualSize(positions.EXIT_CONVERSATION_BBOX_RELATIVE_SIZE,size)
        logger.debug(f"退出会话按钮实际大小: {exitConversationActualSize}")

        sendImageActualSize: tuple[int, int, int, int]=positions.toActualSize(positions.SEND_IMAGE_BBOX_RELATIVE_SIZE,size)
        logger.debug(f"发送图片按钮实际大小: {sendImageActualSize}")


        atPlaceActualSize: tuple[int, int, int, int]=positions.toActualSize(positions.AT_PLACE_BBOX_RELATIVE_SIZE,size)
        logger.debug(f"@位置实际大小: {atPlaceActualSize}")

        startDraggingAbsolutePosition=positions.toActualPoint(positions.START_DRAGGING_RELATIVE_POSITION,size)
        endDraggingAbsolutePosition=positions.toActualPoint(positions.END_DRAGGING_RELATIVE_POSITION,size)
        logger.debug(f"开始拖拽位置: {startDraggingAbsolutePosition}")
        logger.debug(f"结束拖拽位置: {endDraggingAbsolutePosition}")

        chatButtonActualPosition=positions.toActualPoint(positions.CHAT_BUTTON_RELATIVE_POSITION,size)
        logger.debug(f"聊天按钮实际位置: {chatButtonActualPosition}")
        contactButtonActualPosition=positions.toActualPoint(positions.CONTACT_BUTTON_RELATIVE_POSITION,size)
        logger.debug(f"联系人按钮实际位置: {contactButtonActualPosition}")


        cancelButtonActualPosition=positions.toActualPoint(positions.CANCEL_BUTTON_RELATIVE_POSITION,size)

        uploadImagePossibleActualSize=positions.toActualSize(positions.UPLOAD_IMAGE_POSSIBLE_BBOX_RELATIVE_SIZE,size)
        logger.debug(f"上传图片可能位置: {uploadImagePossibleActualSize}")
        totalTokens=0
        copyButtonPossibleAcutalSize=positions.toActualSize(positions.COPY_BUTTON_BBOX_RELATIVE_SIZE,size)
        logger.debug(f"复制可能位置: {copyButtonPossibleAcutalSize}")
        
        if os.path.exists(TOKENCOUNTFILE):
            with open(TOKENCOUNTFILE,'r',encoding='utf8') as f:
                totalTokens=int(f.read())
        else:
            with open(TOKENCOUNTFILE,'w',encoding='utf8') as f:
                f.write("0")
        def GoBack():
            logger.info("GoBack")
            # dockLog.setText(1)
            count=0
            while 1:
                click(chatListActualSize[0]+int(100*scale),chatListActualSize[1]+int(20*scale))
                time.sleep(0.1)

                click(*contactButtonActualPosition)
                time.sleep(0.1)
                click(*chatButtonActualPosition)
                time.sleep(1)
                image.fullScreenShot()
                time.sleep(1.5)
                count+=1
                if(count>2):
                    break
                dockLog.setText(count)
                
                
                pointsOfUpload=Vision.FindTemplates("screenshot.png",'uploadImage.png',30,1)
                logger.info(pointsOfUpload)
                
                if(len(pointsOfUpload)>1):
                    time.sleep(1.5)
                    continue
                
                
                pointsOfCopy=Vision.FindTemplates("screenshot.png",'copy.png',30,1)
                logger.info(pointsOfCopy)
                
                if len(pointsOfCopy)>1:
                    time.sleep(1.5)
                    
                    continue
                # image.screenshot(*uploadImagePossibleActualSize)

                break
                
                
        while True:
            try:
                # im=image.screenshot(*positionRect)
                
                # im.save("screenshot.png")
                # chatList: Image.Image=im.crop(chatListActualSize)
                chatList=image.fullScreenShot()

                dockLog.setText("等待扩展完成操作")
                extensionLoader.callEveryExtension("after_screenshot")

                # del im
                if ATDetect:
                    contain=image.containsRedDot(image.rect(*atPlaceActualSize))
                else:
                    contain=image.containsRedDot(image.rect(*chatListActualSize))   
                if contain!=[0,0]:
                    time.sleep(1)
                    if ATDetect:
                        contain=image.containsRedDot(image.rect(*atPlaceActualSize))
                    else:
                        contain=image.containsRedDot(image.rect(*chatListActualSize))  
                    if contain==[0,0]:
                        continue 
                    
                    dockLog.setText("🚫🖱️发现新信息  ")
                    logger.info(f"发现红点: {contain}")

                    click(contain[0],contain[1])
                    time.sleep(2)
                    

                    conversationText=[]
                    
                    dragFromTo(*startDraggingAbsolutePosition,*endDraggingAbsolutePosition)

                    dockLog.setText("🚫🖱️ 请勿移动鼠标")
                    time.sleep(.1)
                    goto(conversationActualSize[0]+((conversationActualSize[2]-conversationActualSize[0])//2),conversationActualSize[1]+((conversationActualSize[3]-conversationActualSize[1])//2))
                    image.fullScreenShot()

                    t=Vision.FindTemplates('screenshot.png','copy.png',30,1)
                    if len(t)>=1 and t[0]!=[0,0]:
                        click(t[0][0],t[0][1])
                    else:
                        logger.error(f"{Fore.YELLOW}使用模板匹配查找复制按钮失败{Fore.RESET}")
                        
                        
                    
                        for i in range(scrollTries):
                            scrollDown()
                        time.sleep(.4)
                        
                        click(commentSectionActualSize[0]+((commentSectionActualSize[2]-commentSectionActualSize[0])//2),commentSectionActualSize[1]+((commentSectionActualSize[3]-commentSectionActualSize[1])//2))
                        for i in range(tab_times):
                            tab()
                            time.sleep(.4)
                        press('enter')

                    

                        time.sleep(2)
                        
                        for _ in range(4):
                            click(cancelButtonActualPosition[0],cancelButtonActualPosition[1])
                            time.sleep(.2)
                    time.sleep(2)

                    # click(cancelButtonActualPosition[0],cancelButtonActualPosition[1])

                    chat=pyperclip.paste()
                    if chat=="":
                        dockLog.setText("没有提取到消息。")
                        logger.error("没有提取到消息。")
                        GoBack()
                        continue
                        
                    ChatContents=ParseChatLog(chat,userName)
                    
                    

                    dockLog.setText("等待扩展完成操作")
                    extensionLoader.callEveryExtension("after_receiving_messages",ChatContents)

                    # print(ChatContents,ChatContentsList) 

                    # conversationText=[str(text) for text iChatContentsts]
                    
                    dockLog.setText("等待语言模型生成答案")
                    #send answer
                    click(commentSectionActualSize[0]+((commentSectionActualSize[2]-commentSectionActualSize[0])//2),commentSectionActualSize[1]+((commentSectionActualSize[3]-commentSectionActualSize[1])//2))



                    print(f"{Fore.CYAN}{'\n'.join(list(conversationText))}{Fore.RESET}")
                    
                    try:
                        result,tokenUsage=answer.getAnswer(ChatContents)
                        totalTokens+=tokenUsage
                        with open(TOKENCOUNTFILE,'w',encoding='utf8') as f:
                            f.write(str(totalTokens))
                    except Exception as e:
                        logger.error(f"语言模型生成答案失败\n{e}")
                        dockLog.setText("× 语言模型生成答案失败")
                        result=""
                    
                    dockLog.setText("等待扩展完成操作")
                    result2=extensionLoader.callEveryExtension("before_sending_the_message_by_AI_generated",result)


                    try:
                        if result2!=None and result2!="":  
                            result=''.join(list(result2))
                    except:
                        result=""
                    if result.strip()=="":
                        logger.info("退出会话")
                        GoBack()
                        continue
                    click(commentSectionActualSize[0]+((commentSectionActualSize[2]-commentSectionActualSize[0])//2),commentSectionActualSize[1]+((commentSectionActualSize[3]-commentSectionActualSize[1])//2))
                    
                    time.sleep(.1)
                    

                    if type(result)==str:
                        # result+=indentificationString
                        SendText(result,commentSectionActualSize)

                    # click "send" button
                    time.sleep(2)
                    logger.info("发送消息")
                    hotkey('ctrl','enter')
                    dockLog.setText("发送消息 🎉")
                    # click(sendButtonActualSize[0]+((sendButtonActualSize[2]-sendButtonActualSize[0])//2)
                    #         ,sendButtonActualSize[1]+((sendButtonActualSize[3]-sendButtonActualSize[1])//2))
                    
                    time.sleep(.1)

                    # exit conversation
                    logger.info("退出会话")
                    GoBack()
                # else:
                #     if isVisionModel:
                #         conversationImages.findImageBegin()
                else:
                    time.sleep(2) # 防止截图过快对硬盘损伤大
                    dockLog.setText("正在寻找新信息...")
            except KeyboardInterrupt:
                logger.error(f"{Fore.RED}结束运行{Fore.RESET}")
                autoFocusShouldRun=False
                raise SystemExit
                if t:
                    t.join()
    except KeyboardInterrupt:
        logger.error(f"{Fore.RED}结束运行{Fore.RESET}")
        dockLog.stop_floating_window()
        
        autoFocusShouldRun=False
        raise SystemExit
        if t:
            t.join()
        

