from config import get_db_connection

def migrate():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Check if columns already exist
            cursor.execute("SHOW COLUMNS FROM students LIKE 'reset_token'")
            if cursor.fetchone():
                print("Columns already exist.")
                return
            cursor.execute("ALTER TABLE students ADD COLUMN reset_token VARCHAR(255) NULL, ADD COLUMN reset_token_expiry TIMESTAMP NULL")
        conn.commit()
        print("Migration successful.")
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
