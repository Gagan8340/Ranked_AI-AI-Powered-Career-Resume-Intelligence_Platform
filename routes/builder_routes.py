import json
import io
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
import uuid

from config import get_db_connection
from utils.pdf_generator import generate_ats_pdf
from utils.docx_generator import generate_ats_docx

builder_bp = Blueprint('builder', __name__)

# -------------------------
# UI ROUTES
# -------------------------
@builder_bp.route('/templates', methods=['GET'])
@jwt_required()
def templates_page():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    has_resume = False
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM resumes WHERE user_id=%s", (user_id,))
            res = cursor.fetchone()
            has_resume = res['count'] > 0 if res else False
    except Exception:
        has_resume = False
    finally:
        conn.close()
    return render_template("templates.html", has_resume=has_resume)

@builder_bp.route('/template-editor/<template_id>', methods=['GET'])
@jwt_required()
def template_editor_page(template_id):
    user_id = get_jwt_identity()
    conn = get_db_connection()
    has_resume = False
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM resumes WHERE user_id=%s", (user_id,))
            res = cursor.fetchone()
            has_resume = res['count'] > 0 if res else False
    except Exception:
        has_resume = False
    finally:
        conn.close()
    return render_template("template_editor.html", has_resume=has_resume, template_id=template_id)



# -------------------------
# API ENDPOINTS
# -------------------------
@builder_bp.route('/api/builder/data', methods=['GET'])
@jwt_required()
def get_builder_data():
    """Fetches the user's saved resume builder profile elements."""
    user_id = get_jwt_identity()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Base User info from Students table (read-only for builder)
            cursor.execute("SELECT name, email, phone FROM students WHERE id = %s", (user_id,))
            student_info = cursor.fetchone()
            
            # 2. Builder Profile
            cursor.execute("SELECT * FROM builder_profiles WHERE user_id = %s", (user_id,))
            profile = cursor.fetchone() or {
                "professional_summary": "",
                "linkedin": "",
                "github": "",
                "portfolio": "",
                "skills": "[]",
                "achievements": "[]",
                "education": "[]",
                "experience": "[]"
            }
            
            # Safely parse JSON strings stored in DB back to arrays
            if isinstance(profile.get('skills'), str):
                profile['skills'] = json.loads(profile['skills']) if profile['skills'] else []
            if isinstance(profile.get('achievements'), str):
                profile['achievements'] = json.loads(profile['achievements']) if profile['achievements'] else []
            if isinstance(profile.get('education'), str):
                profile['education'] = json.loads(profile['education']) if profile['education'] else []
            if isinstance(profile.get('experience'), str):
                profile['experience'] = json.loads(profile['experience']) if profile['experience'] else []
                
            # 3. Projects list
            cursor.execute("SELECT id, project_name, description, tech_stack, github_url, live_url FROM user_projects WHERE user_id = %s", (user_id,))
            projects = cursor.fetchall()
            
            # 4. Certifications list
            cursor.execute("SELECT id, name, issuer, issue_date, certificate_url FROM certifications WHERE user_id = %s", (user_id,))
            certs = cursor.fetchall()
            
            # 5. Portfolio Items
            cursor.execute("SELECT * FROM student_portfolio_items WHERE user_id = %s ORDER BY display_order ASC", (user_id,))
            portfolio_items = cursor.fetchall()
            
            return jsonify({
                "student_info": student_info,
                "profile": profile,
                "projects": projects,
                "certifications": certs,
                "portfolio_items": portfolio_items
            }), 200
    finally:
        conn.close()


@builder_bp.route('/api/builder/save', methods=['POST'])
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

@builder_bp.route('/api/builder/score', methods=['POST'])
@jwt_required()
def score_builder_data():
    """Converts the frontend JSON state into text and calculates ATS score via backend engine."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid payload"}), 400
        
    try:
        from utils.ats_engine import evaluate_resume
        user_id = get_jwt_identity()
        
        # Extract data
        user_data = data.get('student_info', {})
        profile = data.get('profile', {})
        projects = data.get('projects', [])
        
        # Rebuild text
        text_lines = []
        if user_data.get('name'): text_lines.append(user_data['name'])
        if user_data.get('email'): text_lines.append(user_data['email'])
        
        if profile.get('professional_summary'):
            text_lines.append("SUMMARY: " + profile['professional_summary'])
        
        skills = profile.get('skills', [])
        if isinstance(skills, str):
            import json
            try: skills = json.loads(skills)
            except: skills = []
        if skills:
            text_lines.append("SKILLS: " + ", ".join(skills))
            
        experience = profile.get('experience', [])
        if isinstance(experience, str):
            import json
            try: experience = json.loads(experience)
            except: experience = []
        for exp in experience:
            if isinstance(exp, dict):
                text_lines.append(f"EXPERIENCE: {exp.get('role', '')} at {exp.get('company', '')} - {exp.get('description', '')}")
            else:
                text_lines.append(f"EXPERIENCE: {exp}")
                
        for p in projects:
            text_lines.append(f"PROJECT: {p.get('project_name', '')} - {p.get('description', '')}")
            
        resume_text = "\n".join(text_lines)
        
        # Calculate Score
        score_data = evaluate_resume(resume_text, "")
        
        # Score logic calculated, no ATS history logging for builder interactions
        return jsonify({
            "score": score_data.get('overall_score', 0),
            "breakdown": score_data.get('breakdown', {})
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@builder_bp.route('/api/resume/generate-pdf', methods=['POST'])
@jwt_required()
def generate_pdf_endpoint():
    """Generates PDF directly from the database persisted builder profile."""
    user_id = get_jwt_identity()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT name, email, phone FROM students WHERE id = %s", (user_id,))
            user_data = cursor.fetchone() or {}
            
            cursor.execute("SELECT * FROM builder_profiles WHERE user_id = %s", (user_id,))
            profile_data = cursor.fetchone() or {}
            
            # Parse JSON fields safely
            import json
            for field in ['skills', 'education', 'experience', 'achievements', 'hidden_sections']:
                if isinstance(profile_data.get(field), str):
                    try: profile_data[field] = json.loads(profile_data[field])
                    except: profile_data[field] = [] if field != 'hidden_sections' else {}
            
            cursor.execute("SELECT project_name, description, tech_stack FROM user_projects WHERE user_id = %s", (user_id,))
            projects = cursor.fetchall()
            
            cursor.execute("SELECT name, issuer, issue_date FROM certifications WHERE user_id = %s", (user_id,))
            certs = cursor.fetchall()
            
            cursor.execute("SELECT * FROM student_portfolio_items WHERE user_id = %s ORDER BY display_order ASC", (user_id,))
            portfolio_items = cursor.fetchall()
            
        from utils.pdf_generator import generate_ats_pdf
        pdf_bytes = generate_ats_pdf(user_data, profile_data, projects, certs, portfolio_items)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"resume_{timestamp}.pdf"
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@builder_bp.route('/api/resume/builder/generate-docx', methods=['POST'])
@jwt_required()
def generate_docx_endpoint():
    """Generates DOCX from builder JSON state."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid payload"}), 400
        
    user_data = data.get('student_info', {})
    profile_data = data.get('profile', {})
    projects = data.get('projects', [])
    certs = data.get('certifications', [])
    template_id = data.get('template_id', 'tpl_prof_03')
    
    try:
        from utils.docx_generator import generate_ats_docx
        docx_bytes = generate_ats_docx(user_data, profile_data, projects, certs, template_id)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"resume_{timestamp}.docx"
        
        return send_file(
            io.BytesIO(docx_bytes),
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@builder_bp.route('/api/resume/builder/save-to-resumes', methods=['POST'])
@jwt_required()
def save_builder_to_resumes():
    """Saves the current builder profile into the resumes table as a text resume."""
    user_id = get_jwt_identity()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT name, email, phone FROM students WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
            if not user_data:
                return jsonify({"error": "Student account not found"}), 404
                
            cursor.execute("SELECT * FROM builder_profiles WHERE user_id = %s", (user_id,))
            profile_data = cursor.fetchone() or {}
            
            cursor.execute("SELECT project_name, description, tech_stack, github_url, live_url FROM user_projects WHERE user_id = %s", (user_id,))
            projects = cursor.fetchall()
            
            cursor.execute("SELECT name, issuer, issue_date, certificate_url FROM certifications WHERE user_id = %s", (user_id,))
            certs = cursor.fetchall()
            
            # Format text
            text_lines = []
            text_lines.append(user_data.get('name', ''))
            text_lines.append(user_data.get('email', ''))
            
            if profile_data.get('professional_summary'):
                text_lines.append("SUMMARY: " + profile_data['professional_summary'])
            if profile_data.get('skills'):
                text_lines.append("SKILLS: " + profile_data['skills'])
            if profile_data.get('achievements'):
                text_lines.append("EXPERIENCE: " + profile_data['achievements'])
                
            for p in projects:
                text_lines.append(f"PROJECT: {p.get('project_name')} - {p.get('description')}")
            for c in certs:
                text_lines.append(f"CERT: {c.get('name')}")
                
            resume_text = "\n".join(text_lines)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"builder_resume_{timestamp}.docx"
            public_id = f"local:{uuid.uuid4().hex}_{filename}"
            
            cursor.execute(
                """
                INSERT INTO resumes (user_id, filename, cloudinary_public_id, resource_type, file_size, resume_text)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, filename, public_id, 'docx', len(resume_text), resume_text)
            )
            
            # Create a mock physical file just so local download doesn't crash 404
            import os
            from flask import current_app
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], public_id.split('local:')[1])
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(resume_text)
                
            cursor.execute(
                "INSERT INTO notifications (student_id, message, type) VALUES (%s, %s, %s)",
                (user_id, "Builder profile saved to resumes successfully.", "success")
            )
            conn.commit()
        return jsonify({"message": "Successfully saved to Resumes"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@builder_bp.route('/api/builder/apply-suggestions', methods=['POST'])
@jwt_required()
def apply_suggestions():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or 'suggestions' not in data:
        return jsonify({"error": "Invalid payload"}), 400
        
    resume_id = data.get('resume_id')
    jd_id = data.get('jd_id')
    
    if not resume_id or not jd_id:
        return jsonify({"error": "resume_id and jd_id required"}), 400
        
    suggestions = data['suggestions']
    if not isinstance(suggestions, list):
        return jsonify({"error": "suggestions must be a list"}), 400
        
    conn = get_db_connection()
    try:
        from utils.ats_engine import evaluate_resume
        
        with conn.cursor() as cursor:
            # 1. Verify ownership and get old resume text
            cursor.execute("SELECT resume_text FROM resumes WHERE resume_id = %s AND user_id = %s AND is_active = 1", (resume_id, user_id))
            resume_record = cursor.fetchone()
            if not resume_record:
                return jsonify({"error": "Resume not found or unauthorized"}), 404
                
            old_resume_text = resume_record['resume_text']
            
            # Fetch jd_text for ATS scoring context
            cursor.execute("SELECT jd_text FROM job_descriptions WHERE id = %s AND user_id = %s", (jd_id, user_id))
            jd_record = cursor.fetchone()
            jd_text = jd_record['jd_text'] if jd_record else None
            
            # 2. Calculate old ATS score
            old_score_data = evaluate_resume(old_resume_text, jd_text)
            old_score = old_score_data.get('overall_score', 0)
            old_breakdown = old_score_data.get('breakdown', {})
            
            # 3. Fetch current builder profile
            cursor.execute("SELECT * FROM builder_profiles WHERE user_id = %s", (user_id,))
            profile = cursor.fetchone() or {
                "professional_summary": "",
                "skills": "[]",
                "achievements": "[]",
                "education": "[]",
                "experience": "[]"
            }
            
            def parse_json(val):
                if not val: return []
                if isinstance(val, list): return val
                try: return json.loads(val)
                except: return []
                
            current_skills = parse_json(profile.get('skills'))
            current_experience = parse_json(profile.get('experience'))
            current_education = parse_json(profile.get('education'))
            current_summary = profile.get('professional_summary') or ""
            
            # 4. Process suggestions safely
            for sug in suggestions:
                s_type = sug.get('type')
                s_val = sug.get('value', '').strip()
                if not s_val: continue
                
                if s_type == "skill":
                    continue
                        
                elif s_type == "summary":
                    if s_val not in current_summary:
                        current_summary += f"\n\n{s_val}"
                        
                elif s_type == "experience":
                    if s_val not in current_experience:
                        current_experience.append(s_val)
                        
            # Do NOT update builder_profiles here!
            # The builder should remain untouched until the user explicitly restores the version.
            
            # 5. Rebuild the resume text to calculate the new ATS Score
            cursor.execute("SELECT name, email FROM students WHERE id = %s", (user_id,))
            student_data = cursor.fetchone()
            
            cursor.execute("SELECT project_name, description FROM user_projects WHERE user_id = %s", (user_id,))
            projects = cursor.fetchall()
            
            text_lines = []
            if student_data:
                text_lines.append(student_data.get('name', ''))
                text_lines.append(student_data.get('email', ''))
                
            if current_summary:
                text_lines.append("SUMMARY: " + current_summary)
            if current_skills:
                text_lines.append("SKILLS: " + ", ".join(current_skills))
            if current_experience:
                text_lines.append("EXPERIENCE: " + " ".join(current_experience))
                
            for p in projects:
                text_lines.append(f"PROJECT: {p.get('project_name')} - {p.get('description')}")
                
            new_resume_text = "\n".join(text_lines)
            
            # 6. Calculate New ATS Score
            new_score_data = evaluate_resume(new_resume_text, jd_text)
            new_score = new_score_data.get('overall_score', 0)
            new_breakdown = new_score_data.get('breakdown', {})
            
            improvement_score = new_score - old_score
            improvement_reason = []
            if new_breakdown.get('keyword', {}).get('score', 0) > old_breakdown.get('keyword', {}).get('score', 0):
                improvement_reason.append("Keyword Match Increased")
            if new_breakdown.get('experience', {}).get('score', 0) > old_breakdown.get('experience', {}).get('score', 0):
                improvement_reason.append("Experience Language Improved")
            if new_breakdown.get('section', {}).get('score', 0) > old_breakdown.get('section', {}).get('score', 0):
                improvement_reason.append("Sections Optimized")
                
            if not improvement_reason:
                improvement_reason = "No major changes in evaluated criteria"
            else:
                improvement_reason = ", ".join(improvement_reason)
            
            # 7. Save Version History
            cursor.execute("SELECT MAX(version_number) as max_v FROM resume_versions WHERE original_resume_id = %s", (resume_id,))
            v_res = cursor.fetchone()
            next_version = (v_res['max_v'] or 0) + 1
            
            # Prepare version_data with the NEW state
            version_data = {
                "professional_summary": current_summary.strip(),
                "skills": current_skills,
                "experience": current_experience,
                "education": current_education
            }
            
            cursor.execute("""
                INSERT INTO resume_versions (user_id, original_resume_id, jd_id, version_data, optimized_resume_text, ats_improvement_score, version_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, resume_id, jd_id, json.dumps(version_data, default=str), new_resume_text, improvement_score, next_version))
            
            conn.commit()
            
            # No ATS history logging for optimizations
        return jsonify({
            "old_score": old_score,
            "new_score": new_score,
            "improvement": improvement_score,
            "before_breakdown": old_breakdown,
            "after_breakdown": new_breakdown,
            "improvement_reason": improvement_reason
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@builder_bp.route('/api/builder/restore-version', methods=['POST'])
@jwt_required()
def restore_version():
    user_id = get_jwt_identity()
    data = request.get_json()
    version_number = data.get('version_number')
    
    if not version_number:
        return jsonify({"error": "Version number required"}), 400
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get version
            cursor.execute("SELECT version_data, optimized_resume_text FROM resume_versions WHERE user_id = %s AND version_number = %s", (user_id, version_number))
            version_rec = cursor.fetchone()
            if not version_rec:
                return jsonify({"error": "Version not found"}), 404
                
            version_data = json.loads(version_rec['version_data'])
            
            # Restore to builder_profiles
            cursor.execute("""
                UPDATE builder_profiles 
                SET professional_summary = %s,
                    skills = %s,
                    education = %s,
                    experience = %s,
                    optimized_resume_text = %s
                WHERE user_id = %s
            """, (
                version_data.get('professional_summary', ''),
                version_data.get('skills', '[]'),
                version_data.get('education', '[]'),
                version_data.get('experience', '[]'),
                version_rec['optimized_resume_text'],
                user_id
            ))
            
            if cursor.rowcount == 0:
                # Insert instead if missing
                cursor.execute("""
                    INSERT INTO builder_profiles (user_id, professional_summary, skills, education, experience, optimized_resume_text)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    version_data.get('professional_summary', ''),
                    version_data.get('skills', '[]'),
                    version_data.get('education', '[]'),
                    version_data.get('experience', '[]'),
                    version_rec['optimized_resume_text']
                ))
                
            conn.commit()
            return jsonify({"message": "Version restored successfully"}), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
