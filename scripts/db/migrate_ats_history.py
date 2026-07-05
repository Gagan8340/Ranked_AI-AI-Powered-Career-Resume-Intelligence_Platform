import json
from config import get_db_connection

def migrate():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Create table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ats_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                resume_id INT,
                resume_title VARCHAR(255),
                scan_type VARCHAR(50),
                ats_score INT NOT NULL,
                breakdown_json JSON,
                scan_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES students(id)
            )
            """)
            
            # 2. Count existing job_descriptions
            cursor.execute("SELECT COUNT(*) as c FROM job_descriptions WHERE ats_score IS NOT NULL")
            jd_count = cursor.fetchone()['c']
            print(f"Found {jd_count} records in job_descriptions to migrate.")
            
            # 3. Perform migration
            cursor.execute("""
            INSERT INTO ats_history (user_id, resume_id, ats_score, scan_timestamp, scan_type)
            SELECT user_id, resume_id, ats_score, created_at, 'LEGACY_DASHBOARD'
            FROM job_descriptions
            WHERE ats_score IS NOT NULL
            """)
            migrated_count = cursor.rowcount
            print(f"Inserted {migrated_count} records into ats_history.")
            
            # 4. Describe table
            cursor.execute("DESCRIBE ats_history")
            schema = cursor.fetchall()
            print("ats_history schema:")
            for s in schema:
                print(s)
                
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
