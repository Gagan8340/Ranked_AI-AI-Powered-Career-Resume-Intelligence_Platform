import json
from datetime import datetime, timedelta
from config import get_db_connection

def log_ats_history(user_id, ats_score, scan_type, resume_id=None, resume_title=None, breakdown=None):
    """
    Logs an ATS scan to the ats_history table.
    Includes duplicate protection to prevent identical scans within 2 seconds.
    """
    if user_id is None or ats_score is None:
        return
        
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # Check for duplicate within the last 2 seconds
        cursor.execute("""
            SELECT id FROM ats_history 
            WHERE user_id = %s 
              AND scan_type = %s 
              AND ats_score = %s
              AND scan_timestamp >= NOW() - INTERVAL 2 SECOND
        """, (user_id, scan_type, ats_score))
        
        if cursor.fetchone():
            # Duplicate detected, skip insertion
            return
            
        breakdown_json = json.dumps(breakdown) if breakdown else None
        
        cursor.execute("""
            INSERT INTO ats_history (user_id, resume_id, resume_title, scan_type, ats_score, breakdown_json)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, resume_id, resume_title, scan_type, ats_score, breakdown_json))
    conn.commit()
    conn.close()
