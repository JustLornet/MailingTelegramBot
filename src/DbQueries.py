from sqlite3.dbapi2 import Connection, IntegrityError


class DbQueries:
    def __init__(self, db: Connection):
        self.db = db
        self.cursor = db.cursor()

    def create_default_tables(self):
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS Users(
           UserId INTEGER PRIMARY KEY AUTOINCREMENT,
           ChatAiogramId INTEGER UNIQUE NOT NULL,
           UserFirstName TEXT);
        """)
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS SendingMails(
           MailId INTEGER PRIMARY KEY AUTOINCREMENT,
           UserId INTEGER REFERENCES Users (UserId),
           MailName TEXT NOT NULL,
           UNIQUE (UserId, MailName));
        """)
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS DestinationMails(
           MailId INTEGER PRIMARY KEY AUTOINCREMENT,
           UserId INTEGER UNIQUE REFERENCES Users (UserId),
           MailName TEXT NOT NULL);
        """)

    def get_user(self, aiogram_id: int) -> int:
        query = f'SELECT UserId from Users where ChatAiogramId = {aiogram_id}'
        res_unparsed = self.cursor.execute(query)
        res = res_unparsed.fetchone()

        return res[0]

    def add_user(self, chat_aiogram_id: int, user_first_name: str):
        try:
            query = f"INSERT INTO Users (ChatAiogramId, UserFirstName) VALUES ({chat_aiogram_id}, '{user_first_name}')"
            self.cursor.execute(query)
            self.db.commit()
        except IntegrityError:
            print('пользователь уже существует')

    def add_sending_mail(self, user_id: int, mail_name: str):
        try:
            query = f"INSERT INTO SendingMails (UserId, MailName) VALUES ({user_id}, '{mail_name}')"
            self.cursor.execute(query)
            self.db.commit()
        except IntegrityError:
            query = f"UPDATE SendingMails SET MailName='{mail_name}' where UserId={user_id}"
            self.cursor.execute(query)
            self.db.commit()

    def get_sending_mails(self, user_id: int):
        query = f'SELECT MailId, MailName from SendingMails where UserId = {user_id}'
        res = self.cursor.execute(query)
        fetched = res.fetchall()

        return fetched

    def set_dest_mail(self, user_id: int, mail_name: str):
        try:
            query = f"INSERT INTO DestinationMails (UserId, MailName) VALUES ({user_id}, '{mail_name}')"
            self.cursor.execute(query)
            self.db.commit()
        except IntegrityError:
            query = f"UPDATE DestinationMails SET MailName = '{mail_name}' where UserId = {user_id}"
            self.cursor.execute(query)
            self.db.commit()

    def get_dest_mail(self, user_id: int):
        query = f'SELECT MailName from DestinationMails where UserId = {user_id}'
        res = self.cursor.execute(query)
        fetched = res.fetchone()

        return fetched[0]

    def delete_sending_mail(self, user_id: int, mail_name: str):
        query = f"DELETE FROM SendingMails where UserId={user_id} AND MailName='{mail_name}'"
        self.cursor.execute(query)
        self.db.commit()

    def get_sending_mail_id(self, user_id: int, mail_name: str):
        query = f"SELECT MailId from SendingMails where UserId = {user_id} AND MailName='{mail_name}'"
        res = self.cursor.execute(query)
        fetched = res.fetchone()

        return fetched[0]
