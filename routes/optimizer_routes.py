import json
from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity

from config import get_db_connection
from utils.extensions import limiter
from utils.gemini_helper import optimize_resume

optimizer_bp = Blueprint('optimizer', __name__)

# -------------------------
# UI ROUTES
# -------------------------
@optimizer_bp.route('/resume-optimizer', methods=['GET'])
@jwt_required()
def resume_optimizer_page():
    return render_template("resume_optimizer.html")

@optimizer_bp.route('/version-compare/<int:version_id>', methods=['GET'])
@jwt_required()
def version_compare_page(version_id):
    return render_template("version_compare.html", version_id=version_id)


# -------------------------
# API ENDPOINTS
# -------------------------
@optimizer_bp.route('/api/resume/optimize', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")
def optimize_resume_api():
    """Executes AI rewriting securely without hallucinations."""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Invalid payload"}), 400
        
    resume_id = data.get('resume_id')
    jd_id = data.get('jd_id')
    
    if not resume_id or not jd_id:
        return jsonify({"error": "Resume ID and JD ID are required"}), 400
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Enforce Asset Ownership Security
            cursor.execute("SELECT jd_text FROM job_descriptions WHERE id = %s AND user_id = %s", (jd_id, user_id))
            jd = cursor.fetchone()
            if not jd:
                return jsonify({"error": "Job description not found or unauthorized"}), 404
                
            cursor.execute("SELECT resume_text FROM resumes WHERE resume_id = %s AND user_id = %s AND is_active = 1", (resume_id, user_id))
            resume = cursor.fetchone()
            if not resume:
                return jsonify({"error": "Resume not found or unauthorized"}), 404
                
            cursor.execute("SELECT optimized_resume_text FROM builder_profiles WHERE user_id = %s", (user_id,))
            profile = cursor.fetchone()
            
            if profile and profile.get('optimized_resume_text'):
                resume_text = profile['optimized_resume_text']
            else:
                resume_text = resume['resume_text']
                
            jd_text = jd['jd_text']
            
        # 2. AI Optimization Engine
        from utils.ai_fallback import safe_gemini_call
        opt_data = safe_gemini_call(optimize_resume, resume_text, jd_text)
        
        if opt_data.get('fallback_mode'):
            return jsonify({
                "fallback_mode": True,
                "message": "AI optimization temporarily unavailable."
            }), 200
        
        # 3. Store Version History
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO resume_versions (user_id, original_resume_id, jd_id, version_data, ats_improvement_score)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, resume_id, jd_id, json.dumps(opt_data), opt_data.get('ats_improvement_score', 0))
            )
            version_id = cursor.lastrowid
        conn.commit()
        
        from utils.activity_logger import log_activity
        log_activity(user_id, "Resume Optimization", {"version_id": version_id, "ats_improvement_score": opt_data.get('ats_improvement_score')})
        
        # 4. Add Notification
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO notifications (student_id, message, type)
                VALUES (%s, %s, %s)
                """,
                (user_id, f"Resume successfully optimized! ATS score improved by {opt_data.get('ats_improvement_score', 0)} points.", "success")
            )
        conn.commit()
        
        return jsonify({
            "version_id": version_id,
            "optimized_sections": opt_data.get('optimized_sections'),
            "improvements_made": opt_data.get('improvements_made'),
            "ats_improvement_score": opt_data.get('ats_improvement_score')
        }), 200
        
    except ValueError:
        # Fallback exactly as requested
        return jsonify({"error": "Optimization failed. Please retry."}), 500
    except Exception:
        return jsonify({"error": "An internal error occurred."}), 500
    finally:
        conn.close()


@optimizer_bp.route('/api/resume/versions/<int:resume_id>', methods=['GET'])
@jwt_required()
def list_versions(resume_id):
    """Returns chronological history of optimizations."""
    user_id = get_jwt_identity()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, jd_id, ats_improvement_score, created_at 
                FROM resume_versions 
                WHERE original_resume_id = %s AND user_id = %s 
                ORDER BY created_at DESC
                """, 
                (resume_id, user_id)
            )
            versions = cursor.fetchall()
            return jsonify({"versions": versions}), 200
    finally:
        conn.close()


@optimizer_bp.route('/api/resume/compare/<int:version_id>', methods=['GET'])
@jwt_required()
def compare_version(version_id):
    """Delivers strict structural data for the dual-pane UI."""
    user_id = get_jwt_identity()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT rv.version_data, rv.ats_improvement_score, r.resume_text 
                FROM resume_versions rv
                JOIN resumes r ON rv.original_resume_id = r.resume_id
                WHERE rv.id = %s AND rv.user_id = %s
                """,
                (version_id, user_id)
            )
            row = cursor.fetchone()
            if not row:
                return jsonify({"error": "Version not found or unauthorized"}), 404
                
            version_data = json.loads(row['version_data']) if isinstance(row['version_data'], str) else row['version_data']
                
            return jsonify({
                "original_text": row['resume_text'],
                "optimized_sections": version_data.get('optimized_sections', {}),
                "improvements_made": version_data.get('improvements_made', []),
                "ats_improvement_score": row['ats_improvement_score']
            }), 200
    finally:
        conn.close()


@optimizer_bp.route('/api/jd/list/<int:resume_id>', methods=['GET'])
@jwt_required()
def list_jds_for_resume(resume_id):
    """Helper to populate the JD dropdown based on selected resume."""
    user_id = get_jwt_identity()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, created_at, ats_score FROM job_descriptions WHERE resume_id = %s AND user_id = %s ORDER BY created_at DESC", (resume_id, user_id))
            jds = cursor.fetchall()
            return jsonify({"jds": jds}), 200
    finally:
        conn.close()
