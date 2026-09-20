import threading
from time import sleep,time
from localization import t

loading=False
startTime=0
l=[
'[->                         ]',
'[-->                        ]',
'[ <-->                      ]',
'[  <-->                     ]',
'[    <-->                   ]',
'[      <-->                 ]',
'[        <-->               ]',
'[          <-->             ]',
'[            <-->           ]',
'[              <-->         ]',
'[                <-->       ]',
'[                  <-->     ]',
'[                    <-->   ]',
'[                      <--> ]',
'[                        <--]',
'[                         <-]',]
l+=l[::-1]
from colorama import Fore
def load(color,text):
    l2=['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    index=0
    global l
    while loading:
        for i in l:
            print(color+l2[index%10]+i+'\t'+text+Fore.RESET,end='\r')
            index+=1
            sleep(0.1)
            if not loading:
                break
        
def startLoading(color,text):
    global loading,startTime
    startTime=time()

    loading=True
    thread=threading.Thread(target=load,args=(color,text))
    thread.start()

def stopLoading():
    global loading,startTime
    loading=False
    print(f'\n{t("default.loading.elapsed")}:{time()-startTime:.2f}s')
    print('\n')
    

if __name__=='__main__':
    startLoading('',t("loading.text"))
    sleep(12)
    stopLoading()