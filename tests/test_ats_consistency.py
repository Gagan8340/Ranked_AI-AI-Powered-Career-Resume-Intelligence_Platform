from app import create_app
from flask_jwt_extended import create_access_token
import utils.gemini_helper

def mock_analyze_ats_qualitative(resume_text, jd_text=None):
    return {
        "strengths": ["Test strength"],
        "weaknesses": ["Test weakness"],
        "recommendations": ["Test recommendation"],
        "missing_keywords": ["Test missing"]
    }

utils.gemini_helper.analyze_ats_qualitative = mock_analyze_ats_qualitative

def run_consistency_test():
    app = create_app()
    with app.test_client() as client:
        with app.app_context():
            token = create_access_token(identity="11")
            
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # User 11 has resume_id 17
        data = {
            "resume_id": 17,
            "jd_text": "Software Engineer python flask."
        }
        
        results = []
        for i in range(1):
            print(f"Run {i+1}...")
            response = client.post('/api/ats/analyze', headers=headers, json=data)
            if response.status_code == 200:
                results.append(response.json['analysis'])
            else:
                print(f"Failed: {response.text}")
                return
                
        base = results[0]
        print("Scores:", base['overall_score'])
        print("Formatting:", base['breakdown']['formatting']['score'])
        print("Readability:", base['breakdown']['readability']['score'])
        print("Section:", base['breakdown']['section']['score'])
        print("Keyword:", base['breakdown']['keyword']['score'])
        import json
        print("Sample JSON Response:")
        print(json.dumps(base, indent=2))

if __name__ == "__main__":
    run_consistency_test()
