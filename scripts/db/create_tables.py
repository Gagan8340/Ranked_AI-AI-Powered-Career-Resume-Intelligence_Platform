from config import get_db_connection

def create_missing_tables():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Notifications
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                message TEXT NOT NULL,
                type VARCHAR(50) DEFAULT 'info',
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            )
            """)
            print("Created notifications table")
            
            # Builder Profiles
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS builder_profiles (
                user_id INT PRIMARY KEY,
                professional_summary TEXT,
                linkedin VARCHAR(255),
                github VARCHAR(255),
                portfolio VARCHAR(255),
                skills TEXT,
                achievements TEXT,
                FOREIGN KEY (user_id) REFERENCES students(id) ON DELETE CASCADE
            )
            """)
            print("Created builder_profiles table")
            
            # User Projects
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_projects (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                project_name VARCHAR(255) NOT NULL,
                description TEXT,
                tech_stack VARCHAR(255),
                github_url VARCHAR(255),
                live_url VARCHAR(255),
                FOREIGN KEY (user_id) REFERENCES students(id) ON DELETE CASCADE
            )
            """)
            print("Created user_projects table")
            
            # Certifications
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS certifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                name VARCHAR(255) NOT NULL,
                issuer VARCHAR(255),
                issue_date DATE,
                certificate_url VARCHAR(255),
                FOREIGN KEY (user_id) REFERENCES students(id) ON DELETE CASCADE
            )
            """)
            print("Created certifications table")
            
            conn.commit()
    except Exception as e:
        print(f"Error creating tables: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    create_missing_tables()
