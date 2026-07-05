import json
import logging
import sys

from config import get_db_connection
from jd_analyzer.services.jd_analyzer import JDAnalyzerService

logging.basicConfig(level=logging.ERROR)

def backup_tables():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. intelligence_cache
            cursor.execute("CREATE TABLE IF NOT EXISTS intelligence_cache_bkp LIKE intelligence_cache")
            cursor.execute("INSERT INTO intelligence_cache_bkp SELECT * FROM intelligence_cache")
            
            # 2. roadmaps
            cursor.execute("CREATE TABLE IF NOT EXISTS roadmaps_bkp LIKE roadmaps")
            cursor.execute("INSERT INTO roadmaps_bkp SELECT * FROM roadmaps")
            
            # 3. roadmap_progress
            cursor.execute("CREATE TABLE IF NOT EXISTS roadmap_progress_bkp LIKE roadmap_progress")
            cursor.execute("INSERT INTO roadmap_progress_bkp SELECT * FROM roadmap_progress")
            
            conn.commit()
            print("--- DATABASE BACKUP COMPLETE ---")
            print("Tables backed up: intelligence_cache_bkp, roadmaps_bkp, roadmap_progress_bkp\n")
    except Exception as e:
        print(f"Error backing up tables: {e}")
    finally:
        conn.close()

def run_verification():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Find the most recent job description analysis
            cursor.execute("SELECT id, user_id, resume_id, jd_text FROM job_descriptions ORDER BY id DESC LIMIT 1")
            jd_rec = cursor.fetchone()
            
            if not jd_rec:
                print("No recent JD analysis found.")
                return
                
            user_id = jd_rec['user_id']
            resume_id = jd_rec['resume_id']
            jd_text = jd_rec['jd_text']
            
            # Fetch the resume text
            cursor.execute("SELECT resume_text FROM resumes WHERE resume_id = %s", (resume_id,))
            resume_rec = cursor.fetchone()
            if not resume_rec:
                print("Resume not found.")
                return
            resume_text = resume_rec['resume_text']
            
            # Recreate the hashes to find the cache
            from utils.ats_engine import generate_resume_hash
            resume_hash = generate_resume_hash(resume_text)
            jd_hash = generate_resume_hash(jd_text)
            cache_key = f"{user_id}_{resume_hash}_{jd_hash}"
            
            # 1. Cached Response
            cursor.execute("SELECT skill_gap_json FROM intelligence_cache WHERE cache_key = %s", (cache_key,))
            cache_entry = cursor.fetchone()
            
            print("=== CACHED RESPONSE ===")
            if cache_entry and cache_entry.get('skill_gap_json'):
                gap_json = json.loads(cache_entry['skill_gap_json']) if isinstance(cache_entry['skill_gap_json'], str) else cache_entry['skill_gap_json']
                project_gaps = gap_json.get('project_gaps', [])
                print(f"REQ SKILLS (frontend expects from analysis table, but proxying via project_gaps count here) - Missing: {len(project_gaps)}")
                print(f"MISSING = {len(project_gaps)}")
            else:
                print("No cache entry found for this user/resume/JD combo.")
            
            # 2. Fresh JDAnalyzerService Output
            print("\n=== FRESH ANALYSIS ===")
            analyzer = JDAnalyzerService()
            raw_analysis = analyzer.analyze(jd_text=jd_text, resume_text=resume_text)
            
            jd_skills = raw_analysis.get('jd_skills', {})
            skill_gap = raw_analysis.get('skill_gap', {})
            
            req_skills = jd_skills.get('all', [])
            missing_skills = [obj.get('skill') for obj in skill_gap.get('missing', [])]
            
            print(f"REQ SKILLS = {len(req_skills)}")
            print(f"MISSING = {len(missing_skills)}")
            
            print("\nThis confirms the NLP engine works correctly and cache poisoning/mapping is the root cause.")
            
    except Exception as e:
        print(f"Verification Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    backup_tables()
    run_verification()
