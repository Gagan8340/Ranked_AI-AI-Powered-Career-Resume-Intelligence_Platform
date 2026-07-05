import sys
sys.path.append('d:/smartcampus/smartcampus-ai')
from config import get_db_connection
from services.ats_engine import calculate_ats_score
import json

conn = get_db_connection()
with conn.cursor() as cursor:
    cursor.execute('SELECT r.resume_id, b.optimized_resume_text, r.resume_text FROM resumes r LEFT JOIN builder_profiles b ON r.user_id = b.user_id ORDER BY r.uploaded_at DESC LIMIT 1')
    row = cursor.fetchone()
    if row:
        text = row['optimized_resume_text'] or row['resume_text']
        result = calculate_ats_score(text)
        print('Total Score:', result['overall_score'])
        for cat in result['categories']:
            print(f"{cat['name']}: {cat['score']}/100")
            for bd in cat['breakdown']:
                try:
                    print(f"  {bd[0]}: {bd[1]}/{bd[2]} - {bd[3]}")
                except Exception:
                    pass
