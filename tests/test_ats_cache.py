import time
import requests
from app import create_app, get_db_connection
from flask_jwt_extended import create_access_token

def run_cache_tests():
    app = create_app()
    with app.app_context():
        token = create_access_token(identity="11")
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # We will test using the actual flask test client to avoid network overhead, 
    # but the test requirements ask for performance benchmarks. Using test_client is fine.
    
    # Wait, if we use test_client, time.time() will accurately measure the response time.
    client = app.test_client()
    
    resume_id = 17
    data = {"resume_id": resume_id}
    
    print("--- TASK 7: PERFORMANCE TEST ---")
    
    # Clear cache for this user/resume first to ensure a fresh run
    with app.app_context():
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM ats_cache WHERE user_id = 11 AND resume_id = 17")
            conn.commit()
            
            # Make sure we have a known resume text to start
            cursor.execute("SELECT resume_text FROM resumes WHERE resume_id = 17")
            original_resume_text = cursor.fetchone()['resume_text']
        conn.close()
        
    print("FIRST RUN (Fresh Analysis)...")
    start = time.time()
    response1 = client.post('/api/ats/analyze', headers=headers, json=data)
    t1 = time.time() - start
    res1 = response1.json.get('analysis', {})
    
    print(f"Time: {t1:.2f} seconds")
    print(f"Cache Used: {res1.get('cache_used')}")
    if t1 > 10:
        print("FAIL: First run took more than 10 seconds.")
    else:
        print("PASS: First run < 10 seconds.")
        
    print("\nSECOND RUN (Cached Analysis)...")
    start = time.time()
    response2 = client.post('/api/ats/analyze', headers=headers, json=data)
    t2 = time.time() - start
    res2 = response2.json.get('analysis', {})
    
    print(f"Time: {t2:.4f} seconds ({t2*1000:.0f} ms)")
    print(f"Cache Used: {res2.get('cache_used')}")
    if t2 > 0.5:
        print("FAIL: Second run took more than 500ms.")
    else:
        print("PASS: Second run < 500 ms.")
        
    print("\n--- TASK 8: CACHE INVALIDATION TEST ---")
    
    print("Modifying resume text in database to simulate an update...")
    with app.app_context():
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE resumes SET resume_text = %s WHERE resume_id = 17", (original_resume_text + "\nUpdated text for hash change",))
            conn.commit()
        conn.close()
        
    print("THIRD RUN (After Resume Update)...")
    start = time.time()
    response3 = client.post('/api/ats/analyze', headers=headers, json=data)
    t3 = time.time() - start
    res3 = response3.json.get('analysis', {})
    
    print(f"Time: {t3:.2f} seconds")
    print(f"Cache Used: {res3.get('cache_used')}")
    if res3.get('cache_used'):
        print("FAIL: Cache was incorrectly used after resume was updated.")
    else:
        print("PASS: Cache was successfully invalidated because hash changed.")
        
    # Restore original resume
    with app.app_context():
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE resumes SET resume_text = %s WHERE resume_id = 17", (original_resume_text,))
            conn.commit()
        conn.close()
        
    print("\n--- AUDIT LOGGING CHECK ---")
    print("Please verify the Flask console output for ATS_CACHE_MISS, ATS_CACHE_HIT, and ATS_CACHE_EXPIRED logs.")

if __name__ == "__main__":
    run_cache_tests()
