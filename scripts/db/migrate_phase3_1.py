import pymysql
from app import get_db_connection

def migrate():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Add column if not exists
            try:
                cursor.execute("ALTER TABLE builder_profiles ADD COLUMN optimized_resume_text LONGTEXT DEFAULT NULL")
                print("Column 'optimized_resume_text' added to builder_profiles.")
            except pymysql.err.OperationalError as e:
                if e.args[0] == 1060: # Duplicate column name
                    print("Column 'optimized_resume_text' already exists.")
                else:
                    raise e
                    
            # 2. Migrate existing overwritten resumes
            # We will just copy the latest active resume text to the builder_profile if it's currently null
            cursor.execute("""
                UPDATE builder_profiles bp
                JOIN (
                    SELECT user_id, resume_text 
                    FROM resumes 
                    WHERE is_active = 1
                ) r ON bp.user_id = r.user_id
                SET bp.optimized_resume_text = r.resume_text
                WHERE bp.optimized_resume_text IS NULL
            """)
            print(f"Migrated {cursor.rowcount} profiles with existing resume text.")
            
        conn.commit()
    except Exception as e:
        print(f"Migration Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
