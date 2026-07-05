from config import get_db_connection
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("SELECT jd_text FROM job_descriptions ORDER BY id DESC LIMIT 1")
text = cursor.fetchone()['jd_text']
conn.close()

with open("data/latest_jd.txt", "w", encoding="utf-8") as f:
    f.write(text)
