from config import get_db_connection

connection = get_db_connection()

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
