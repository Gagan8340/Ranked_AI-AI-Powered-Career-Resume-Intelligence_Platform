import re
import time
from datetime import datetime
import os
import uuid

import bcrypt
from flask import Blueprint, current_app, jsonify, make_response, redirect, render_template, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from config import get_db_connection
from utils.extensions import limiter

recruiter_auth_bp = Blueprint("recruiter_auth", __name__)

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

@recruiter_auth_bp.get("/recruiter/login")
def login_page():
    return render_template("recruiter_login.html")

@recruiter_auth_bp.get("/recruiter/register")
def register_page():
    return render_template("recruiter_register.html")

@recruiter_auth_bp.post("/api/recruiter/auth/register")
@limiter.limit("10 per hour")
def register():
    data = request.get_json() or {}
    
    # Recruiter Info
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    
    # Company Info
    company_name = (data.get("company_name") or "").strip()
    company_website = (data.get("company_website") or "").strip()
    company_industry = (data.get("company_industry") or "").strip()
    company_description = (data.get("company_description") or "").strip()

    if not name or not email or not password or not company_name:
        return jsonify({"success": False, "message": "Name, email, password, and company name are required"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"success": False, "message": "Invalid email format"}), 400

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Check if email exists
            cursor.execute("SELECT id FROM recruiters WHERE email=%s", (email,))
            if cursor.fetchone():
                return jsonify({"success": False, "message": "Email already registered"}), 409

            # 1. Create Company
            cursor.execute(
                """
                INSERT INTO companies (name, website, industry, description)
                VALUES (%s, %s, %s, %s)
                """,
                (company_name, company_website, company_industry, company_description)
            )
            company_id = cursor.lastrowid

            # 2. Create Recruiter
            cursor.execute(
                """
                INSERT INTO recruiters (company_id, name, email, password_hash)
                VALUES (%s, %s, %s, %s)
                """,
                (company_id, name, email, password_hash)
            )
            recruiter_id = cursor.lastrowid

        connection.commit()
        return jsonify({"success": True, "message": "Recruiter registered successfully"}), 201
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e), "message": "Internal Server Error"}), 500
    finally:
        connection.close()

@recruiter_auth_bp.post("/api/recruiter/auth/login")
@limiter.limit("5 per 15 minutes")
def login():
    try:
        data = request.get_json(force=True)
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if not email or not password:
            return jsonify({"success": False, "message": "Email and password are required"}), 400

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM recruiters WHERE email=%s AND is_active=TRUE", (email,)
                )
                recruiter = cursor.fetchone()
                if recruiter:
                    cursor.execute("SELECT name FROM companies WHERE id=%s", (recruiter['company_id'],))
                    company = cursor.fetchone()
                    company_name = company['name'] if company else ''
        finally:
            connection.close()

        if not recruiter:
            return jsonify({"success": False, "message": "Invalid credentials"}), 401

        is_valid_pw = bcrypt.checkpw(password.encode("utf-8"), recruiter["password_hash"].encode("utf-8"))

        if not is_valid_pw:
            return jsonify({"success": False, "message": "Invalid credentials"}), 401

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE recruiters SET last_seen=%s WHERE id=%s",
                    (datetime.utcnow(), recruiter["id"]),
                )
            connection.commit()
        finally:
            connection.close()

        # Create JWT with custom claims
        access_token = create_access_token(
            identity=str(recruiter["id"]),
            additional_claims={"role": "recruiter", "company_id": recruiter["company_id"]}
        )
        
        response = make_response(
            jsonify(
                {
                    "success": True,
                    "token": access_token,
                    "recruiter": {
                        "id": recruiter["id"],
                        "name": recruiter["name"],
                        "email": recruiter["email"],
                        "company_id": recruiter["company_id"],
                        "company_name": company_name
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
        return response
    except Exception as e:
        import logging
        logging.error(f"RECRUITER LOGIN ERROR: {str(e)}")
        return jsonify({"error": "Database temporarily unavailable"}), 503
