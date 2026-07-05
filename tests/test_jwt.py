from app import create_app
app = create_app()
with app.test_client() as c:
    res = c.post("/auth/login", json={"email": "testuser6@example.com", "password": "password123"})
    print("LOGIN:", res.status_code)
    cookies = res.headers.getlist("Set-Cookie")
    print("SET-COOKIE:", cookies)
    res2 = c.get("/jd-analyzer")
    print("JD ANALYZER:", res2.status_code, res2.json)
