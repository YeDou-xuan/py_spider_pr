import pymysql
from PyQt6.QtWidgets import QMainWindow

class DatabaseManager:
    def __init__(self):
        self.connection = None

    def __enter__(self):
        print("enter")
        self.connection = self.create_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("exit")
        self.connection.close()

    def create_connection(self):
        if not self.connection or not self.connection.open():
            try:
                self.connection=pymysql.connect(
                    host='localhost',
                    port=3306,
                    user='root',
                    passwd='liu@423615',
                    database='spider_database',
                    charset='utf8',
                    cursorclass=pymysql.cursors.DictCursor)
            except Exception as e:
                print(f"数据库连接错误，由于{e}")
        return self.connection



    def fetch_query(self,query,params=None,single=False):
        result = None
        if self.connection:
            try:
                with self.connection.cursor() as cursor:
                    cursor.execute(query,params)
                    if single:
                        result = cursor.fetchone()
                    else:
                        result = cursor.fetchall()
            except Exception as e:
                print(f"查询错误：{e}")
        else:
            print("并未建立数据库连接")
        return result

    def execute_query(self,query,params=None):
        if self.connection:
            try:
                with self.connection.cursor() as cursor:
                    cursor.execute(query,params)
                    self.connection.commit()
            except Exception as e:
                print(f"执行异常:{e}")
                self.connection.rollback()
                return None
        else:
            print("并未建立数据库连接")
        return None

    def close_connection(self):
        if self.connection:
            self.connection.close()

if __name__ == '__main__':
    with DatabaseManager() as db:
        pass
