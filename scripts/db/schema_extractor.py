from config import get_db_connection

def main():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = [row[f"Tables_in_ai_career_platform"] for row in cursor.fetchall()]
            
            print(f"TABLES FOUND: {len(tables)}")
            for t in tables:
                print(f"\n--- TABLE: {t} ---")
                
                # Row count
                cursor.execute(f"SELECT COUNT(*) as count FROM {t}")
                count = cursor.fetchone()['count']
                print(f"Row count: {count}")
                
                # Primary key
                cursor.execute(f"SHOW KEYS FROM {t} WHERE Key_name = 'PRIMARY'")
                pk_rows = cursor.fetchall()
                pks = [row['Column_name'] for row in pk_rows]
                print(f"Primary key: {', '.join(pks) if pks else 'None'}")
                
                # Foreign keys
                query = f"""
                SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = 'ai_career_platform' AND TABLE_NAME = '{t}'
                AND REFERENCED_TABLE_NAME IS NOT NULL;
                """
                cursor.execute(query)
                fks = cursor.fetchall()
                if fks:
                    for fk in fks:
                        print(f"Foreign key: {fk['COLUMN_NAME']} -> {fk['REFERENCED_TABLE_NAME']}({fk['REFERENCED_COLUMN_NAME']})")
                else:
                    print("Foreign keys: None")

    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
