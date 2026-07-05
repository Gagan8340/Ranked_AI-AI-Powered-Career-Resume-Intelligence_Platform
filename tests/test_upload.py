import io
from app import create_app
from config import get_db_connection

def run_test():
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()

    # 1. Create User directly in DB to ensure password works
    email = "real_upload_test@example.com"
    import bcrypt
    password = "password123"
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM students WHERE email = %s", (email,))
            row = cursor.fetchone()
            if row:
                user_id = row['id']
                cursor.execute("UPDATE students SET password_hash = %s WHERE id = %s", (hashed, user_id))
            else:
                cursor.execute(
                    "INSERT INTO students (name, email, password_hash) VALUES (%s, %s, %s)",
                    ("Test User", email, hashed)
                )
                user_id = cursor.lastrowid
            # clear previous resumes for this test user
            cursor.execute("DELETE FROM resumes WHERE user_id = %s", (user_id,))
        conn.commit()
    finally:
        conn.close()

    from unittest.mock import patch

    patcher1 = patch('routes.resume.validate_file', return_value=(True, None))
    patcher2 = patch('routes.resume.extract_resume_text', return_value=("Dummy text", False))
    patcher1.start()
    patcher2.start()

    print("--- 1. Login ---")
    response = client.post('/auth/login', json={
        "email": email,
        "password": password
    })
    print("Login Status:", response.status_code)
    
    # Check cookies
    cookies = response.headers.getlist('Set-Cookie')
    access_token_cookie = None
    for cookie in cookies:
        if 'access_token' in cookie:
            access_token_cookie = cookie
            print(f"Cookie Found: {cookie}")
            
    # Set cookie in client manually if needed, but test_client usually manages cookies automatically.
    # We will rely on test_client's automatic cookie handling which sends them in requests.

    print("\n--- 2. Upload PDF ---")
    dummy_pdf = io.BytesIO(b"%PDF-1.4\n" + b"dummy pdf content for testing " * 10)
    data = {
        'file': (dummy_pdf, 'test.pdf')
    }
    upload_res = client.post(
        '/api/resume/upload',
        data=data,
        content_type='multipart/form-data'
    )
    print("PDF Upload Status:", upload_res.status_code)
    try:
        print("Response JSON:", upload_res.get_json())
    except:
        print("Response Text:", upload_res.data)

    print("\n--- 3. Upload DOCX ---")
    dummy_docx = io.BytesIO(b"PK\x03\x04" + b"dummy docx content for testing " * 10)
    data2 = {
        'file': (dummy_docx, 'test.docx')
    }
    upload_res2 = client.post(
        '/api/resume/upload',
        data=data2,
        content_type='multipart/form-data'
    )
    print("DOCX Upload Status:", upload_res2.status_code)
    try:
        print("Response JSON:", upload_res2.get_json())
    except:
        print("Response Text:", upload_res2.data)

    # 4. Check DB for Rows
    print("\n--- 4. Verify DB Rows ---")
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM resumes WHERE user_id = %s", (user_id,))
            rows = cursor.fetchall()
            print(f"Found {len(rows)} resumes in DB for user {user_id}")
            for row in rows:
                print(f" - {row['filename']} ({row['resource_type']}) - Size: {row['file_size']}")
    finally:
        conn.close()

if __name__ == '__main__':
    run_test()

