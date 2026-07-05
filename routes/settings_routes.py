from flask import Blueprint, render_template, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from config import get_db_connection

settings_bp = Blueprint("settings", __name__)

@settings_bp.get("/settings")
@jwt_required()
def settings_page():
    student_id = get_jwt_identity()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Get student
            cursor.execute("SELECT id, name, email, phone, created_at FROM students WHERE id=%s", (student_id,))
            student = cursor.fetchone()

            # Check if user has active resume
            cursor.execute("SELECT resume_id FROM resumes WHERE user_id=%s AND is_active=1", (student_id,))
            resume_row = cursor.fetchone()
            has_resume = resume_row is not None
            active_resume_id = resume_row['resume_id'] if resume_row else None

            # Unified Profile Strength Calculation
            from utils.profile_strength import calculate_profile_strength
            profile_data = calculate_profile_strength(student_id)
            total_profile_strength = profile_data['total_score']
            profile_categories = profile_data['categories']
            missing_items = profile_data['missing_items']

            # Fetch builder profile data for form
            cursor.execute("SELECT professional_summary, linkedin, github, portfolio, skills, achievements, education, experience FROM builder_profiles WHERE user_id=%s", (student_id,))
            builder_profile = cursor.fetchone() or {}
            
            import json
            for field in ['skills', 'education', 'achievements', 'experience']:
                if isinstance(builder_profile.get(field), str):
                    try:
                        builder_profile[field] = json.loads(builder_profile[field])
                    except:
                        builder_profile[field] = []

            # Fetch projects
            cursor.execute("SELECT * FROM user_projects WHERE user_id=%s", (student_id,))
            user_projects = cursor.fetchall()
            
            # Fetch certifications
            cursor.execute("SELECT * FROM certifications WHERE user_id=%s", (student_id,))
            user_certs = cursor.fetchall()

            # Fetch Resume Versions
            cursor.execute("SELECT * FROM resume_versions WHERE user_id=%s ORDER BY version_number DESC", (student_id,))
            resume_versions = cursor.fetchall()
            
            # Fetch Roadmaps
            cursor.execute("SELECT * FROM roadmaps WHERE user_id=%s ORDER BY id DESC", (student_id,))
            roadmaps = cursor.fetchall()

    finally:
        connection.close()

    return render_template(
        "settings.html", 
        active_page="settings", 
        page_title="My Profile",
        student=student,
        builder_profile=builder_profile,
        user_projects=user_projects,
        user_certs=user_certs,
        has_resume=has_resume,
        active_resume_id=active_resume_id,
        profile_categories=profile_categories,
        missing_items=missing_items,
        total_profile_strength=total_profile_strength,
        resume_versions=resume_versions,
        roadmaps=roadmaps
    )

@settings_bp.post("/api/profile/save")
@jwt_required()
def save_profile():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid payload"}), 400
        
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 1. Update Student details
            cursor.execute(
                "UPDATE students SET name=%s, phone=%s WHERE id=%s",
                (data.get('name', ''), data.get('phone', ''), user_id)
            )
            
            # 2. Update Builder Profile
            import json
            cursor.execute("""
                INSERT INTO builder_profiles (user_id, professional_summary, linkedin, github, portfolio, skills, education)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                professional_summary = VALUES(professional_summary),
                linkedin = VALUES(linkedin),
                github = VALUES(github),
                portfolio = VALUES(portfolio),
                skills = VALUES(skills),
                education = VALUES(education)
            """, (
                user_id,
                data.get('professional_summary', ''),
                data.get('linkedin', ''),
                data.get('github', ''),
                data.get('portfolio', ''),
                json.dumps(data.get('skills', [])),
                json.dumps(data.get('education', []))
            ))
            
            # 3. Update Projects
            cursor.execute("DELETE FROM user_projects WHERE user_id = %s", (user_id,))
            for p in data.get('projects', []):
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
                
            # 4. Update Certifications
            cursor.execute("DELETE FROM certifications WHERE user_id = %s", (user_id,))
            for c in data.get('certifications', []):
                raw_date = c.get('issue_date')
                valid_date = None
                if raw_date and str(raw_date).strip():
                    d_str = str(raw_date).strip()
                    import re
                    if re.match(r'^\d{4}-\d{2}-\d{2}$', d_str):
                        valid_date = d_str
                    elif re.match(r'^\d{4}-\d{2}$', d_str):
                        valid_date = f"{d_str}-01"
                    elif re.match(r'^\d{4}$', d_str):
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
                
        connection.commit()
        return jsonify({"message": "Profile saved successfully"}), 200
    except Exception as e:
        connection.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()


@settings_bp.route("/api/validate-entity", methods=["POST"])
@jwt_required()
def validate_entity():
    data = request.json
    entity_type = data.get("type")
    values = data.get("values", [])
    
    if not entity_type or not values:
        return jsonify({"error": "Missing type or values"}), 400
        
    from utils.gemini_helper import validate_entities
    
    # Batch validate all values
    results = validate_entities(entity_type, values)
    
    # results is a dict: { "value1": True, "value2": False }
    return jsonify({"results": results}), 200
