import json
from app import create_app

def test_health():
    app = create_app()
    with app.test_client() as client:
        response = client.get("/jd-analyzer/health", headers={"Authorization": "Bearer dummy_token"})
        print("Health Status:", response.status_code)
        print("Health Output:", response.json)
        assert response.status_code == 200
        assert response.json == {"status": "ok", "service": "jd_analyzer"}
        print("Health Check Passed!\n")

def test_analyze():
    app = create_app()
    with app.test_client() as client:
        data = {
            "jd_input_type": "text",
            "jd_text": "We are looking for a Software Engineer with 5 years of Python, React, and AWS experience. Must be good at microservices.",
            "resume_input_type": "text",
            "resume_text": "Experienced Software Engineer. I have worked with Python, Flask, React, and Kubernetes for 4 years."
        }
        print("Testing Analyze Endpoint with Text...")
        response = client.post("/jd-analyzer/analyze", data=data, headers={"Authorization": "Bearer dummy_token"})
        print("Analyze Status:", response.status_code)
        try:
            res_json = response.json
            print("Analyze Success! Keys:", list(res_json.keys()) if res_json else None)
            if response.status_code != 200:
                print("Error payload:", res_json)
        except Exception as e:
            print("Failed to parse JSON:", response.text)

if __name__ == "__main__":
    test_health()
    test_analyze()
