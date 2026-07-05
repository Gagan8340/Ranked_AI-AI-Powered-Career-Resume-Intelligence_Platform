import pymysql
from app import get_db_connection

conn = get_db_connection()
cursor = conn.cursor(pymysql.cursors.DictCursor)
tables = ['builder_profiles', 'user_projects', 'certifications', 'resumes', 'job_descriptions']

for t in tables:
    cursor.execute(f"SHOW CREATE TABLE {t}")
    row = cursor.fetchone()
    print(f"--- {t} ---")
    print(row['Create Table'])
    print("\n")

conn.close()
