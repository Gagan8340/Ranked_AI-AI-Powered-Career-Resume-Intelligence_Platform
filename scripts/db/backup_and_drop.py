import json
from config import get_db_connection

def backup_and_drop_tables():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            tables_to_drop = ['students_backup', 'students_before_final_cleanup']
            
            for table in tables_to_drop:
                print(f"Backing up {table}...")
                try:
                    cursor.execute(f"SELECT * FROM {table}")
                    rows = cursor.fetchall()
                    with open(f"{table}_backup.json", "w") as f:
                        # Convert datetime to string for JSON serialization
                        for row in rows:
                            for key, val in row.items():
                                if hasattr(val, 'isoformat'):
                                    row[key] = val.isoformat()
                        json.dump(rows, f, indent=2)
                    print(f"[OK] {table} backed up to {table}_backup.json ({len(rows)} rows)")
                    
                    print(f"Dropping {table}...")
                    cursor.execute(f"DROP TABLE {table}")
                    print(f"[OK] {table} dropped.")
                except Exception as e:
                    print(f"Error processing {table}: {e}")
            
            conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    backup_and_drop_tables()
