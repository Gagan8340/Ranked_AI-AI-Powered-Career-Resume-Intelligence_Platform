import json
from app import create_app
from config import get_db_connection

def test_user_11():
    app = create_app()
    with app.app_context():
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Get user 11's resumes
            cursor.execute("SELECT resume_id, resume_text FROM resumes WHERE user_id = 11")
            resumes = cursor.fetchall()
            print(f"User 11 resumes: {len(resumes)}")
            
            if resumes:
                for r in resumes:
                    print(f"Resume ID: {r['resume_id']}")
                    text = r['resume_text']
                    if text:
                        print(f"Resume Text Length: {len(text)}")
                    else:
                        print(f"Resume Text is None!")
        conn.close()

if __name__ == "__main__":
    test_user_11()
