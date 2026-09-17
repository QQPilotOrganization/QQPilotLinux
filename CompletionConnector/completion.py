from typing import Union,List,Dict,Literal,Any
import json
from dataclasses import dataclass
class CompletionMessage:
    def __init__(self,role,content:Union[str,List[Dict[str,str]]]) -> None:
        pass
@dataclass
class CompletionContent:
    def __init__(self,Type:Union[Literal["text"],Literal["image_url"]],typeContent:str) -> None:
        self.Type=Type
        self.typeContent=typeContent
    
    @staticmethod
    def FromDict(dict:Dict[str,Union[str,Dict[str,str]]])->CompletionContent:
        if isinstance(dict,str):
            return CompletionContent("text",dict) 
        t=dict.get("type","text")
        content=""
        if t=="text":
            content=str(dict.get("text",""))
        
        elif t=="image_url":
            c=dict.get("image_url",{})
            if isinstance(c,Dict):
                content=c.get("url","")
            else:
                content=""
        return CompletionContent(t,content) # type: ignore
    @staticmethod
    def FromJson(Json:str)-> CompletionContent:
        return CompletionContent.FromDict(json.loads(Json))
    def ToDict(self):
        if self.Type=="text":
            return {'type':self.Type,self.Type:self.typeContent}
        elif self.Type=="image_url":
            return {'type':self.Type,self.Type:{'url':self.typeContent}}
        else:
            return{}
    def ToJson(self):
        return json.dumps(self.ToDict())
    def __repr__(self) -> str:
        return f"{self.Type}:{self.typeContent}"[:30]+"..."
