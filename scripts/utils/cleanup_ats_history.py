from config import get_db_connection

def cleanup_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ats_history WHERE scan_type != 'ATS_CHECKER'")
    conn.commit()
    print(f'Deleted {cursor.rowcount} invalid scans')
    conn.close()

if __name__ == '__main__':
    cleanup_db()
