import os
import sys

# Ensure dummy auth doesn't get rejected
os.environ['TEST_MODE'] = '1'

# We mock gemini completely. If any code tries to import it and call it, it will fail.
import sys
sys.modules['google.generativeai'] = None

from app import create_app
from config import get_db_connection

def test_migration():
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()

    print("--- Testing /api/jd/analyze ---")
    
    # We need a user and a resume in DB.
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get an existing resume
            cursor.execute("SELECT user_id, resume_id FROM resumes WHERE is_active = 1 LIMIT 1")
            row = cursor.fetchone()
            if row:
                user_id = row['user_id']
                resume_id = row['resume_id']
            else:
                print("No resumes found in DB to test with.")
                return
    except Exception as e:
        print("DB query failed:", e)
        return
    finally:
        conn.close()

    # Create dummy JWT (mocking get_jwt_identity)
    from flask_jwt_extended import create_access_token
    with app.app_context():
        token = create_access_token(identity=str(user_id))
        
        # Test 1: JD Analyze
        jd_text = "We are looking for a Senior Software Engineer with strong Python, AWS, and Docker skills. 5+ years experience required. Bachelor's degree."
        
        response = client.post('/api/jd/analyze', 
                               json={'resume_id': resume_id, 'jd_text': jd_text},
                               headers={'Authorization': f'Bearer {token}'})
        
        print(f"JD Analyze Status: {response.status_code}")
        data = response.get_json()
        print(f"JD Analyze Keys: {list(data.get('analysis', {}).keys())}")
        jd_id = data.get('jd_id')
        print(f"JD ID returned: {jd_id}")
        assert 'ats_score' in data['analysis']
        assert 'missing_skills' in data['analysis']
        
        # Test 2: Gap Analysis
        response2 = client.post('/api/intelligence/gap-analysis', 
                               json={'resume_id': resume_id, 'jd_text': jd_text},
                               headers={'Authorization': f'Bearer {token}'})
        
        print(f"Gap Analysis Status: {response2.status_code}")
        data2 = response2.get_json()
        print(f"Gap Analysis Readiness Score: {data2.get('readiness_score')}")
        print(f"Gap Analysis Keys: {list(data2.get('gap_analysis', {}).keys())}")
        
        # Test 3: Roadmap Generation
        response3 = client.post('/api/intelligence/roadmap', 
                               json={'resume_id': resume_id, 'jd_text': jd_text, 'jd_id': jd_id, 'priority_skills': ['Docker']},
                               headers={'Authorization': f'Bearer {token}'})
        
        print(f"Roadmap Status: {response3.status_code}")
        data3 = response3.get_json()
        print(f"Roadmap Generated ID: {data3.get('roadmap_id')}")

if __name__ == '__main__':
    test_migration()
