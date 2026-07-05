from config import get_db_connection

conn = get_db_connection()
try:
    with conn.cursor() as cursor:
        print("=== FINAL VERIFICATION SCRIPT ===\n")
        
        # 1. Total row count
        cursor.execute("SELECT COUNT(*) as total FROM ats_history;")
        total_count = cursor.fetchone()['total']
        print(f"TOTAL ROWS IN ats_history: {total_count}\n")
        
        # 2. Count grouped by scan_type
        cursor.execute("SELECT scan_type, COUNT(*) as count FROM ats_history GROUP BY scan_type;")
        group_counts = cursor.fetchall()
        print("COUNT BY SCAN_TYPE:")
        for row in group_counts:
            print(f"  {row['scan_type']}: {row['count']}")
        print("\n")
        
        # 3. Real rows for a real user (user_id=1)
        cursor.execute("""
        SELECT scan_type, ats_score, scan_timestamp 
        FROM ats_history 
        WHERE user_id = 1 
        ORDER BY scan_timestamp DESC 
        LIMIT 20;
        """)
        real_rows = cursor.fetchall()
        print("RECENT 20 ROWS FOR USER 1:")
        for row in real_rows:
            print(f"  {row['scan_timestamp']} | {row['scan_type']} | Score: {row['ats_score']}")
            
finally:
    conn.close()
