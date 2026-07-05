import re

def append_restore_version():
    with open('d:/smartcampus/smartcampus-ai/routes/builder_routes.py', 'a', encoding='utf-8') as f:
        f.write("""

@builder_bp.route('/api/builder/restore-version', methods=['POST'])
@jwt_required()
def restore_version():
    user_id = get_jwt_identity()
    data = request.get_json()
    version_number = data.get('version_number')
    
    if not version_number:
        return jsonify({"error": "Version number required"}), 400
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get version
            cursor.execute("SELECT version_data, optimized_resume_text FROM resume_versions WHERE user_id = %s AND version_number = %s", (user_id, version_number))
            version_rec = cursor.fetchone()
            if not version_rec:
                return jsonify({"error": "Version not found"}), 404
                
            version_data = json.loads(version_rec['version_data'])
            
            # Restore to builder_profiles
            cursor.execute(\"\"\"
                UPDATE builder_profiles 
                SET professional_summary = %s,
                    skills = %s,
                    education = %s,
                    experience = %s,
                    optimized_resume_text = %s
                WHERE user_id = %s
            \"\"\", (
                version_data.get('professional_summary', ''),
                version_data.get('skills', '[]'),
                version_data.get('education', '[]'),
                version_data.get('experience', '[]'),
                version_rec['optimized_resume_text'],
                user_id
            ))
            
            if cursor.rowcount == 0:
                # Insert instead if missing
                cursor.execute(\"\"\"
                    INSERT INTO builder_profiles (user_id, professional_summary, skills, education, experience, optimized_resume_text)
                    VALUES (%s, %s, %s, %s, %s, %s)
                \"\"\", (
                    user_id,
                    version_data.get('professional_summary', ''),
                    version_data.get('skills', '[]'),
                    version_data.get('education', '[]'),
                    version_data.get('experience', '[]'),
                    version_rec['optimized_resume_text']
                ))
                
            conn.commit()
            return jsonify({"message": "Version restored successfully"}), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
""")
        
if __name__ == '__main__':
    append_restore_version()
