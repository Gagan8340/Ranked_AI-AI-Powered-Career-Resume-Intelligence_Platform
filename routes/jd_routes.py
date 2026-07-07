import json
from flask import Blueprint, jsonify, request, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity

from config import get_db_connection
from utils.extensions import limiter
from utils.gemini_helper import analyze_jd_match

jd_bp = Blueprint('jd', __name__)

# Global instances for memory optimization
_JD_ANALYZER_SERVICE = None
_RECOMMENDATION_ENGINE = None

def get_jd_analyzer_service():
    global _JD_ANALYZER_SERVICE
    if _JD_ANALYZER_SERVICE is None:
        from jd_analyzer.services.jd_analyzer import JDAnalyzerService
        _JD_ANALYZER_SERVICE = JDAnalyzerService()
    return _JD_ANALYZER_SERVICE

def get_recommendation_engine():
    global _RECOMMENDATION_ENGINE
    if _RECOMMENDATION_ENGINE is None:
        from jd_analyzer.services.recommendation_engine import RecommendationEngine
        _RECOMMENDATION_ENGINE = RecommendationEngine()
    return _RECOMMENDATION_ENGINE


@jd_bp.route('/jd-analyzer', methods=['GET'])
@jwt_required()
def jd_analyzer_page():
    """Renders the Job Description Analyzer UI"""
    return render_template("jd_analyzer.html")

@jd_bp.route('/api/jd/analyze', methods=['POST'])
@jwt_required()
@limiter.limit("20 per hour")
def analyze_jd():
    """
    Analyzes a JD against a specific user resume securely using Gemini.
    """
    import time
    import logging
    import traceback
    from utils.telemetry import record_latency
    logger = logging.getLogger(__name__)
    
    logger.info("[JD] Request received")
    start_time = time.time()
    
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Invalid payload"}), 400
        
    resume_id = data.get('resume_id')
    jd_text = data.get('jd_text', '').strip()
    
    if not resume_id:
        return jsonify({"error": "Resume ID is required"}), 400
        
    if len(jd_text) < 50:
        return jsonify({"error": "Job description must be at least 50 characters."}), 400
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Verify Ownership & Fetch Resume Text securely
            cursor.execute("SELECT resume_text FROM resumes WHERE resume_id = %s AND user_id = %s AND is_active = 1", (resume_id, user_id))
            resume = cursor.fetchone()
            
            if not resume:
                return jsonify({"error": "Resume not found or unauthorized."}), 404
                
            # Phase 3.1: Fallback to optimized_resume_text if it exists
            cursor.execute("SELECT optimized_resume_text FROM builder_profiles WHERE user_id = %s", (user_id,))
            profile = cursor.fetchone()
            
            if profile and profile.get('optimized_resume_text'):
                resume_text = profile['optimized_resume_text']
            else:
                resume_text = resume['resume_text']
            
        try:
            logger.info("[JD] Creating JDAnalyzerService")
            analyzer = get_jd_analyzer_service()
            logger.info("[JD] JDAnalyzerService created")
            
            logger.info("[JD] Parsing JD text")
            raw_analysis = analyzer.analyze(jd_text=jd_text, resume_text=resume_text)
        except Exception as e:
            logger.error(f"[JD] Error in JDAnalyzerService.analyze: {e}")
            logger.error(traceback.format_exc())
            raise
            
        if not raw_analysis.get('valid_jd', True):
            return jsonify({
                "valid_jd": False,
                "confidence": raw_analysis.get('validation_confidence', 0),
                "message": raw_analysis.get('message', "This does not appear to be a valid Job Description.")
            }), 200
            
        # Extract variables from new service output
        scores = raw_analysis.get('scores', {})
        semantic = raw_analysis.get('semantic', {})
        skill_gap = raw_analysis.get('skill_gap', {})
        jd_skills = raw_analysis.get('jd_skills', {})
        
        # Get variables
        job_title = raw_analysis.get('jd_entities', {}).get('job_title', 'Target Role')
        company = raw_analysis.get('jd_entities', {}).get('company', 'Target Company')
        
        missing_skills_objects = skill_gap.get('missing', [])
        missing_skills = [obj.get('skill') for obj in missing_skills_objects] if missing_skills_objects else []
        jd_required = jd_skills.get('all', [])
        
        try:
            import time
            logger.info("[JD] About to generate roadmap")
            t0_road = time.perf_counter()
            engine = get_recommendation_engine()
            
            project_recs = engine.generate_project_recommendations(job_title, missing_skills, jd_required)
            interview_prep = engine.generate_interview_prep(missing_skills, jd_required)
            experience_recs = engine.generate_experience_improvements(job_title, missing_skills)
            logger.info(f"[JD] Roadmap generated in {time.perf_counter() - t0_road:.2f} sec")
        except Exception as e:
            logger.error(f"[JD] Error in Roadmap generation: {e}")
            logger.error(traceback.format_exc())
            raise
        
        logger.info("[JD] Response serialization started")
        analysis_data = {
            "job_title": job_title,
            "company": company,
            "ats_score": scores.get('overall_score', 0),
            "jd_required_skills": jd_required,
            "missing_skills": missing_skills,
            "missing_keywords": missing_skills,
            "interview_topics": interview_prep,
            "project_gaps": project_recs,
            "experience_improvements": experience_recs.get("recommendations", []),
            "summary_improvements": experience_recs.get("missing_evidence", []),
            "_raw_jd_analysis": raw_analysis
        }
        try:
            # 3. Save to Job Descriptions Table
            title = analysis_data.get('job_title', 'Target Role')
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO job_descriptions 
                    (user_id, resume_id, title, jd_text, ats_score, analysis_json)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user_id, resume_id, title, jd_text, analysis_data.get('ats_score', 0), json.dumps(analysis_data)))
                jd_id = cursor.lastrowid
                
                # Populate company_profiles automatically
                if company and company != "Not specified" and company != "Target Company":
                    try:
                        cursor.execute("""
                            INSERT INTO company_profiles (company_name, known_skills)
                            VALUES (%s, %s)
                            ON DUPLICATE KEY UPDATE known_skills = JSON_ARRAY_APPEND(COALESCE(known_skills, JSON_ARRAY()), '$', %s)
                        """, (company, json.dumps(jd_required[:5]), jd_required[0] if jd_required else ""))
                    except Exception as e:
                        pass # Ignore if duplicate key logic fails
                        
                # Store evidence for missing skills
                for missing in missing_skills:
                    try:
                        cursor.execute("""
                            INSERT INTO skill_evidence (analysis_id, skill_name, evidence_type, evidence_text)
                            VALUES (%s, %s, 'resume_missing', %s)
                        """, (jd_id, missing, f"Missing {missing} in resume for {job_title} role at {company}"))
                    except Exception:
                        pass
                
                # Also store learning resources
                for prep in interview_prep:
                    skill_cat = prep.get('category', '')
                    for vid in prep.get('videos', []):
                        try:
                            cursor.execute("""
                                INSERT INTO learning_resources (skill_name, resource_type, title, url, provider, difficulty)
                                VALUES (%s, 'youtube', %s, %s, %s, 'Intermediate')
                            """, (skill_cat, vid.get('title'), vid.get('url'), vid.get('channel')))
                        except Exception:
                            pass
                            
                # Store recommendation_cache
                try:
                    cursor.execute("INSERT INTO recommendation_cache (user_id, analysis_id, recommendation_type, recommendation_json) VALUES (%s, %s, 'project', %s)", (user_id, jd_id, json.dumps(project_recs)))
                    cursor.execute("INSERT INTO recommendation_cache (user_id, analysis_id, recommendation_type, recommendation_json) VALUES (%s, %s, 'interview', %s)", (user_id, jd_id, json.dumps(interview_prep)))
                    cursor.execute("INSERT INTO recommendation_cache (user_id, analysis_id, recommendation_type, recommendation_json) VALUES (%s, %s, 'experience', %s)", (user_id, jd_id, json.dumps(experience_recs)))
                except Exception:
                    pass
                            
            conn.commit()    
            # 4. Add Notification
            with conn.cursor() as cursor:
                ats_score = analysis_data.get('ats_score') or 0
                missing_keywords = analysis_data.get('missing_keywords') or []
                missing = len(missing_keywords)
                cursor.execute(
                    """
                    INSERT INTO notifications (student_id, message, type)
                    VALUES (%s, %s, %s)
                    """,
                    (user_id, f"JD Analysis completed for {title}. ATS Score: {ats_score}. Missing keywords: {missing}.", "info")
                )

            conn.commit()
            
        except Exception as e:
            logger.error(f"[JD] Error in Response serialization/DB insertion: {e}")
            logger.error(traceback.format_exc())
            raise
            
        # No ATS history logging for JD Analyzer
        from utils.activity_logger import log_activity
        log_activity(user_id, "JD Analysis", {"ats_score": analysis_data.get('ats_score')})
        
        record_latency("jd_analysis", int((time.time() - start_time) * 1000))
        return jsonify({"analysis": analysis_data, "jd_id": jd_id}), 200
        
    except ValueError as ve:
        # Expected error from JSON Parsing or Gemini Helper failures
        return jsonify({"error": str(ve)}), 500
    except Exception:
        # Fallback to prevent raw crashes on unknown failures
        return jsonify({"error": "An internal error occurred during analysis."}), 500
    finally:
        conn.close()

@jd_bp.route('/api/jd/list', methods=['GET'])
@jwt_required()
def list_jds():
    """
    Fetches the user's saved Job Descriptions.
    """
    user_id = get_jwt_identity()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get latest 15 saved JDs for the user
            cursor.execute("""
                SELECT id, title, jd_text, created_at 
                FROM job_descriptions 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT 15
            """, (user_id,))
            jds = cursor.fetchall()
            
            return jsonify({
                "jds": jds
            }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
