import re

def update_generate_roadmap():
    with open('d:/smartcampus/smartcampus-ai/routes/intelligence_routes.py', 'r', encoding='utf-8') as f:
        content = f.read()

    new_func = """@intelligence_bp.route('/api/intelligence/roadmap', methods=['POST'])
@jwt_required()
def generate_roadmap():
    user_id = get_jwt_identity()
    data = request.json
    
    priority_skills = data.get("priority_skills")
    resume_id = data.get("resume_id")
    jd_id = data.get("jd_id")
    jd_text = data.get("jd_text")
    force_regenerate = data.get("force_regenerate", False)
    
    if not priority_skills or not resume_id or not jd_text or not jd_id:
        return jsonify({"error": "Missing required fields"}), 400
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Get Resume Text
            cursor.execute("SELECT resume_text FROM resumes WHERE resume_id = %s AND user_id = %s AND is_active = 1", (resume_id, user_id))
            resume = cursor.fetchone()
            if not resume:
                return jsonify({"error": "Resume not found"}), 404
                
            cursor.execute("SELECT optimized_resume_text FROM builder_profiles WHERE user_id = %s", (user_id,))
            profile = cursor.fetchone()
            
            if profile and profile.get('optimized_resume_text'):
                resume_text = profile['optimized_resume_text']
            else:
                resume_text = resume['resume_text']
                
            resume_hash = generate_resume_hash(resume_text)
            jd_hash = generate_resume_hash(jd_text)
            
            # 2. Check if a roadmap already exists for these hashes
            if not force_regenerate:
                cursor.execute(\"\"\"
                    SELECT roadmap_json FROM roadmaps 
                    WHERE user_id = %s AND jd_id = %s AND resume_hash = %s AND jd_hash = %s
                    ORDER BY id DESC LIMIT 1
                \"\"\", (user_id, jd_id, resume_hash, jd_hash))
                existing_roadmap = cursor.fetchone()
                
                if existing_roadmap and existing_roadmap.get('roadmap_json'):
                    logging.info(f"ROADMAP_DB_HIT user={user_id}")
                    return jsonify({"roadmap": json.loads(existing_roadmap['roadmap_json'])})
                    
            logging.info(f"ROADMAP_DB_MISS user={user_id}")
            
            # 3. Generate new roadmap
            from utils.ai_fallback import safe_gemini_call
            roadmap_data = safe_gemini_call(generate_learning_roadmap, priority_skills, resume_text, jd_text)
            
            if roadmap_data.get('fallback_mode'):
                return jsonify({
                    "roadmap_available": False,
                    "fallback_mode": True,
                    "message": "Roadmap generation temporarily unavailable."
                }), 200
                
            # 4. Get historical scores
            cursor.execute("SELECT ats_score FROM job_descriptions WHERE id = %s", (jd_id,))
            jd_rec = cursor.fetchone()
            ats_score = jd_rec['ats_score'] if jd_rec else 0
            
            cache_key = f"{user_id}_{resume_hash}_{jd_hash}"
            cursor.execute("SELECT intelligence_score FROM intelligence_cache WHERE cache_key = %s", (cache_key,))
            intel_rec = cursor.fetchone()
            match_score = intel_rec['intelligence_score'] if intel_rec else 0
            
            # Get max version
            cursor.execute("SELECT MAX(roadmap_version) as max_v FROM roadmaps WHERE jd_id = %s AND user_id = %s", (jd_id, user_id))
            v_rec = cursor.fetchone()
            next_version = (v_rec['max_v'] or 0) + 1
            
            # Save to roadmaps table
            cursor.execute(\"\"\"
                INSERT INTO roadmaps (user_id, jd_id, roadmap_json, ats_score, match_score, resume_hash, jd_hash, roadmap_version)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            \"\"\", (user_id, jd_id, json.dumps(roadmap_data), ats_score, match_score, resume_hash, jd_hash, next_version))
            
            # Update cache for compatibility
            cursor.execute("UPDATE intelligence_cache SET roadmap_json = %s WHERE cache_key = %s", (json.dumps(roadmap_data), cache_key))
            conn.commit()
            
            return jsonify({"roadmap": roadmap_data})
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        logging.error(f"Roadmap Error: {e}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        conn.close()"""

    content = re.sub(r"@intelligence_bp\.route\('/api/intelligence/roadmap'.*?conn\.close\(\)", new_func, content, flags=re.DOTALL)
    
    with open('d:/smartcampus/smartcampus-ai/routes/intelligence_routes.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Done")

if __name__ == '__main__':
    update_generate_roadmap()
