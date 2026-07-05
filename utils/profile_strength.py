import json
from config import get_db_connection

def calculate_profile_strength(user_id):
    """
    Calculates the profile strength based on a weighted scoring model.
    Returns: { "total_score": int, "missing_items": list, "categories": dict }
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Fetch Student Details
            cursor.execute("SELECT name, email, phone FROM students WHERE id = %s", (user_id,))
            student = cursor.fetchone() or {}

            # 2. Fetch Builder Profile
            cursor.execute("SELECT linkedin, github, portfolio, education, skills, experience FROM builder_profiles WHERE user_id = %s", (user_id,))
            bp = cursor.fetchone() or {}

            # 3. Fetch active resumes
            cursor.execute("SELECT 1 FROM resumes WHERE user_id = %s AND is_active = 1 LIMIT 1", (user_id,))
            has_resume = cursor.fetchone() is not None

            # 4. Fetch Projects
            cursor.execute("SELECT 1 FROM user_projects WHERE user_id = %s LIMIT 1", (user_id,))
            has_project = cursor.fetchone() is not None

            # 5. Fetch Certifications
            cursor.execute("SELECT 1 FROM certifications WHERE user_id = %s LIMIT 1", (user_id,))
            has_cert = cursor.fetchone() is not None

        # --- Evaluate Fields ---
        def is_valid_str(val):
            return val is not None and isinstance(val, str) and len(val.strip()) > 2
            
        def is_valid_json_list(val):
            if not val: return False
            if isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    return isinstance(parsed, list) and len(parsed) > 0
                except:
                    return False
            if isinstance(val, list):
                return len(val) > 0
            return False

        # Personal Details
        has_name = is_valid_str(student.get('name'))
        has_email = is_valid_str(student.get('email'))
        has_phone = student.get('phone') is not None and str(student.get('phone')).strip() != ""

        # Professional Links
        has_linkedin = is_valid_str(bp.get('linkedin'))
        has_github = is_valid_str(bp.get('github'))
        has_portfolio = is_valid_str(bp.get('portfolio'))

        # Academic Profile
        has_education = is_valid_json_list(bp.get('education'))
        has_skills = is_valid_json_list(bp.get('skills'))

        # Career Readiness
        has_experience = is_valid_json_list(bp.get('experience'))

        # --- Calculate Weighted Score ---
        total_score = 0
        missing_items = []
        
        categories = {
            "Personal Details": {"Name": has_name, "Email": has_email, "Phone": has_phone},
            "Professional Links": {"LinkedIn": has_linkedin, "GitHub": has_github, "Portfolio": has_portfolio},
            "Academic Profile": {"Education": has_education, "Skills": has_skills, "Certifications": has_cert},
            "Career Readiness": {"Resume": has_resume, "Projects": has_project, "Experience": has_experience}
        }

        # Personal Details (20%) - Redistributed 5% from location
        if has_name: total_score += 7
        else: missing_items.append("Name")
        
        if has_email: total_score += 7
        else: missing_items.append("Email")
        
        if has_phone: total_score += 6
        else: missing_items.append("Phone")

        # Professional Links (15%)
        if has_linkedin: total_score += 5
        else: missing_items.append("LinkedIn")
        
        if has_github: total_score += 5
        else: missing_items.append("GitHub Profile")
        
        if has_portfolio: total_score += 5
        else: missing_items.append("Portfolio URL")

        # Academic Profile (25%)
        if has_education: total_score += 10
        else: missing_items.append("Education")
        
        if has_skills: total_score += 10
        else: missing_items.append("Skills")
        
        if has_cert: total_score += 5
        else: missing_items.append("Certifications")

        # Career Readiness (40%)
        if has_resume: total_score += 15
        else: missing_items.append("Active Resume")
        
        if has_project: total_score += 10
        else: missing_items.append("Projects")
        
        if has_experience: total_score += 15
        else: missing_items.append("Experience")

        return {
            "total_score": total_score,
            "missing_items": missing_items,
            "categories": categories
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "total_score": 0,
            "missing_items": [],
            "categories": {}
        }
    finally:
        conn.close()
