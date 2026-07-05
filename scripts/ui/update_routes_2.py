import os

file_path = r'd:\smartcampus\smartcampus-ai\routes\builder_routes.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = "@builder_bp.route('/api/builder/save', methods=['POST'])"
end_marker = "@builder_bp.route('/api/builder/preview', methods=['POST'])"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

new_save_func = '''@builder_bp.route('/api/builder/save', methods=['POST'])
@jwt_required()
def save_builder_data():
    """Auto-saves changes when the user switches tabs to prevent data loss."""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Invalid payload"}), 400
        
    profile = data.get('profile', {})
    projects = data.get('projects', [])
    certs = data.get('certifications', [])
    portfolio_items = data.get('portfolio_items', [])
    
    import json
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Upsert Profile Data
            cursor.execute("""
                INSERT INTO builder_profiles (user_id, professional_summary, linkedin, github, portfolio, skills, achievements, education, experience, hidden_sections)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                professional_summary = VALUES(professional_summary),
                linkedin = VALUES(linkedin),
                github = VALUES(github),
                portfolio = VALUES(portfolio),
                skills = VALUES(skills),
                achievements = VALUES(achievements),
                education = VALUES(education),
                experience = VALUES(experience),
                hidden_sections = VALUES(hidden_sections)
            """, (
                user_id,
                profile.get('professional_summary', ''),
                profile.get('linkedin', ''),
                profile.get('github', ''),
                profile.get('portfolio', ''),
                json.dumps(profile.get('skills', [])),
                json.dumps(profile.get('achievements', [])),
                json.dumps(profile.get('education', [])),
                json.dumps(profile.get('experience', [])),
                json.dumps(profile.get('hidden_sections', {}))
            ))
            
            # 2. Resync Projects
            cursor.execute("DELETE FROM user_projects WHERE user_id = %s", (user_id,))
            for p in projects:
                cursor.execute("""
                    INSERT INTO user_projects (user_id, project_name, description, tech_stack, github_url, live_url)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    p.get('project_name', ''),
                    p.get('description', ''),
                    p.get('tech_stack', ''),
                    p.get('github_url', ''),
                    p.get('live_url', '')
                ))
                
            # 3. Resync Certifications
            cursor.execute("DELETE FROM certifications WHERE user_id = %s", (user_id,))
            for c in certs:
                raw_date = c.get('issue_date')
                valid_date = None
                if raw_date and str(raw_date).strip():
                    d_str = str(raw_date).strip()
                    import re as regex
                    if regex.match(r'^\d{4}-\d{2}-\d{2}$', d_str):
                        valid_date = d_str
                    elif regex.match(r'^\d{4}-\d{2}$', d_str):
                        valid_date = f"{d_str}-01"
                    elif regex.match(r'^\d{4}$', d_str):
                        valid_date = f"{d_str}-01-01"

                cursor.execute("""
                    INSERT INTO certifications (user_id, name, issuer, issue_date, certificate_url)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    user_id,
                    c.get('name', ''),
                    c.get('issuer') or None,
                    valid_date,
                    c.get('certificate_url') or None
                ))
                
            # 4. Resync Portfolio Items
            cursor.execute("DELETE FROM student_portfolio_items WHERE user_id = %s", (user_id,))
            for i, item in enumerate(portfolio_items):
                cursor.execute("""
                    INSERT INTO student_portfolio_items 
                    (user_id, item_type, title, organization, associated_with, start_date, end_date, url, description, display_order, is_visible)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    item.get('item_type', 'EXTRACURRICULAR'),
                    item.get('title', ''),
                    item.get('organization', ''),
                    item.get('associated_with', ''),
                    item.get('start_date') or None,
                    item.get('end_date') or None,
                    item.get('url', ''),
                    item.get('description', ''),
                    item.get('display_order', i),
                    int(item.get('is_visible', 1))
                ))
                
        conn.commit()
        return jsonify({"message": "Auto-saved successfully"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

'''

new_content = content[:start_idx] + new_save_func + content[end_idx:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Phase 2 rewrite done')
