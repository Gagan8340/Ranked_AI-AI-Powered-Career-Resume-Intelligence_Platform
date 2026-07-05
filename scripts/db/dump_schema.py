import pymysql
import os
from dotenv import load_dotenv

load_dotenv('d:/smartcampus/smartcampus-ai/.env')

connection = pymysql.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', ''),
    database=os.getenv('DB_NAME', 'ai_career_platform'),
    cursorclass=pymysql.cursors.DictCursor
)

try:
    with connection.cursor() as cursor:
        cursor.execute('SHOW TABLES')
        tables = [list(row.values())[0] for row in cursor.fetchall()]
        print('TABLES:', tables)
        for table in tables:
            print(f'\n--- TABLE: {table} ---')
            cursor.execute(f'SHOW COLUMNS FROM {table}')
            for col in cursor.fetchall():
                print(f"{col['Field']} ({col['Type']})")
finally:
    connection.close()
