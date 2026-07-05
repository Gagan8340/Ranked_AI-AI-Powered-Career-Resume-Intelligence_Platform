from config import get_db_connection

connection = get_db_connection()

tables = [
    'students',
    'resumes',
    'resume_versions',
    'cover_letters',
    'job_descriptions',
    'notifications',
    'builder_profiles',
    'certifications',
    'activity_logs'
]

try:
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        all_tables = [list(row.values())[0] for row in cursor.fetchall()]
        print("ALL TABLES:", all_tables)
        print("-" * 50)
        
        for table in tables:
            if table in all_tables:
                print(f"TABLE: {table}")
                cursor.execute(f"SHOW COLUMNS FROM {table};")
                columns = cursor.fetchall()
                for col in columns:
                    print(f"  {col['Field']} - {col['Type']}")
            else:
                print(f"TABLE: {table} DOES NOT EXIST")
            print("-" * 50)
finally:
    connection.close()
