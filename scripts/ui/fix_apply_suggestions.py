import re

def fix_apply_suggestions():
    with open('d:/smartcampus/smartcampus-ai/routes/builder_routes.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    new_func = """@builder_bp.route('/api/builder/apply-suggestions', methods=['POST'])
@jwt_required()
def apply_suggestions():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or 'suggestions' not in data:
        return jsonify({"error": "Invalid payload"}), 400
        
    resume_id = data.get('resume_id')
    jd_id = data.get('jd_id')
    
    if not resume_id or not jd_id:
        return jsonify({"error": "resume_id and jd_id required"}), 400
        
    suggestions = data['suggestions']
    if not isinstance(suggestions, list):
        return jsonify({"error": "suggestions must be a list"}), 400
        
    conn = get_db_connection()
    try:
        from utils.ats_engine import evaluate_resume
        
        with conn.cursor() as cursor:
            # 1. Verify ownership and get old resume text
            cursor.execute("SELECT resume_text FROM resumes WHERE resume_id = %s AND user_id = %s AND is_active = 1", (resume_id, user_id))
            resume_record = cursor.fetchone()
            if not resume_record:
                return jsonify({"error": "Resume not found or unauthorized"}), 404
                
            old_resume_text = resume_record['resume_text']
            
            # Fetch jd_text for ATS scoring context
            cursor.execute("SELECT jd_text FROM job_descriptions WHERE id = %s AND user_id = %s", (jd_id, user_id))
            jd_record = cursor.fetchone()
            jd_text = jd_record['jd_text'] if jd_record else None
            
            # 2. Calculate old ATS score
            old_score_data = evaluate_resume(old_resume_text, jd_text)
            old_score = old_score_data.get('overall_score', 0)
            old_breakdown = old_score_data.get('breakdown', {})
            
            # 3. Fetch current builder profile
            cursor.execute("SELECT * FROM builder_profiles WHERE user_id = %s", (user_id,))
            profile = cursor.fetchone() or {
                "professional_summary": "",
                "skills": "[]",
                "achievements": "[]",
                "education": "[]",
                "experience": "[]"
            }
            
            def parse_json(val):
                if not val: return []
                if isinstance(val, list): return val
                try: return json.loads(val)
                except: return []
                
            current_skills = parse_json(profile.get('skills'))
            current_experience = parse_json(profile.get('experience'))
            current_education = parse_json(profile.get('education'))
            current_summary = profile.get('professional_summary') or ""
            
            # 4. Process suggestions safely
            for sug in suggestions:
                s_type = sug.get('type')
                s_val = sug.get('value', '').strip()
                if not s_val: continue
                
                if s_type == "skill":
                    continue
                        
                elif s_type == "summary":
                    if s_val not in current_summary:
                        current_summary += f"\\n\\n{s_val}"
                        
                elif s_type == "experience":
                    if s_val not in current_experience:
                        current_experience.append(s_val)
                        
            # Do NOT update builder_profiles here!
            # The builder should remain untouched until the user explicitly restores the version.
            
            # 5. Rebuild the resume text to calculate the new ATS Score
            cursor.execute("SELECT name, email FROM students WHERE id = %s", (user_id,))
            student_data = cursor.fetchone()
            
            cursor.execute("SELECT project_name, description FROM user_projects WHERE user_id = %s", (user_id,))
            projects = cursor.fetchall()
            
            text_lines = []
            if student_data:
                text_lines.append(student_data.get('name', ''))
                text_lines.append(student_data.get('email', ''))
                
            if current_summary:
                text_lines.append("SUMMARY: " + current_summary)
            if current_skills:
                text_lines.append("SKILLS: " + ", ".join(current_skills))
            if current_experience:
                text_lines.append("EXPERIENCE: " + " ".join(current_experience))
                
            for p in projects:
                text_lines.append(f"PROJECT: {p.get('project_name')} - {p.get('description')}")
                
            new_resume_text = "\\n".join(text_lines)
            
            # 6. Calculate New ATS Score
            new_score_data = evaluate_resume(new_resume_text, jd_text)
            new_score = new_score_data.get('overall_score', 0)
            new_breakdown = new_score_data.get('breakdown', {})
            
            improvement_score = new_score - old_score
            improvement_reason = []
            if new_breakdown.get('keyword', {}).get('score', 0) > old_breakdown.get('keyword', {}).get('score', 0):
                improvement_reason.append("Keyword Match Increased")
            if new_breakdown.get('experience', {}).get('score', 0) > old_breakdown.get('experience', {}).get('score', 0):
                improvement_reason.append("Experience Language Improved")
            if new_breakdown.get('section', {}).get('score', 0) > old_breakdown.get('section', {}).get('score', 0):
                improvement_reason.append("Sections Optimized")
                
            if not improvement_reason:
                improvement_reason = "No major changes in evaluated criteria"
            else:
                improvement_reason = ", ".join(improvement_reason)
            
            # 7. Save Version History
            cursor.execute("SELECT MAX(version_number) as max_v FROM resume_versions WHERE original_resume_id = %s", (resume_id,))
            v_res = cursor.fetchone()
            next_version = (v_res['max_v'] or 0) + 1
            
            # Prepare version_data with the NEW state
            version_data = {
                "professional_summary": current_summary.strip(),
                "skills": current_skills,
                "experience": current_experience,
                "education": current_education
            }
            
            cursor.execute(\"\"\"
                INSERT INTO resume_versions (user_id, original_resume_id, jd_id, version_data, optimized_resume_text, ats_improvement_score, version_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            \"\"\", (user_id, resume_id, jd_id, json.dumps(version_data, default=str), new_resume_text, improvement_score, next_version))
            
            conn.commit()
            
        return jsonify({
            "old_score": old_score,
            "new_score": new_score,
            "improvement": improvement_score,
            "before_breakdown": old_breakdown,
            "after_breakdown": new_breakdown,
            "improvement_reason": improvement_reason
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()"""

    content = re.sub(r"@builder_bp\.route\('/api/builder/apply-suggestions'.*?conn\.close\(\)", new_func, content, flags=re.DOTALL)
    
    with open('d:/smartcampus/smartcampus-ai/routes/builder_routes.py', 'w', encoding='utf-8') as f:
        f.write(content)
        
if __name__ == '__main__':
    fix_apply_suggestions()
