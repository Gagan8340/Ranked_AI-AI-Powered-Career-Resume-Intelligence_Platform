from app import create_app
from flask_jwt_extended import create_access_token

app = create_app()

with app.test_request_context():
    access_token = create_access_token(identity="7")

with app.test_client() as client:
    client.set_cookie('access_token', access_token)
    response = client.get('/jd-analyzer')
    html = response.data.decode('utf-8')
    if "Sanagala" in html:
        print("SUCCESS! Sidebar rendered the actual user name.")
    else:
        print("FAIL! User name not found in the sidebar.")
        if "Student" in html:
            print("Found fallback text 'Student'.")
