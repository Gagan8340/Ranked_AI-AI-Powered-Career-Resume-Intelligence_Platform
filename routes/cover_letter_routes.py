from flask import Blueprint, jsonify, request, Response, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from config import get_db_connection
from utils.gemini_helper import generate_cover_letter
from utils.activity_logger import log_activity

cover_letter_bp = Blueprint("cover_letter", __name__)

@cover_letter_bp.get("/cover-letters")
@jwt_required()
def cover_letter_page():
    return render_template("cover_letter.html", active_page="cover_letters", page_title="Cover Letters")

@cover_letter_bp.post("/api/cover-letter/generate")
@jwt_required()
def generate():
    user_id = get_jwt_identity()
    data = request.json
    
    resume_id = data.get("resume_id")
    jd_id = data.get("jd_id")
    role_title = data.get("role_title")
    company_name = data.get("company_name")
    
    if not all([resume_id, jd_id, role_title, company_name]):
        return jsonify({"success": False, "message": "Missing required fields"}), 400
        
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Verify Ownership
            cursor.execute("SELECT jd_text FROM job_descriptions WHERE id=%s AND user_id=%s", (jd_id, user_id))
            jd = cursor.fetchone()
            if not jd:
                return jsonify({"error": "Job description not found"}), 404
            jd_text = jd['jd_text']
            
            # Optimized Resume Selection Fallback
            cursor.execute("SELECT resume_text FROM resumes WHERE resume_id=%s AND user_id=%s AND is_active = 1", (resume_id, user_id))
            resume = cursor.fetchone()
            if not resume:
                return jsonify({"error": "Resume not found"}), 404
                
            cursor.execute("SELECT optimized_resume_text FROM builder_profiles WHERE user_id=%s", (user_id,))
            profile = cursor.fetchone()
            
            if profile and profile.get('optimized_resume_text'):
                resume_text = profile['optimized_resume_text']
            else:
                resume_text = resume['resume_text']
                
        # Generate cover letter using safe wrapper
        from utils.ai_fallback import safe_gemini_call
        cl_data = safe_gemini_call(generate_cover_letter, resume_text, jd_text, role_title, company_name)
        
        if cl_data.get('fallback_mode'):
            return jsonify({
                "fallback_mode": True,
                "message": "AI cover letter generation temporarily unavailable."
            }), 200

        # Extract values
        cover_letter_text = cl_data.get('cover_letter_text', '')
        match_score = cl_data.get('match_score', 0)
        
        # Save to DB
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO cover_letters (user_id, resume_id, jd_id, role_title, company_name, content, match_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (user_id, resume_id, jd_id, role_title, company_name, cover_letter_text, match_score)
            )
            cl_id = cursor.lastrowid
        connection.commit()
        
        log_activity(user_id, "Generated Cover Letter", {"cover_letter_id": cl_id, "match_score": match_score})

        # Add Notification
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO notifications (student_id, message, type)
                VALUES (%s, %s, %s)
                """,
                (user_id, f"Cover letter generated for {role_title} at {company_name}!", "success")
            )
        connection.commit()
        
        return jsonify({"success": True, "cover_letter_id": cl_id, "content": cover_letter_text, "score": match_score})
    except Exception as e:
        return jsonify({"success": False, "message": "An internal error occurred."}), 500
    finally:
        connection.close()

@cover_letter_bp.get("/api/cover-letter/list")
@jwt_required()
def list_letters():
    user_id = get_jwt_identity()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, role_title as role, company_name as company, created_at as date
                FROM cover_letters
                WHERE user_id=%s
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
            results = cursor.fetchall()
            return jsonify({"success": True, "cover_letters": results})
    finally:
        connection.close()

@cover_letter_bp.put("/api/cover-letter/<int:cl_id>")
@jwt_required()
def edit_letter(cl_id):
    user_id = get_jwt_identity()
    data = request.json
    content = data.get("content")
    
    if not content:
        return jsonify({"success": False, "message": "Missing content"}), 400
        
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Check ownership
            cursor.execute("SELECT id FROM cover_letters WHERE id=%s AND user_id=%s", (cl_id, user_id))
            if not cursor.fetchone():
                return jsonify({"success": False, "message": "Unauthorized"}), 403
                
            cursor.execute("UPDATE cover_letters SET content=%s WHERE id=%s", (content, cl_id))
        connection.commit()
        return jsonify({"success": True, "message": "Saved successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        connection.close()

@cover_letter_bp.get("/api/cover-letter/<int:cl_id>/download")
@jwt_required()
def download_letter(cl_id):
    user_id = get_jwt_identity()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT content, role_title, company_name FROM cover_letters WHERE id=%s AND user_id=%s", (cl_id, user_id))
            row = cursor.fetchone()
            if not row:
                return jsonify({"success": False, "message": "Unauthorized or not found"}), 403
                
            content = row['content']
            filename = f"Cover_Letter_{row['company_name']}_{row['role_title']}.txt".replace(" ", "_")
            
            return Response(
                content,
                mimetype="text/plain",
                headers={"Content-disposition": f"attachment; filename={filename}"}
            )
    finally:
        connection.close()
