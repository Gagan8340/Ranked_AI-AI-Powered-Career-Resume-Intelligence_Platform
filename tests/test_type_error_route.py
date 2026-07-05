from app import create_app
from config import get_db_connection
from flask_jwt_extended import create_access_token

def test_type_error_in_route():
    app = create_app()
    with app.test_client() as client:
        with app.app_context():
            token = create_access_token(identity="11")
            
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        data = {
            "resume_id": 17,
            "jd_text": "We are looking for a Senior Software Engineer with strong Python and Flask skills. The ideal candidate will have at least 5 years of experience." * 2
        }
        
        # Patch the jd_routes directly!
        from routes import jd_routes
        def fake_analyze(*args, **kwargs):
            return {
                "job_title": "Test Role",
                "ats_score": 50,
                "missing_keywords": None
            }
        jd_routes.analyze_jd_match = fake_analyze
        
        print("Sending request...")
        response = client.post('/api/jd/analyze', headers=headers, json=data)
        print("Status Code:", response.status_code)
        try:
            print("Response:", response.json)
        except Exception:
            print("Response Text:", response.text)

if __name__ == "__main__":
    test_type_error_in_route()
