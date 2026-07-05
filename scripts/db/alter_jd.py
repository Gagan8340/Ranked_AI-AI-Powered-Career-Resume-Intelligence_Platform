import pymysql
from config import get_db_connection

def alter_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Check if title column exists in job_descriptions
            cursor.execute("SHOW COLUMNS FROM job_descriptions LIKE 'title'")
            result = cursor.fetchone()
            if not result:
                cursor.execute("ALTER TABLE job_descriptions ADD COLUMN title VARCHAR(255)")
                print("Added title column to job_descriptions")
            else:
                print("title column already exists in job_descriptions")
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    alter_db()
