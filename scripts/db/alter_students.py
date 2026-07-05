from config import get_db_connection

def alter_students():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # First drop foreign keys if needed? No, altering columns doesn't require dropping FKs unless dropping referenced column.
            
            # Check if 'full_name' exists to rename it to 'name'
            cursor.execute("SHOW COLUMNS FROM students LIKE 'full_name'")
            if cursor.fetchone():
                cursor.execute("ALTER TABLE students CHANGE COLUMN full_name name VARCHAR(100) NOT NULL")
                print("Renamed full_name to name.")
            
            # Add missing columns
            columns_to_add = [
                ("phone", "VARCHAR(15)"),
                ("last_seen", "TIMESTAMP NULL"),
                ("is_active", "BOOLEAN DEFAULT TRUE")
            ]
            
            for col_name, col_type in columns_to_add:
                cursor.execute(f"SHOW COLUMNS FROM students LIKE '{col_name}'")
                if not cursor.fetchone():
                    cursor.execute(f"ALTER TABLE students ADD COLUMN {col_name} {col_type}")
                    print(f"Added column {col_name}")
            
            conn.commit()
            print("Successfully updated students table schema.")
    except Exception as e:
        print(f"Error altering students schema: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    alter_students()
