import re
import time
from datetime import datetime, timedelta
import os
import uuid
import json
import secrets

import bcrypt
from flask import Blueprint, current_app, jsonify, make_response, redirect, render_template, request, url_for
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

from config import get_db_connection, TOKEN_EXPIRY_HOURS, PASSWORD_RESET_EXPIRY_HOURS
from services.email_service import send_verification_email, send_welcome_email, send_password_reset_email
from utils.activity_logger import log_activity
from utils.extensions import limiter
from utils.validators import validate_file
from utils.cloudinary_helper import upload_private_resume
from utils.resume_parser import extract_resume_text
from utils.gemini_helper import parse_resume_for_profile

auth_bp = Blueprint("auth", __name__)

LOGIN_ATTEMPTS = {}
LOGIN_MAX_DELAY_SECONDS = 300
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@auth_bp.get("/login")
def login_page():
    return render_template("login.html")


@auth_bp.get("/register")
def register_page():
    return render_template("register.html")


def _serialize_student(student):
    return {
        "id": student["id"],
        "name": student["name"],
        "email": student["email"],
        "phone": student["phone"],
        "created_at": student["created_at"],
        "last_seen": student["last_seen"],
        "is_active": bool(student["is_active"]),
    }


def _get_request_data():
    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict()
    return data or {}


def _login_key(email, ip):
    return f"{email}:{ip}"


def _login_delay_seconds(email, ip):
    key = _login_key(email, ip)
    info = LOGIN_ATTEMPTS.get(key)
    if not info:
        return 0
    failures = info.get("failures", 0)
    last_failed = info.get("last_failed", 0)
    if failures <= 0:
        return 0
    delay = min(2 ** failures, LOGIN_MAX_DELAY_SECONDS)
    elapsed = time.time() - last_failed
    remaining = max(delay - elapsed, 0)
    return remaining


def _record_login_failure(email, ip):
    key = _login_key(email, ip)
    info = LOGIN_ATTEMPTS.get(key, {"failures": 0, "last_failed": 0})
    info["failures"] = min(info.get("failures", 0) + 1, 10)
    info["last_failed"] = time.time()
    LOGIN_ATTEMPTS[key] = info


def _clear_login_failures(email, ip):
    LOGIN_ATTEMPTS.pop(_login_key(email, ip), None)


@auth_bp.post("/auth/register")
@limiter.limit("10 per hour")
def register():
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    phone = request.form.get("phone")
    no_resume = request.form.get("no_resume") == "on"

    if not name or not email or not password:
        return jsonify({"success": False, "message": "name, email, and password are required"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"success": False, "message": "Invalid email format"}), 400

    if not no_resume:
        resume_file = request.files.get("resume")
        if not resume_file or not resume_file.filename:
            return jsonify({"success": False, "message": "Resume upload is required"}), 400
            
        is_valid, error_msg = validate_file(resume_file)
        if not is_valid:
            return jsonify({"success": False, "message": error_msg}), 400

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    cloud_data = {}
    ext = ""
    filename = ""
    text = ""
    parsed_data = {}

    if not no_resume:
        filename = secure_filename(resume_file.filename)
        ext = filename.rsplit('.', 1)[-1].lower()

        try:
            # Parse resume to extract text
            text, is_scanned = extract_resume_text(resume_file, ext)
            if is_scanned:
                return jsonify({"success": False, "message": "This PDF appears to be scanned. Please upload a text-based PDF."}), 400
                
            # Upload to Cloudinary
            try:
                cloud_data = upload_private_resume(resume_file, filename)
            except Exception as e:
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                resume_file.seek(0)
                resume_file.save(filepath)
                cloud_data = {
                    "public_id": f"local:{unique_filename}",
                    "url": f"/api/resume/local/{unique_filename}",
                    "format": ext,
                    "bytes": os.path.getsize(filepath)
                }

            # Send text to Gemini for profile parsing
            parsed_data = parse_resume_for_profile(text)
        except Exception as e:
            return jsonify({"success": False, "message": f"Failed processing resume: {str(e)}"}), 500

    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM students WHERE email=%s", (email,))
                if cursor.fetchone():
                    return jsonify({"success": False, "message": "Email already registered"}), 409

                token = secrets.token_urlsafe(32)
                expiry = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)

                # Create Student
                cursor.execute(
                    """
                    INSERT INTO students
                        (name, email, phone, password_hash, email_verified, verification_token, verification_token_expiry)
                    VALUES
                        (%s, %s, %s, %s, 0, %s, %s)
                    """,
                    (name, email, phone, password_hash, token, expiry)
                )
                student_id = cursor.lastrowid
                
                if not no_resume:
                    # Insert Resume
                    cursor.execute(
                        """
                        INSERT INTO resumes (user_id, filename, cloudinary_public_id, resource_type, file_size, resume_text)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (student_id, filename, cloud_data.get('public_id', ''), ext, cloud_data.get('bytes', 0), text)
                    )

                    # Insert Builder Profile
                    cursor.execute("""
                        INSERT INTO builder_profiles (user_id, professional_summary, linkedin, github, portfolio, skills, achievements, education, experience)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        student_id,
                        parsed_data.get('professional_summary', ''),
                        parsed_data.get('linkedin', ''),
                        parsed_data.get('github', ''),
                        parsed_data.get('portfolio', ''),
                        json.dumps(parsed_data.get('skills', [])),
                        json.dumps(parsed_data.get('achievements', [])),
                        json.dumps(parsed_data.get('education', [])),
                        json.dumps(parsed_data.get('experience', []))
                    ))
                    
                    # Insert Projects
                    for p in parsed_data.get('projects', []):
                        cursor.execute("""
                            INSERT INTO user_projects (user_id, project_name, description, tech_stack, github_url, live_url)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            student_id,
                            p.get('project_name', ''),
                            p.get('description', ''),
                            p.get('tech_stack', ''),
                            p.get('github_url', ''),
                            p.get('live_url', '')
                        ))
                        
                    # Insert Certifications
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
                            student_id,
                            c.get('name', ''),
                            c.get('issuer') or None,
                            valid_date,
                            c.get('certificate_url') or None
                        ))

                connection.commit()
                cursor.execute("SELECT * FROM students WHERE id=%s", (student_id,))
                student = cursor.fetchone()
        finally:
            connection.close()

        log_activity(student["id"], "register", {"email": email})
        
        send_verification_email(email, name, token)

        return jsonify({"success": True, "redirect": "/email-verification-pending", "student": _serialize_student(student)}), 201
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "message": "Internal Server Error"}), 500


@auth_bp.post("/auth/login")
@limiter.limit("5 per 15 minutes")
def login():
    try:
        data = request.get_json(force=True)
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if not email or not password:
            return jsonify({"success": False, "message": "email and password are required"}), 400
        if not EMAIL_RE.match(email):
            return jsonify({"success": False, "message": "Invalid credentials"}), 401

        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
        delay = _login_delay_seconds(email, ip)
        if delay > 0:
            return (
                jsonify({"success": False, "message": "Too many failed attempts. Try again soon."}),
                429,
            )

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.execute(
                    "SELECT * FROM students WHERE email=%s AND is_active=TRUE", (email,)
                )
                student = cursor.fetchone()
        finally:
            connection.close()

        if not student:
            _record_login_failure(email, ip)
            return jsonify({"success": False, "message": "Invalid credentials"}), 401

        is_valid_pw = bcrypt.checkpw(password.encode("utf-8"), student["password_hash"].encode("utf-8"))

        if not is_valid_pw:
            _record_login_failure(email, ip)
            return jsonify({"success": False, "message": "Invalid credentials"}), 401

        if not student.get("email_verified"):
            return jsonify({"success": False, "message": "Your email address has not been verified.", "is_unverified": True}), 403

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE students SET last_seen=%s WHERE id=%s",
                    (datetime.utcnow(), student["id"]),
                )
            connection.commit()
        finally:
            connection.close()

        _clear_login_failures(email, ip)
        log_activity(student["id"], "login", {"ip": ip})
        
        access_token = create_access_token(identity=str(student["id"]))
        
        response = make_response(
            jsonify(
                {
                    "success": True,
                    "token": access_token,
                    "student": {
                        "id": student["id"],
                        "name": student["name"],
                        "email": student["email"],
                    },
                }
            )
        )
        response.set_cookie(
            "access_token",
            access_token,
            httponly=True,
            samesite="Lax",
            secure=current_app.config.get("JWT_COOKIE_SECURE", False),
            max_age=86400,
            path="/",
        )
        log_activity(student["id"], "login", {"ip": ip})
        return response
    except Exception as e:
        import logging
        logging.error(f"LOGIN ERROR: {str(e)}")
        # Do not expose stack traces to the user
        return jsonify({"error": "Database temporarily unavailable"}), 503


@auth_bp.get("/me")
@jwt_required()
def me():
    student_id = get_jwt_identity()

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM students WHERE id=%s", (student_id,))
            student = cursor.fetchone()
    finally:
        connection.close()

    if not student:
        return jsonify({"success": False, "message": "Student not found"}), 404

    return jsonify({"success": True, "student": _serialize_student(student)})


@auth_bp.get("/auth/logout")
def logout():
    response = make_response(redirect("/login"))
    response.delete_cookie("access_token", path="/")
    return response


@auth_bp.get("/email-verification-pending")
def verification_pending():
    return render_template("verification_pending.html")


@auth_bp.get("/email-verification-success")
def verification_success():
    return render_template("verification_success.html")


@auth_bp.get("/auth/verify-email/<token>")
def verify_email(token):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, name, email, verification_token_expiry FROM students WHERE verification_token=%s", (token,))
            student = cursor.fetchone()
            
            if not student:
                return render_template("verification_pending.html", error="Invalid verification token."), 400
                
            if student["verification_token_expiry"] and student["verification_token_expiry"] < datetime.utcnow():
                return render_template("verification_pending.html", error="Verification token has expired. Please request a new one."), 400
                
            cursor.execute(
                """
                UPDATE students 
                SET email_verified=1, verified_at=%s, verification_token=NULL, verification_token_expiry=NULL
                WHERE id=%s
                """,
                (datetime.utcnow(), student["id"])
            )
            connection.commit()
            
            # Send welcome email after successful verification
            send_welcome_email(student["email"], student["name"])
            
    except Exception as e:
        return render_template("verification_pending.html", error="An error occurred during verification. Please try again later."), 500
    finally:
        connection.close()
        
    return redirect(url_for("auth.verification_success"))


@auth_bp.post("/auth/resend-verification")
@limiter.limit("3 per hour")
def resend_verification():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    
    if not email:
        return jsonify({"success": False, "message": "Email is required"}), 400
        
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, email_verified, name FROM students WHERE email=%s", (email,))
            student = cursor.fetchone()
            
            if not student:
                return jsonify({"success": True, "message": "If the email is registered, a new verification email has been sent."})
                
            if student["email_verified"]:
                return jsonify({"success": False, "message": "Email is already verified."}), 400
                
            token = secrets.token_urlsafe(32)
            expiry = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)
            
            cursor.execute(
                "UPDATE students SET verification_token=%s, verification_token_expiry=%s WHERE id=%s",
                (token, expiry, student["id"])
            )
            connection.commit()
            
            result = send_verification_email(email, student["name"], token)
            if not result.get("success"):
                return jsonify({"success": False, "error": result.get("error", "Email delivery failed")}), 500
                
    except Exception as e:
        print(f"Error in resend verification: {e}", flush=True)
        return jsonify({"success": False, "message": "Internal server error"}), 500
    finally:
        connection.close()
        
    return jsonify({"success": True, "message": "A new verification email has been sent."})

@auth_bp.get("/forgot-password")
def forgot_password_page():
    return render_template("forgot_password.html")

@auth_bp.post("/auth/forgot-password")
@limiter.limit("3 per hour")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    
    if not email:
        return jsonify({"success": False, "message": "Email is required"}), 400
        
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, name FROM students WHERE email=%s", (email,))
            student = cursor.fetchone()
            
            if not student:
                return jsonify({"success": True, "message": "If the email is registered, a password reset link has been sent."})
                
            token = secrets.token_urlsafe(32)
            expiry = datetime.utcnow() + timedelta(hours=PASSWORD_RESET_EXPIRY_HOURS)
            
            cursor.execute(
                "UPDATE students SET reset_token=%s, reset_token_expiry=%s WHERE id=%s",
                (token, expiry, student["id"])
            )
            connection.commit()
            
            result = send_password_reset_email(email, student["name"], token)
            if not result.get("success"):
                return jsonify({"success": False, "error": result.get("error", "Email delivery failed")}), 500
                
    except Exception as e:
        print(f"Error in forgot password: {e}", flush=True)
        return jsonify({"success": False, "message": "Internal server error"}), 500
    finally:
        connection.close()
        
    return jsonify({"success": True, "message": "If the email is registered, a password reset link has been sent."})

@auth_bp.get("/auth/reset-password/<token>")
def reset_password_page(token):
    # Verify token
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, reset_token_expiry FROM students WHERE reset_token=%s", (token,))
            student = cursor.fetchone()
            
            if not student:
                return render_template("verification_pending.html", error="Invalid or expired reset token."), 400
                
            if student["reset_token_expiry"] and student["reset_token_expiry"] < datetime.utcnow():
                return render_template("verification_pending.html", error="Reset token has expired. Please request a new one."), 400
                
    finally:
        connection.close()
        
    return render_template("reset_password.html", token=token)

@auth_bp.post("/auth/reset-password/<token>")
@limiter.limit("5 per hour")
def reset_password(token):
    data = request.get_json(silent=True) or {}
    password = data.get("password")
    
    if not password:
        return jsonify({"success": False, "message": "Password is required"}), 400
        
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, reset_token_expiry FROM students WHERE reset_token=%s", (token,))
            student = cursor.fetchone()
            
            if not student or (student["reset_token_expiry"] and student["reset_token_expiry"] < datetime.utcnow()):
                return jsonify({"success": False, "message": "Invalid or expired token"}), 400
                
            password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            
            cursor.execute(
                "UPDATE students SET password_hash=%s, reset_token=NULL, reset_token_expiry=NULL WHERE id=%s",
                (password_hash, student["id"])
            )
            connection.commit()
            
    except Exception as e:
        print(f"Error in reset password: {e}", flush=True)
        return jsonify({"success": False, "message": "Internal server error"}), 500
    finally:
        connection.close()
        
    return jsonify({"success": True, "message": "Password has been successfully reset. Redirecting to login...", "redirect": "/login"})
