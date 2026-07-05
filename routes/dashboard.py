import random
from datetime import date, datetime

from flask import Blueprint, jsonify, redirect, render_template, request
from flask_jwt_extended import decode_token, get_jwt_identity, jwt_required

from config import get_db_connection
dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

QUOTES = [
    "Build momentum one application at a time.",
    "Your career OS is ready for focus.",
    "Strong resumes come from clear stories.",
    "Small improvements compound into offers.",
    "Keep shipping career wins, one day at a time.",
]


def _get_greeting():
    hour = datetime.now().hour
    if hour < 12:
        return "Good Morning"
    if hour < 18:
        return "Good Afternoon"
    return "Good Evening"


def _default_context():
    today = date.today()
    return {
        "student": None,
        "active_page": "dashboard",
        "page_title": "Dashboard",
        "greeting": _get_greeting(),
        "today_label": today.strftime("%A, %d %B %Y"),
        "quote": random.choice(QUOTES),
        "notifications": [],
        "unread_count": 0,
        "resume_count": 0,
        "cover_letter_count": 0,
        "ats_score": 0,
        "version_count": 0,
    }


def _get_current_student_id():
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        decoded = decode_token(token)
        return decoded.get("sub")
    except Exception:
        return None


@dashboard_bp.get("/")
def dashboard():
    student_id = _get_current_student_id()
    if not student_id:
        return redirect("/login")

    today = date.today()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 1. Student details
            cursor.execute("SELECT * FROM students WHERE id=%s", (student_id,))
            student = cursor.fetchone()
            if not student:
                return jsonify({"error": "Student not found"}), 404

            # 2. Resumes count (Active only)
            cursor.execute("SELECT COUNT(*) AS c FROM resumes WHERE user_id=%s AND is_active=1", (student_id,))
            resume_count = cursor.fetchone()['c']
            has_resume = resume_count > 0

            # 3. Resume versions count
            cursor.execute(
                "SELECT COUNT(*) AS c FROM resume_versions rv JOIN resumes r ON rv.original_resume_id=r.resume_id WHERE r.user_id=%s",
                (student_id,)
            )
            resume_version_count = cursor.fetchone()['c']

            # 4. ATS Statistics (Highest, Total, Average)
            cursor.execute(
                "SELECT MAX(ats_score) AS max_score, COUNT(*) AS total_scans, AVG(ats_score) AS avg_score FROM ats_history WHERE user_id=%s",
                (student_id,)
            )
            stats_row = cursor.fetchone()
            highest_ats_score = stats_row['max_score'] if stats_row and stats_row['max_score'] else 0
            total_ats_scans = stats_row['total_scans'] if stats_row else 0
            average_ats_score = int(stats_row['avg_score']) if stats_row and stats_row['avg_score'] else 0
            
            # 5. Templates Used (Mock logic since we don't track per-resume templates yet)
            cursor.execute("SELECT COUNT(DISTINCT template_id) AS t_count FROM (SELECT 'tpl_prof_03' AS template_id) AS sub") # Mocked for now
            templates_used = 1
            
            # 6. Resume Downloads (Count of resumes generated/versions)
            cursor.execute("SELECT COUNT(*) AS c FROM resumes WHERE user_id=%s", (student_id,))
            resume_downloads = cursor.fetchone()['c'] + resume_version_count
            
            # 7. ATS Reports (has_jd_analysis, ats_score, ats_trend)
            cursor.execute(
                "SELECT ats_score, breakdown_json as analysis_json, scan_timestamp as created_at, scan_type, resume_title "
                "FROM ats_history "
                "WHERE user_id=%s "
                "ORDER BY scan_timestamp DESC",
                (student_id,)
            )
            ats_rows = cursor.fetchall()
            has_jd_analysis = len(ats_rows) > 0
            latest_ats_score = ats_rows[0]['ats_score'] if has_jd_analysis else 0
            
            # Parse missing keywords
            skill_gap_count = 0
            missing_keywords_list = []
            if has_jd_analysis and ats_rows[0]['analysis_json']:
                import json
                try:
                    analysis = ats_rows[0]['analysis_json']
                    if isinstance(analysis, str):
                        analysis = json.loads(analysis)
                    missing_keywords_list = analysis.get('missing_keywords', [])
                    skill_gap_count = len(missing_keywords_list)
                except Exception:
                    pass

            ats_trend = [{"score": r['ats_score'], "date": r['created_at'].isoformat()} for r in reversed(ats_rows)]

            # 6. Notifications
            cursor.execute(
                "SELECT message, type, created_at FROM notifications WHERE student_id=%s AND is_read=FALSE ORDER BY created_at DESC LIMIT 5",
                (student_id,)
            )
            notifications = cursor.fetchall()

            # 7. Recent Activity Logs
            cursor.execute(
                "SELECT action, details, created_at FROM activity_logs WHERE user_id=%s ORDER BY created_at DESC LIMIT 5",
                (student_id,)
            )
            activities = cursor.fetchall()
            
            # Cover Letters count
            cursor.execute("SELECT COUNT(*) AS c FROM cover_letters WHERE user_id=%s", (student_id,))
            cover_letter_count = cursor.fetchone()['c']

            # Unified Profile Strength Calculation
            from utils.profile_strength import calculate_profile_strength
            profile_data = calculate_profile_strength(student_id)
            total_profile_strength = profile_data['total_score']
            profile_categories = profile_data['categories']
            missing_items = profile_data['missing_items']

    finally:
        connection.close()

    return render_template(
        "dashboard.html",
        student=student,
        active_page="dashboard",
        page_title="Dashboard",
        greeting=_get_greeting(),
        today_label=today.strftime("%A, %d %B %Y"),
        quote=random.choice(QUOTES),
        notifications=notifications,
        activities=activities,
        has_resume=has_resume,
        has_jd_analysis=has_jd_analysis,
        resume_count=resume_count,
        highest_ats_score=highest_ats_score,
        templates_used=templates_used,
        resume_downloads=resume_downloads,
        latest_ats_score=latest_ats_score,
        ats_trend=ats_trend,
        profile_categories=profile_categories,
        missing_items=missing_items,
        total_profile_strength=total_profile_strength,
        total_ats_scans=total_ats_scans,
        average_ats_score=average_ats_score
    )


@dashboard_bp.get("/api/notifications")
@jwt_required()
def notifications_api():
    student_id = get_jwt_identity()

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, message, type, created_at, is_read
                FROM notifications
                WHERE student_id=%s
                ORDER BY created_at DESC
                LIMIT 10
                """,
                (student_id,),
            )
            rows = cursor.fetchall()
    finally:
        connection.close()

    notifications = [
        {
            "id": row["id"],
            "message": row["message"],
            "type": row["type"],
            "created_at": row["created_at"].isoformat(),
            "is_read": bool(row["is_read"]),
        }
        for row in rows
    ]
    return jsonify(notifications)


@dashboard_bp.post("/api/notifications/mark-read")
@jwt_required()
def notifications_mark_read():
    student_id = get_jwt_identity()

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE notifications SET is_read=TRUE WHERE student_id=%s",
                (student_id,),
            )
        connection.commit()
    finally:
        connection.close()

    return jsonify({"success": True})

@dashboard_bp.get("/api/dashboard/stats")
@jwt_required()
def dashboard_stats():
    student_id = get_jwt_identity()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as c FROM resumes WHERE user_id=%s", (student_id,))
            resumes_count = cursor.fetchone()['c']
            
            cursor.execute("SELECT COUNT(*) as c FROM cover_letters WHERE user_id=%s", (student_id,))
            cover_letters_count = cursor.fetchone()['c']
            
            cursor.execute("SELECT COUNT(*) as c FROM resume_versions WHERE user_id=%s", (student_id,))
            optimizations_count = cursor.fetchone()['c']
            
            cursor.execute(
                "SELECT ats_score, scan_timestamp as created_at FROM ats_history WHERE user_id=%s ORDER BY scan_timestamp DESC",
                (student_id,)
            )
            jd_scores = cursor.fetchall()
            
            latest_ats = jd_scores[0]['ats_score'] if jd_scores else 0
            
            trend_data = [{"score": r['ats_score'], "date": r['created_at'].isoformat()} for r in reversed(jd_scores)]
            
            cursor.execute(
                "SELECT action, created_at FROM activity_logs WHERE user_id=%s ORDER BY created_at DESC LIMIT 10",
                (student_id,)
            )
            activities = cursor.fetchall()
            activity_list = [{"action": r['action'], "date": r['created_at'].isoformat()} for r in activities]
            
            return jsonify({
                "success": True,
                "stats": {
                    "resumes": resumes_count,
                    "cover_letters": cover_letters_count,
                    "optimizations": optimizations_count,
                    "latest_ats": latest_ats,
                    "ats_trend": trend_data,
                    "activities": activity_list
                }
            })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        connection.close()
