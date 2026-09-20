from chatContent import ChatContent
from typing import List
import answer
import configparser
from localization import t
parser=configparser.ConfigParser()
from messagebox import *
import GUIOperations2

option=parser.read("config.ini",encoding='utf-8')

###################
# Vision QQ 扩展 API
# 不要修改这里的代码
###################
def notify(text:str,title:str=""):
    MessageBox(text,title=title or t('dialog.default_title'))
def get_answer_as_string(question:str,system_prompt:str):
    # 从配置的LLM中获取答案
    # 参数
    # question : 问题
    # use_system_prompt : 是否使用系统提示
    # 返回值
    # 获取的答案
    return answer.get_answer_as_string(question,system_prompt)

