import pymysql
from app import get_db_connection

def create_intelligence_table():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS intelligence_cache (
              cache_key VARCHAR(255) PRIMARY KEY,
              user_id INT NOT NULL,
              resume_hash VARCHAR(255) NOT NULL,
              jd_hash VARCHAR(255) NOT NULL,
              readiness_score INT DEFAULT 0,
              intelligence_score INT DEFAULT 0,
              skill_gap_json JSON,
              roadmap_json JSON,
              generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (user_id) REFERENCES students(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """)
            
            # Create indexes safely (ignoring if they exist)
            try:
                cursor.execute("CREATE INDEX idx_intel_cache_user ON intelligence_cache(user_id)")
            except Exception as e:
                pass
                
            try:
                cursor.execute("CREATE INDEX idx_intel_cache_generated ON intelligence_cache(generated_at)")
            except Exception as e:
                pass
                
            print("Successfully created intelligence_cache table and indexes.")
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    create_intelligence_table()
