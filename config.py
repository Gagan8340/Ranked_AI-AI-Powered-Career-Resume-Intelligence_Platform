import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv
from pymysql.cursors import DictCursor

_dotenv_path = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=_dotenv_path, override=False)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "ai_career_platform")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_TOKEN_LOCATION = ["headers", "cookies"]
JWT_COOKIE_SECURE = False
JWT_COOKIE_CSRF_PROTECT = False
JWT_COOKIE_NAME = "access_token"
JWT_HEADER_NAME = "Authorization"
JWT_HEADER_TYPE = "Bearer"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:5000").split(",")
    if origin.strip()
]
FORCE_HTTPS = os.getenv("FORCE_HTTPS", "false").lower() in {"1", "true", "yes"}
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "static/uploads")
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(5 * 1024 * 1024)))
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:5000")
EMAIL_FROM = os.getenv("EMAIL_FROM", "ranked1ai@gmail.com")
TOKEN_EXPIRY_HOURS = int(os.getenv("TOKEN_EXPIRY_HOURS", "24"))
PASSWORD_RESET_EXPIRY_HOURS = int(os.getenv("PASSWORD_RESET_EXPIRY_HOURS", "1"))

MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_USERNAME = os.getenv("MAIL_USERNAME", "ranked1ai@gmail.com")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() in ("true", "1", "t", "yes")

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS students (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        phone VARCHAR(15),
        password_hash VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen TIMESTAMP NULL,
        is_active BOOLEAN DEFAULT TRUE
    );
    """,

    """
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        action VARCHAR(80) NOT NULL,
        metadata JSON NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES students(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS resumes (
        resume_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        filename VARCHAR(255) NOT NULL,
        cloudinary_public_id VARCHAR(255) NOT NULL,
        resource_type ENUM('pdf', 'docx') NOT NULL,
        file_size INT,
        resume_text LONGTEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NULL,
        is_active BOOLEAN DEFAULT TRUE,
        FOREIGN KEY (user_id) REFERENCES students(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS job_descriptions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        resume_id INT NOT NULL,
        title VARCHAR(255),
        jd_text LONGTEXT NOT NULL,
        ats_score INT,
        analysis_json JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES students(id),
        FOREIGN KEY (resume_id) REFERENCES resumes(resume_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS resume_versions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        original_resume_id INT NOT NULL,
        jd_id INT NOT NULL,
        version_data JSON NOT NULL,
        optimized_resume_text LONGTEXT,
        ats_improvement_score INT DEFAULT 0,
        version_number INT NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES students(id),
        FOREIGN KEY (original_resume_id) REFERENCES resumes(resume_id),
        FOREIGN KEY (jd_id) REFERENCES job_descriptions(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS roadmaps (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        jd_id INT NOT NULL,
        company_name VARCHAR(255),
        job_title VARCHAR(255),
        roadmap_json JSON,
        status VARCHAR(50) DEFAULT 'active',
        roadmap_version INT DEFAULT 1,
        ats_score INT,
        match_score INT,
        resume_hash VARCHAR(64),
        jd_hash VARCHAR(64),
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES students(id),
        FOREIGN KEY (jd_id) REFERENCES job_descriptions(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS builder_profiles (
        user_id INT PRIMARY KEY,
        professional_summary TEXT,
        linkedin VARCHAR(255),
        github VARCHAR(255),
        portfolio VARCHAR(255),
        skills JSON,
        achievements JSON,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES students(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS user_projects (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        project_name VARCHAR(255) NOT NULL,
        description TEXT,
        tech_stack VARCHAR(255),
        github_url VARCHAR(255),
        live_url VARCHAR(255),
        FOREIGN KEY (user_id) REFERENCES students(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS certifications (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        name VARCHAR(255) NOT NULL,
        issuer VARCHAR(255),
        issue_date VARCHAR(50),
        certificate_url VARCHAR(255),
        FOREIGN KEY (user_id) REFERENCES students(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS cover_letters (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        resume_id INT NOT NULL,
        jd_id INT NOT NULL,
        role_title VARCHAR(255) NOT NULL,
        company_name VARCHAR(255) NOT NULL,
        content LONGTEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES students(id),
        FOREIGN KEY (resume_id) REFERENCES resumes(resume_id),
        FOREIGN KEY (jd_id) REFERENCES job_descriptions(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS notifications (
        id INT AUTO_INCREMENT PRIMARY KEY,
        student_id INT NOT NULL,
        message TEXT NOT NULL,
        type VARCHAR(50) DEFAULT 'info',
        is_read BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    );
    """
]


import time
import logging

def get_db_connection():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return pymysql.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                cursorclass=DictCursor,
                autocommit=False,
                charset="utf8mb4",
                connect_timeout=10,
                read_timeout=10,
                write_timeout=10
            )
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                logging.error(f"Database connection failed after {max_retries} attempts: {e}")
                raise e

def init_db():
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                for statement in SCHEMA_STATEMENTS:
                    cursor.execute(statement)
            connection.commit()
        finally:
            connection.close()
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        # Never crash startup
        pass
