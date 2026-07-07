from flask import Blueprint, request, jsonify, render_template, current_app, send_from_directory, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
import uuid
import io
import requests

from config import get_db_connection
from utils.validators import validate_file
from utils.cloudinary_helper import upload_private_resume, get_signed_url, delete_resume
from utils.resume_parser import extract_resume_text, parse_resume_for_profile_deterministic
import json

resume_bp = Blueprint('resume', __name__)

from utils.activity_logger import log_activity

# -------------------------
# UI PAGES
# -------------------------



# -------------------------
# API ENDPOINTS
# -------------------------
@resume_bp.route('/api/resume/upload', methods=['POST'])
def upload_resume():
    print("UPLOAD: Request received", flush=True)
    try:
        from flask_jwt_extended import verify_jwt_in_request
        verify_jwt_in_request()
    except Exception as e:
        print(f"UPLOAD: JWT validation failed: {e}", flush=True)
        return jsonify({"error": "Unauthorized"}), 401
        
    print("UPLOAD: JWT validated", flush=True)
    user_id = get_jwt_identity()
    print("student_id:", user_id, flush=True)
    print("request.cookies:", request.cookies, flush=True)
    print("request.headers:", request.headers, flush=True)

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    
    # 1. Size & MIME validation
    is_valid, error_msg = validate_file(file)
    if not is_valid:
        return jsonify({"error": error_msg}), 400
        
    conn = get_db_connection()
    try:

        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[-1].lower()
        
        # 3. Mark old resumes as inactive instead of deleting (Preserves historical data & foreign keys)
        with conn.cursor() as cursor:
            cursor.execute("UPDATE resumes SET is_active = 0 WHERE user_id = %s AND is_active = 1", (user_id,))
            conn.commit()

        # 2. Parse and detect scanned PDFs
        text, is_scanned = extract_resume_text(file, ext)
        if is_scanned:
            return jsonify({"error": "This PDF appears to be scanned. Please upload a text-based PDF."}), 400
            
        # 4. Upload to Cloudinary
        try:
            cloud_data = upload_private_resume(file, filename)
        except Exception as e:
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            file.seek(0)
            file.save(filepath)
            cloud_data = {
                "public_id": f"local:{unique_filename}",
                "url": f"/api/resume/local/{unique_filename}",
                "format": ext,
                "bytes": os.path.getsize(filepath)
            }
            
        # 5. Parse profile deterministically
        try:
            parsed_data = parse_resume_for_profile_deterministic(text)
        except Exception as e:
            print(f"Deterministic parsing failed during upload: {e}")
            parsed_data = {}
            
        # 6. Database Operations
        with conn.cursor() as cursor:
            # Insert new Active Resume
            cursor.execute(
                """
                INSERT INTO resumes (user_id, filename, cloudinary_public_id, resource_type, file_size, resume_text, is_active, secure_url)
                VALUES (%s, %s, %s, %s, %s, %s, 1, %s)
                """,
                (user_id, filename, cloud_data['public_id'], ext, cloud_data['bytes'], text, cloud_data['url'])
            )
            
            # Upsert Builder Profile
            cursor.execute("""
                INSERT INTO builder_profiles (user_id, professional_summary, linkedin, github, portfolio, skills, achievements, education, experience)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                professional_summary = VALUES(professional_summary),
                linkedin = VALUES(linkedin),
                github = VALUES(github),
                portfolio = VALUES(portfolio),
                skills = VALUES(skills),
                achievements = VALUES(achievements),
                education = VALUES(education),
                experience = VALUES(experience)
            """, (
                user_id,
                parsed_data.get('professional_summary', ''),
                parsed_data.get('linkedin', ''),
                parsed_data.get('github', ''),
                parsed_data.get('portfolio', ''),
                json.dumps(parsed_data.get('skills', [])),
                json.dumps(parsed_data.get('achievements', [])),
                json.dumps(parsed_data.get('education', [])),
                json.dumps(parsed_data.get('experience', []))
            ))
            
            # Wipe and resync Projects
            cursor.execute("DELETE FROM user_projects WHERE user_id = %s", (user_id,))
            for p in parsed_data.get('projects', []):
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
                
            # Wipe and resync Certifications
            cursor.execute("DELETE FROM certifications WHERE user_id = %s", (user_id,))
            for c in parsed_data.get('certifications', []):
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

            # Add Notification
            cursor.execute(
                """
                INSERT INTO notifications (student_id, message, type)
                VALUES (%s, %s, %s)
                """,
                (user_id, f"Resume '{filename}' activated and profile updated.", "success")
            )
            
            # Invalidate Caches
            cursor.execute("DELETE FROM ats_cache WHERE user_id = %s", (user_id,))
            cursor.execute("DELETE FROM intelligence_cache WHERE user_id = %s", (user_id,))
            
        conn.commit()
        log_activity(user_id, "resume_upload", {"filename": filename})
        return jsonify({"message": "Resume uploaded and profile parsed successfully!"}), 201
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@resume_bp.route('/api/resume/list', methods=['GET'])
@jwt_required()
def list_resumes():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT resume_id, filename, uploaded_at, file_size FROM resumes WHERE user_id = %s AND is_active = 1 ORDER BY uploaded_at DESC", 
                (user_id,)
            )
            resumes = cursor.fetchall()
            return jsonify({"resumes": resumes}), 200
    finally:
        conn.close()


@resume_bp.route('/api/resume/download/<int:resume_id>', methods=['GET'])
@jwt_required()
def download_resume(resume_id):
    user_id = get_jwt_identity()
    conn = get_db_connection()
    try:
        # JWT Ownership Verification
        with conn.cursor() as cursor:
            cursor.execute("SELECT cloudinary_public_id, filename, secure_url FROM resumes WHERE resume_id = %s AND user_id = %s", (resume_id, user_id))
            resume = cursor.fetchone()
            if not resume:
                return jsonify({"error": "Resume not found or unauthorized"}), 404
                
        # Generate URL
        if resume['secure_url']:
            url = resume['secure_url']
        else:
            url = get_signed_url(resume['cloudinary_public_id'])
        log_activity(user_id, "resume_download", {"filename": resume['filename']})
        
        return jsonify({"url": url}), 200
    finally:
        conn.close()


@resume_bp.route('/api/resume/stream/<int:resume_id>', methods=['GET'])
@jwt_required()
def stream_resume(resume_id):
    """Proxies the Cloudinary PDF to bypass strict delivery restrictions for viewing."""
    user_id = get_jwt_identity()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT cloudinary_public_id, filename, secure_url FROM resumes WHERE resume_id = %s AND user_id = %s", (resume_id, user_id))
            resume = cursor.fetchone()
            if not resume:
                return jsonify({"error": "Resume not found or unauthorized"}), 404
                
        # Generate URL
        if resume['secure_url']:
            url = resume['secure_url']
        else:
            url = get_signed_url(resume['cloudinary_public_id'])
            
        # Proxy it
        res = requests.get(url)
        if res.status_code == 200:
            return send_file(
                io.BytesIO(res.content),
                mimetype='application/pdf',
                as_attachment=False,
                download_name=resume['filename']
            )
        else:
            return jsonify({"error": "Failed to fetch resume from storage"}), 500
    finally:
        conn.close()


@resume_bp.route('/view-resume/<int:resume_id>', methods=['GET'])
@jwt_required()
def view_resume_page(resume_id):
    from flask import render_template
    user_id = get_jwt_identity()
    conn = get_db_connection()
    try:
        # Verify ownership
        with conn.cursor() as cursor:
            cursor.execute("SELECT resume_id FROM resumes WHERE resume_id = %s AND user_id = %s", (resume_id, user_id))
            resume = cursor.fetchone()
            
            if not resume:
                return render_template("view_resume.html", resume_url=None), 404
                
        # Use our new Flask proxy URL instead of hitting Cloudinary directly
        proxy_url = f"/api/resume/stream/{resume_id}"
        
        return render_template("view_resume.html", resume_url=proxy_url)
    finally:
        conn.close()


@resume_bp.route('/api/resume/<int:resume_id>', methods=['DELETE'])
@jwt_required()
def delete_resume_endpoint(resume_id):
    user_id = get_jwt_identity()
    conn = get_db_connection()
    try:
        # JWT Ownership Verification
        with conn.cursor() as cursor:
            cursor.execute("SELECT cloudinary_public_id, filename FROM resumes WHERE resume_id = %s AND user_id = %s", (resume_id, user_id))
            resume = cursor.fetchone()
            if not resume:
                return jsonify({"error": "Resume not found or unauthorized"}), 404
                
        # Destroy securely from Cloud
        delete_resume(resume['cloudinary_public_id'])
        
        # Destroy from DB
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM resumes WHERE resume_id = %s AND user_id = %s", (resume_id, user_id))
        conn.commit()
        
        log_activity(user_id, "resume_delete", {"filename": resume['filename']})
        
        return jsonify({"message": "Resume deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@resume_bp.route('/api/resume/local/<path:filename>', methods=['GET'])
@jwt_required()
def download_local_resume(filename):
    user_id = get_jwt_identity()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Verify Ownership
            cursor.execute("SELECT resume_id FROM resumes WHERE cloudinary_public_id = %s AND user_id = %s", (f"local:{filename}", user_id))
            if not cursor.fetchone():
                return jsonify({"error": "Unauthorized"}), 403
    finally:
        conn.close()
        
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
