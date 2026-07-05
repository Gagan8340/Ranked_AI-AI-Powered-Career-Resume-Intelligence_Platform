import json
import logging
from app import create_app
from flask_jwt_extended import create_access_token

logging.basicConfig(level=logging.INFO)

def test_intelligence():
    print("--- TASK 1: AUTHENTICATE ---")
    app = create_app()
    with app.app_context():
        token = create_access_token(identity="11")
        
    client = app.test_client()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # We will use resume_id = 17, and a sample JD
    jd_text = "Looking for a Senior Backend Developer with expertise in Docker, Kubernetes, AWS, and CI/CD pipelines. Must know system design and microservices."
    
    print("\n--- TASK 2: GAP ANALYSIS (MISS) ---")
    res1 = client.post("/api/intelligence/gap-analysis", json={
        "resume_id": 17,
        "jd_text": jd_text
    }, headers=headers)
    
    data1 = res1.json
    print(f"Status: {res1.status_code}")
    print(f"Readiness Score: {data1.get('readiness_score')}")
    print(f"Intelligence Score: {data1.get('intelligence_score')}")
    
    gap = data1.get("gap_analysis", {})
    priority_skills = gap.get("priority_skills", [])
    print(f"Priority Skills: {priority_skills}")
    
    if res1.status_code != 200 or not priority_skills:
        print("FAIL: Gap analysis generation failed.")
        return
    print("PASS: Gap analysis generated successfully.")
    
    import time
    print("\n--- TASK 3: GAP ANALYSIS (HIT) ---")
    start = time.time()
    res2 = client.post("/api/intelligence/gap-analysis", json={
        "resume_id": 17,
        "jd_text": jd_text
    }, headers=headers)
    elapsed = time.time() - start
    
    if elapsed < 0.2:
        print(f"PASS: Gap analysis served rapidly from cache ({elapsed}s)")
    else:
        print(f"FAIL: Cache might not be working. ({elapsed}s)")
        
    print("\n--- TASK 4: ROADMAP GENERATION (MISS) ---")
    res3 = client.post("/api/intelligence/roadmap", json={
        "resume_id": 17,
        "jd_text": jd_text,
        "priority_skills": priority_skills
    }, headers=headers)
    
    data3 = res3.json
    print(f"Status: {res3.status_code}")
    if res3.status_code == 200 and data3.get('roadmap'):
        print("PASS: Roadmap generated.")
        print(f"Week 1 Title: {data3['roadmap'].get('week_1', {}).get('title')}")
    else:
        print("FAIL: Roadmap generation failed.")
        
    print("\n--- TASK 5: ROADMAP GENERATION (HIT) ---")
    start = time.time()
    res4 = client.post("/api/intelligence/roadmap", json={
        "resume_id": 17,
        "jd_text": jd_text,
        "priority_skills": priority_skills
    }, headers=headers)
    elapsed = time.time() - start
    
    if elapsed < 0.2:
        print(f"PASS: Roadmap served rapidly from cache ({elapsed}s)")
    else:
        print(f"FAIL: Cache might not be working. ({elapsed}s)")
        

if __name__ == "__main__":
    test_intelligence()
