import time
import requests
from app import create_app, get_db_connection
from flask_jwt_extended import create_access_token
import json

def test_phase3():
    app = create_app()
    with app.app_context():
        token = create_access_token(identity="11")
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    client = app.test_client()
    resume_id = 17
    user_id = 11
    
    print("--- TASK 1: CLEANUP BEFORE TEST ---")
    with app.app_context():
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Clear existing skills and cache
            cursor.execute("UPDATE builder_profiles SET skills = '[]' WHERE user_id = %s", (user_id,))
            cursor.execute("DELETE FROM ats_cache WHERE user_id = %s", (user_id,))
            # Set a generic resume
            cursor.execute("UPDATE resumes SET resume_text = 'John Doe\\njohn@doe.com' WHERE resume_id = %s", (resume_id,))
            conn.commit()
        conn.close()
        
    print("--- TASK 2: APPLY SUGGESTIONS ---")
    data = {
        "resume_id": resume_id,
        "suggestions": [
            {"type": "skill", "value": "Docker"},
            {"type": "skill", "value": "Kubernetes"},
            {"type": "skill", "value": "Python"},
            {"type": "summary", "value": "Test summary addition"},
            {"type": "project", "value": "Test Kubernetes Project"},
            {"type": "certification", "value": "AWS Certified"}
        ]
    }
    
    response = client.post('/api/builder/apply-suggestions', headers=headers, json=data)
    res_data = response.json
    print(f"Apply API Status: {response.status_code}")
    print(f"Old Score: {res_data.get('old_score')}")
    print(f"New Score: {res_data.get('new_score')}")
    print(f"Improvement: {res_data.get('improvement')}")
    
    if res_data.get('improvement', 0) <= 0:
        print("FAIL: Improvement was not > 0")
    else:
        print("PASS: ATS score improved successfully!")
        
    print("--- TASK 3: VERIFY DATABASE MERGE ---")
    with app.app_context():
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT skills, professional_summary FROM builder_profiles WHERE user_id = %s", (user_id,))
            profile = cursor.fetchone()
            skills = json.loads(profile['skills'])
            print(f"Skills exactly match: {skills == ['Docker', 'Kubernetes', 'Python']} ({skills})")
            print(f"Summary updated: {'Test summary addition' in profile['professional_summary']}")
            
            cursor.execute("SELECT project_name FROM user_projects WHERE user_id = %s AND project_name = 'Test Kubernetes Project'", (user_id,))
            print(f"Project created: {cursor.fetchone() is not None}")
            
            cursor.execute("SELECT name FROM certifications WHERE user_id = %s AND name = 'AWS Certified'", (user_id,))
            print(f"Cert created: {cursor.fetchone() is not None}")
            
            # Ensure no duplicates
            client.post('/api/builder/apply-suggestions', headers=headers, json=data)
            cursor.execute("SELECT skills FROM builder_profiles WHERE user_id = %s", (user_id,))
            skills2 = json.loads(cursor.fetchone()['skills'])
            print(f"No duplicate skills after 2nd run: {len(skills2) == 3}")
            
            cursor.execute("SELECT COUNT(*) as c FROM user_projects WHERE user_id = %s AND project_name = 'Test Kubernetes Project'", (user_id,))
            print(f"No duplicate projects: {cursor.fetchone()['c'] == 1}")
            
        conn.close()

if __name__ == "__main__":
    test_phase3()
