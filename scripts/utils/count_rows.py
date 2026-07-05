import pymysql
from config import get_db_connection

def count_rows():
    tables = [
        "activity_logs",
        "ats_reports",
        "builder_profiles",
        "certifications",
        "cover_letters",
        "email_verifications",
        "job_descriptions",
        "notifications",
        "resume_versions",
        "resumes"
    ]
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) as c FROM {table}")
                    result = cursor.fetchone()
                    print(f"{table}: {result['c']} rows")
                except Exception as e:
                    print(f"{table}: ERROR or DOES NOT EXIST - {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    count_rows()
