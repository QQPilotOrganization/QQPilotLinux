import sqlite3
from typing import Any


class DB:
    def __init__(self, filename: str) -> None:
        self.conn: sqlite3.Connection = sqlite3.connect(filename)
        self.cursor = self.conn.cursor()
        # 启用外键支持
        self.execute("PRAGMA foreign_keys = ON;")

    def execute(self, cmd: str, *args) -> sqlite3.Cursor:
        self.cursor.execute(cmd, *args)
        self.conn.commit()
        return self.cursor

    def fetchone(self, cmd: str, *args)->Any:
        self.cursor.execute(cmd, *args)
        return self.cursor.fetchone()

    def fetchall(self, cmd: str, *args) -> list[Any]:
        self.cursor.execute(cmd, *args)
        return self.cursor.fetchall()

    def __del__(self) -> None:
        if hasattr(self, 'conn'):
            self.conn.close()