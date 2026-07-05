import requests

# 1. Login to get token
login_data = {
    "email": "test@example.com",
    "password": "password123"
}
# wait, the user's login is unknown. Let's just create a token using flask-jwt-extended!
from app import create_app
from flask_jwt_extended import create_access_token

app = create_app()
with app.app_context():
    token = create_access_token(identity="27") # from logs: AUTH: JWT Identity = 27
    
    # 2. Make request to the endpoint using the test client
    client = app.test_client()
    response = client.get('/api/latex/template/01_Google_SWE', headers={
        'Authorization': f'Bearer {token}'
    })
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.get_json()
        print(f"ID: {data.get('id')}")
        print(f"Has PDF: {data.get('has_default_pdf')}")
        print(f"PDF URL: {data.get('pdf_url')}")
        print(f"Content Length: {len(data.get('content', ''))}")
    else:
        print(f"Error: {response.get_data(as_text=True)}")
