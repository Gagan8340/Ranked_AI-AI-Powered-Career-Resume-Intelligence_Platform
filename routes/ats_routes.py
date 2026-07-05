import json
import logging
import time
from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity

from config import get_db_connection

ats_bp = Blueprint('ats', __name__)

@ats_bp.route('/ats-score-checker', methods=['GET'])
@jwt_required()
def ats_checker_page():
    return render_template("ats_checker.html")

@ats_bp.route('/api/ats/analyze', methods=['POST'])
@jwt_required()
def analyze_ats():
    logging.info("ATS_ROUTE_ENTERED")
    user_id = get_jwt_identity()
    data = request.json
    resume_id = data.get('resume_id')
    jd_text = data.get('jd_text', '')
    
    if not resume_id:
        return jsonify({"error": "Resume ID is required"}), 400
        
    conn = get_db_connection()
    try:
        start_time = time.time()
        with conn.cursor() as cursor:
            # Source Selection Logic
            cursor.execute("""
                SELECT 
                    r.resume_text as original_text,
                    b.optimized_resume_text as optimized_text
                FROM resumes r
                LEFT JOIN builder_profiles b ON r.user_id = b.user_id
                WHERE r.resume_id = %s AND r.user_id = %s AND r.is_active = 1
            """, (resume_id, user_id))
            resume = cursor.fetchone()
            
            if not resume:
                return jsonify({"error": "Resume not found"}), 404

            # Prioritize optimized_resume_text over original
            resume_text = resume.get('optimized_text') or resume.get('original_text')
            if not resume_text:
                return jsonify({"error": "No resume text available for analysis"}), 400

            # Hashing and caching logic
            from utils.ats_engine import generate_resume_hash, evaluate_resume
            from utils.telemetry import increment_metric, record_latency
            
            # Setup logging
            logging.basicConfig(level=logging.INFO)
            
            resume_hash = generate_resume_hash(resume_text)
            jd_hash = generate_resume_hash(jd_text) if jd_text else "NO_JD"
            
            cache_key = f"{user_id}_{resume_hash}_{jd_hash}_v15"
            
            cursor.execute("SELECT ats_result, generated_at FROM ats_cache WHERE cache_key = %s", (cache_key,))
            cache_entry = cursor.fetchone()
            
            if cache_entry:
                logging.info(f"ATS_CACHE_HIT user={user_id}")
                increment_metric("ats_cache_hits")
                record_latency("ats_analysis", int((time.time() - start_time) * 1000))
                ats_result = cache_entry['ats_result']
                if isinstance(ats_result, str):
                    ats_result = json.loads(ats_result)
                return jsonify({"analysis": ats_result}), 200
                
            logging.info(f"ATS_CACHE_MISS user={user_id}")
            increment_metric("ats_cache_misses")
                
        # Call Deterministic ATS Engine
        from services.ats_engine import analyze_resume, build_api_response
        result = analyze_resume(resume_text, jd_text if jd_text else "")
        engine_results = build_api_response(result)
        
        logging.info("ATS_SCORE_GENERATED")
        
        # Add required disclaimer
        engine_results["disclaimer"] = "This ATS Compatibility Score measures resume structure, formatting, content quality, and keyword alignment using Ranked AI's proprietary analysis engine. It is not a score from any employer, recruiter, applicant tracking system, or hiring platform, and it does not predict hiring outcomes."
        engine_results["ats_score_label"] = "ATS Compatibility Score"
        
        # Combine results for backwards compatibility with ats_checker.html
        engine_results["overall_score"] = engine_results["ats_score"]
        engine_results["weak_areas"] = engine_results["top_issues"] + engine_results["keyword_missing"]
        
        # Collect all unique feedback from components
        all_feedback = []
        for comp in engine_results.get("components", {}).values():
            for f in comp.get("feedback", []):
                if f not in all_feedback and f not in engine_results["top_issues"]:
                    all_feedback.append(f)
                    
        # Recommendations should not duplicate weak areas
        engine_results["recommendations"] = all_feedback + engine_results["parsing_warnings"]
        if not engine_results["recommendations"]:
            engine_results["recommendations"] = ["Continue tailoring your resume with role-specific keywords.", "Quantify your achievements where possible."]
            
        engine_results["missing_keywords"] = engine_results["keyword_missing"]
        engine_results["fallback_mode"] = False
        
        # Format breakdown for legacy UI
        legacy_breakdown = {}
        if "ats_formatting" in engine_results["components"]:
            legacy_breakdown["formatting"] = {"score": engine_results["components"]["ats_formatting"]["percentage"]}
        else:
            legacy_breakdown["formatting"] = {"score": 0}
            
        # Calculate Readability Score for legacy UI
        text_lower = resume_text.lower()
        import re
        pronouns = len(re.findall(r"\b(i|me|my|we|our|myself)\b", text_lower))
        pronoun_penalty = min(30, pronouns * 5)
        
        words = text_lower.split()
        word_count = len(words)
        word_count_score = 100
        if word_count < 150:
            word_count_score = 70
        elif word_count > 1000:
            word_count_score = 80
            
        from services.ats_engine import ACTION_VERBS
        verbs_found = [v for v in ACTION_VERBS if v in text_lower]
        verb_bonus = min(20, len(verbs_found) * 2)
        
        sentences = re.split(r"[.!?•\n]", resume_text)
        long_sentences = sum(1 for s in sentences if len(s.split()) > 25)
        long_sentence_penalty = min(20, long_sentences * 4)
        
        readability_score = word_count_score - pronoun_penalty - long_sentence_penalty + verb_bonus
        readability_score = max(0, min(100, readability_score))
        
        logging.info(f"RAW_READABILITY_METRICS: words={word_count}, pronouns={pronouns}(-{pronoun_penalty}), verbs={len(verbs_found)}(+{verb_bonus}), long_sentences={long_sentences}(-{long_sentence_penalty}), final={readability_score}")
        
        legacy_breakdown["readability"] = {"score": readability_score}
            
        engine_results["breakdown"] = legacy_breakdown
        engine_results["missing_skills"] = engine_results["keyword_missing"]
        engine_results["summary"] = engine_results["disclaimer"]
        
        engine_results["cache_used"] = False
        import datetime
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        engine_results["generated_at"] = current_time
        engine_results["resume_hash"] = resume_hash
        
        # Save to cache
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO ats_cache (cache_key, resume_id, user_id, resume_hash, ats_result)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE ats_result = VALUES(ats_result), generated_at = CURRENT_TIMESTAMP
            """, (cache_key, resume_id, user_id, resume_hash, json.dumps(engine_results)))
            conn.commit()
            
        from utils.ats_history_logger import log_ats_history
        log_ats_history(user_id, engine_results.get("overall_score", 0), "ATS_CHECKER", resume_id=resume_id, breakdown=engine_results.get("breakdown", {}))
        
        return jsonify({"analysis": engine_results}), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "An internal error occurred during ATS analysis."}), 500
    finally:
        conn.close()
