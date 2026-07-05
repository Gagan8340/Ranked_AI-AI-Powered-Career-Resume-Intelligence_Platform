import io
from app import create_app
from flask_jwt_extended import create_access_token
from config import get_db_connection

def test_upload():
    app = create_app()
    with app.test_client() as client:
        with app.app_context():
            conn = get_db_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id FROM students LIMIT 1")
                    student = cursor.fetchone()
                    if not student:
                        print("No student found to test")
                        return
                    student_id = student['id']
            finally:
                conn.close()
                
            token = create_access_token(identity=str(student_id))
            
            # create a dummy text file
            data = {
                'file': (io.BytesIO(b"John Doe\nSoftware Engineer\nPython, Java\n"), 'test_resume.txt')
            }
            
            headers = {
                'Authorization': f'Bearer {token}'
            }
            
            print(f"Testing upload for student {student_id}...")
            response = client.post('/api/resume/upload', data=data, headers=headers, content_type='multipart/form-data')
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.get_data(as_text=True)}")

if __name__ == '__main__':
    test_upload()
