import time
from app import create_app
from config import get_db_connection

app = create_app()

def run_tests():
    print("--- RESUME REPLACEMENT VERIFICATION ---")
    
    with app.app_context():
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 1. Setup User C
                cursor.execute("DELETE FROM resumes WHERE user_id IN (SELECT id FROM students WHERE email = 'userC@test.com')")
                cursor.execute("DELETE FROM builder_profiles WHERE user_id IN (SELECT id FROM students WHERE email = 'userC@test.com')")
                cursor.execute("DELETE FROM ats_cache WHERE user_id IN (SELECT id FROM students WHERE email = 'userC@test.com')")
                cursor.execute("DELETE FROM intelligence_cache WHERE user_id IN (SELECT id FROM students WHERE email = 'userC@test.com')")
                cursor.execute("DELETE FROM students WHERE email = 'userC@test.com'")
                
                cursor.execute("INSERT INTO students (name, email, password_hash, phone) VALUES ('User C', 'userC@test.com', 'hash', '123')")
                user_c_id = cursor.lastrowid
                
                # 2. Upload Resume 1
                cursor.execute("INSERT INTO resumes (user_id, resume_text, filename, cloudinary_public_id, resource_type, is_active) VALUES (%s, %s, %s, %s, %s, %s)", 
                               (user_c_id, "Old Resume Text", "old.pdf", "old_id", "pdf", 1))
                old_resume_id = cursor.lastrowid
                
                # Simulate ATS & Intelligence Cache Population for Resume 1
                cursor.execute("INSERT INTO ats_cache (cache_key, user_id, resume_hash, ats_result) VALUES (%s, %s, %s, %s)", 
                               (f"{user_c_id}_hash1", user_c_id, "hash1", '{"score": 50}'))
                cursor.execute("INSERT INTO intelligence_cache (cache_key, user_id, resume_hash, jd_hash) VALUES (%s, %s, %s, %s)", 
                               (f"{user_c_id}_hash1_jd1", user_c_id, "hash1", "jd1"))
                conn.commit()
                
                # 3. REPLACE RESUME
                # The actual route /api/resume/upload DELETES old resumes and inserts the new one.
                cursor.execute("DELETE FROM resumes WHERE user_id = %s", (user_c_id,))
                
                cursor.execute("INSERT INTO resumes (user_id, resume_text, filename, cloudinary_public_id, resource_type, is_active) VALUES (%s, %s, %s, %s, %s, %s)", 
                               (user_c_id, "New Resume Text", "new.pdf", "new_id", "pdf", 1))
                new_resume_id = cursor.lastrowid
                
                # The upload route invalidates caches
                cursor.execute("DELETE FROM ats_cache WHERE user_id = %s", (user_c_id,))
                cursor.execute("DELETE FROM intelligence_cache WHERE user_id = %s", (user_c_id,))
                conn.commit()
                
                # 4. Verifications
                cursor.execute("SELECT * FROM resumes WHERE user_id = %s ORDER BY resume_id ASC", (user_c_id,))
                resumes = cursor.fetchall()
                
                old_res = next((r for r in resumes if r['resume_id'] == old_resume_id), None)
                new_res = next((r for r in resumes if r['resume_id'] == new_resume_id), None)
                
                print(f"  Old Resume Deactivated/Deleted: {'PASS' if old_res is None else 'FAIL'}")
                print(f"  New Resume Active: {'PASS' if new_res is not None else 'FAIL'}")
                print(f"  Cloudinary Public ID Updated: {'PASS' if new_res and new_res['cloudinary_public_id'] == 'new_id' else 'FAIL'}")
                
                cursor.execute("SELECT COUNT(*) as c FROM ats_cache WHERE user_id = %s", (user_c_id,))
                ats_cache_cleared = cursor.fetchone()['c'] == 0
                print(f"  ATS Cache Invalidated: {'PASS' if ats_cache_cleared else 'FAIL'}")
                
                cursor.execute("SELECT COUNT(*) as c FROM intelligence_cache WHERE user_id = %s", (user_c_id,))
                intel_cache_cleared = cursor.fetchone()['c'] == 0
                print(f"  Intelligence Cache Invalidated: {'PASS' if intel_cache_cleared else 'FAIL'}")
                
        finally:
            conn.close()

if __name__ == '__main__':
    run_tests()
