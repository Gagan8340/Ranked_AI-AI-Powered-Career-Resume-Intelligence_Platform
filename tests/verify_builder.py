import json
from app import create_app
from flask_jwt_extended import create_access_token
from config import get_db_connection

app = create_app()
app.testing = True

def run_verification():
    print("--- RESUME BUILDER VERIFICATION ---")
    
    with app.app_context():
        # Setup test user
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SET FOREIGN_KEY_CHECKS=0")
                cursor.execute("DELETE FROM builder_profiles WHERE user_id IN (SELECT id FROM students WHERE email='verify@test.com')")
                cursor.execute("DELETE FROM students WHERE email='verify@test.com'")
                cursor.execute("SET FOREIGN_KEY_CHECKS=1")
                
                cursor.execute("INSERT INTO students (name, email, password_hash, phone) VALUES ('Verify User', 'verify@test.com', 'hash', '123')")
                user_id = cursor.lastrowid
            conn.commit()
            
            token = create_access_token(identity=str(user_id))
            headers = {"Authorization": f"Bearer {token}"}
        finally:
            conn.close()

        with app.test_client() as client:
            print("\n1. Testing /templates route")
            res = client.get('/templates', headers=headers)
            print(f"   Status: {res.status_code} (Expected 200)")
            
            print("\n2. Testing /api/builder/data (Load)")
            res = client.get('/api/builder/data', headers=headers)
            print(f"   Status: {res.status_code} (Expected 200)")
            print(f"   Response Preview: {str(res.json)[:100]}...")
            
            print("\n3. Testing /api/builder/save (Autosave)")
            payload = {
                "profile": {"professional_summary": "Test Summary"},
                "projects": [],
                "certifications": [],
                "portfolio_items": []
            }
            res = client.post('/api/builder/save', json=payload, headers=headers)
            print(f"   Status: {res.status_code} (Expected 200)")
            print(f"   Response: {res.json}")
            
            print("\n4. Testing /api/resume/generate-pdf (Export PDF)")
            res = client.post('/api/resume/generate-pdf', json=payload, headers=headers)
            print(f"   Status: {res.status_code} (Expected 200)")
            print(f"   Content-Type: {res.content_type}")

if __name__ == '__main__':
    run_verification()
