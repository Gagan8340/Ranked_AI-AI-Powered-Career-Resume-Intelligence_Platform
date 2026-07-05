import os
from datetime import timedelta

# pyrefly: ignore [missing-import]
from flask import Flask, jsonify, make_response, redirect, render_template, request, url_for
from flask_cors import CORS
from flask_jwt_extended import JWTManager, decode_token
from flask_compress import Compress

from config import (
    ALLOWED_ORIGINS,
    FORCE_HTTPS,
    JWT_COOKIE_CSRF_PROTECT,
    JWT_COOKIE_NAME,
    JWT_COOKIE_SECURE,
    JWT_HEADER_NAME,
    JWT_HEADER_TYPE,
    JWT_SECRET_KEY,
    JWT_TOKEN_LOCATION,
    MAX_CONTENT_LENGTH,
    UPLOAD_FOLDER,
    get_db_connection,
    init_db,
)
from utils.extensions import limiter

def create_app():
    app = Flask(__name__)
    if len(JWT_SECRET_KEY or "") < 64:
        raise ValueError("JWT_SECRET_KEY must be at least 64 characters")
    app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
    app.config["JWT_TOKEN_LOCATION"] = JWT_TOKEN_LOCATION
    app.config["JWT_COOKIE_SECURE"] = JWT_COOKIE_SECURE or FORCE_HTTPS
    app.config["JWT_COOKIE_CSRF_PROTECT"] = JWT_COOKIE_CSRF_PROTECT
    app.config["JWT_ACCESS_COOKIE_NAME"] = JWT_COOKIE_NAME
    app.config["JWT_HEADER_NAME"] = JWT_HEADER_NAME
    app.config["JWT_HEADER_TYPE"] = JWT_HEADER_TYPE
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
    jwt_hours = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_HOURS", "8"))
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=jwt_hours)

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=True)
    jwt = JWTManager(app)
    Compress(app)
    limiter.init_app(app)

    import pymysql
    try:
        init_db()
    except Exception as e:
        app.logger.warning(f"Database unavailable during startup: {e}")

    try:
        from services.email_service import test_email_connection
        test_email_connection()
    except Exception as e:
        app.logger.warning(f"Email service unavailable during startup: {e}")

    @app.route('/health', methods=['GET'])
    def health_check():
        status = {"app": "online", "database": "offline"}
        try:
            print("HEALTH: Trying to get connection", flush=True)
            conn = get_db_connection()
            print("HEALTH: Got connection", flush=True)
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
            conn.close()
            print("HEALTH: Connection closed", flush=True)
            status["database"] = "online"
        except Exception as e:
            print(f"HEALTH ERROR: {e}", flush=True)
            app.logger.error(f"Health check DB error: {e}")
        return jsonify(status)
        
    # @app.errorhandler(pymysql.err.OperationalError)
    # def handle_db_error(e):
    #     return jsonify({"success": False, "message": "Service temporarily unavailable. Please try again shortly."}), 503

    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.resume import resume_bp
    from routes.jd_routes import jd_bp
    from routes.optimizer_routes import optimizer_bp
    from routes.builder_routes import builder_bp
    from routes.cover_letter_routes import cover_letter_bp
    from routes.settings_routes import settings_bp
    from routes.ats_routes import ats_bp
    from routes.intelligence_routes import intelligence_bp
    from routes.admin_routes import admin_bp
    from routes.recruiter_auth import recruiter_auth_bp
    from jd_analyzer import jd_analyzer_bp
    from routes.latex_routes import latex_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(resume_bp)
    app.register_blueprint(jd_bp)
    app.register_blueprint(optimizer_bp)
    app.register_blueprint(builder_bp)
    app.register_blueprint(cover_letter_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(ats_bp)
    app.register_blueprint(intelligence_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(recruiter_auth_bp)
    app.register_blueprint(jd_analyzer_bp)
    app.register_blueprint(latex_bp)

    @app.before_request
    def enforce_https_redirect():
        if not FORCE_HTTPS:
            return None
        if request.is_secure:
            return None
        if request.headers.get("X-Forwarded-Proto", "").lower() == "https":
            return None
        return redirect(request.url.replace("http://", "https://", 1), code=301)

    @app.before_request
    def check_auth():
        public_routes = {
            "health_check",
            "auth.login",
            "auth.register",
            "auth.login_page",
            "auth.register_page",
            "auth.logout",
            "auth.verification_pending",
            "auth.verification_success",
            "auth.verify_email",
            "auth.resend_verification",
            "auth.forgot_password_page",
            "auth.forgot_password",
            "auth.reset_password_page",
            "auth.reset_password",
            "static",
            "home",
            "terms",
            "privacy",
        }
        if request.endpoint is None or request.endpoint in public_routes or request.path == '/health':
            return None
        token = request.cookies.get("access_token") or request.headers.get("Authorization")
        if token:
            print(f"AUTH: Token found for {request.path}", flush=True)
            try:
                decoded = decode_token(token.split("Bearer ")[-1] if "Bearer" in token else token)
                student_id = decoded.get('sub')
                print(f"AUTH: JWT Identity = {student_id} for {request.path}", flush=True)
                
                # Check email verification
                conn = get_db_connection()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT email_verified FROM students WHERE id=%s", (student_id,))
                        student = cursor.fetchone()
                        if student and not student["email_verified"]:
                            if request.path.startswith('/api/'):
                                return jsonify({"success": False, "message": "Your email address has not been verified.", "is_unverified": True}), 403
                            return redirect('/email-verification-pending')
                finally:
                    conn.close()
            except Exception as e:
                print(f"AUTH: Token decode/verify failed for {request.path}: {str(e)}", flush=True)
        else:
            print(f"AUTH: No token found for {request.path}", flush=True)
            
        if not token and "api" not in request.path:
            return redirect(url_for("auth.login_page"))
        return None

    @app.get("/")
    def home():
        return render_template("landing.html")

    @app.get("/terms")
    def terms():
        return render_template("terms.html")

    @app.get("/privacy")
    def privacy():
        return render_template("privacy.html")

    def _get_current_student_id():
        token = request.cookies.get("access_token")
        if not token:
            return None
        try:
            decoded = decode_token(token)
            return decoded.get("sub")
        except Exception:
            return None

    @app.context_processor
    def inject_student():
        student_id = _get_current_student_id()
        if not student_id:
            return dict(student=None)
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM students WHERE id=%s", (student_id,))
                student = cursor.fetchone()
                return dict(student=student)
        except Exception:
            return dict(student=None)
        finally:
            if 'conn' in locals() and conn:
                conn.close()

    @app.get("/attendance-gate")
    def attendance_gate():
        student_id = _get_current_student_id()
        if not student_id:
            return redirect(url_for("auth.login_page"))
        return redirect("/dashboard")

    @app.get("/api/health")
    def health():
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                table_names = [
                    "students",
                    "attendance",
                    "streak_history",
                    "study_plans",
                    "quiz_results",
                    "language_progress",
                    "notifications",
                    "admin_users",
                ]
                existing = []
                for name in table_names:
                    cursor.execute("SHOW TABLES LIKE %s", (name,))
                    if cursor.fetchone():
                        existing.append(name)
            return jsonify(
                {
                    "status": "ok",
                    "database": "connected",
                    "tables_created": len(existing) == len(table_names),
                    "project": "ranked.ai",
                }
            )
        finally:
            connection.close()

    @app.errorhandler(404)
    def not_found(_error):
        if request.path.startswith('/api/'):
            return jsonify({"success": False, "message": "Not found"}), 404
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        import traceback
        traceback.print_exception(type(error), error, error.__traceback__)
        if request.path.startswith('/api/'):
            return jsonify({"success": False, "message": "Internal server error"}), 500
        return render_template("500.html"), 500

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if FORCE_HTTPS:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: blob:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:; "
            "connect-src 'self' https://cdnjs.cloudflare.com blob:;"
            "worker-src 'self' blob: data: https://cdnjs.cloudflare.com;"
            "frame-src 'self' blob:;"
            "object-src 'self' blob:;"
        )
        return response

    @jwt.unauthorized_loader
    def unauthorized_callback(callback_error_string):
        print(f"AUTH: Authentication failed for {request.path}. Reason: {callback_error_string}", flush=True)
        if request.path.startswith('/api/'):
            return jsonify({"success": False, "message": "Please login first", "redirect": "/login"}), 401
        return redirect(url_for("auth.login_page"))

    @jwt.expired_token_loader
    def expired_token_callback(_jwt_header, _jwt_data):
        if request.path.startswith('/api/'):
            response = make_response(jsonify({"success": False, "message": "Session expired"}), 401)
            response.delete_cookie("access_token", path="/")
            return response
        response = make_response(redirect(url_for("auth.login_page")))
        response.delete_cookie("access_token", path="/")
        return response

    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        if request.path.startswith('/api/'):
            return jsonify({"success": False, "message": "Invalid token"}), 401
        response = make_response(redirect(url_for("auth.login_page")))
        response.delete_cookie("access_token", path="/")
        return response


    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=False)
