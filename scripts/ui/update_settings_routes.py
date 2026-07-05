import re

def update_settings_routes():
    with open('d:/smartcampus/smartcampus-ai/routes/settings_routes.py', 'r', encoding='utf-8') as f:
        content = f.read()

    new_query = """            # Fetch projects
            cursor.execute("SELECT * FROM user_projects WHERE user_id=%s", (student_id,))
            user_projects = cursor.fetchall()
            
            # Fetch certifications
            cursor.execute("SELECT * FROM certifications WHERE user_id=%s", (student_id,))
            user_certs = cursor.fetchall()

            # Fetch Resume Versions
            cursor.execute("SELECT * FROM resume_versions WHERE user_id=%s ORDER BY version_number DESC", (student_id,))
            resume_versions = cursor.fetchall()
            
            # Fetch Roadmaps
            cursor.execute("SELECT * FROM roadmaps WHERE user_id=%s ORDER BY id DESC", (student_id,))
            roadmaps = cursor.fetchall()

    finally:
        connection.close()

    return render_template(
        "settings.html", 
        active_page="settings", 
        page_title="My Profile",
        student=student,
        builder_profile=builder_profile,
        user_projects=user_projects,
        user_certs=user_certs,
        has_resume=has_resume,
        profile_strength=profile_strength,
        total_profile_strength=total_profile_strength,
        resume_versions=resume_versions,
        roadmaps=roadmaps
    )"""

    # We need to replace the last part of settings_page
    content = re.sub(r'            # Fetch projects.*?    \)', new_query, content, flags=re.DOTALL)

    with open('d:/smartcampus/smartcampus-ai/routes/settings_routes.py', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Done")

if __name__ == '__main__':
    update_settings_routes()
