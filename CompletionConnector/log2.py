from clr import *
def _log(*args) -> None:
    """编码安全的日志：stdout 可能是 cp1252，中文打印会抛 UnicodeEncodeError，
    进而杀死 daemon 连接线程。这里用 ASCII 过滤兜底，保证打印永不失败。"""
    text = " ".join(str(a) for a in args)
    try:
        print(text)
    except UnicodeEncodeError:
        ascii_only = text.encode("ascii", errors="replace").decode("ascii")
        print(ascii_only)
def LogColored(*args,color=Fore.CYAN)->None:
    text = " ".join(str(a) for a in args)
    _log(f"{color}{text}{Fore.RESET}")