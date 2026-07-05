import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

host = os.getenv("DB_HOST")
port = int(os.getenv("DB_PORT", 3306))
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
database = os.getenv("DB_NAME")

print("--- TABLE VERIFICATION ---")

try:
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        connect_timeout=10
    )
    with conn.cursor() as cursor:
        print("Running SELECT 1...")
        cursor.execute("SELECT 1")
        print("SELECT 1: PASS")
        
        print("Running SHOW TABLES...")
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Found {len(tables)} tables: {tables}")
        
        required_tables = [
            "students",
            "resumes",
            "job_descriptions",
            "resume_versions",
            "cover_letters",
            "user_projects",
            "certifications"
        ]
        
        for rt in required_tables:
            if rt in tables:
                print(f"Table '{rt}': PASS")
            else:
                print(f"Table '{rt}': FAIL (Missing)")
                
    conn.close()
except Exception as e:
    print(f"Table verification FAIL: {e}")
