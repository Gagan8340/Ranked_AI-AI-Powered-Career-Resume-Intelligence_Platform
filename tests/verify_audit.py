import os
import json
from io import BytesIO
import jwt
from datetime import datetime, timedelta, timezone

os.environ['GEMINI_API_KEY'] = 'dummy_api_key'
os.environ['JWT_SECRET_KEY'] = 'dummy_jwt_secret_which_is_at_least_sixty_four_characters_long_for_security_purposes'

from app import create_app
from config import get_db_connection

def create_test_user(app):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Check if test user exists
            cursor.execute("SELECT id FROM students WHERE email = 'audit_test@example.com'")
            user = cursor.fetchone()
            if user:
                user_id = user['id']
            else:
                import uuid
                email = f'audit_test_{uuid.uuid4().hex[:8]}@example.com'
                cursor.execute("INSERT INTO students (name, email, password_hash, phone) VALUES (%s, %s, %s, %s)",
                               ('Audit Test', email, 'hashed_pass', '1234567890'))
                user_id = cursor.lastrowid
                
            # Setup builder profile data
            cursor.execute("REPLACE INTO builder_profiles (user_id, professional_summary, skills, achievements) VALUES (%s, %s, %s, %s)",
                           (user_id, 'Experienced software engineer.', 'Python, Flask, React', 'Built a great app.'))
            conn.commit()
            return user_id
    finally:
        conn.close()

def generate_test_token(app, user_id):
    # Create a valid JWT token
    with app.app_context():
        from flask_jwt_extended import create_access_token
        token = create_access_token(identity=str(user_id))
        return token

from unittest.mock import patch

class MockGenerateContentResponse:
    def __init__(self, text):
        self.text = text

def mock_generate_content(*args, **kwargs):
    return MockGenerateContentResponse('{"ats_score": 85, "missing_keywords": ["Python"], "job_title": "Developer"}')

def run_audit():
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()
    
    user_id = create_test_user(app)
    token = generate_test_token(app, user_id)
    headers = {'Authorization': f'Bearer {token}'}
    client.set_cookie('access_token', token, domain='localhost')
    
    results = {}
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        patcher = patch('utils.gemini_helper.client.models.generate_content', side_effect=mock_generate_content)
        patcher.start()
        
        # UI ROUTES TEST
        print("TEST UI: Dashboard")
        res_ui1 = client.get('/dashboard/')
        results['ui_dashboard'] = res_ui1.status_code
        if res_ui1.status_code != 200: print(f"Dashboard failed: {res_ui1.status_code}")
        
        print("TEST UI: JD Analyzer")
        res_ui2 = client.get('/jd-analyzer')
        results['ui_jd_analyzer'] = res_ui2.status_code
        
        print("TEST UI: Resume Optimizer")
        res_ui3 = client.get('/resume-optimizer')
        results['ui_optimizer'] = res_ui3.status_code
        
        print("TEST UI: Resume Builder")
        res_ui4 = client.get('/resume-builder')
        results['ui_builder'] = res_ui4.status_code
        
        print("TEST UI: Cover Letters")
        res_ui5 = client.get('/cover-letters')
        results['ui_cover_letters'] = res_ui5.status_code
        
        print("TEST UI: Settings")
        res_ui6 = client.get('/settings')
        results['ui_settings'] = res_ui6.status_code

        # API TESTS
        print("TEST 1: Builder save-to-resumes")
        res1 = client.post('/api/resume/builder/save-to-resumes', headers=headers)
        results['test1_status'] = res1.status_code
        if res1.status_code != 200: results['test1_err'] = res1.get_data(as_text=True)
        cursor.execute("SELECT * FROM resumes WHERE user_id = %s ORDER BY uploaded_at DESC LIMIT 1", (user_id,))
        builder_resume = cursor.fetchone()
        results['test1_db_row'] = builder_resume
        
        # TEST 2: Builder PDF
        print("TEST 2: Builder generate-pdf")
        res2 = client.post('/api/resume/generate-pdf', headers=headers)
        results['test2_status'] = res2.status_code
        if res2.status_code != 200: results['test2_err'] = res2.get_data(as_text=True)
        results['test2_content_type'] = res2.content_type
        
        # TEST 3: Builder DOCX
        print("TEST 3: Builder generate-docx")
        res3 = client.post('/api/resume/builder/generate-docx', headers=headers)
        results['test3_status'] = res3.status_code
        if res3.status_code != 200: results['test3_err'] = res3.get_data(as_text=True)
        results['test3_content_type'] = res3.content_type
        
        # TEST 4: Resume Upload (Path A) - PDF
        print("TEST 4: Resume Upload PDF")
        with patch('routes.resume.validate_file', return_value=(True, None)):
            with patch('routes.resume.extract_resume_text', return_value=("This is a dummy resume text that is long enough to bypass the scanner check. " * 5, False)):
                dummy_pdf = BytesIO(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF")
                res4 = client.post('/api/resume/upload', headers=headers, data={
                    'file': (dummy_pdf, 'test_upload.pdf')
                }, content_type='multipart/form-data')
                results['test4_status'] = res4.status_code
                if res4.status_code != 200: results['test4_err'] = res4.get_data(as_text=True)
                cursor.execute("SELECT * FROM resumes WHERE user_id = %s AND filename = 'test_upload.pdf' ORDER BY uploaded_at DESC LIMIT 1", (user_id,))
                uploaded_resume = cursor.fetchone()
                results['test4_db_row'] = uploaded_resume
        
        # TEST 5: Resume List
        print("TEST 5: Resume List")
        res5 = client.get('/api/resume/list', headers=headers)
        results['test5_status'] = res5.status_code
        if res5.status_code == 200:
            results['test5_count'] = len(res5.get_json().get('resumes', []))
        else:
            results['test5_err'] = res5.get_data(as_text=True)
            
        # TEST 6: JD Analyzer (Builder Resume)
        print("TEST 6: JD Analyzer")
        if builder_resume:
            long_jd = "Looking for a highly skilled Python Developer with extensive Flask and React experience. Must have 5 years of industry experience and a strong background in software engineering. " * 3
            res6 = client.post('/api/jd/analyze', headers=headers, json={
                'resume_id': builder_resume['resume_id'],
                'jd_text': long_jd
            })
            results['test6_status'] = res6.status_code
            if res6.status_code != 200: results['test6_err'] = res6.get_data(as_text=True)
            cursor.execute("SELECT * FROM job_descriptions WHERE user_id = %s ORDER BY created_at DESC LIMIT 1", (user_id,))
            jd_row = cursor.fetchone()
            results['test6_db_row'] = jd_row
            
        # TEST 7: Resume Optimizer
        print("TEST 7: Resume Optimizer")
        if builder_resume and 'jd_row' in locals() and jd_row:
            res7 = client.post('/api/resume/optimize', headers=headers, json={
                'resume_id': builder_resume['resume_id'],
                'jd_id': jd_row['id']
            })
            results['test7_status'] = res7.status_code
            if res7.status_code != 200: results['test7_err'] = res7.get_data(as_text=True)
            cursor.execute("SELECT * FROM resume_versions WHERE original_resume_id = %s ORDER BY created_at DESC LIMIT 1", (builder_resume['resume_id'],))
            opt_row = cursor.fetchone()
            results['test7_db_row'] = opt_row
            
        # TEST 8: Cover Letter Generator
        print("TEST 8: Cover Letter Generator")
        if builder_resume and 'jd_row' in locals() and jd_row:
            res8 = client.post('/api/cover-letter/generate', headers=headers, json={
                'resume_id': builder_resume['resume_id'],
                'jd_id': jd_row['id'],
                'role_title': 'Developer',
                'company_name': 'Tech Corp'
            })
            results['test8_status'] = res8.status_code
            if res8.status_code != 200: results['test8_err'] = res8.get_data(as_text=True)
            cursor.execute("SELECT * FROM cover_letters WHERE resume_id = %s ORDER BY created_at DESC LIMIT 1", (builder_resume['resume_id'],))
            cl_row = cursor.fetchone()
            results['test8_db_row'] = cl_row

    except Exception as e:
        import traceback
        results['exception'] = traceback.format_exc()
        print("Exception:", traceback.format_exc())
    finally:
        conn.close()
        
    with open('data/audit_results.json', 'w') as f:
        json.dump(results, f, default=str, indent=4)
        
    print("Audit Complete. Check data/audit_results.json")

if __name__ == "__main__":
    run_audit()
