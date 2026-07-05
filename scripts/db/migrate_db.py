import pymysql
from config import get_db_connection

def migrate():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Add columns to resume_versions
            try:
                cursor.execute("ALTER TABLE resume_versions ADD COLUMN optimized_resume_text LONGTEXT;")
            except Exception as e:
                print(f"Skipping optimized_resume_text: {e}")
                
            try:
                cursor.execute("ALTER TABLE resume_versions ADD COLUMN version_number INT NOT NULL DEFAULT 1;")
            except Exception as e:
                print(f"Skipping version_number: {e}")
                
            # Create roadmaps table
            cursor.execute("""
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
            """)
        conn.commit()
        print("Migration successful")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
