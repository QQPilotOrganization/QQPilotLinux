from DBConnector import DB
class IncomingMessageDB(DB):
    def __init__(self) -> None:
        super().__init__('IncomingMessage.sqlite3')
        self.execute('''CREATE TABLE IF NOT EXISTS IncomingMessages (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            message TEXT NOT NULL UNIQUE
                            );
                            ''')
        
    def MessageExists(self,message:str):
        # return False
        cursor=self.execute(f'Select id FROM IncomingMessages WHERE message=?',(message,))
        if cursor.fetchone() is None:
            self.execute('INSERT INTO IncomingMessages(message) VALUES(?)',(message,))
            return False
        return True
    