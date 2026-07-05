import sys
import os
import json
sys.path.append(os.path.dirname(__file__))

from app import create_app
from config import get_db_connection

app = create_app()

with app.test_client() as client:
    # Cleanup before test
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT id FROM students WHERE email='test_verifier@example.com'")
        student = cursor.fetchone()
        if student:
            cursor.execute("DELETE FROM activity_logs WHERE user_id=%s", (student["id"],))
            cursor.execute("DELETE FROM students WHERE id=%s", (student["id"],))
    conn.commit()
    conn.close()

    print("1. Testing Registration")
    res = client.post('/auth/register', data={
        "name": "Test Verifier",
        "email": "test_verifier@example.com",
        "phone": "1234567890",
        "password": "Password123!",
        "no_resume": "on"
    })
    
    if res.status_code != 201:
        print("Registration failed!", res.status_code, res.get_data())
    else:
        print("Registration response:", res.get_json())
        assert res.get_json()["redirect"] == "/email-verification-pending"
        print("Redirect is correct.")
        
    print("\n2. Testing DB insertion")
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, email_verified, verification_token FROM students WHERE email='test_verifier@example.com'")
        student = cursor.fetchone()
        print("Student:", student)
        assert student["email_verified"] == 0
        assert student["verification_token"] is not None
        token = student["verification_token"]
    conn.close()
    
    print("\n3. Testing Login Blocked")
    res = client.post('/auth/login', json={
        "email": "test_verifier@example.com",
        "password": "Password123!"
    })
    print("Login response:", res.status_code, res.get_json())
    assert res.status_code == 403
    assert res.get_json()["is_unverified"] == True
    
    print("\n4. Testing Resend")
    res = client.post('/auth/resend-verification', json={"email": "test_verifier@example.com"})
    print("Resend response:", res.status_code, res.get_json())
    
    print("\n5. Testing Verify Email")
    res = client.get(f'/auth/verify-email/{token}')
    print("Verify response:", res.status_code, res.headers.get("Location"))
    assert res.status_code == 302
    assert "/email-verification-success" in res.headers.get("Location")
    
    print("\n6. Testing DB update")
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT email_verified, verification_token FROM students WHERE email='test_verifier@example.com'")
        student = cursor.fetchone()
        print("Student after verification:", student)
        assert student["email_verified"] == 1
        assert student["verification_token"] is None
    conn.close()

    print("\n7. Testing Login Success")
    res = client.post('/auth/login', json={
        "email": "test_verifier@example.com",
        "password": "Password123!"
    })
    print("Login response after verification:", res.status_code, res.get_json())
    assert res.status_code == 200

    print("\nAll tests passed!")
