from flask import Blueprint, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from config import get_db_connection

admin_bp = Blueprint('admin', __name__)

def check_admin(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT is_admin FROM students WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            if not user or not user.get('is_admin'):
                return False
            return True
    finally:
        conn.close()

@admin_bp.route('/admin/monitoring', methods=['GET'])
@jwt_required()
def render_admin_dashboard():
    current_user = get_jwt_identity()
    if not check_admin(current_user):
        return jsonify({"error": "Unauthorized. Admin access required."}), 403
    return render_template('admin_dashboard.html')

@admin_bp.route('/api/admin/metrics', methods=['GET'])
@jwt_required()
def get_metrics():
    user_id = get_jwt_identity()
    if not check_admin(user_id):
        return jsonify({"error": "Unauthorized. Admin access required."}), 403

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT metric_key, metric_value FROM system_metrics")
            rows = cursor.fetchall()
            
        metrics = {r['metric_key']: r['metric_value'] for r in rows}
        
        # Calculate derived metrics
        ats_calls = metrics.get('ats_analysis_calls', 0)
        ats_time = metrics.get('ats_analysis_time_ms', 0)
        avg_ats_time = round(ats_time / ats_calls, 2) if ats_calls > 0 else 0
        
        jd_calls = metrics.get('jd_analysis_calls', 0)
        jd_time = metrics.get('jd_analysis_time_ms', 0)
        avg_jd_time = round(jd_time / jd_calls, 2) if jd_calls > 0 else 0
        
        gap_calls = metrics.get('gap_analysis_calls', 0)
        gap_time = metrics.get('gap_analysis_time_ms', 0)
        avg_gap_time = round(gap_time / gap_calls, 2) if gap_calls > 0 else 0
        
        gemini_success = metrics.get('gemini_success_count', 0)
        gemini_fallback = metrics.get('gemini_fallback_count', 0)
        total_gemini = gemini_success + gemini_fallback
        gemini_success_rate = round((gemini_success / total_gemini) * 100, 2) if total_gemini > 0 else 100
        
        ats_hits = metrics.get('ats_cache_hits', 0)
        ats_misses = metrics.get('ats_cache_misses', 0)
        
        intel_hits = metrics.get('intel_cache_hits', 0)
        intel_misses = metrics.get('intel_cache_misses', 0)
        
        return jsonify({
            "cache": {
                "ats_hits": ats_hits,
                "ats_misses": ats_misses,
                "intel_hits": intel_hits,
                "intel_misses": intel_misses
            },
            "gemini": {
                "success_count": gemini_success,
                "fallback_count": gemini_fallback,
                "success_rate": gemini_success_rate
            },
            "latency": {
                "avg_ats_time_ms": avg_ats_time,
                "avg_jd_time_ms": avg_jd_time,
                "avg_gap_analysis_time_ms": avg_gap_time
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/admin/users', methods=['GET'])
@jwt_required()
def get_users():
    user_id = get_jwt_identity()
    if not check_admin(user_id):
        return jsonify({"error": "Unauthorized. Admin access required."}), 403

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT email, email_verified, verified_at, created_at FROM students ORDER BY created_at DESC")
            users = cursor.fetchall()
        return jsonify({"users": users}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/admin/test-email', methods=['POST', 'GET'])
def test_email():
    from services.email_service import _send_email
    result = _send_email("ranked1ai@gmail.com", "Test Email", "<p>This is a test email.</p>")
    if result.get("success"):
        return jsonify({"success": True, "message": "Test email sent successfully"})
    else:
        return jsonify({"success": False, "message": result.get("error")}), 500
