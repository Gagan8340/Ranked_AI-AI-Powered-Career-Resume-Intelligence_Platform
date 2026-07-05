from config import get_db_connection

try:
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT DATABASE();")
        result = cursor.fetchone()

    print("SUCCESS")
    print(result)

    conn.close()
except Exception as e:
    print("FAILED")
    print(e)
