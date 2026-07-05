import json
import time
import sys
from config import get_db_connection
from utils.ats_history_logger import log_ats_history

print("=== PRE-DEPLOYMENT VERIFICATION ===")
sys.stdout.flush()

conn = get_db_connection()
try:
    with conn.cursor() as cursor:
        # Use user 1 which we know exists
        user_id = 1
        
        # Clear existing history for user 1 to test cleanly
        cursor.execute("DELETE FROM ats_history WHERE user_id = %s", (user_id,))
        conn.commit()
        
        # Test 1: Empty state analytics
        cursor.execute("SELECT MAX(ats_score) AS max_score, COUNT(*) AS total_scans, AVG(ats_score) AS avg_score FROM ats_history WHERE user_id=%s", (user_id,))
        stats = cursor.fetchone()
        print(f"\n[Empty State Analytics] Total: {stats['total_scans']}, Max: {stats['max_score']}, Avg: {stats['avg_score']}")
        sys.stdout.flush()
        
        # Test 2: Hooking 4 origins
        print("\n[Simulating Scans from 4 Origins]")
        sys.stdout.flush()
        log_ats_history(user_id, 45, "ATS_CHECKER")
        time.sleep(2) # Wait to bypass 2-sec duplicate protection
        log_ats_history(user_id, 50, "JD_ANALYZER")
        time.sleep(2)
        log_ats_history(user_id, 80, "BUILDER_SCORE")
        time.sleep(2)
        log_ats_history(user_id, 85, "OPTIMIZED_RESUME")
        
        cursor.execute("SELECT scan_type, ats_score FROM ats_history WHERE user_id = %s ORDER BY scan_timestamp ASC", (user_id,))
        scans = cursor.fetchall()
        for s in scans:
            print(f"Recorded: {s['scan_type']} -> {s['ats_score']}")
        sys.stdout.flush()
            
        # Test 3: Duplicate protection
        print("\n[Testing Duplicate Protection]")
        log_ats_history(user_id, 99, "ATS_CHECKER") # original
        log_ats_history(user_id, 99, "ATS_CHECKER") # duplicate exactly 0 secs later
        log_ats_history(user_id, 99, "ATS_CHECKER") # duplicate
        
        cursor.execute("SELECT COUNT(*) as c FROM ats_history WHERE user_id = %s AND ats_score = 99", (user_id,))
        dup_count = cursor.fetchone()['c']
        print(f"Attempted 3 identical rapid inserts. Rows inserted: {dup_count}")
        sys.stdout.flush()
        
        # Test 4: Dashboard stats with 5 scans (4 + 1 from dup test)
        cursor.execute("SELECT MAX(ats_score) AS max_score, COUNT(*) AS total_scans, AVG(ats_score) AS avg_score FROM ats_history WHERE user_id=%s", (user_id,))
        stats = cursor.fetchone()
        
        cursor.execute("SELECT ats_score FROM ats_history WHERE user_id=%s ORDER BY scan_timestamp DESC LIMIT 1", (user_id,))
        latest = cursor.fetchone()
        latest_score = latest['ats_score'] if latest else None
        
        print(f"\n[Scans Analytics]")
        print(f"Total Scans: {stats['total_scans']}")
        print(f"Highest Score: {stats['max_score']}")
        print(f"Latest Score: {latest_score}")
        avg = stats['avg_score']
        print(f"Average Score: {float(avg):.1f}" if avg is not None else "Average Score: None")
        sys.stdout.flush()
        
        # Test 5: 100 scans scaling
        print("\n[Inserting 95 more scans to reach 100]")
        for i in range(95):
            cursor.execute("INSERT INTO ats_history (user_id, ats_score, scan_type, scan_timestamp) VALUES (%s, %s, %s, DATE_SUB(NOW(), INTERVAL %s DAY))", (user_id, 70 + (i%20), "ATS_CHECKER", 100-i))
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) as c FROM ats_history WHERE user_id = %s", (user_id,))
        total = cursor.fetchone()['c']
        print(f"Total rows successfully inserted: {total}")
        sys.stdout.flush()
        
finally:
    conn.close()
