from colorama import Fore
import Vision
import sysDetect
if sysDetect.isLinux():
    import scaleToiniLinux
import load
import dockLog
from localization import t
load.startLoading(Fore.GREEN,t("default.loading"))
floatingTextApp=dockLog.start_floating_window()
dockLog.setText(t("default.loading.hint"))
from typing import Any, Generator, Literal
from random import randint
import subprocess
import platform
import tqdm
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

import os
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

logger.info(f"{Fore.GREEN}{t('default.loading.done')}{Fore.RESET}")
dockLog.setText(t("default.ready"))


autoFocusShouldRun=True
def autoFocus():
    global autoFocusShouldRun
    while autoFocusShouldRun:
        focus()
        logger.debug("Focusing...")
        time.sleep(4)

auto_thread=None



if __name__ == '__main__':
    try:

        time.sleep(1)
        match os.environ.get('XDG_SESSION_TYPE',''):
            case 'wayland':
                logger.warning(t("warning.wayland"))
            case '':
                logger.warning(t("warning.no_display"))
        config=configparser.ConfigParser()
        config.read(filenames='config.ini',encoding='utf-8')
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
        sleep2=config.getint('general','sleep')

        print(f"{Fore.YELLOW}{t('program.name')} {config.get('general','version')}{Fore.RESET}",end='\t')
        print(f"{Fore.CYAN}{platform.platform()}{Fore.RESET}")
        sendImagePossibility=int(sendImagePossibility)

        logger.info(t("program.welcome", name=userName))
        logger.info(t("info.autofocus"))
        auto_thread=threading.Thread(target=autoFocus)
        auto_thread.start()
        if autoLogin:
            logger.info(t("info.autologin"))
            logger.info(t("info.login.try"))
            dockLog.setText(t("info.login.try"))
            for _ in range(4):

                image.fullScreenShot()
                i=image.containsBlue()
                if i==[0,0]:
                    time.sleep(1)
                    continue
                click(*i)
                time.sleep(2)
            time.sleep(1)
                

        print(Fore.YELLOW,"======================================================")
        print("")
        print("\t" + t("warning.never_mouse"))
        print("")
        print("======================================================",Fore.RESET);

        
        size=(int(size[0]*scale),int(size[1]*scale))

        logger.debug(f"size with scale: {size}, scale: {scale}")



        positionRect: tuple[Literal[0], Literal[0], int, int]=(0,0,*size)


        logger.debug(f'{t("screenshot.qq_window")}: {positionRect}')

        chatListActualSize: tuple[int, int, int, int]=positions.toActualSize(positions.CHAT_LIST_BBOX_RELATIVE_SIZE,size)
        logger.debug(f'{t("screenshot.chat_list")}: {chatListActualSize}')

        conversationActualSize: tuple[int, int, int, int]=positions.toActualSize(positions.CONVERSATION_BBOX_RELATIVE_SIZE,size)
        logger.debug(f'{t("screenshot.chat_area")}: {conversationActualSize}')

        commentSectionActualSize: tuple[int, int, int, int]=positions.toActualSize(positions.COMMENT_SECTION_BBOX_RELATIVE_SIZE,size)
        logger.debug(f'{t("screenshot.input_box")}: {commentSectionActualSize}')

        sendButtonActualSize: tuple[int, int, int, int]=positions.toActualSize(positions.SEND_BUTTON_BBOX_RELATIVE_SIZE,size)
        logger.debug(f'{t("screenshot.send_button")}: {sendButtonActualSize}')

        exitConversationActualSize: tuple[int, int, int, int]=positions.toActualSize(positions.EXIT_CONVERSATION_BBOX_RELATIVE_SIZE,size)
        logger.debug(f'{t("screenshot.quit_button")}: {exitConversationActualSize}')

        sendImageActualSize: tuple[int, int, int, int]=positions.toActualSize(positions.SEND_IMAGE_BBOX_RELATIVE_SIZE,size)
        logger.debug(f'{t("screenshot.upload_button")}: {sendImageActualSize}')


        atPlaceActualSize: tuple[int, int, int, int]=positions.toActualSize(positions.AT_PLACE_BBOX_RELATIVE_SIZE,size)
        logger.debug(f'{t("screenshot.at_position")}: {atPlaceActualSize}')

        startDraggingAbsolutePosition=positions.toActualPoint(positions.START_DRAGGING_RELATIVE_POSITION,size)
        endDraggingAbsolutePosition=positions.toActualPoint(positions.END_DRAGGING_RELATIVE_POSITION,size)
        logger.debug(f'{t("screenshot.drag_start")}: {startDraggingAbsolutePosition}')
        logger.debug(f'{t("screenshot.drag_end")}: {endDraggingAbsolutePosition}')

        chatButtonActualPosition=positions.toActualPoint(positions.CHAT_BUTTON_RELATIVE_POSITION,size)
        logger.debug(f'{t("screenshot.chat_button")}: {chatButtonActualPosition}')
        contactButtonActualPosition=positions.toActualPoint(positions.CONTACT_BUTTON_RELATIVE_POSITION,size)
        logger.debug(f'{t("screenshot.contact_button")}: {contactButtonActualPosition}')


        cancelButtonActualPosition=positions.toActualPoint(positions.CANCEL_BUTTON_RELATIVE_POSITION,size)

        uploadImagePossibleActualSize=positions.toActualSize(positions.UPLOAD_IMAGE_POSSIBLE_BBOX_RELATIVE_SIZE,size)
        logger.debug(f'{t("screenshot.upload_maybe")}: {uploadImagePossibleActualSize}')
        totalTokens=0
        copyButtonPossibleAcutalSize=positions.toActualSize(positions.COPY_BUTTON_BBOX_RELATIVE_SIZE,size)
        logger.debug(f'{t("screenshot.copy_maybe")}: {copyButtonPossibleAcutalSize}')
        
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
            
            for _ in tqdm.trange(0,sleep2,desc=t("info.wait")):
                time.sleep(1)
        def CleanInputSection():
            HotKey('ctrl','a')
            time.sleep(0.2)
            press_key('backspace')
            time.sleep(0.2)
            
        def UploadImageWithoutSend(upload_image_area):
            image_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Images")
            logger.info(image_dir)
            
            dirs = []
            if not os.path.exists(image_dir):
                logger.error(t("error.image_dir_not_found"))
            else:
                dirs = [os.path.join(image_dir, f) for f in os.listdir(image_dir) if os.path.isfile(os.path.join(image_dir, f))]
            
            contains_image = False
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif'}
            
            for dir_path in dirs:
                logger.info(dir_path)
                ext = os.path.splitext(dir_path)[1].lower()
                if ext in image_extensions:
                    contains_image = True
                    logger.info(f"Image:{dir_path}")
                    break
            
            if os.path.exists(image_dir) and contains_image:
                image.screenshot(*upload_image_area)
                time.sleep(0.5)
                
                copy_button_position = Vision.FindTemplates("screenshot.png", "uploadImage.png", 30, 1)
                if len(copy_button_position) <= 0:
                    logger.warning(t("error.template_upload_failed"))
                    try:
                        import subprocess
                        if os.name == 'nt':
                            subprocess.Popen("uploadImage2.exe").wait()
                            time.sleep(0.2)
                            HotKey('ctrl', 'v')
                    except:
                        pass
                else:
                    x, y = copy_button_position[0]
                    x += upload_image_area[0]
                    y += upload_image_area[1]
                    click(x, y)
                    time.sleep(4)
                time.sleep(4)
        
        while True:
            try:
                # im=image.screenshot(*positionRect)
                
                # im.save("screenshot.png")
                # chatList: Image.Image=im.crop(chatListActualSize)
                chatList=image.fullScreenShot()

                dockLog.setText(t("info.waiting_extension"))
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
                    
                    dockLog.setText(t("docklog.found_new"))
                    logger.info(t("info.found_reddot") + f": {contain}")

                    click(contain[0],contain[1])
                    time.sleep(2)
                    

                    conversationText=[]
                    
                    dragFromTo(*startDraggingAbsolutePosition,*endDraggingAbsolutePosition)

                    dockLog.setText(t("docklog.no_mouse"))
                    time.sleep(.1)
                    goto(conversationActualSize[0]+((conversationActualSize[2]-conversationActualSize[0])//2),conversationActualSize[1]+((conversationActualSize[3]-conversationActualSize[1])//2))
                    image.fullScreenShot()

                    t_pts=Vision.FindTemplates('screenshot.png','copy.png',30,1)
                    if len(t_pts)>=1 and t_pts[0]!=[0,0]:
                        click(t_pts[0][0],t_pts[0][1])
                    else:
                        logger.error(f"{Fore.YELLOW}{t('error.template_copy_failed')}{Fore.RESET}")
                        
                        
                    
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
                        dockLog.setText(t("docklog.no_message"))
                        logger.error(t("docklog.no_message"))
                        GoBack()
                        continue
                        
                    ChatContents=ParseChatLog(chat,userName)
                    
                    

                    dockLog.setText(t("info.waiting_extension"))
                    extensionLoader.callEveryExtension("after_receiving_messages",ChatContents)

                    # print(ChatContents,ChatContentsList) 

                    # conversationText=[str(text) for text iChatContentsts]
                    
                    dockLog.setText(t("info.waiting_answer"))
                    #send answer
                    click(commentSectionActualSize[0]+((commentSectionActualSize[2]-commentSectionActualSize[0])//2),commentSectionActualSize[1]+((commentSectionActualSize[3]-commentSectionActualSize[1])//2))
                    
                    HotKey("ctrl","a")
                    time.sleep(0.2)
                    press("backspace")
                    time.sleep(0.2)
                    


                    conversation_text = '\n'.join(list(conversationText))
                    print(f"{Fore.CYAN}{conversation_text}{Fore.RESET}")
                    
                    try:
                        result,tokenUsage=answer.getAnswer(ChatContents)
                        totalTokens+=tokenUsage
                        with open(TOKENCOUNTFILE,'w',encoding='utf8') as f:
                            f.write(str(totalTokens))
                    except Exception as e:
                        logger.error(f"{t('error.answer_failed')}\n{e}")
                        dockLog.setText(t("docklog.answer_failed"))
                        result=""
                    
                    dockLog.setText(t("info.waiting_extension"))
                    result2=extensionLoader.callEveryExtension("before_sending_the_message_by_AI_generated",result)


                    try:
                        if result2!=None and result2!="":  
                            result=''.join(list(result2))
                    except:
                        result=""
                    if result.strip()=="":
                        if withImage and sendImagePossibility>0:
                            logger.warning(t("warning.answer_not_generated"))
                            UploadImageWithoutSend(uploadImagePossibleActualSize)
                            HotKey('ctrl','enter')
                            logger.info(t("info.quit_conversation"))
                        else:
                            logger.error(t("error.answer_not_generated_quit"))
                        GoBack()
                        continue
                    click(commentSectionActualSize[0]+((commentSectionActualSize[2]-commentSectionActualSize[0])//2),commentSectionActualSize[1]+((commentSectionActualSize[3]-commentSectionActualSize[1])//2))
                    
                    time.sleep(.1)
                    

                    if type(result)==str:
                        # result+=indentificationString
                        SendText(result,commentSectionActualSize)

                    # click "send" button
                    time.sleep(2)
                    logger.info(t("info.sent_message"))
                    HotKey('ctrl','enter')
                    dockLog.setText(t("docklog.sent_message"))
                    # click(sendButtonActualSize[0]+((sendButtonActualSize[2]-sendButtonActualSize[0])//2)
                    #         ,sendButtonActualSize[1]+((sendButtonActualSize[3]-sendButtonActualSize[1])//2))
                    
                    time.sleep(.1)

                    # exit conversation
                    logger.info(t("info.quit_conversation"))
                    CleanInputSection()
                    GoBack()
                # else:
                #     if isVisionModel:
                #         conversationImages.findImageBegin()
                else:
                    time.sleep(2) # 防止截图过快对硬盘损伤大
                    dockLog.setText(t("info.searching_new"))
            except KeyboardInterrupt:
                logger.error(f"{Fore.RED}{t('error.exit_run')}{Fore.RESET}")
                autoFocusShouldRun=False
                raise SystemExit
                if auto_thread:
                    auto_thread.join()
    except KeyboardInterrupt:
        logger.error(f"{Fore.RED}{t('error.exit_run')}{Fore.RESET}")
        dockLog.stop_floating_window()
        
        autoFocusShouldRun=False
        raise SystemExit
        if auto_thread:
            auto_thread.join()
        

