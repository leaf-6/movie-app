import pymysql
from config import Config

class Database:
    
    @staticmethod
    def get_connection():
        return pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

    @staticmethod
    def execute_query(sql, params=None, fetch_one=False, fetch_all=False):
        conn = None
        try:
            conn = Database.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                if fetch_one:
                    return cursor.fetchone()
                if fetch_all:
                    result = cursor.fetchall()
                    return result if result is not None else []
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            print('SQL执行错误:', sql)
            print('参数:', params)
            print('错误:', e)
            raise e
        finally:
            if conn:
                conn.close()

    @staticmethod
    def execute_insert(sql, params=None):
        conn = None
        try:
            conn = Database.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print('SQL执行错误:', sql)
            print('参数:', params)
            print('错误:', e)
            raise e
        finally:
            if conn:
                conn.close()