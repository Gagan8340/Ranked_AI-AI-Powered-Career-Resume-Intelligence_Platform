import sys
from app import create_app
from flask_jwt_extended import create_access_token
app = create_app()

with app.test_request_context():
    # create token for user 7
    access_token = create_access_token(identity="7")

with app.test_client() as client:
    # Set the JWT cookie
    client.set_cookie('access_token', access_token)
    response = client.get('/dashboard', follow_redirects=True)
    print("Status:", response.status_code)
    html = response.data.decode('utf-8')
    print("HTML Length:", len(html))
    if "atsChart" in html:
        print("Chart canvas found.")
    else:
        print("Chart canvas NOT found.")
        
    if "ats-data" in html:
        print("ats-data found.")
        # extract the ats-data
        start = html.find('<script id="ats-data" type="application/json">')
        end = html.find('</script>', start)
        print("Data:", html[start:end+9])
    else:
        print("ats-data NOT found.")
        if "No ATS scans available yet" in html:
             print("Empty state found.")
