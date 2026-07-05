import os
import re

file_path = r'd:\smartcampus\smartcampus-ai\routes\builder_routes.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Redirect /templates to /resume-builder
content = re.sub(
    r'@builder_bp\.route\(\'/templates\', methods=\\[\'GET\'\\]\)\n@jwt_required\(\)\ndef templates_page\(\):\n(?:.|\n)*?return render_template\(\"templates\.html\", has_resume=has_resume\)',
    '''@builder_bp.route('/templates', methods=['GET'])
@jwt_required()
def templates_page():
    from flask import redirect, url_for
    return redirect(url_for('builder.resume_builder_page'))''',
    content
)

# Replace get_builder_data
content = re.sub(
    r'@builder_bp\.route\(\'/api/builder/data\', methods=\\[\'GET\'\\]\)\n@jwt_required\(\)\ndef get_builder_data\(\):(.*?)(?=@builder_bp\.route)',
    '''@builder_bp.route('/api/builder/data', methods=['GET'])
@jwt_required()
def get_builder_data():
    \"\"\"Fetches the user's saved resume builder profile elements.\"\"\"
    user_id = get_jwt_identity()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT name, email, phone FROM students WHERE id = %s", (user_id,))
            student_info = cursor.fetchone()
            
            cursor.execute("SELECT * FROM builder_profiles WHERE user_id = %s", (user_id,))
            profile = cursor.fetchone() or {
                "professional_summary": "",
                "linkedin": "",
                "github": "",
                "portfolio": "",
                "skills": "[]",
                "achievements": "[]",
                "education": "[]",
                "experience": "[]",
                "hidden_sections": "{}"
            }
            
            import json
            if isinstance(profile.get('skills'), str):
                profile['skills'] = json.loads(profile['skills']) if profile['skills'] else []
            if isinstance(profile.get('achievements'), str):
                profile['achievements'] = json.loads(profile['achievements']) if profile['achievements'] else []
            if isinstance(profile.get('education'), str):
                profile['education'] = json.loads(profile['education']) if profile['education'] else []
            if isinstance(profile.get('experience'), str):
                profile['experience'] = json.loads(profile['experience']) if profile['experience'] else []
            if isinstance(profile.get('hidden_sections'), str):
                try:
                    profile['hidden_sections'] = json.loads(profile['hidden_sections']) if profile['hidden_sections'] else {}
                except:
                    profile['hidden_sections'] = {}
                
            cursor.execute("SELECT id, project_name, description, tech_stack, github_url, live_url FROM user_projects WHERE user_id = %s", (user_id,))
            projects = cursor.fetchall()
            
            cursor.execute("SELECT id, name, issuer, issue_date, certificate_url FROM certifications WHERE user_id = %s", (user_id,))
            certs = cursor.fetchall()
            
            cursor.execute(\"\"\"
                SELECT id, item_type, title, organization, associated_with, start_date, end_date, url, description, display_order, is_visible 
                FROM student_portfolio_items 
                WHERE user_id = %s 
                ORDER BY display_order ASC
            \"\"\", (user_id,))
            portfolio_items = cursor.fetchall()
            
            for item in portfolio_items:
                if item.get('start_date'): item['start_date'] = str(item['start_date'])
                if item.get('end_date'): item['end_date'] = str(item['end_date'])
            
            return jsonify({
                "student_info": student_info,
                "profile": profile,
                "projects": projects,
                "certifications": certs,
                "portfolio_items": portfolio_items
            }), 200
    finally:
        conn.close()

''', content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Phase 1 rewrite done')
