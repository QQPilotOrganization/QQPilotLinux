import tkinter as tk
from tkinter import scrolledtext, messagebox
import json
import re

class JSONEditor:
    def __init__(self, root,target=""):
        self.root = root
        self.root.title("JSON编辑器")
        self.root.geometry("800x600")
        self.target=target
        # 创建文本框
        self.text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=("Consolas", 12))
        self.text_area.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # 绑定按键释放事件，实现实时高亮
        self.text_area.bind("<KeyRelease>", lambda event: self.save())
        self.text_area.bind("<KeyRelease>", lambda event: self.highlight_json())
        # self.text_area.bind("<KeyRelease>", lambda event: self.format_json())

        # 创建按钮区
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)
        
        tk.Button(btn_frame, text="格式化 JSON", command=self.format_json, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="保存", command=self.save).pack(side=tk.LEFT, padx=5)

        # 预定义高亮样式
        self.setup_tags()
        self.Aopen();
        
    def save(self):
        print("save")
        if self.target=="":
            return
        with open(self.target,'w',encoding='utf8') as f:
            f.write(self.text_area.get("1.0", tk.END))
    def Aopen(self):
        if self.target=="":
            return
        with open(self.target,'r',encoding='utf8') as f:
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert("1.0", f.read())
    def setup_tags(self):
        """配置高亮标签的颜色"""
        self.text_area.tag_configure("key", foreground="#92278F")      # 键：紫色
        self.text_area.tag_configure("string", foreground="#3AB54A")   # 字符串值：绿色
        self.text_area.tag_configure("number", foreground="#25AAE2")   # 数字：蓝色
        self.text_area.tag_configure("keyword", foreground="#F1592A")  # true/false/null：橙色
        self.text_area.tag_configure("bracket", foreground="#999999")  # 括号：灰色

    def highlight_json(self):
        """核心高亮逻辑：通过正则匹配并应用标签"""
        # 清除旧的高亮
        for tag in ("key", "string", "number", "keyword", "bracket"):
            self.text_area.tag_remove(tag, "1.0", tk.END)

        content = self.text_area.get("1.0", tk.END)

        # 匹配 JSON 键 (例如: "name":)
        for match in re.finditer(r'"(.*?)"\s*:', content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()-1}c" # 排除冒号
            self.text_area.tag_add("key", start, end)

        # 匹配字符串值
        for match in re.finditer(r':\s*"(.*?)"', content):
            start = f"1.0+{match.start()+2}c" # 跳过 ": 
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("string", start, end)

        # 匹配数字
        for match in re.finditer(r':\s*(\d+\.?\d*)', content):
            start = f"1.0+{match.start()+2}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("number", start, end)

        # 匹配布尔值和 null
        for match in re.finditer(r'\b(true|false|null)\b', content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("keyword", start, end)

    def format_json(self):
        """格式化 JSON 字符串"""
        try:
            raw_json = self.text_area.get("1.0", tk.END).strip()
            parsed = json.loads(raw_json)
            formatted = json.dumps(parsed, indent=4, ensure_ascii=False)
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert("1.0", formatted)
            self.highlight_json() # 格式化后重新高亮
        except json.JSONDecodeError as e:
            # messagebox.showerror("格式错误", f"JSON 解析失败:\n{e}")
            pass

    def clear_text(self):
        self.text_area.delete("1.0", tk.END)


def Open(file:str):
    root = tk.Tk()
    app = JSONEditor(root,file)
    root.mainloop()
    
if __name__ == "__main__":
    Open("")