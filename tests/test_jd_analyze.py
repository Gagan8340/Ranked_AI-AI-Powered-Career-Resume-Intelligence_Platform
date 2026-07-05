import json
from app import create_app
from config import get_db_connection
from flask_jwt_extended import create_access_token

def test_jd_route():
    app = create_app()
    with app.test_client() as client:
        with app.app_context():
            # Generate a token for user ID 11
            token = create_access_token(identity="11")
            
            # Find a valid resume for user 11 or insert one
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT resume_id FROM resumes WHERE user_id = 11 LIMIT 1")
                res = cursor.fetchone()
                if not res:
                    cursor.execute("INSERT INTO resumes (user_id, resume_text, title) VALUES (11, 'Experienced Software Engineer with Python and React skills.', 'My Resume')")
                    conn.commit()
                    resume_id = cursor.lastrowid
                else:
                    resume_id = res['resume_id']
            conn.close()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        data = {
            "resume_id": resume_id,
            "jd_text": "Software Engineer with Python, Flask, and React experience. Must have 5 years of experience."
        }
        
        response = client.post('/api/jd/analyze', headers=headers, json=data)
        print("Status Code:", response.status_code)
        try:
            print("Response:", response.json)
        except Exception:
            print("Response Text:", response.text)

if __name__ == "__main__":
    test_jd_route()
